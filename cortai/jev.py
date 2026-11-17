"""Cliente Jev (TypeSafe) via OpenRouter Decisions API."""

from __future__ import annotations

import os
import time
from typing import Any

import requests

from pipeline.util import log

ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
DEFAULT_MODEL = "typesafe/jev-1.14"


def ready() -> bool:
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def decide(
    state: Any,
    questions: dict[str, Any],
    model: str = DEFAULT_MODEL,
    timeout: int = 60,
) -> dict[str, Any] | None:
    """Uma chamada, N perguntas em paralelo. Devolve {'answers', 'usage', 'ms'}."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            ENDPOINT,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost",
                "X-Title": "cortai",
            },
            json={"model": model, "state": state, "questions": questions},
            timeout=timeout,
        )
    except Exception as exc:
        log(f"[jev] falhou: {exc}")
        return None
    ms = int((time.perf_counter() - t0) * 1000)
    if resp.status_code >= 300:
        log(f"[jev] HTTP {resp.status_code}: {resp.text[:300]}")
        return None
    data = resp.json()
    return {
        "answers": data.get("answers") or {},
        "usage": data.get("usage") or {},
        "model": data.get("model"),
        "ms": ms,
    }


def image_part(b64: str) -> dict[str, Any]:
    return {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}


def box_to_pixels(box: dict[str, float], width: int, height: int) -> dict[str, float]:
    left = max(0.0, min(1.0, box.get("left", 0.0))) * width
    right = max(0.0, min(1.0, box.get("right", 0.0))) * width
    top = max(0.0, min(1.0, box.get("top", 0.0))) * height
    bottom = max(0.0, min(1.0, box.get("bottom", 0.0))) * height
    side = min(right - left, bottom - top)
    return {
        "x": round(left, 1),
        "y": round(top, 1),
        "w": round(max(side, 16.0), 1),
        "h": round(max(side, 16.0), 1),
    }
