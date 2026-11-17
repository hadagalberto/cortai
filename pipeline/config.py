from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

from .util import ROOT, load_json

DEFAULTS: dict[str, Any] = {
    "work_dir": "work",
    "out_dir": "out",
    "live": {
        "buffer_seconds": 600,
        "window_s": 60,
        "cycle_s": 20,
        "min_buffer_s": 75,
        "quality": "best",
        "chat_enabled": True,
        "max_streams": 5,
    },
    "moments": {
        "top_n": 10,
        "min_sep_s": 45,
        "peak_z": 1.3,
        "pre_roll_s": 10,
        "post_roll_s": 20,
        "context_pre_s": 12,
        "context_post_s": 25,
        "min_clip_s": 10,
        "max_clip_s": 37,
        "weights": {"loudness": 1.0, "flux": 0.7, "chat": 1.3},
    },
    "asr": {
        "language": "pt",
        "chain": ["openrouter", "groq", "openai", "local"],
        "local_model": "small",
        "keyterms": ["GTA", "GTA V", "GTA 6", "Los Santos", "Trevor", "Franklin", "Michael"],
    },
    "llm": {"cooldown_s": 180, "providers": []},
    "classify": {
        "min_score": 7.0,
        "frames": 6,        "mode": "cascade",
        "jev": {
            "enabled": True,
            "model": "typesafe/jev-1.14",
            "min_score": 5.5,
            "min_event": 0.5,
        },
    },
    "pricing": {
        "asr": {"openai": 0.006, "groq": 0.0004, "local": 0.0},
        "llm": {"default": {"in": 0.50, "out": 2.00}},
        "brl_per_usd": 5.40,
    },
    "facecam": {
        "enabled": True,
        "provider": "jev",
        "refresh_s": 900,
        "samples": 20,
        "jev_samples": 3,
        "min_confidence": 0.12,
        "pad": 3.4,
        "min_frame_hits": 0.3,
    },
    "render": {
        "mode": "pad_blur",
        "focus_x": 0.5,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "crf": 20,
        "preset": "veryfast",
        "audio_bitrate": "192k",
        "burn_subs": True,
        "hook_caption": True,
        "sub_size": 76,
        "karaoke_size": 96,
        "karaoke_words": 3,
        "karaoke_margin_v": 300,
        "hook_size": 92,
        "sub_margin_v": 300,
        "blur_sigma": 22,
        "pip_scale": 0.37,
        "pip_position": "tr",
        "pip_offset_y": 400,
        "pip_margin": 44,
        "pip_border": 8,
    },
    "publish": {
        "auto": False,
        "auto_min_score": 7.5,
        "privacy": "unlisted",
        "category_id": "20",
        "description_footer": "",
        "schedule_hours": [],
        "max_attempts": 5,
        "retry_minutes": 5,
    },
    "templates": {"default": {}},
    "maintenance": {
        "enabled": True,
        "clip_retention_days": 30,
        "keep_unpublished_days": 0,
        "db_retention_days": 90,
        "run_every_hours": 6,
    },
    "branding": {
        "logo": "branding/logo.png",        "logo_width": 220,
        "logo_position": "tr",
        "handle": "",
        "cta": "SEGUE PRA MAIS",
        "accent": "0xFFD400",
        "handle_offset": 210,
        "cta_offset": 150,
    },
}


def _deep_merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


ENV_PREFIX = "CORTAI_"


def _coerce(value: str, current: Any) -> Any:
    text = value.strip()
    if isinstance(current, bool):
        return text.lower() in ("1", "true", "yes", "on", "sim")
    if isinstance(current, int) and not isinstance(current, bool):
        return int(float(text))
    if isinstance(current, float):
        return float(text)
    if isinstance(current, list):
        return [p.strip() for p in text.split(",") if p.strip()]
    if current is None:
        for cast in (int, float):
            try:
                return cast(text)
            except ValueError:
                pass
        if text.lower() in ("true", "false"):
            return text.lower() == "true"
    return text


def _apply_env(data: dict[str, Any]) -> dict[str, Any]:
    """CORTAI_RENDER__KARAOKE_SIZE=110 sobrepoe config.json sem editar arquivo.

    Separador __ porque chaves legitimas tem underscore (auto_min_score).
    """
    for key, raw in os.environ.items():
        if not key.startswith(ENV_PREFIX):
            continue
        path = key[len(ENV_PREFIX) :].lower().split("__")
        if not all(path):
            continue
        node: Any = data
        for part in path[:-1]:
            if not isinstance(node.get(part), dict):
                node[part] = {}
            node = node[part]
        node[path[-1]] = _coerce(raw, node.get(path[-1]))
    return data


class Config:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.work_dir = (ROOT / data["work_dir"]).resolve()
        self.out_dir = (ROOT / data["out_dir"]).resolve()

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def section(self, key: str) -> dict[str, Any]:
        return self.data[key]

    @classmethod
    def load(cls, path: Path | None = None) -> "Config":
        p = path or (ROOT / "config.json")
        data = load_json(p, {}) or {}
        return cls(_apply_env(_deep_merge(DEFAULTS, data)))
