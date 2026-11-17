"""Estado do sistema para o painel web: lido de arquivos + SQLite, sem tocar nos workers."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .db import DB
from .ring import SEGMENT_SECONDS
from . import publish_youtube as yt


def _ring_info(work: Path) -> dict[str, Any]:
    ring = work / "ring"
    if not ring.is_dir():
        return {"buffer_s": 0.0, "files": 0, "age_s": None, "live": False, "newest": None}
    segs = sorted(ring.glob("seg_*.ts"), key=lambda p: p.name)
    if not segs:
        return {"buffer_s": 0.0, "files": 0, "age_s": None, "live": False, "newest": None}
    newest = segs[-1].stat().st_mtime
    age = time.time() - newest
    return {
        "buffer_s": round(len(segs) * SEGMENT_SECONDS, 1),
        "files": len(segs),
        "age_s": round(age, 1),
        "live": age < 45,
        "newest": round(newest, 1),
    }


def _facecam(work: Path) -> dict[str, Any] | None:
    p = work / "facecam.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _chat_state(work: Path) -> dict[str, Any] | None:
    p = work / "chat.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _clip_row(row: Any, db: DB) -> dict[str, Any]:
    meta: dict[str, Any] = {}
    try:
        meta = json.loads(row["meta"]) if row["meta"] else {}
    except Exception:
        pass
    published: dict[str, Any] | None = None
    try:
        published = json.loads(row["published"]) if row["published"] else None
    except Exception:
        published = None
    path = Path(row["path"]) if row["path"] else None
    has_file = bool(path and path.exists())
    return {
        "id": row["id"],
        "score": row["score"],
        "title": row["title"],
        "hook": row["hook"],
        "caption": row["caption"],
        "hashtags": row["hashtags"],
        "layout": meta.get("layout") or "game",
        "created_at": row["created_at"],
        "when": time.strftime("%H:%M:%S", time.localtime(row["created_at"])),
        "video_url": f"/media/{row['id']}.mp4" if has_file else None,
        "thumb_url": f"/media/{row['id']}.jpg",
        "has_thumb": bool(path and path.with_suffix(".jpg").exists()),
        "size_mb": round(path.stat().st_size / 1e6, 1) if has_file else 0,
        "feedback": row["feedback"],
        "published": published,
    }


def snapshot(cfg: Any, db: DB) -> dict[str, Any]:
    streams = []
    for row in db.streams(None):
        work = cfg.work_dir / row["slug"]
        info = _ring_info(work)
        clip_rows = db.conn().execute(
            "SELECT COUNT(*) AS n FROM clips WHERE stream_id=?", (row["id"],)
        ).fetchone()
        last = db.conn().execute(
            "SELECT score, created_at FROM clips WHERE stream_id=? "
            "ORDER BY created_at DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
        streams.append(
            {
                "slug": row["slug"],
                "platform": row["platform"],
                "title": row["title"],
                "status": row["status"],
                "url": row["url"],
                **info,
                "buffer_pct": round(
                    min(100.0, info["buffer_s"] / max(1, cfg["live"]["buffer_seconds"]) * 100),
                    1,
                ),
                "facecam": _facecam(work),
                "chat": _chat_state(work),
                "clips": int(clip_rows["n"]) if clip_rows else 0,
                "last_score": last["score"] if last else None,
                "last_clip_at": last["created_at"] if last else None,
                "preview_url": f"/preview/{row['slug']}.mp4",
                "preview_at": info["newest"],
            }
        )

    clips = [_clip_row(r, db) for r in db.clips(limit=40)]

    logs = []
    for r in db.conn().execute(
        "SELECT ts, slug, level, msg FROM log ORDER BY id DESC LIMIT 60"
    ):
        logs.append(
            {
                "time": time.strftime("%H:%M:%S", time.localtime(r["ts"])),
                "slug": r["slug"],
                "level": r["level"],
                "msg": r["msg"],
            }
        )

    candidates = [
        {
            "time": time.strftime("%H:%M:%S", time.localtime(r["ts"])),
            "slug": r["slug"],
            "msg": r["msg"],
        }
        for r in db.conn().execute(
            "SELECT ts, slug, msg FROM log WHERE msg LIKE 'candidato%' "
            "ORDER BY id DESC LIMIT 40"
        )
    ]

    return {
        "now": time.time(),
        "streams": streams,
        "clips": clips,
        "logs": logs,
        "candidates": candidates,
        "feedback": db.feedback_stats(),
        "publish": yt.status(),
        "auto_publish": _auto_publish(cfg),
        "published_today": _published_today(db),
        "cost": {
            "hoje": _cost(cfg, db, _start_of_day()),
            "total": _cost(cfg, db, 0.0),
            "brl": float(cfg["pricing"].get("brl_per_usd", 5.4)),
        },
        "totals": {
            "clips": len(clips),
            "streams_live": sum(1 for s in streams if s["live"]),
        },
    }


def _auto_publish(cfg: Any) -> dict[str, Any]:
    pub = cfg.data.get("publish") or {}
    return {
        "enabled": bool(pub.get("auto")),
        "min_score": float(pub.get("auto_min_score") or 0.0),
        "privacy": str(pub.get("privacy") or "unlisted"),
    }


def _published_today(db: DB) -> int:
    try:
        row = db.conn().execute(
            "SELECT COUNT(*) AS c FROM clips WHERE published IS NOT NULL"
            " AND json_extract(published,'$.state')='done'"
            " AND json_extract(published,'$.at') >= ?",
            (_start_of_day(),),
        ).fetchone()
        return int(row["c"] or 0)
    except Exception:
        return 0


def _start_of_day() -> float:
    t = time.localtime()
    return time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 0, 0, 0, 0, 0, -1))


def _cost(cfg: Any, db: DB, since: float) -> dict[str, Any]:
    summary = db.cost_summary(since)
    usd = summary["usd"]
    clips = db.conn().execute(
        "SELECT COUNT(*) c FROM clips WHERE created_at >= ?", (since,)
    ).fetchone()["c"]
    return {
        **summary,
        "brl": round(usd * float(cfg["pricing"].get("brl_per_usd", 5.4)), 2),
        "clips": int(clips or 0),
        "per_clip_usd": round(usd / clips, 3) if clips else 0.0,
    }
