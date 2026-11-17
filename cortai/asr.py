"""Transcricao (ASR) plugavel: groq -> openai -> local (faster-whisper)."""

from __future__ import annotations

import io
import os
import time
from pathlib import Path
from typing import Any, Callable

import requests

from pipeline.util import log

RETRY = {429, 500, 502, 503, 504}

ENDPOINTS: dict[str, dict[str, str]] = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/audio/transcriptions",
        "key_env": "OPENROUTER_API_KEY",
        "model": "elevenlabs/scribe-v2",
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/audio/transcriptions",
        "key_env": "GROQ_API_KEY",
        "model": "whisper-large-v3-turbo",
    },
    "openai": {
        "url": "https://api.openai.com/v1/audio/transcriptions",
        "key_env": "OPENAI_API_KEY",
        "model": "whisper-1",
    },
}


def endpoint_for(name: str, cfg: dict[str, Any]) -> dict[str, str] | None:
    """Modelo vem de asr.models[name]; sem isso usa o padrao da tabela."""
    spec = ENDPOINTS.get(name)
    if not spec:
        return None
    override = (cfg.get("models") or {}).get(name)
    if override:
        spec = {**spec, "model": str(override)}
    base = (cfg.get("base_urls") or {}).get(name)
    if base:
        spec = {**spec, "url": str(base).rstrip("/") + "/audio/transcriptions"}
    return spec


class ASR:
    def __init__(self, cfg: dict[str, Any]):
        self.cfg = cfg
        self.language = cfg.get("language", "pt")
        self.chain = [
            name
            for name in cfg.get("chain", ["groq", "openai", "local"])
            if self._usable(name)
        ]
        self._down: dict[str, float] = {}
        self._local = None
        if self.chain:
            log(f"[asr] cadeia: {' -> '.join(self.chain)}")
        else:
            log("[asr] nenhum backend configurado -> clipes sem transcricao/legenda")

    def _usable(self, name: str) -> bool:
        if name == "local":
            try:
                import faster_whisper  # noqa: F401

                return True
            except Exception:
                return False
        spec = endpoint_for(name, self.cfg)
        return bool(spec and os.environ.get(spec["key_env"]))

    def __bool__(self) -> bool:
        return bool(self.chain)

    def transcribe(self, wav: Path) -> dict[str, Any] | None:
        now = time.time()
        for name in self.chain:
            if self._down.get(name, 0) > now:
                continue
            try:
                spec = endpoint_for(name, self.cfg)
                result = (
                    self._local_transcribe(wav)
                    if name == "local"
                    else self._remote(wav, spec or ENDPOINTS[name])
                )
                if result:
                    result["backend"] = name
                    return result
            except Exception as exc:
                self._down[name] = time.time() + 120
                log(f"[asr] {name} falhou ({exc}) -> proximo")
        return None

    # -- remoto --------------------------------------------------------
    def _remote(self, wav: Path, spec: dict[str, str]) -> dict[str, Any] | None:
        key = os.environ.get(spec["key_env"], "")
        base: list[tuple[str, str]] = [
            ("model", spec["model"]),
            ("response_format", "verbose_json"),
            ("temperature", "0"),
            ("timestamp_granularities[]", "word"),
        ]
        if self.language:
            base.append(("language", self.language))

        keyterms = [t for t in (self.cfg.get("keyterms") or []) if t][:50]
        last: Exception | None = None
        for attempt in range(1, 5):
            data = list(base)
            for term in keyterms:
                data.append(("keyterms", term))
            with wav.open("rb") as fh:
                resp = requests.post(
                    spec["url"],
                    headers={"Authorization": f"Bearer {key}"},
                    files={"file": (wav.name, fh.read(), "audio/wav")},
                    data=data,
                    timeout=300,
                )
            if resp.status_code < 300:
                return _shape(resp.json(), _wav_duration(wav))
            # modelo sem suporte a enviesar vocabulario: refaz sem
            if resp.status_code == 400 and keyterms and "keyterm" in resp.text.lower():
                log("[asr] modelo nao aceita keyterms -> tentando sem")
                keyterms = []
                continue
            if resp.status_code in RETRY and attempt < 4:
                time.sleep(2**attempt)
                continue
            last = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            break
        raise last or RuntimeError("asr falhou")

    # -- local ---------------------------------------------------------
    def _local_transcribe(self, wav: Path) -> dict[str, Any] | None:
        from faster_whisper import WhisperModel

        if self._local is None:
            self._local = WhisperModel(
                self.cfg.get("local_model", "small"),
                device="cpu",
                compute_type="int8",
            )
        segments, _info = self._local.transcribe(
            str(wav),
            language=self.language,
            word_timestamps=True,
            vad_filter=True,
        )
        out = []
        texts = []
        for seg in segments:
            texts.append(seg.text.strip())
            out.append(
                {
                    "start": float(seg.start),
                    "end": float(seg.end),
                    "text": seg.text.strip(),
                    "words": [
                        {"start": float(w.start), "end": float(w.end), "word": w.word}
                        for w in (seg.words or [])
                    ],
                }
            )
        if not out:
            return None
        return {"text": " ".join(texts), "segments": out, "language": self.language}


def _wav_duration(path: Path) -> float:
    import wave

    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 16000)
    except Exception:
        return 0.0


def _shape(payload: dict[str, Any], duration: float | None = None) -> dict[str, Any] | None:
    text = (payload.get("text") or "").strip()

    # palavras no topo sao o dado mais fino: reconstroi a partir delas
    top_words = [
        {
            "start": float(w.get("start", 0.0)),
            "end": float(w.get("end", 0.0)),
            "word": w.get("word", ""),
        }
        for w in (payload.get("words") or [])
    ]

    segments: list[dict[str, Any]] = []
    if top_words:
        segments = _segments_from_words(top_words)
    else:
        for seg in payload.get("segments") or []:
            segments.append(
                {
                    "start": float(seg.get("start", 0.0)),
                    "end": float(seg.get("end", 0.0)),
                    "text": (seg.get("text") or "").strip(),
                    "words": [
                        {
                            "start": float(w.get("start", 0.0)),
                            "end": float(w.get("end", 0.0)),
                            "word": w.get("word", ""),
                        }
                        for w in seg.get("words") or []
                    ],
                }
            )

    # Alguns endpoints devolvem texto sem segmentos. Sem segmento nao ha legenda
    # e o juiz le a transcricao como silencio — entao reconstroi.
    if not segments and text:
        segments = _segments_from_text(text, duration or 0.0)

    if not text and not segments:
        return None
    if not text:
        text = " ".join(s["text"] for s in segments)
    usage = payload.get("usage") or {}
    return {
        "text": text,
        "segments": segments,
        "language": payload.get("language"),
        "usage_seconds": round(float(usage.get("seconds") or duration or 0.0), 2),
        "usage_cost": round(float(usage.get("cost") or 0.0), 6),
    }


def _segments_from_words(words: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for word in words:
        if current and (
            word["start"] - current[-1]["end"] > 0.8 or len(current) >= 7
        ):
            groups.append(current)
            current = []
        current.append(word)
    if current:
        groups.append(current)
    # junta fragmentos curtos ("A", "é.") no grupo anterior
    merged: list[list[dict[str, Any]]] = []
    for g in groups:
        if merged and len(g) < 3 and (g[-1]["end"] - g[0]["start"]) < 0.7:
            merged[-1].extend(g)
        else:
            merged.append(g)
    groups = merged
    return [
        {
            "start": g[0]["start"],
            "end": g[-1]["end"],
            "text": " ".join(w["word"] for w in g).strip(),
            "words": g,
        }
        for g in groups
    ]


def _segments_from_text(text: str, duration: float) -> list[dict[str, Any]]:
    """Ultimo recurso: reparte o texto no tempo proporcional aos caracteres."""
    words = text.split()
    if not words:
        return []
    if duration <= 0:
        duration = max(2.0, len(words) * 0.4)
    chunks: list[list[str]] = [words[i : i + 8] for i in range(0, len(words), 8)]
    total = sum(len(" ".join(c)) for c in chunks) or 1
    out: list[dict[str, Any]] = []
    t = 0.0
    for chunk in chunks:
        span = duration * (len(" ".join(chunk)) / total)
        out.append(
            {
                "start": round(t, 2),
                "end": round(min(duration, t + span), 2),
                "text": " ".join(chunk),
                "words": [],
            }
        )
        t += span
    if out:
        out[-1]["end"] = round(duration, 2)
    return out
