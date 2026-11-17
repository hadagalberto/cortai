"""Perfis de video por canal: cada live pode usar um template proprio."""

from __future__ import annotations

import copy
from typing import Any

DEFAULT_TEMPLATE = "default"


def _merge(base: dict[str, Any], override: dict[str, Any] | None) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def names(cfg: Any) -> list[str]:
    tpl = cfg["templates"] if "templates" in cfg.data else {}
    return sorted(tpl.keys()) or [DEFAULT_TEMPLATE]


def resolve(cfg: Any, template: str | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Devolve (render_cfg, branding_cfg) ja com o template aplicado."""
    templates = cfg.data.get("templates") or {}
    chosen = templates.get(template or DEFAULT_TEMPLATE) or {}
    render_cfg = _merge(cfg["render"], chosen.get("render"))
    brand_cfg = _merge(cfg["branding"], chosen.get("branding"))
    return render_cfg, brand_cfg


def get(cfg: Any, template: str) -> dict[str, Any]:
    return (cfg.data.get("templates") or {}).get(template) or {}


def save(cfg_path, cfg: dict[str, Any], template: str, body: dict[str, Any]) -> None:
    """Grava/atualiza um template dentro do config.json."""
    import json

    templates = cfg.setdefault("templates", {})
    current = templates.get(template) or {}
    for section in ("render", "branding"):
        if section in body and isinstance(body[section], dict):
            current[section] = _merge(current.get(section) or {}, body[section])
    templates[template] = current
    cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def delete(cfg: dict[str, Any], template: str) -> bool:
    if template == DEFAULT_TEMPLATE:
        return False
    return (cfg.get("templates") or {}).pop(template, None) is not None
