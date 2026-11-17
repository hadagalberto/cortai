"""Classificador de momento viral (LLM + frames). Prompts afinados para GTA."""

from __future__ import annotations

import base64
import json
import subprocess
from pathlib import Path
from typing import Any

from pipeline.util import find_exe

from . import jev
from .llm import LLMRouter

SYSTEM = """Voce e editor-chefe de cortes de gameplay para TikTok, Reels e Shorts.
Recebe: transcricao de uma janela de live, o perfil de energia do audio, o sinal de chat e alguns frames do video.
Decida se existe UM corte viral pronto. Voce ve o frame: use-o. Reacao sem evento visivel e corte ruim.

Viral em gameplay (GTA em particular):
- reacao genuina e forte (raiva, choque, riso) com CAUSA visivel na tela
- jogada decisiva ou erro absurdo, com reacao
- bug/glitch engraçado do jogo, NPC surreal, fisica quebrada
- momento de descoberta (mecanica nova, easter egg, cutscene inesperada)
- frase curta e afiada que funcione sozinha

Nao vira corte:
- fala generica ("vou pegar agua", "calma ai")
- gritaria sem causa visivel
- explicacao que precisa de 2 minutos de contexto
- nada acontecendo na tela
- audio clipado/estourado ou fala inaudivel

Regras do corte:
- comecar ~1s antes do gatilho, terminar quando a reacao morre, sem sobra
- a janela recebida costuma ser maior que o corte ideal: cortar o excesso, nao esticar
- duracao alvo 15-37s; prefira 20-30s, e so passe de 30 se a reacao realmente durar
- duracao 15-40s
- o gancho (hook) precisa ser legivel em 2s sem som

Voce tambem escolhe o enquadramento vertical:
- "face": zoom na facecam. Use quando a REACAO do streamer e o conteudo (cara de choque,
  raiva, riso). O jogo vira contexto, nao importa.
- "pip": gameplay em tela cheia + facecam ampliada no canto. Use quando os dois importam
  (jogada + reacao). E o padrao seguro.
- "game": so gameplay, sem facecam. Use quando o rosto nao reage ou nao acrescenta.

Responda SOMENTE JSON valido:
{
  "score": 0-10,
  "keep": true|false,
  "start_s": numero relativo ao inicio da janela,
  "end_s": numero relativo ao inicio da janela,
  "layout": "face"|"pip"|"game",
  "title": "titulo PT-BR, max 60 chars, concreto, sem clickbait vazio",
  "hook": "texto na tela nos 2 primeiros segundos, MAIUSCULO, max 32 chars",
  "caption": "legenda PT-BR para o post, 1-2 frases, tom de quem assistiu",
  "hashtags": ["#gta6", "#gameplay", "..."],
  "why": "1 frase justificando"
}"""

FALLBACK = {
    "score": 0.0,
    "keep": False,
    "start_s": 0.0,
    "end_s": 30.0,
    "layout": "game",
    "title": "",
    "hook": "",
    "caption": "",
    "hashtags": [],
    "why": "sem classificador",
}


def extract_frames(
    video: Path,
    start_s: float,
    dur_s: float,
    out_dir: Path,
    count: int = 3,
    width: int = 640,
) -> list[str]:
    """3 frames em base64 (jpeg) para o LLM multimodal 'ver' o momento."""
    out_dir.mkdir(parents=True, exist_ok=True)
    frames: list[str] = []
    for i in range(count):
        at = start_s + dur_s * (0.15 + 0.7 * i / max(1, count - 1))
        dest = out_dir / f"f{i}.jpg"
        try:
            subprocess.run(
                [
                    find_exe("ffmpeg"),
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{max(0.0, at):.3f}",
                    "-i",
                    str(video),
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={width}:-2",
                    "-q:v",
                    "4",
                    str(dest),
                ],
                capture_output=True,
                timeout=60,
            )
            if dest.exists() and dest.stat().st_size > 0:
                frames.append(base64.b64encode(dest.read_bytes()).decode("ascii"))
        except Exception:
            continue
    return frames


def _user_prompt(
    transcript: dict[str, Any] | None,
    signals: dict[str, float],
    peak_rel: float,
    duration: float,
    chat_peak: float = 0.0,
) -> str:
    lines = []
    if transcript:
        for seg in transcript.get("segments") or []:
            lines.append(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text']}")
    # nunca deixar a transcricao existir e o juiz ler como silencio
    body = "\n".join(lines) or (transcript.get("text") if transcript else "") or "(silencio)"

    return (
        f"Janela de {duration:.0f}s. Pico de energia do audio em {peak_rel:.0f}s.\n"
        f"Z-scores: audio {signals.get('loudness', 0):.2f}, "
        f"onset {signals.get('flux', 0):.2f}, chat {signals.get('chat', 0):.2f}"
        + (f", pico de chat em {chat_peak:.0f}s" if chat_peak else "")
        + "\n\nA transcricao vem do audio inteiro da live, entao mistura fala do streamer "
        "com dialogo de personagem, radio do jogo e musica. Fala de personagem do jogo "
        "NAO e reacao do streamer.\n"
        f"\nTranscricao:\n{body}"
    )


def _jev_state(
    transcript: dict[str, Any] | None,
    signals: dict[str, float],
    duration: float,
    frames: list[str] | None,
) -> list[Any]:
    lines = []
    if transcript:
        for seg in transcript.get("segments") or []:
            lines.append(f"[{seg['start']:.1f}-{seg['end']:.1f}] {seg['text']}")
    body = "\n".join(lines) or (transcript.get("text") if transcript else "") or "(silencio)"
    head = (
        f"Trecho de {duration:.0f}s de uma live de GTA V. "
        f"Z-scores: audio {signals.get('loudness', 0):.2f}, "
        f"onset {signals.get('flux', 0):.2f}, chat {signals.get('chat', 0):.2f}. "
        "A transcricao mistura fala do streamer com dialogo do jogo.\n"
        f"Transcricao:\n{body}"
    )
    state: list[Any] = [head]
    for f in frames or []:
        state.append(jev.image_part(f))
    return state


def _jev_gate(
    transcript: dict[str, Any] | None,
    signals: dict[str, float],
    duration: float,
    frames: list[str] | None,
    has_facecam: bool,
    cfg: dict[str, Any],
) -> dict[str, Any] | None:
    criteria = [
        "nada acontece, silencio ou menu",
        "fala generica, sem evento",
        "alguma reacao do streamer",
        "reacao forte com evento visivel na tela",
        "momento unico e inesperado com reacao forte",
    ]
    questions: dict[str, Any] = {
        "viral": {
            "type": "score",
            "instructions": "Quao bom seria este trecho como corte viral?",
            "criteria": criteria,
        },
        "evento": {
            "type": "noul",
            "instructions": "Ha um evento visivel na tela (jogada, bug, cena) e nao so conversa?",
        },
    }
    if has_facecam:
        questions["layout"] = {
            "type": "choice",
            "instructions": "Melhor enquadramento vertical para este trecho",
            "criteria": {
                "pip": "gameplay importa e a reacao do streamer tambem",
                "face": "o rosto do streamer e o conteudo",
                "game": "so o gameplay, rosto nao acrescenta",
            },
        }

    res = jev.decide(
        _jev_state(transcript, signals, duration, frames),
        questions,
        model=str(cfg.get("model") or jev.DEFAULT_MODEL),
    )
    if not res:
        return None
    answers = res["answers"]
    viral = answers.get("viral") or {}
    if viral.get("type") == "refusal":
        return None

    raw = float(viral.get("score") or 0.0)
    score = round(raw / 4.0 * 10.0, 1)
    evento = float((answers.get("evento") or {}).get("noul") or 0.0)
    layout = str((answers.get("layout") or {}).get("choice") or "game")
    if not has_facecam or layout not in ("pip", "face", "game"):
        layout = "game"

    min_score = float(cfg.get("min_score", 5.5))
    min_event = float(cfg.get("min_event", 0.5))
    keep = score >= min_score and evento >= min_event
    return {
        "score": score,
        "keep": keep,
        "layout": layout,
        "confidence": float(viral.get("confidence") or 0.0),
        "event_score": round(evento, 3),
        "why": f"jev: viral {score:.1f}/10, evento {evento:.2f}",
        "_gate": {
            "model": res.get("model"),
            "cost": float((res.get("usage") or {}).get("cost") or 0.0),
            "ms": res.get("ms"),
            "tokens": int((res.get("usage") or {}).get("input_tokens") or 0),
        },
    }


def classify(
    router: LLMRouter,
    transcript: dict[str, Any] | None,
    signals: dict[str, float],
    peak_rel: float,
    duration: float,
    frames: list[str] | None = None,
    chat_peak: float = 0.0,
    has_facecam: bool = False,
    gate_cfg: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Cascata: Jev decide (barato/rapido), LLM escreve a copy so no aprovado."""
    gate_cfg = gate_cfg or {}
    mode = str(gate_cfg.get("mode", "llm"))
    jev_cfg = gate_cfg.get("jev") or {}
    gate: dict[str, Any] | None = None

    if mode in ("cascade", "jev") and jev_cfg.get("enabled") and jev.ready():
        gate = _jev_gate(
            transcript, signals, duration, frames, has_facecam, jev_cfg
        )
        if gate is not None and mode == "jev":
            return {**FALLBACK, **gate, "title": "", "hook": "", "caption": "",
                    "hashtags": [], "judge": "jev"}
        if gate is not None and not gate["keep"]:
            # reprovado no gate: nao paga LLM
            return {**FALLBACK, **gate, "title": "", "hook": "", "caption": "",
                    "hashtags": [], "judge": "jev", "_usage": None}

    if not router:
        return {**FALLBACK, **(gate or {})}

    user_text = _user_prompt(transcript, signals, peak_rel, duration, chat_peak)
    if has_facecam:
        user_text += "\n\nFacecam do streamer: detectada. Voce pode usar layout face/pip/game."
    else:
        user_text += "\n\nFacecam: NAO detectada. Use obrigatoriamente layout game."
    try:
        if frames:
            verdict = router.chat_json_with_images(SYSTEM, user_text, frames)
        else:
            verdict = router.chat_json(SYSTEM, user_text)
    except Exception as exc:
        # LLM caiu: se o gate do Jev aprovou, ainda vale entregar o corte sem copy
        if gate and gate.get("keep"):
            return {**FALLBACK, **gate, "title": "", "hook": "", "caption": "",
                    "hashtags": [], "judge": "jev", "why": gate["why"] + " (llm falhou)"}
        return {**FALLBACK, "why": f"llm falhou: {exc}"}

    merged = dict(FALLBACK)
    merged.update({k: v for k, v in verdict.items() if not k.startswith("_")})
    merged["_provider"] = verdict.get("_provider")
    merged["_model"] = verdict.get("_model")
    merged["_usage"] = verdict.get("_usage")
    merged["judge"] = "llm"
    if gate:
        merged["_gate"] = gate.get("_gate")
        merged["gate_score"] = gate.get("score")
    merged.setdefault("hashtags", [])
    if isinstance(merged["hashtags"], str):
        merged["hashtags"] = [h for h in merged["hashtags"].split() if h.startswith("#")]
    if not has_facecam or merged.get("layout") not in ("face", "pip", "game"):
        merged["layout"] = "game"
    return merged


def _snap_back(value: float, boundaries: list[float], tol: float = 2.5) -> float:
    """Puxa o inicio para o comeco de uma fala (nao cortar no meio da palavra)."""
    prior = [b for b in boundaries if b <= value + 0.6]
    if prior:
        best = max(prior)
        if value - best <= tol:
            return best
    return value


def _snap_forward(value: float, boundaries: list[float], tol: float = 3.0) -> float:
    """Empurra o fim para o termino de uma fala (nao cortar a reacao no meio)."""
    nxt = [b for b in boundaries if b >= value - 0.6]
    if nxt:
        best = min(nxt)
        if best - value <= tol:
            return best
    return value


def choose_bounds(
    verdict: dict[str, Any],
    transcript: dict[str, Any] | None,
    peak_rel: float,
    ctx_len: float,
    min_s: float,
    max_s: float,
    fallback_pre: float = 10.0,
    fallback_post: float = 20.0,
) -> dict[str, float]:
    """Converte start_s/end_s do modelo em limites reais do corte."""
    raw_start = verdict.get("start_s")
    raw_end = verdict.get("end_s")
    if raw_start is None or raw_end is None:
        start = max(0.0, peak_rel - fallback_pre)
        end = min(ctx_len, peak_rel + fallback_post)
    else:
        start, end = float(raw_start), float(raw_end)

    start = max(0.0, min(start, ctx_len - 1.0))
    end = max(start + 1.0, min(end, ctx_len))

    segs = (transcript or {}).get("segments") or []
    if segs:
        start = _snap_back(start, [s["start"] for s in segs])
        end = _snap_forward(end, [s["end"] for s in segs])

    if end - start < min_s:
        missing = min_s - (end - start)
        end = min(ctx_len, end + missing)          # estende o fim primeiro
        start = max(0.0, start - (min_s - (end - start)))
    if end - start > max_s:
        end = start + max_s

    return {"start": round(start, 2), "end": round(max(start + 1.0, end), 2)}


def heuristic(signals: dict[str, float], peak_rel: float) -> dict[str, Any]:
    z = max(
        signals.get("loudness", 0.0), signals.get("chat", 0.0) * 0.8
    )
    score = max(0.0, min(10.0, 3.0 + z * 1.4))
    return {
        **FALLBACK,
        "score": round(score, 1),
        "keep": score >= 6.0,
        "start_s": max(0.0, peak_rel - 8.0),
        "end_s": peak_rel + 12.0,
        "title": f"Pico @ {int(peak_rel)}s",
        "hook": f"PICO {int(peak_rel)}s",
        "why": "heuristica de audio/chat (sem LLM)",
    }
