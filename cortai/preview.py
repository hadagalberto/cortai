"""Preview quase ao vivo: remux curto do ring buffer, servido para o painel."""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from pipeline.util import find_exe, run

_locks: dict[str, threading.Lock] = {}
_guard = threading.Lock()


def _lock(slug: str) -> threading.Lock:
    with _guard:
        if slug not in _locks:
            _locks[slug] = threading.Lock()
        return _locks[slug]


def ensure(cfg: Any, slug: str, max_age: float = 5.0) -> Path | None:
    """Garante um preview.mp4 fresco (<= max_age). Devolve o arquivo ou None."""
    work = cfg.work_dir / slug
    ring_dir = work / "ring"
    if not ring_dir.is_dir():
        return None

    out = work / "preview.mp4"
    fresh = out.exists() and (time.time() - out.stat().st_mtime) < max_age
    if fresh:
        return out
    if out.exists() and not fresh and _lock(slug).locked():
        return out  # serve o anterior enquanto outro request remonta

    if not _lock(slug).acquire(blocking=False):
        return out if out.exists() else None
    try:
        segs = sorted(ring_dir.glob("seg_*.ts"), key=lambda p: p.name)[-3:]
        if len(segs) < 2:
            return out if out.exists() else None

        list_file = work / "preview.txt"
        list_file.write_text(
            "\n".join(f"file '{p.resolve().as_posix()}'" for p in segs) + "\n",
            encoding="utf-8",
        )
        tmp = work / "preview.tmp.mp4"
        run(
            [
                find_exe("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-t",
                "6",
                "-c",
                "copy",
                "-an",
                "-movflags",
                "+faststart",
                str(tmp),
            ]
        )
        tmp.replace(out)
        return out
    except Exception:
        return out if out.exists() else None
    finally:
        _lock(slug).release()


def stamp(cfg: Any, slug: str) -> float | None:
    p = cfg.work_dir / slug / "preview.mp4"
    return round(p.stat().st_mtime, 1) if p.exists() else None
