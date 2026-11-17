"""Corte + reframe vertical + legenda queimada (ffmpeg/libass)."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from .util import find_exe, log, run

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font},{sub_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,6,3,2,64,64,{sub_mv},1
Style: Karaoke,{font},{karaoke_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,4,2,48,48,{karaoke_mv},1
Style: Hook,{font},{hook_size},&H0000FFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,4,8,56,56,140,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _ass_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\n", " ")
    )


def _wrap(text: str, max_chars: int, max_lines: int = 2) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        candidate = f"{cur} {word}".strip()
        if len(candidate) <= max_chars or not cur:
            cur = candidate
        else:
            lines.append(cur)
            cur = word
        if len(lines) == max_lines:
            break
    if cur and len(lines) < max_lines:
        lines.append(cur)
    return lines


def build_ass(
    transcript: dict[str, Any] | None,
    hook: str,
    clip_len: float,
    cfg: dict[str, Any],
) -> str:
    w, h = int(cfg["width"]), int(cfg["height"])
    sub_size = int(cfg.get("sub_size") or 76)
    # ~0.55 * fontsize px por caractere
    max_chars = max(12, int((w - 128) / (sub_size * 0.55)))

    out = [
        ASS_HEADER.format(
            w=w,
            h=h,
            font=cfg.get("font") or "Arial Black",
            sub_size=sub_size,
            karaoke_size=int(cfg.get("karaoke_size") or 96),
            karaoke_mv=int(cfg.get("karaoke_margin_v") or 300),
            hook_size=int(cfg.get("hook_size") or 92),
            sub_mv=int(cfg.get("sub_margin_v") or 300),
        )
    ]

    if hook and cfg.get("hook_caption", True):
        text = hook.upper().strip()
        margin = 56
        usable = w - 2 * margin
        hook_size = int(cfg.get("hook_size") or 92)
        chosen = lines = None

        # 1) tenta 1 linha sem encolher demais (mantem impacto)
        for size in range(hook_size, int(hook_size * 0.8), -4):
            max_chars = max(8, int(usable / (size * 0.56)))
            candidate = _wrap(text, max_chars, 1)
            if " ".join(candidate) == text:
                chosen, lines = size, candidate
                break

        # 2) senao, 2 linhas no maior tamanho que couber inteiro
        if lines is None:
            for size in range(hook_size, 38, -4):
                max_chars = max(8, int(usable / (size * 0.56)))
                candidate = _wrap(text, max_chars, 2)
                if sum(len(line) for line in candidate) >= len(text) - 1:
                    chosen, lines = size, candidate
                    break

        if lines:
            body = "\\N".join(_ass_escape(line) for line in lines)
            out.append(
                "Dialogue: 0,{},{},Hook,,0,0,0,,{{\\fs{}}}{}".format(
                    _ass_time(0.05), _ass_time(min(6.0, clip_len)), chosen, body
                )
            )

    if transcript:
        words = _flatten_words(transcript)
        if words:
            out.extend(_word_events(words, clip_len, cfg, w))
        else:
            for seg in transcript["segments"]:
                text = (seg["text"] or "").strip()
                if not text:
                    continue
                lines = _wrap(text, max_chars)
                if not lines:
                    continue
                body = "\\N".join(_ass_escape(line) for line in lines)
                start = max(0.0, seg["start"])
                end = min(clip_len, seg["end"])
                if end - start < 0.25:
                    end = start + 0.25
                out.append(
                    f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Sub,,0,0,0,,{body}"
                )
    return "\n".join(out) + "\n"


def _flatten_words(transcript: dict[str, Any]) -> list[dict[str, Any]]:
    words: list[dict[str, Any]] = []
    for seg in transcript.get("segments") or []:
        for w in seg.get("words") or []:
            text = (w.get("word") or "").strip()
            if not text:
                continue
            words.append(
                {"word": text, "start": float(w.get("start") or 0.0), "end": float(w.get("end") or 0.0)}
            )
    words.sort(key=lambda x: x["start"])
    return words


def _word_cards(
    words: list[dict[str, Any]], max_words: int, max_chars: int
) -> list[list[dict[str, Any]]]:
    cards: list[list[dict[str, Any]]] = []
    cur: list[dict[str, Any]] = []
    for word in words:
        candidate = cur + [word]
        joined = " ".join(x["word"] for x in candidate)
        if cur and (len(candidate) > max_words or len(joined) > max_chars):
            cards.append(cur)
            cur = [word]
        else:
            cur = candidate
    if cur:
        cards.append(cur)
    return cards


def _word_events(
    words: list[dict[str, Any]], clip_len: float, cfg: dict[str, Any], width: int
) -> list[str]:
    """Legenda estilo clipe viral: 2-3 palavras na tela, palavra atual em destaque."""
    size = int(cfg.get("karaoke_size") or 96)
    max_words = int(cfg.get("karaoke_words") or 3)
    usable = width - 128
    max_chars = max(10, int(usable / (size * 0.58)))
    accent = cfg.get("karaoke_accent") or "&H0000FFFF"  # amarelo (AABBGGRR)

    words = [w for w in words if w["start"] < clip_len]
    if not words:
        return []

    cards = _word_cards(words, max_words, max_chars)
    events: list[str] = []
    for ci, card in enumerate(cards):
        card_end = card[-1]["end"] or card[-1]["start"] + 0.4
        # cada palavra vira um evento: o resto do cartao fica visivel, a atual acende
        for wi, word in enumerate(card):
            start = max(0.0, word["start"])
            if wi + 1 < len(card):
                end = max(start + 0.1, card[wi + 1]["start"])
            else:
                end = max(start + 0.15, min(card_end, clip_len))
            end = min(end, clip_len)
            if end <= start:
                continue
            parts = []
            for xi, other in enumerate(card):
                txt = _ass_escape(other["word"])
                parts.append(f"{{\\c{accent}&}}{txt}{{\\c&HFFFFFF&}}" if xi == wi else txt)
            body = " ".join(parts)
            events.append(
                f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Karaoke,,0,0,0,,{{\\fs{size}}}{body}"
            )
    return events


def _escape_filter_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/").replace(":", "\\:")


def _fps_prefix(cfg: dict[str, Any]) -> str:
    """Descarta frames antes de filtrar: live de 60fps entregava 60 e saia a 30."""
    fps = int(cfg.get("fps") or 30)
    return f"fps={fps}," if fps > 0 else ""


def _game_chain(cfg: dict[str, Any], src: str = "0:v") -> str:
    w, h = int(cfg["width"]), int(cfg["height"])
    mode = cfg.get("mode", "pad_blur")
    pre = _fps_prefix(cfg) if src == "0:v" else ""
    if mode == "crop":
        focus = min(0.95, max(0.05, float(cfg.get("focus_x", 0.5))))
        return (
            f"[{src}]{pre}scale=-2:{h},crop={w}:{h}:(iw-{w})*{focus}:0,setsar=1[v0]"
        )
    if mode != "pad_blur":
        raise ValueError(f"render.mode invalido: {mode}")
    sigma = int(cfg.get("blur_sigma") or 22)
    return (
        f"[{src}]{pre}split=2[a][b];"
        f"[a]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},gblur=sigma={sigma},eq=brightness=-0.10[bg];"
        f"[b]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]"
    )


def _face_box(face: dict[str, Any]) -> tuple[int, int, int]:
    """Retangulo quadrado da facecam, seguro dentro do frame da fonte."""
    x = max(0, int(face["x"]))
    y = max(0, int(face["y"]))
    side = max(16, int(min(face["w"], face["h"])))
    sw = int(face.get("source_w") or 0)
    sh = int(face.get("source_h") or 0)
    if sw:
        side = min(side, sw - x)
    if sh:
        side = min(side, sh - y)
    side = max(16, side - (side % 2))
    return x, y, side


def _face_crop(face: dict[str, Any]) -> str:
    x, y, side = _face_box(face)
    return f"crop={side}:{side}:{x}:{y}"


def _face_chain(cfg: dict[str, Any], face: dict[str, Any]) -> str:
    """Zoom total na facecam: ela preenche o centro, fundo desfocado da propria facecam."""
    w, h = int(cfg["width"]), int(cfg["height"])
    sigma = int(cfg.get("blur_sigma") or 22)
    crop = _face_crop(face)
    return (
        f"[0:v]{_fps_prefix(cfg)}{crop},split=2[fa][fb];"
        f"[fa]scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},gblur=sigma={sigma},eq=brightness=-0.15[fbg];"
        f"[fb]scale={w}:{w}:flags=lanczos[ffg];"
        f"[fbg][ffg]overlay=(W-w)/2:(H-h)/2,setsar=1[v0]"
    )


def _pip_chain(cfg: dict[str, Any], face: dict[str, Any]) -> str:
    """Gameplay em tela cheia + facecam ampliada num canto.

    A facecam original do gameplay e desfocada para nao aparecer duplicada.
    """
    w, h = int(cfg["width"]), int(cfg["height"])
    pip = max(160, int(w * float(cfg.get("pip_scale", 0.37))))
    border = int(cfg.get("pip_border", 8))
    anchor = str(cfg.get("pip_position", "tr"))
    margin = int(cfg.get("pip_margin", 44))
    top = int(cfg.get("pip_offset_y", 400))
    blur = int(cfg.get("face_patch_blur", 18))

    if anchor in ("tr", "br"):
        px = f"W-{pip + 2 * border}-{margin}"
    else:
        px = str(margin)
    py = f"H-{pip + 2 * border}-{margin}" if anchor in ("br", "bl") else str(top)

    fx, fy, fside = _face_box(face)
    return (
        f"[0:v]{_fps_prefix(cfg)}crop={fside}:{fside}:{fx}:{fy},gblur=sigma={blur}[bp];"
        f"[0:v][bp]overlay={fx}:{fy}[gb];"
        f"{_game_chain(cfg, 'gb').replace('[v0]', '[g]')};"
        f"[0:v]{_fps_prefix(cfg)}{_face_crop(face)},scale={pip}:{pip}:flags=lanczos,"
        f"pad={pip + 2 * border}:{pip + 2 * border}:{border}:{border}:color=white@1[fc];"
        f"[g][fc]overlay={px}:{py},setsar=1[v0]"
    )


def _video_chain(
    cfg: dict[str, Any], layout: str = "game", face: dict[str, Any] | None = None
) -> str:
    if face and layout == "face":
        return _face_chain(cfg, face)
    if face and layout == "pip":
        return _pip_chain(cfg, face)
    return _game_chain(cfg)


def render_clip(
    source: Path,
    start_s: float,
    end_s: float,
    out_path: Path,
    cfg: dict[str, Any],
    transcript: dict[str, Any] | None,
    hook: str,
    branding: dict[str, Any] | None = None,
    layout: str = "game",
    face: dict[str, Any] | None = None,
    focus_x: float | None = None,
) -> Path:
    clip_len = max(1.0, end_s - start_s)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if focus_x is not None:
        cfg = {**cfg, "focus_x": focus_x}
    filt = _video_chain(cfg, layout, face)
    if cfg.get("burn_subs", True):
        ass_path = out_path.with_suffix(".ass")
        ass_path.write_text(
            build_ass(transcript, hook, clip_len, cfg), encoding="utf-8"
        )
        filt += f";[v0]ass=filename='{_escape_filter_path(ass_path)}'[v1]"
    else:
        filt += ";[v0]null[v1]"

    from cortai.branding import build as build_branding

    extra_inputs, brand_filter = build_branding("v1", "vout", 1, branding)
    filt += ";" + brand_filter

    log(f"[render] {out_path.name}  {start_s:.1f}s -> {end_s:.1f}s ({clip_len:.0f}s)")
    run(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            f"{start_s:.3f}",
            "-t",
            f"{clip_len:.3f}",
            "-i",
            str(source),
            *[arg for pair in extra_inputs for arg in pair],
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            str(cfg.get("preset", "veryfast")),
            "-crf",
            str(cfg.get("crf", 20)),
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(cfg.get("fps", 30)),
            "-c:a",
            "aac",
            "-b:a",
            str(cfg.get("audio_bitrate", "192k")),
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return out_path


def render_still(
    source: Path,
    at_s: float,
    out_path: Path,
    cfg: dict[str, Any],
    transcript: dict[str, Any] | None,
    hook: str,
    branding: dict[str, Any] | None = None,
    layout: str = "game",
    face: dict[str, Any] | None = None,
    focus_x: float | None = None,
) -> Path:
    """Mesmo visual do clipe, mas um unico frame (preview do builder)."""
    if focus_x is not None:
        cfg = {**cfg, "focus_x": focus_x}
    filt = _video_chain(cfg, layout, face)
    if cfg.get("burn_subs", True):
        ass_path = out_path.with_suffix(".ass")
        ass_path.write_text(build_ass(transcript, hook, 10.0, cfg), encoding="utf-8")
        filt += f";[v0]ass=filename='{_escape_filter_path(ass_path)}'[v1]"
    else:
        filt += ";[v0]null[v1]"
    from cortai.branding import build as build_branding

    extra_inputs, brand_filter = build_branding("v1", "vout", 1, branding)
    filt += ";" + brand_filter
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(source),
            *[arg for pair in extra_inputs for arg in pair],
            "-filter_complex",
            filt,
            "-map",
            "[vout]",
            # seek na SAIDA: mantem o tempo do ASS (hook/legenda) correto no frame
            "-ss",
            f"{max(0.0, at_s):.3f}",
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(out_path),
        ]
    )
    return out_path


def make_thumb(clip: Path, at_s: float = 1.0) -> Path | None:
    thumb = clip.with_suffix(".jpg")
    try:
        run(
            [
                find_exe("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{at_s}",
                "-i",
                str(clip),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(thumb),
            ]
        )
        return thumb
    except Exception:
        return None


def probe_size(path: Path) -> tuple[int, int] | None:
    try:
        out = run(
            [
                find_exe("ffprobe"),
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=p=0",
                str(path),
            ]
        )
        w, h = out.strip().split(",")[:2]
        return int(w), int(h)
    except Exception:
        return None


def estimate_bitrate_mbps(cfg: dict[str, Any]) -> float:
    w = int(cfg["width"])
    h = int(cfg["height"])
    crf = float(cfg.get("crf", 20))
    return round((w * h * float(cfg.get("fps", 30))) / 1e7 * (22 - crf) / 6, 2)


def _unused_guard(x: float) -> float:  # pragma: no cover
    return math.ceil(x)
