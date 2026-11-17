"""Fila de publicacao: agendamento por horario, retry com backoff, um job por clipe."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline.util import log

from .db import DB
from . import publish_youtube as yt

_lock = threading.Lock()


# -- utilidades -------------------------------------------------------
def _data(cfg: Any) -> dict[str, Any]:
    """Aceita Config ou dict — o resto do sistema passa os dois."""
    return getattr(cfg, "data", cfg) or {}


def should_auto_publish(cfg: dict[str, Any], score: float) -> tuple[bool, float]:
    """Termometro: publica sozinho apenas se a nota passar do limiar."""
    cfg = _data(cfg)
    pub = cfg.get("publish") or {}
    if not pub.get("auto"):
        return False, 0.0
    limit = float(pub.get("auto_min_score") or 0.0)
    return float(score) >= limit, limit


def next_slot(cfg: dict[str, Any], now: float | None = None) -> float | None:
    """Proximo horario de pico configurado. None = publicar na hora."""
    cfg = _data(cfg)
    hours = (cfg.get("publish") or {}).get("schedule_hours") or []
    hours = sorted({int(h) for h in hours if 0 <= int(h) <= 23})
    if not hours:
        return None
    now = now or time.time()
    base = datetime.fromtimestamp(now)
    for hour in hours:
        candidate = base.replace(hour=hour, minute=0, second=0, microsecond=0)
        ts = candidate.timestamp()
        if ts > now + 90:
            return ts
    # nenhum sobrou hoje: primeiro horario de amanha
    from datetime import timedelta

    tomorrow = (base + timedelta(days=1)).replace(
        hour=hours[0], minute=0, second=0, microsecond=0
    )
    return tomorrow.timestamp()


def build_metadata(cfg: dict[str, Any], row: Any) -> dict[str, Any]:
    cfg = _data(cfg)
    pub = cfg.get("publish") or {}
    footer = pub.get("description_footer") or ""
    handle = (cfg.get("branding") or {}).get("handle") or ""

    title = (row["title"] or "Corte").strip()
    if handle and handle.lower() not in title.lower():
        title = title[:90]

    caption = (row["caption"] or "").strip()
    tags_line = (row["hashtags"] or "").strip()
    parts = [p for p in (caption, tags_line, footer) if p]
    description = "\n\n".join(parts)

    tags = [t.lstrip("#") for t in tags_line.replace(",", " ").split() if t.startswith("#")]
    return {
        "title": title[:100],
        "description": description[:5000],
        "tags": tags,
        "privacy": str(pub.get("privacy") or "unlisted"),
        "category_id": str(pub.get("category_id") or "20"),
    }


def _mark(db: DB, clip_id: int, state: dict[str, Any], status: str | None = None) -> None:
    fields: dict[str, Any] = {"published": state}
    if status:
        fields["status"] = status
    db.update_clip(clip_id, **fields)


# -- fila -------------------------------------------------------------
def enqueue(
    db: DB, cfg: dict[str, Any], clip_id: int, privacy: str | None = None
) -> dict[str, Any]:
    row = db.clip(clip_id)
    if not row:
        raise ValueError("clipe nao existe")
    if not Path(row["path"] or "").exists():
        raise ValueError(f"arquivo do clipe sumiu: {row['path']}")

    pub = _data(cfg).get("publish") or {}
    at = next_slot(cfg)
    job_id = db.enqueue_publish(clip_id, privacy or pub.get("privacy"), at)
    state = {
        "state": "queued",
        "job": job_id,
        "scheduled_for": at,
        "at": time.time(),
    }
    _mark(db, clip_id, state)
    log(
        "[publish] clipe %s na fila%s" % (
            clip_id,
            f", agendado para {datetime.fromtimestamp(at):%d/%m %H:%M}" if at else "",
        )
    )
    return state


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def run_queue(db: DB, cfg: dict[str, Any], limit: int = 3) -> list[dict[str, Any]]:
    """Processa jobs vencidos. Chamado pelo supervisor e pelo CLI."""
    cfg = _data(cfg)
    pub = cfg.get("publish") or {}
    max_attempts = int(pub.get("max_attempts") or 5)
    retry_base = float(pub.get("retry_minutes") or 5)
    results: list[dict[str, Any]] = []

    with _lock:
        jobs = db.due_publish_jobs(limit)

    for job in jobs:
        if not db.claim_job(job["id"]):
            continue
        row = db.clip(job["clip_id"])
        if not row:
            db.finish_job(job["id"], "failed", "clipe nao existe")
            continue

        path = Path(row["path"] or "")
        if not path.exists():
            db.finish_job(job["id"], "failed", "arquivo sumiu")
            _mark(db, row["id"], {"state": "error", "error": "arquivo sumiu"})
            continue

        meta = build_metadata(cfg, row)
        if job["privacy"]:
            meta["privacy"] = job["privacy"]

        publish_at = None
        if job["publish_at"] and job["publish_at"] > time.time() + 90:
            # YouTube exige private + publishAt agendado
            publish_at = _iso(job["publish_at"])
            meta["privacy"] = "private"

        _mark(db, row["id"], {"state": "uploading", "at": time.time()})

        def progress(pct: float, clip_id: int = row["id"]) -> None:
            _mark(db, clip_id, {"state": "uploading", "progress": round(pct, 3), "at": time.time()})

        try:
            result = yt.upload(
                path,
                title=meta["title"],
                description=meta["description"],
                tags=meta["tags"],
                privacy=meta["privacy"],
                category_id=meta["category_id"],
                publish_at=publish_at,
                progress=progress,
            )
        except Exception as exc:
            attempts = int(job["attempts"]) + 1
            msg = str(exc)
            if attempts >= max_attempts:
                db.finish_job(job["id"], "failed", msg)
                _mark(db, row["id"], {"state": "error", "error": msg, "at": time.time()})
                log(f"[publish] clipe {row['id']} desistiu apos {attempts} tentativas: {msg}")
            else:
                wait = retry_base * (2 ** (attempts - 1)) * 60
                db.finish_job(job["id"], "queued", msg, next_try=time.time() + wait)
                _mark(db, row["id"], {
                    "state": "queued", "error": msg,
                    "retry_in_min": round(wait / 60), "attempts": attempts, "at": time.time(),
                })
                log(f"[publish] clipe {row['id']} falhou, nova tentativa em {wait/60:.0f} min")
            results.append({"clip": row["id"], "ok": False, "error": msg})
            continue

        db.finish_job(job["id"], "done")
        state = {"state": "done", "at": time.time(), "scheduled_for": job["publish_at"], **result}
        _mark(db, row["id"], state, status="published")
        log(f"[publish] ok: {result['url']}")
        results.append({"clip": row["id"], "ok": True, "url": result["url"]})

    return results


# -- compatibilidade --------------------------------------------------
def publish_clip(
    db: DB, cfg: dict[str, Any], clip_id: int, privacy: str | None = None,
    background: bool = True,
) -> dict[str, Any]:
    """Enfileira; com background=False processa na hora (CLI)."""
    state = enqueue(db, cfg, clip_id, privacy)
    if not background:
        with _lock:
            pass
        run_queue(db, cfg, limit=1)
        row = db.clip(clip_id)
        if row and row["published"]:
            import json as _json

            try:
                return _json.loads(row["published"])
            except Exception:
                pass
    return state
