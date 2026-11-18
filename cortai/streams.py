"""Cadastro de lives: normaliza URL, descobre plataforma e gera slug."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from .db import DB


def detect_platform(url: str) -> str:
    u = (url or "").lower()
    if "twitch.tv" in u:
        return "twitch"
    if "youtube.com" in u or "youtu.be" in u:
        return "youtube"
    if "kick.com" in u:
        return "kick"
    if "tiktok.com" in u:
        return "tiktok"
    return "other"


def make_slug(url: str, platform: str) -> str:
    if platform == "youtube":
        m = re.search(r"[?&]v=([\w-]{6,})", url)
        if m:
            return f"yt-{m.group(1)}"[:40]
        m = re.search(r"/(?:channel|c|@)([\w.-]+)", url)
        if m:
            return f"yt-{m.group(1).lower()}"[:40]
    tail = url.rstrip("/").split("/")[-1].split("?")[0]
    slug = re.sub(r"[^\w.-]+", "-", tail).strip("-").lower() or "live"
    return slug[:40]


def add(
    db: DB, url: str, platform: str | None = None, title: str = "", slug: str | None = None
) -> tuple[str, int]:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("url invalida: comece com https://")
    plat = platform or detect_platform(url)
    final_slug = slug or make_slug(url, plat)
    sid = db.add_stream(final_slug, url, plat, title)
    return final_slug, sid


def remove(db: DB, cfg: Any, slug: str) -> dict[str, Any]:
    """Tira o canal do painel e apaga clipes, thumbs e o buffer de work/."""
    report = db.remove_stream(slug)
    if not report.get("ok"):
        return report

    removed = 0
    for raw in report.pop("files", []):
        path = Path(raw)
        if not path.is_absolute():
            path = Path(cfg.out_dir) / path.name
        for extra in (path, *(path.with_suffix(s) for s in (".jpg", ".json", ".txt", ".ass"))):
            try:
                if extra.is_file():
                    extra.unlink()
                    removed += 1
            except OSError:
                pass

    shutil.rmtree(Path(cfg.work_dir) / slug, ignore_errors=True)
    report["files"] = removed
    return report


def list_all(db: DB) -> list[dict[str, Any]]:
    return [
        {
            "slug": r["slug"],
            "url": r["url"],
            "platform": r["platform"],
            "title": r["title"],
            "status": r["status"],
        }
        for r in db.streams(None)
    ]
