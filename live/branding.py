"""Sobreposicoes de marca no clipe vertical: logo, @handle, CTA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pipeline.util import ROOT

POSITIONS = {
    "tl": ("40", "40"),
    "tr": ("W-w-40", "40"),
    "bl": ("40", "H-h-200"),
    "br": ("W-w-40", "H-h-200"),
}


def _esc_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
    )


def _esc_path(path: str) -> str:
    return str(path).replace("\\", "/").replace(":", "\\:")


def _font(branding: dict[str, Any]) -> str | None:
    explicit = branding.get("font")
    if explicit and Path(explicit).exists():
        return explicit
    for cand in (
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if Path(cand).exists():
            return cand
    return None


def build(
    vin: str,
    vout: str,
    next_input_index: int,
    branding: dict[str, Any] | None,
) -> tuple[list[list[str]], str]:
    """Devolve (inputs extras, trecho de filtro) ligando [vin] a [vout]."""
    if not branding:
        return [], f"[{vin}]null[{vout}]"

    filters: list[str] = []
    extra_inputs: list[list[str]] = []
    current = vin

    logo = branding.get("logo")
    if logo:
        logo_path = Path(logo)
        if not logo_path.is_absolute():
            logo_path = ROOT / logo_path
        if logo_path.exists():
            width = int(branding.get("logo_width", 220))
            x, y = POSITIONS.get(branding.get("logo_position", "tr"), POSITIONS["tr"])
            extra_inputs.append(["-i", str(logo_path)])
            filters.append(
                f"[{next_input_index}:v]scale={width}:-1[lg]"
            )
            filters.append(
                f"[{current}][lg]overlay={x}:{y}:format=auto[lgd]"
            )
            current = "lgd"

    font = _font(branding)
    if font:
        font_arg = f"fontfile='{_esc_path(font)}'"

        handle = (branding.get("handle") or "").strip()
        if handle:
            filters.append(
                f"[{current}]drawtext={font_arg}:text='{_esc_text(handle)}'"
                f":fontsize=46:fontcolor=white:borderw=3:bordercolor=black@0.8"
                f":box=1:boxcolor=black@0.35:boxborderw=16"
                f":x=(w-text_w)/2:y=h-{int(branding.get('handle_offset', 210))}[hd]"
            )
            current = "hd"

        cta = (branding.get("cta") or "").strip()
        if cta:
            filters.append(
                f"[{current}]drawtext={font_arg}:text='{_esc_text(cta.upper())}'"
                f":fontsize=40:fontcolor={branding.get('accent', '0xFFD400')}"
                f":borderw=3:bordercolor=black@0.85"
                f":x=(w-text_w)/2:y=h-{int(branding.get('cta_offset', 150))}[ct]"
            )
            current = "ct"

    filters.append(f"[{current}]null[{vout}]")
    return extra_inputs, ";".join(filters)
