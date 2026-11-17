"""Escolhe o enquadramento horizontal a partir do movimento real do jogo."""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np

from .util import find_exe, log, run


def _frames(video: Path, start_s: float, dur_s: float, samples: int, tmp: Path) -> list[Path]:
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    step = max(0.3, dur_s / max(2, samples))
    run(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{max(0.0, start_s):.3f}",
            "-t",
            f"{max(0.5, dur_s):.3f}",
            "-i",
            str(video),
            "-vf",
            f"fps=1/{step:.3f},scale=256:-2",
            "-frames:v",
            str(samples),
            "-q:v",
            "4",
            str(tmp / "m%03d.jpg"),
        ]
    )
    return sorted(tmp.glob("m*.jpg"))


def focus_x(
    video: Path,
    start_s: float,
    dur_s: float,
    src_w: int,
    src_h: int,
    out_w: int = 1080,
    out_h: int = 1920,
    samples: int = 6,
) -> float:
    """Devolve 0..1 para `crop=...:(iw-out_w)*focus`, seguindo o movimento."""
    if src_h <= 0 or src_w <= 0:
        return 0.5
    scaled_w = round(src_w * out_h / src_h)
    span = scaled_w - out_w
    if span <= 0:
        return 0.5

    tmp = video.parent / "_motion"
    try:
        frames = _frames(video, start_s, dur_s, samples, tmp)
        if len(frames) < 2:
            return 0.5
        try:
            import cv2
        except Exception:
            return 0.5

        pixels = [cv2.imread(str(p), cv2.IMREAD_GRAYSCALE) for p in frames]
        pixels = [p for p in pixels if p is not None]
        if len(pixels) < 2:
            return 0.5

        energy = np.zeros(pixels[0].shape[1], dtype=np.float64)
        for a, b in zip(pixels, pixels[1:]):
            if a.shape != b.shape:
                continue
            diff = cv2.absdiff(a, b).astype(np.float64)
            energy += diff.sum(axis=0)

        if energy.sum() <= 0:
            return 0.5

        # suaviza para nao grudar em um pixel de ruido
        kernel = np.ones(9) / 9.0
        energy = np.convolve(energy, kernel, mode="same")
        xs = np.arange(energy.size, dtype=np.float64)
        centroid_small = float((energy * xs).sum() / energy.sum())
        centroid_scaled = centroid_small / energy.size * scaled_w

        focus = (centroid_scaled - out_w / 2.0) / span
        return float(min(1.0, max(0.0, focus)))
    except Exception as exc:
        log(f"[motion] falhou: {exc}")
        return 0.5
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
