"""Sobreposicoes de imagem no clipe: logo, arte de canal e fundo personalizado."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.util import ROOT

DEFAULT_ART_POS = {"x": 540, "y": 960, "w": 1080, "anchor": "center"}


def _esc_path(path: str | Path) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")


def build(
    vin: str,
    vout: str,
    inputs: dict[str, int | None],
    branding: dict[str, Any] | None,
) -> tuple[list[list[str]], str]:
    """Liga [vin] a [vout], aplicando arte e logo.

    inputs: {'art': indice|None, 'logo': indice|None} dos -i extras.
    """
    if not branding:
        return [], f"[{vin}]null[{vout}]"

    filters: list[str] = []
    current = vin

    art = branding.get("art") or {}
    art_idx = inputs.get("art")
    art_path = art.get("image")
    if art_idx is not None and art_path:
        pos = branding.get("art_position") or DEFAULT_ART_POS
        filters.append(f"[{art_idx}:v]format=rgba,colorchannelmixer=aa={float(art.get('opacity', 1.0))}[artf]")
        x = int(pos.get("x", 540))
        y = int(pos.get("y", 960))
        filters.append(f"[{current}][artf]overlay=x={x}-w/2:y={y}-h/2:eval=init[artd]")
        current = "artd"

    logo = branding.get("logo")
    logo_idx = inputs.get("logo")
    if logo_idx is not None and logo:
        width = int(branding.get("logo_width", 220))
        anchor = str(branding.get("logo_position", "tr"))
        margin = int(branding.get("logo_margin", 40))
        px = {"tl": str(margin), "tr": f"W-w-{margin}", "bl": str(margin), "br": f"W-w-{margin}"}.get(anchor, f"W-w-{margin}")
        py = str(margin) if anchor in ("tl", "tr") else "H-h-200"
        filters.append(f"[{logo_idx}:v]scale={width}:-1[lg]")
        filters.append(f"[{current}][lg]overlay={px}:{py}:format=auto[lgd]")
        current = "lgd"

    filters.append(f"[{current}]null[{vout}]")
    return [], ";".join(filters)


def art_path(branding: dict[str, Any] | None) -> Path | None:
    art = (branding or {}).get("art") or {}
    rel = art.get("image")
    if not rel:
        return None
    path = Path(rel)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.is_file() else None
