from __future__ import annotations

"""Assets do canal: upload em base64, listagem e remocao."""

import base64
from pathlib import Path
from typing import Any

from pipeline.util import ROOT

KINDS = {
    "bg": ROOT / "branding" / "backgrounds",
    "art": ROOT / "branding" / "art",
    "logo": ROOT / "branding",
}
ALLOWED = {".png", ".jpg", ".jpeg", ".webp"}
MAX_BYTES = 8 * 1024 * 1024


def folder(kind: str) -> Path:
    if kind not in KINDS:
        raise ValueError(f"tipo invalido: {kind}")
    KINDS[kind].mkdir(parents=True, exist_ok=True)
    return KINDS[kind]


def safe_name(name: str) -> str:
    stem = Path(name or "arquivo").stem
    ext = Path(name or "").suffix.lower()
    if ext not in ALLOWED:
        ext = ".png"
    clean = "".join(c if (c.isalnum() or c in "._-") else "-" for c in stem).strip("-").lower()
    return f"{clean or 'arquivo'}{ext}"


def save_b64(kind: str, name: str, data_b64: str) -> dict[str, Any]:
    raw = base64.b64decode(data_b64.split(",")[-1], validate=False)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"arquivo grande demais ({len(raw) / 1e6:.1f} MB, limite 8 MB)")
    if len(raw) < 64:
        raise ValueError("arquivo vazio ou invalido")
    target = folder(kind) / safe_name(name)
    target.write_bytes(raw)
    return {"ok": True, "path": rel(target), "name": target.name, "bytes": len(raw)}


def list_assets() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for kind, path in KINDS.items():
        items: list[dict[str, Any]] = []
        if path.exists():
            for file in sorted(path.iterdir()):
                if file.is_file() and file.suffix.lower() in ALLOWED:
                    items.append(
                        {
                            "name": file.name,
                            "path": rel(file),
                            "bytes": file.stat().st_size,
                        }
                    )
        out[kind] = items
    return out


def delete(kind: str, name: str) -> bool:
    target = folder(kind) / safe_name(name)
    if target.exists():
        target.unlink()
        return True
    return False


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def resolve(rel_path: str | None) -> Path | None:
    if not rel_path:
        return None
    path = Path(rel_path)
    if not path.is_absolute():
        path = ROOT / path
    return path if path.is_file() else None


def pick_background(brand_cfg: dict[str, Any], seed: float | None = None) -> Path | None:
    """Escolhe uma imagem do pool; deterministico por clipe quando ha seed."""
    bg = brand_cfg.get("background") or {}
    if str(bg.get("mode") or "blur") != "image":
        return None
    pool = [p for p in (resolve(str(x)) for x in (bg.get("images") or [])) if p]
    if not pool:
        return None
    if len(pool) == 1:
        return pool[0]
    import time as _t

    return pool[int((seed or _t.time()) * 1000) % len(pool)]
