"""Fusao dos sinais -> candidatos a corte."""

from __future__ import annotations

from typing import Any

import numpy as np

from .util import log


def _robust_z(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    scale = 1.4826 * mad if mad > 1e-9 else (np.std(x) or 1.0)
    return np.clip((x - med) / scale, -4.0, 8.0)


def _smooth(x: np.ndarray, k: int = 3) -> np.ndarray:
    if k <= 1 or x.size < k:
        return x
    kernel = np.ones(k, dtype=np.float64) / k
    return np.convolve(x, kernel, mode="same")


def score_series(
    audio: dict[str, Any],
    chat: dict[str, Any] | None,
    weights: dict[str, float],
) -> dict[str, np.ndarray]:
    seconds = audio["seconds"]
    loud = _robust_z(audio["loud_db"])
    flux = _robust_z(audio["flux"])

    total = weights.get("loudness", 1.0) * loud + weights.get("flux", 0.7) * flux
    parts = {"loudness": loud, "flux": flux}

    if chat:
        rate = _smooth(_robust_z(chat["rate"]), 3)
        hype = _smooth(_robust_z(chat["hype"]), 3)
        chat_z = np.maximum(rate * 0.5 + hype, 0)
        total = total + weights.get("chat", 1.2) * chat_z
        parts["chat"] = chat_z
    else:
        parts["chat"] = np.zeros(seconds)

    return {"score": _smooth(total, 3), **parts}


def pick_peaks(
    series: dict[str, np.ndarray],
    moments_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    score = series["score"]
    n = len(score)
    if n == 0:
        return []

    sep = int(moments_cfg["min_sep_s"])
    threshold = float(moments_cfg["peak_z"])
    half = max(1, sep // 2)

    candidates: list[dict[str, Any]] = []
    for i in range(n):
        v = score[i]
        if v < threshold:
            continue
        lo, hi = max(0, i - half), min(n, i + half + 1)
        if v < score[lo:hi].max():
            continue  # nao e o pico da vizinhanca
        candidates.append({"peak_s": float(i), "peak_score": float(v)})

    candidates.sort(key=lambda c: c["peak_score"], reverse=True)

    chosen: list[dict[str, Any]] = []
    for cand in candidates:
        if any(abs(cand["peak_s"] - c["peak_s"]) < sep for c in chosen):
            continue
        chosen.append(cand)
        if len(chosen) >= int(moments_cfg["top_n"]):
            break

    start_pad = float(moments_cfg["pre_roll_s"])
    end_pad = float(moments_cfg["post_roll_s"])
    out: list[dict[str, Any]] = []
    for c in chosen:
        p = c["peak_s"]
        start = max(0.0, p - start_pad)
        end = min(float(n), p + end_pad)
        out.append(
            {
                "peak_s": p,
                "start_s": start,
                "end_s": end,
                "energy_score": round(c["peak_score"], 3),
                "signals": {
                    k: round(float(series[k][int(p)]), 3)
                    for k in ("loudness", "flux", "chat")
                },
            }
        )

    out.sort(key=lambda c: c["peak_s"])
    for idx, c in enumerate(out):
        c["id"] = f"cand{idx + 1:02d}"
    log(f"[moments] {len(out)} candidatos (de {len(candidates)} picos)")
    return out
