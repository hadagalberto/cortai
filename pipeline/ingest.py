from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import find_exe, log, run


def probe_duration(path: Path) -> float:
    out = run(
        [
            find_exe("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return float(out.strip().splitlines()[0])


def _pick_source_file(work: Path) -> Path | None:
    for ext in ("mp4", "mkv", "webm", "ts", "mov"):
        p = work / f"source.{ext}"
        if p.exists() and p.stat().st_size > 0:
            return p
    return None


def ingest(url: str | None, file: str | None, work: Path) -> dict[str, Any]:
    """Baixa o VOD (ou aceita arquivo local) e devolve metadados basicos."""
    work.mkdir(parents=True, exist_ok=True)

    if file:
        src = Path(file).expanduser().resolve()
        if not src.exists():
            raise FileNotFoundError(f"arquivo nao existe: {src}")
        return {
            "source": str(src),
            "source_kind": "local",
            "title": src.stem,
            "video_id": src.stem,
            "duration_s": probe_duration(src),
        }

    if not url:
        raise ValueError("informe --url ou --file")

    cached = _pick_source_file(work)
    if cached:
        log(f"[ingest] reutilizando {cached.name}")
        meta = _load_meta(work)
        if meta:
            return meta

    import yt_dlp

    log(f"[ingest] baixando {url}")
    opts = {
        "outtmpl": str(work / "source.%(ext)s"),
        "format": (
            "bv*[height<=1080][vcodec^=avc1][ext=mp4]+ba[ext=m4a]/"
            "bv*[height<=1080]+ba/b[height<=1080]/b"
        ),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "retries": 5,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info.get("_type") == "playlist":
            info = info["entries"][0]

    path = _pick_source_file(work)
    if not path:
        raise RuntimeError("download terminou sem arquivo de video reconhecivel")

    meta = {
        "source": str(path),
        "source_kind": "url",
        "url": url,
        "title": info.get("title") or path.stem,
        "video_id": str(info.get("id") or path.stem),
        "uploader": info.get("uploader"),
        "duration_s": float(info.get("duration") or probe_duration(path)),
        "webpage_url": info.get("webpage_url") or url,
        "extractor": info.get("extractor_key"),
    }
    _save_meta(work, meta)
    log(f"[ingest] ok: {meta['duration_s'] / 60:.1f} min")
    return meta


def _load_meta(work: Path) -> dict[str, Any] | None:
    import json

    p = work / "meta.json"
    if not p.exists():
        return None
    meta = json.loads(p.read_text(encoding="utf-8"))
    if not Path(meta.get("source", "")).exists():
        return None
    return meta


def _save_meta(work: Path, meta: dict[str, Any]) -> None:
    import json

    (work / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
