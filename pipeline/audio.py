from __future__ import annotations

import wave
from pathlib import Path
from typing import Any

import numpy as np

from .util import find_exe, log, run

SR = 16000
FRAME = 1024
HOP = 512


def extract_wav(video: Path, wav_path: Path) -> Path:
    if wav_path.exists() and wav_path.stat().st_size > 44:
        return wav_path
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    log("[audio] extraindo trilha -> 16k mono")
    run(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(SR),
            "-c:a",
            "pcm_s16le",
            str(wav_path),
        ]
    )
    return wav_path


def read_wav(path: Path) -> np.ndarray:
    """Le WAV PCM16 e devolve int16 1-D (metade da memoria de float32)."""
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2:
            raise ValueError("esperado WAV 16-bit")
        if w.getnchannels() != 1:
            raise ValueError("esperado WAV mono")
        raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype="<i2").copy()


def write_wav_slice(samples: np.ndarray, out_path: Path, start_s: float, end_s: float) -> Path:
    a = max(0, int(start_s * SR))
    b = min(len(samples), int(end_s * SR))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(samples[a:b].astype("<i2").tobytes())
    return out_path


def _frame_features(
    samples: np.ndarray,
    frame: int = FRAME,
    hop: int = HOP,
    block: int = 1024,
) -> dict[str, np.ndarray]:
    n_frames = max(0, 1 + (len(samples) - frame) // hop)
    if n_frames <= 0:
        z = np.zeros(0, dtype=np.float32)
        return {"times": z, "rms": z, "flux": z, "centroid": z, "zcr": z}

    window = np.hanning(frame).astype(np.float32)
    freqs = np.fft.rfftfreq(frame, 1 / SR).astype(np.float32)
    idx_base = np.arange(frame)

    rms = np.zeros(n_frames, dtype=np.float32)
    flux = np.zeros(n_frames, dtype=np.float32)
    centroid = np.zeros(n_frames, dtype=np.float32)
    zcr = np.zeros(n_frames, dtype=np.float32)

    prev_mag: np.ndarray | None = None
    for b0 in range(0, n_frames, block):
        b1 = min(b0 + block, n_frames)
        idx = np.arange(b0, b1)[:, None] * hop + idx_base[None, :]
        fr = samples[idx].astype(np.float32) / 32768.0

        rms[b0:b1] = np.sqrt(np.mean(fr * fr, axis=1))
        zcr[b0:b1] = np.mean(np.abs(np.diff(np.signbit(fr), axis=1)), axis=1).astype(
            np.float32
        )

        mag = np.abs(np.fft.rfft(fr * window, axis=1))
        if prev_mag is None:
            stack_prev = np.vstack([mag[:1], mag[:-1]])
        else:
            stack_prev = np.vstack([prev_mag, mag[:-1]])
        flux[b0:b1] = np.maximum(mag - stack_prev, 0).sum(axis=1)
        total = mag.sum(axis=1) + 1e-9
        centroid[b0:b1] = (mag @ freqs) / total
        prev_mag = mag[-1:]

    times = (np.arange(n_frames) * hop + frame / 2) / SR
    return {
        "times": times.astype(np.float32),
        "rms": rms,
        "flux": flux,
        "centroid": centroid,
        "zcr": zcr,
    }


def analyze(samples: np.ndarray) -> dict[str, Any]:
    """Serie temporal de 1 valor por segundo, pronta para pontuar momentos."""
    feats = _frame_features(samples)
    if len(feats["times"]) == 0:
        raise ValueError("audio vazio")

    seconds = int(np.floor(len(samples) / SR)) or 1
    bins = np.clip((feats["times"]).astype(np.int64), 0, seconds - 1)

    def agg(key: str, how: str) -> np.ndarray:
        out = np.zeros(seconds, dtype=np.float64)
        src = feats[key].astype(np.float64)
        if how == "max":
            np.maximum.at(out, bins, src)
        else:
            counts = np.bincount(bins, minlength=seconds)
            np.add.at(out, bins, src)
            out /= np.maximum(counts, 1)
        return out

    rms = agg("rms", "max")
    loud_db = 20 * np.log10(np.maximum(rms, 1e-6))
    return {
        "seconds": seconds,
        "loud_db": loud_db,
        "flux": agg("flux", "mean"),
        "centroid": agg("centroid", "mean"),
        "zcr": agg("zcr", "mean"),
    }
