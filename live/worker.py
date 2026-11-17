"""Loop por stream: janela deslizante -> gate -> ASR -> classificador -> corte."""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np

from pipeline import audio as audio_mod
from pipeline import moments as moments_mod
from pipeline.ingest import probe_duration
from pipeline.render import make_thumb, render_clip
from pipeline.render import probe_size
from pipeline.util import log, save_json

from . import classify as classify_mod
from . import costs
from .asr import ASR
from .capture import build_capture_cmd, capture_process, resolve_stream_url
from .chatlive import LiveChat
from .db import DB
from .facecam import FacecamCache, detect_in_range
from .facecam import confirm as confirm_face
from .llm import LLMRouter
from .ring import RingBuffer
from .twitch_irc import TwitchIRC, channel_from_url


def _log(db: DB | None, slug: str, level: str, msg: str) -> None:
    log(f"[{slug}] {level}: {msg}")
    if db is not None:
        try:
            db.log(slug, level, msg)
        except Exception:
            pass


def _shift(transcript: dict[str, Any] | None, delta: float) -> dict[str, Any] | None:
    if not transcript:
        return None
    segs = []
    for seg in transcript["segments"]:
        segs.append(
            {
                "start": max(0.0, seg["start"] + delta),
                "end": max(0.0, seg["end"] + delta),
                "text": seg["text"],
                "words": [
                    {
                        "start": max(0.0, w["start"] + delta),
                        "end": max(0.0, w["end"] + delta),
                        "word": w["word"],
                    }
                    for w in seg.get("words", [])
                ],
            }
        )
    return {**transcript, "segments": segs}


def process_cycle(
    *,
    ring: RingBuffer,
    work_dir: Path,
    cfg: Any,
    router: LLMRouter | None,
    asr: ASR | None,
    chat: LiveChat | None = None,
    db: DB | None = None,
    stream_id: int | None = None,
    slug: str = "test",
    out_dir: Path | None = None,
    peak_z: float | None = None,
    min_score: float | None = None,
    recent: list[float] | None = None,
    force_keep: bool = False,
    transcript_stub: dict[str, Any] | None = None,
    face: dict[str, Any] | None = None,
    face_cache: Any | None = None,
    template: str | None = None,
) -> list[dict[str, Any]]:
    live_cfg = cfg["live"]
    moments_cfg = dict(cfg["moments"])
    from .templates import resolve as resolve_template

    render_cfg, brand_cfg = resolve_template(cfg, template)
    cls_cfg = cfg["classify"]

    if peak_z is not None:
        moments_cfg["peak_z"] = peak_z
    gate = float(min_score if min_score is not None else cls_cfg.get("min_score", 7.0))

    span = float(live_cfg["window_s"])
    work_dir.mkdir(parents=True, exist_ok=True)
    # nome por processo: duas instancias no mesmo work_dir nao podem se atropelar
    pid = os.getpid()
    window = work_dir / f"window_{pid}.mp4"
    if window.exists():
        window.unlink()
    if not ring.materialize(span, window):
        return []

    dur = probe_duration(window)
    if dur < 10:
        return []
    win_start_wall = time.time() - dur

    if face is None and face_cache is not None:
        try:
            face = face_cache.get(window)
        except Exception as exc:
            _log(db, slug, "warn", f"facecam falhou: {exc}")
            face = None

    wav = work_dir / f"window_{pid}.wav"
    if wav.exists():
        wav.unlink()
    audio_mod.extract_wav(window, wav)
    samples = audio_mod.read_wav(wav)
    secs = len(samples) // audio_mod.SR
    if secs < 10:
        return []
    profile = audio_mod.analyze(samples)

    chat_snapshot = chat.snapshot(win_start_wall, secs) if chat else None
    series = moments_mod.score_series(profile, chat_snapshot, moments_cfg["weights"])
    peaks = moments_mod.pick_peaks(series, moments_cfg)

    ctx_pre = float(moments_cfg.get("context_pre_s", 12))
    ctx_post = float(moments_cfg.get("context_post_s", 25))
    min_clip = float(moments_cfg["min_clip_s"])
    max_clip = float(moments_cfg["max_clip_s"])
    cycle = float(live_cfg["cycle_s"])
    lo = max(0.0, secs - ctx_post - cycle - 2)
    hi = secs - ctx_post
    ready = [p for p in peaks if lo <= p["peak_s"] <= hi]

    recent = recent if recent is not None else []
    min_sep = float(moments_cfg["min_sep_s"])

    results: list[dict[str, Any]] = []
    for cand in sorted(ready, key=lambda c: c["peak_s"]):
        peak_s = float(cand["peak_s"])
        peak_wall = win_start_wall + peak_s

        # dedupe por tempo de parede: o mesmo evento aparece em janelas vizinhas
        if any(abs(peak_wall - t) < min_sep for t in recent):
            continue
        recent.append(peak_wall)
        if len(recent) > 60:
            del recent[: len(recent) - 60]

        # dedupe contra clipes JA gravados (sobrevive a restart)
        if db is not None and stream_id:
            try:
                ja = db.overlapping_clip(
                    int(stream_id), peak_wall - ctx_pre, peak_wall + ctx_post
                )
                if ja:
                    _log(db, slug, "info", f"evento ja virou clipe #{ja} -> pulando")
                    continue
            except Exception:
                pass

        # janela de contexto: onde o modelo pode escolher o corte
        ctx_start = max(0.0, peak_s - ctx_pre)
        ctx_end = min(float(secs), peak_s + ctx_post)
        ctx_len = ctx_end - ctx_start
        if ctx_len < min_clip:
            continue

        # --- transcricao (janela de contexto) ---
        transcript = None
        asr_backend = None
        if asr:
            slice_path = work_dir / f"asr_{pid}.wav"
            audio_mod.write_wav_slice(samples, slice_path, ctx_start, ctx_end)
            raw = asr.transcribe(slice_path)
            if raw:
                asr_backend = raw.get("backend")
                transcript = _shift(raw, 0.0)
                if db is not None:
                    c = costs.asr_cost(
                        cfg["pricing"], asr_backend, float(raw.get("usage_seconds") or 0)
                    )
                    if c > 0:
                        db.add_usage(
                            slug, "asr", c,
                            {"backend": asr_backend, "s": raw.get("usage_seconds")},
                        )
        elif transcript_stub:
            transcript = _shift(transcript_stub, 0.0)

        # --- frames para o LLM "olhar" o momento ---
        frames: list[str] = []
        want_frames = router is not None or str(cls_cfg.get("mode")) in ("cascade", "jev")
        if want_frames:
            frames = classify_mod.extract_frames(
                window,
                ctx_start,
                ctx_len,
                work_dir / "frames",
                count=int(cls_cfg.get("frames", 3)),
            )

        signals = {k: float(series[k][int(peak_s)]) for k in ("loudness", "flux", "chat")}
        verdict = classify_mod.classify(
            router,
            transcript,
            signals,
            peak_s - ctx_start,
            ctx_len,
            frames=frames or None,
            chat_peak=float(np.argmax(chat_snapshot["rate"])) if chat_snapshot else 0.0,
            has_facecam=bool(face),
            gate_cfg=cls_cfg,
        ) if router else classify_mod.heuristic(signals, peak_s - ctx_start)

        score = float(verdict.get("score") or 0.0)
        if db is not None and verdict.get("_gate"):
            g = verdict["_gate"]
            if float(g.get("cost") or 0) > 0:
                db.add_usage(
                    slug, "jev", float(g["cost"]),
                    {"model": g.get("model"), "ms": g.get("ms"), "tokens": g.get("tokens")},
                )
        if db is not None and verdict.get("_usage"):
            c = costs.llm_cost(cfg["pricing"], verdict.get("_model"), verdict.get("_usage"))
            if c > 0:
                db.add_usage(
                    slug, "llm", c,
                    {"model": verdict.get("_model"), **verdict["_usage"]},
                )
        _log(db, slug, "info", (
            f"candidato @{time.strftime('%H:%M:%S', time.localtime(peak_wall))} "
            f"score={score} keep={verdict.get('keep')} "
            f"layout={verdict.get('layout')} — {verdict.get('why') or 'sem justificativa'}"
        ))
        if not force_keep and (not verdict.get("keep") or score < gate):
            continue

        # limites do corte decididos pelo modelo, ancorados em fala
        bounds = classify_mod.choose_bounds(
            verdict, transcript, peak_s - ctx_start, ctx_len, min_clip, max_clip,
            ctx_pre, ctx_post,
        )
        clip_start = ctx_start + bounds["start"]
        clip_end = ctx_start + bounds["end"]
        clip_len = clip_end - clip_start
        clip_transcript = _shift(transcript, ctx_start - clip_start)
        _log(db, slug, "info", (
            f"corte {bounds['start']:.1f}s..{bounds['end']:.1f}s "
            f"da janela ({clip_len:.1f}s)"
        ))

        # clipe aprovado: confere a facecam neste trecho, nunca no cache
        layout = str(verdict.get("layout") or "game")
        clip_face = None
        if layout in ("pip", "face"):
            if face is None:
                layout = "game"
            else:
                clip_face = confirm_face(window, clip_start, clip_len, face)
                if clip_face is None:
                    fresh = detect_in_range(window, clip_start, clip_len)
                    if fresh:
                        _log(db, slug, "info", "facecam mudou de lugar -> usando a nova posicao")
                        clip_face = fresh
                        if face_cache is not None:
                            face_cache.current = fresh
                            face_cache.checked_at = time.time()
                            save_json(face_cache.path, fresh)
                if clip_face is None:
                    _log(db, slug, "warn", "facecam nao confirmada no clipe -> layout game")
                    layout = "game"

        out_v = out_dir or cfg.out_dir
        day = time.strftime("%Y-%m-%d", time.localtime(peak_wall))
        folder = out_v / day / slug
        stamp = time.strftime("%H%M%S", time.localtime(peak_wall))
        out_path = folder / f"{slug}_{stamp}_{int(score * 10):03d}.mp4"

        try:
            focus = None
            if str(render_cfg.get("mode")) == "crop":
                from pipeline.motion import focus_x as compute_focus

                size = probe_size(window)
                if size:
                    focus = compute_focus(
                        window, clip_start, clip_len, size[0], size[1],
                        int(render_cfg["width"]), int(render_cfg["height"]),
                    )
                    _log(db, slug, "info", f"enquadramento por movimento: {focus:.2f}")
            render_clip(
                window,
                clip_start,
                clip_end,
                out_path,
                render_cfg,
                clip_transcript,
                verdict.get("hook") or "",
                branding=brand_cfg,
                layout=layout,
                face=clip_face,
                focus_x=focus,
            )
        except Exception as exc:
            _log(db, slug, "error", f"render falhou: {exc}")
            log(f"[{slug}] render falhou: {exc}")
            continue

        thumb = make_thumb(out_path)
        title = (verdict.get("title") or "").strip() or f"Corte {stamp}"
        used_face = clip_face or face
        record = {
            "slug": slug,
            "score": score,
            "title": title,
            "hook": verdict.get("hook") or "",
            "caption": verdict.get("caption") or "",
            "hashtags": verdict.get("hashtags") or [],
            "why": verdict.get("why") or "",
            "start_ts": round(win_start_wall + clip_start, 2),
            "end_ts": round(win_start_wall + clip_end, 2),
            "path": str(out_path),
            "thumb": str(thumb) if thumb else None,
            "text": transcript["text"] if transcript else "",
            "meta": {
                "signals": signals,
                "asr": asr_backend,
                "provider": verdict.get("_provider") or verdict.get("provider"),
                "model": verdict.get("_model"),
                "peak_s": peak_s,
                "window_s": round(dur, 1),
                "layout": layout,
                "facecam": {
                    k: used_face[k]
                    for k in ("x", "y", "w", "confidence")
                    if used_face and k in used_face
                },
            },
        }

        out_path.with_suffix(".txt").write_text(
            "\n".join(
                [title, "", record["caption"], "", " ".join(record["hashtags"])]
            ).strip(),
            encoding="utf-8",
        )
        save_json(out_path.with_suffix(".json"), record)

        if db and stream_id:
            clip_id = db.add_clip(
                stream_id,
                status="rendered",
                score=score,
                title=title,
                hook=record["hook"],
                caption=record["caption"],
                hashtags=" ".join(record["hashtags"]),
                why=record["why"],
                start_ts=record["start_ts"],
                end_ts=record["end_ts"],
                path=record["path"],
                thumb=record["thumb"],
                text=record["text"],
                meta=record["meta"],
            )
            record["id"] = clip_id

            # publicacao automatica condicionada a nota
            try:
                from .publish import publish_clip, should_auto_publish

                go, limiar = should_auto_publish(cfg, score)
                if go:
                    publish_clip(db, cfg, clip_id)
                    _log(db, slug, "info", f"auto-publicado (nota {score} >= {limiar})")
                elif limiar:
                    _log(db, slug, "info", f"nao publicou sozinho: nota {score} < {limiar}")
            except Exception as exc:
                _log(db, slug, "warn", f"auto-publicacao falhou: {exc}")
        log(f"[{slug}] CLIP {out_path.name} score={score} ({clip_len:.0f}s)")
        results.append(record)

    return results


class StreamWorker(threading.Thread):
    def __init__(
        self,
        row: Any,
        cfg: Any,
        db: DB,
        router: LLMRouter | None,
        asr: ASR | None,
        stop: threading.Event,
        source_override: str | None = None,
    ):
        super().__init__(daemon=True, name=f"worker-{row['slug']}")
        self.row = row
        self.cfg = cfg
        self.db = db
        self.router = router
        self.asr = asr
        self.stop = stop
        self.source_override = source_override
        self.slug = row["slug"]
        self.work = cfg.work_dir / self.slug
        self.ring = RingBuffer(
            self.work / "ring",
            keep_seconds=int(cfg["live"]["buffer_seconds"]),
        )
        self.recent: list[float] = []
        self.face_cache = FacecamCache(self.work, cfg["facecam"])
        self.template = self._row_template()
        self.chat: LiveChat | None = None
        self._proc = None
        self._backoff = 5.0
        self._idle_logged = False

    # -- captura -------------------------------------------------------
    def _ensure_capture(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return
        if self._proc is not None:
            log(f"[{self.slug}] capture morreu (rc={self._proc.poll()}), reiniciando")
            self.stop.wait(self._backoff)
            self._backoff = min(60.0, self._backoff * 1.7)
        url = None
        if not self.source_override:
            try:
                url = resolve_stream_url(self.row["url"], self.cfg["live"]["quality"])
            except Exception as exc:
                _log(self.db, self.slug, "error", f"resolve falhou: {exc}")
                log(f"[{self.slug}] resolve falhou: {exc}")
                self.stop.wait(min(60.0, self._backoff * 2))
                self._backoff = min(60.0, self._backoff * 1.7)
                return
        try:
            cmd = build_capture_cmd(
                self.ring, url=url, source=self.source_override
            )
            dropped = self.ring.reset()
            if dropped:
                log(f"[{self.slug}] ring limpo ({dropped} segmentos antigos)")
            self._proc = capture_process(cmd, self.work / "logs" / "capture.log")
        except Exception as exc:
            _log(self.db, self.slug, "error", f"capture falhou: {exc}")
            self.stop.wait(self._backoff)
            self._backoff = min(60.0, self._backoff * 1.7)

    # -- loop ----------------------------------------------------------
    def _row_template(self) -> str | None:
        try:
            row = self.db.conn().execute(
                "SELECT template FROM streams WHERE slug=?", (self.slug,)
            ).fetchone()
            return (row["template"] if row else None) or None
        except Exception:
            return None

    def _refresh(self) -> None:
        """Recarrega config e template do banco: mudanca no painel vale no proximo ciclo."""
        try:
            from pipeline.config import Config

            self.cfg = Config.load()
            self.template = self._row_template()
        except Exception as exc:
            log(f"[{self.slug}] recarga de config falhou: {exc}")

    def run(self) -> None:
        min_buffer = float(self.cfg["live"]["min_buffer_s"])
        cycle = float(self.cfg["live"]["cycle_s"])
        log(f"[{self.slug}] worker iniciado (buffer {min_buffer:.0f}s)")

        if self.cfg["live"].get("chat_enabled", True) and not self.source_override:
            channel = channel_from_url(self.row["url"])
            if channel:
                self.chat = TwitchIRC(channel, self.stop)
            else:
                self.chat = LiveChat(self.row["url"], self.stop)
            self.chat.start()
            log(f"[{self.slug}] chat: {'irc' if channel else 'chat-downloader'}")

        while not self.stop.is_set():
            try:
                self._refresh()
                self._ensure_capture()
                removed = self.ring.gc()
                if removed:
                    log(f"[{self.slug}] ring: -{removed} segmentos")
                if self.ring.buffer_seconds() < min_buffer:
                    self.stop.wait(cycle)
                    continue

                # captura parada/offline: nao reprocessar buffer velho (gastaria API)
                age = self.ring.newest_age()
                if age is None or age > max(45.0, cycle * 2):
                    if not self._idle_logged:
                        log(f"[{self.slug}] sem segmento novo ha {age if age else 0:.0f}s -> aguardando a live")
                        self._idle_logged = True
                    self.stop.wait(cycle)
                    continue
                self._idle_logged = False
                self._backoff = 5.0
                process_cycle(
                    ring=self.ring,
                    work_dir=self.work,
                    cfg=self.cfg,
                    router=self.router,
                    asr=self.asr,
                    chat=self.chat,
                    db=self.db,
                    stream_id=int(self.row["id"]),
                    slug=self.slug,
                    recent=self.recent,
                    face_cache=self.face_cache,
                    template=self.template,
                )
            except Exception as exc:
                _log(self.db, self.slug, "error", f"cycle falhou: {exc}")
                log(f"[{self.slug}] cycle falhou: {exc}")
            self.stop.wait(cycle)

        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        log(f"[{self.slug}] worker encerrado")

