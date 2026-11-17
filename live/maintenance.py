"""Limpeza automatica: clipes antigos, arquivos orfaos, log e custo.

Regra de ouro: clipe que nunca foi publicado NAO e apagado por padrao.
Arquivo e dado do usuario; apagar sem certeza e pior que gastar disco.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from pipeline.util import log

from .db import DB

DAY = 86400.0


def _age_days(ts: float | None) -> float:
    if not ts:
        return 0.0
    return (time.time() - float(ts)) / DAY


def _published_state(raw: Any) -> str:
    if not raw:
        return ""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return str(data.get("state") or "")
    except Exception:
        return ""


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def purge(cfg: Any, db: DB, dry_run: bool = False) -> dict[str, Any]:
    """Aplica a retencao. Devolve relatorio do que saiu (ou sairia)."""
    m = cfg.data.get("maintenance") or {}
    if not m.get("enabled", True) and not dry_run:
        return {"skipped": True, "reason": "maintenance.enabled = false"}

    clip_days = float(m.get("clip_retention_days") or 30)
    keep_unpublished = float(m.get("keep_unpublished_days") or 0)
    db_days = float(m.get("db_retention_days") or 90)
    out_dir = Path(cfg.out_dir)

    report: dict[str, Any] = {
        "dry_run": dry_run,
        "clips_removed": 0,
        "clips_kept_unpublished": 0,
        "orphans_removed": 0,
        "log_rows": 0,
        "usage_rows": 0,
        "bytes_freed": 0,
        "clip_retention_days": clip_days,
        "db_retention_days": db_days,
    }

    known: set[str] = set()
    for row in db.clips(limit=100000):
        path = Path(row["path"]) if row["path"] else None
        if path:
            known.add(str(path.resolve()))

        state = _published_state(row["published"])
        old = _age_days(row["created_at"]) >= clip_days
        if not old or not path:
            continue

        if state != "done":
            # nao publicado: so sai se o usuario definiu um prazo
            if not keep_unpublished or _age_days(row["created_at"]) < keep_unpublished:
                report["clips_kept_unpublished"] += 1
                continue

        if not path.exists():
            continue

        report["clips_removed"] += 1
        report["bytes_freed"] += _size(path)
        for extra in (path.with_suffix(".jpg"), path.with_suffix(".json"),
                      path.with_suffix(".txt"), path.with_suffix(".ass")):
            report["bytes_freed"] += _size(extra)
            if not dry_run and extra.exists():
                try:
                    extra.unlink()
                except OSError:
                    pass
        if not dry_run:
            try:
                path.unlink()
            except OSError:
                pass
            db.update_clip(row["id"], status="purged")

    # arquivos em out/ que nao pertencem a nenhum registro
    if out_dir.exists():
        for file in out_dir.rglob("*"):
            if not file.is_file() or str(file.resolve()) in known:
                continue
            if file.suffix not in (".mp4", ".jpg", ".json", ".txt", ".ass"):
                continue
            if _age_days(file.stat().st_mtime) < max(clip_days, 1):
                continue
            report["orphans_removed"] += 1
            report["bytes_freed"] += _size(file)
            if not dry_run:
                try:
                    file.unlink()
                except OSError:
                    pass

    if db_days > 0:
        cutoff = time.time() - db_days * DAY
        rows = db.conn().execute("SELECT COUNT(*) n FROM log WHERE ts < ?", (cutoff,)).fetchone()
        report["log_rows"] = int(rows["n"] or 0)
        rows = db.conn().execute("SELECT COUNT(*) n FROM usage WHERE ts < ?", (cutoff,)).fetchone()
        report["usage_rows"] = int(rows["n"] or 0)
        if not dry_run:
            db.conn().execute("DELETE FROM log WHERE ts < ?", (cutoff,))
            db.conn().execute("DELETE FROM usage WHERE ts < ?", (cutoff,))

    if not dry_run:
        msg = (
            f"{report['clips_removed']} clipes, {report['orphans_removed']} orfaos, "
            f"{report['log_rows']} logs, {report['usage_rows']} custos, "
            f"{report['bytes_freed'] / 1e6:.1f} MB"
        )
        log(f"[purge] {msg}")
        if report["clips_removed"] or report["orphans_removed"]:
            db.log(None, "info", f"limpeza: {msg}")

    return report
