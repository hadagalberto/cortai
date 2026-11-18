"""Preview do template: um frame renderizado com o visual do canal."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any

from pipeline.render import render_still
from pipeline.util import find_exe, log, run

from .templates import resolve

_cache: dict[str, tuple[float, Path]] = {}
_lock = threading.Lock()
SAMPLE_LABELS = [
    "CARALHO MANO OLHA ISSO",
]


def _sample_source(cfg: Any) -> tuple[Path, dict[str, Any] | None]:
    """Usa a captura CRUA (preview.mp4 do ring), nunca um clipe pronto.

    Clipe pronto ja tem gancho e legenda queimados: o preview sairia com texto
    sobreposto e mentiria sobre o resultado.
    """
    work = Path(cfg.work_dir)
    raws = sorted(work.glob("*/preview.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not raws:
        raws = sorted(work.glob("*/window_*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if raws:
        source = raws[0]
        face = None
        try:
            import json as _json

            fc = source.parent / "facecam.json"
            if fc.exists():
                face = _json.loads(fc.read_text(encoding="utf-8-sig"))
        except Exception:
            face = None
        return source, face

    synth = work / "_preview_src.mp4"
    if not synth.exists() or time.time() - synth.stat().st_mtime > 86400:
        synth.parent.mkdir(parents=True, exist_ok=True)
        run(
            [
                find_exe("ffmpeg"), "-y", "-hide_banner", "-loglevel", "error",
                "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=300:sample_rate=48000",
                "-t", "6", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(synth),
            ]
        )
    return synth, None


def _stub_transcript() -> dict[str, Any]:
    words = [
        {"word": w, "start": 0.4 + i * 0.42, "end": 0.75 + i * 0.42}
        for i, w in enumerate("olha o tamanho desse maluco".split())
    ]
    return {
        "text": "olha o tamanho desse maluco",
        "segments": [
            {
                "start": 0.4,
                "end": 0.4 + len(words) * 0.42,
                "text": "olha o tamanho desse maluco",
                "words": words,
            }
        ],
    }


def preview_png(
    cfg: Any,
    template: str,
    hook: str = "NAO E POSSIVEL",
    layout: str = "pip",
    render_override: dict[str, Any] | None = None,
    branding_override: dict[str, Any] | None = None,
    variables: dict[str, Any] | None = None,
) -> bytes | None:
    source, cached_face = _sample_source(cfg)
    base_render, base_brand = resolve(cfg, template)
    render_cfg = {**base_render, **(render_override or {})}
    brand_cfg = {**base_brand, **(branding_override or {})}
    key_src = json.dumps(
        {"r": render_cfg, "b": brand_cfg, "h": hook, "l": layout, "s": str(source)},
        sort_keys=True,
        default=str,
    )
    key = hashlib.sha256(key_src.encode()).hexdigest()[:16]

    with _lock:
        hit = _cache.get(key)
        if hit and hit[1].exists():
            return hit[1].read_bytes()

    out_dir = Path(cfg.work_dir) / "_preview"
    out_dir.mkdir(parents=True, exist_ok=True)
    png = out_dir / f"{key}.png"
    try:
        face = cached_face if (cached_face and layout in ("pip", "face")) else None

        render_still(
            source,
            1.0,
            png,
            render_cfg,
            _stub_transcript(),
            hook,
            branding=brand_cfg,
            layout=layout if layout in ("pip", "face", "game") else "pip",
            face=face if (face and layout in ("pip", "face")) else None,
            focus_x=0.5,
            variables=variables or {"streamer": "canal", "date": "hoje"},
        )
    except Exception as exc:
        log(f"[preview] falhou: {exc}")
        return None

    with _lock:
        _cache[key] = (time.time(), png)
    return png.read_bytes()
