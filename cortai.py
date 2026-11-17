#!/usr/bin/env python
"""CLI do sistema de cortes para lives.

  python cortai.py add --url https://www.twitch.tv/canal
  python cortai.py run
  python cortai.py clips
  python cortai.py doctor
  python cortai.py selftest
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from pathlib import Path

from pipeline.config import Config
from pipeline.util import ROOT, find_exe, load_dotenv, log

from cortai.db import DB


def db_for(cfg: Config) -> DB:
    path = cfg.work_dir / "cortai.db"
    legacy = cfg.work_dir / "lives.db"
    if legacy.exists() and not path.exists():
        # migra o banco do nome antigo sem perder historico
        for suffix in ("", "-wal", "-shm"):
            src = Path(str(legacy) + suffix)
            if src.exists():
                src.replace(Path(str(path) + suffix))
        print("banco migrado: lives.db -> cortai.db")
    return DB(path)


def detect_platform(url: str) -> str:
    if "twitch.tv" in url:
        return "twitch"
    if "youtube.com" in url or "youtu.be" in url:
        return "youtube"
    if "kick.com" in url:
        return "kick"
    return "other"


def make_slug(url: str, platform: str) -> str:
    if platform == "youtube":
        m = re.search(r"[?&]v=([\w-]{6,})", url)
        if m:
            return f"yt-{m.group(1)}"
        m = re.search(r"/(?:channel|@)([\w.-]+)", url)
        if m:
            return f"yt-{m.group(1).lower()}"
    tail = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"[^\w.-]+", "-", tail).strip("-").lower() or "live"
    return slug[:40]


def cmd_add(cfg: Config, args: argparse.Namespace) -> int:
    db = db_for(cfg)
    platform = args.platform or detect_platform(args.url)
    slug = args.slug or make_slug(args.url, platform)
    sid = db.add_stream(slug, args.url, platform, args.title or "")
    print(f"live cadastrada: {slug} (id {sid}, {platform})")
    return 0


def cmd_rm(cfg: Config, args: argparse.Namespace) -> int:
    db = db_for(cfg)
    db.set_stream_status(args.slug, "stopped")
    print(f"{args.slug} parada")
    return 0


def cmd_list(cfg: Config, args: argparse.Namespace) -> int:
    from cortai.supervisor import status

    status(cfg, db_for(cfg))
    return 0


def cmd_run(cfg: Config, args: argparse.Namespace) -> int:
    from cortai.supervisor import run

    return run(
        cfg,
        db_for(cfg),
        only=args.only,
        source=args.source,
        once=args.once,
        minutes=args.minutes,
    )


def cmd_clips(cfg: Config, args: argparse.Namespace) -> int:
    db = db_for(cfg)
    rows = db.clips(limit=args.limit)
    if not rows:
        print("nenhum clipe ainda")
        return 0
    for r in rows:
        ts = time.strftime("%d/%m %H:%M:%S", time.localtime(r["created_at"]))
        print(f"[{r['id']:>3}] {ts}  score {r['score'] or 0:>4}  {r['title'] or '-'}")
        print(f"      {r['path']}")
    return 0


def cmd_doctor(cfg: Config, args: argparse.Namespace) -> int:
    ok = True

    def check(label: str, good: bool, hint: str = "") -> None:
        nonlocal ok
        mark = "OK " if good else "FAIL"
        if not good:
            ok = False
        print(f"  [{mark}] {label}" + (f"  -> {hint}" if not good and hint else ""))

    print("binarios:")
    for exe in ("ffmpeg", "ffprobe"):
        try:
            path = find_exe(exe)
            check(exe, True)
            print(f"         {path}")
        except FileNotFoundError as exc:
            check(exe, False, str(exc))

    check("streamlink (opcional, mas melhor p/ twitch)",
          __import__("cortai.capture", fromlist=["streamlink_cmd"]).streamlink_cmd() is not None,
          "pip install streamlink")
    try:
        import yt_dlp  # noqa: F401

        check("yt-dlp", True)
    except Exception:
        check("yt-dlp", False, "pip install yt-dlp")
    try:
        import chat_downloader  # noqa: F401

        check("chat-downloader (sinal de chat)", True)
    except Exception:
        check("chat-downloader", False, "pip install chat-downloader")
    try:
        import cv2  # noqa: F401

        from cortai.facecam import ensure_model

        model = ensure_model()
        check(f"facecam: opencv {cv2.__version__} + YuNet", bool(model),
              "sem modelo a deteccao de facecam fica desligada")
    except Exception:
        check("facecam: opencv-python-headless", False, "pip install opencv-python-headless")

    print("chaves:")
    check("OPENROUTER_API_KEY (juiz)", bool(os.environ.get("OPENROUTER_API_KEY")))
    has_asr = bool(os.environ.get("GROQ_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    check("ASR: GROQ_API_KEY ou OPENAI_API_KEY", has_asr, "sem isso nao ha legenda")
    if not has_asr:
        try:
            import faster_whisper  # noqa: F401

            print("         faster-whisper local disponivel")
        except Exception:
            pass

    print("config:")
    providers = cfg["llm"].get("providers") or []
    check(f"providers configurados ({len(providers)})", bool(providers))
    for p in providers:
        key = bool(os.environ.get(p.get("key_env", "")))
        print(f"         {p['name']}: {p['model']} [{p['key_env']} {'ok' if key else 'vazio'}]")
    check("branding/logo.png (opcional)", True)
    free = shutil.disk_usage(ROOT).free / 1e9
    need = float(cfg["live"]["buffer_seconds"]) * 0.5 / 60 * (cfg["live"].get("max_streams", 5))
    check(f"disco livre {free:.0f} GB", free > 5, "buffer de varias lives enche rapido")
    print(f"  [info] buffer ~{need:.0f} GB estimado para as lives configuradas")

    print("\npronto" if ok else "\nresolva os FAIL acima")
    return 0 if ok else 1


def cmd_selftest(cfg: Config, args: argparse.Namespace) -> int:
    """E2E sem internet: gera video sintetico, segmenta, detecta e corta."""
    from cortai import capture as cap
    from cortai.ring import RingBuffer
    from cortai.worker import process_cycle

    base = cfg.work_dir / "_selftest"
    if base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True)

    src = base / "source.mp4"
    log("[selftest] gerando video sintetico (40s, 2 explosioes de audio)")
    from pipeline.util import run as run_cmd

    run_cmd(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=1280x720:rate=30",
            "-f",
            "lavfi",
            "-i",
            "aevalsrc='0.02*random(0)+(0.9*random(0)+0.6*sin(2*PI*300*t))*"
            "(between(t,14,19)+between(t,28,34))':s=48000:d=40",
            "-t",
            "40",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-g",
            "60",
            "-keyint_min",
            "60",
            "-sc_threshold",
            "0",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(src),
        ]
    )

    ring = RingBuffer(base / "ring", keep_seconds=120, segment_seconds=4)
    log("[selftest] segmentando (buffer circular)")
    proc = cap.capture_process(
        cap.build_capture_cmd(ring, source=str(src), realtime=False),
        base / "capture.log",
    )
    proc.wait(timeout=180)
    segs = ring.segments()
    log(f"[selftest] {len(segs)} segmentos, {ring.buffer_seconds():.0f}s no buffer")
    if len(segs) < 4:
        print("FAIL: buffer nao gerou segmentos suficientes")
        return 1

    test_cfg = Config(
        {
            **cfg.data,
            "live": {**cfg["live"], "window_s": 32, "cycle_s": 8, "min_buffer_s": 20},
            "moments": {
                **cfg["moments"],
                "pre_roll_s": 6,
                "post_roll_s": 8,
                "min_clip_s": 8,
                "max_clip_s": 30,
                "min_sep_s": 10,
                "peak_z": 0.9,
            },
            "branding": {**cfg["branding"], "logo": "", "handle": "@canal_teste"},
        }
    )

    log("[selftest] rodando um ciclo (sem LLM/ASR: heuristica + legenda sintetica)")
    stub = {
        "text": "cara olha isso nao e possivel que aconteceu de novo eu nao acredito",
        "segments": [
            {"start": 0.4, "end": 3.2, "text": "cara olha isso nao e possivel", "words": []},
            {"start": 3.3, "end": 6.8, "text": "que aconteceu de novo", "words": []},
            {"start": 7.0, "end": 10.4, "text": "eu nao acredito nisso", "words": []},
        ],
        "language": "pt",
    }
    clips = process_cycle(
        ring=ring,
        work_dir=base / "cycle",
        cfg=test_cfg,
        router=None,
        asr=None,
        out_dir=base / "out",
        slug="selftest",
        force_keep=True,
        min_score=0.0,
        transcript_stub=stub,
    )

    if not clips:
        print("FAIL: nenhum clipe gerado")
        return 1

    for c in clips:
        p = Path(c["path"])
        size_mb = p.stat().st_size / 1e6 if p.exists() else 0
        print(f"OK clipe: {p.name}  {size_mb:.1f} MB  score {c['score']}")
        print(f"   {p}")
    print("selftest passou")
    return 0


def cmd_serve(cfg: Config, args: argparse.Namespace) -> int:
    """Painel web local (ou na VPS, com senha)."""
    import getpass

    from cortai.auth import Auth, config_path
    from cortai.server import serve

    auth = Auth(config_path(cfg))
    seed = os.environ.get("PANEL_PASSWORD")
    if seed and not auth.enabled:
        if len(seed) < 8:
            print("PANEL_PASSWORD curta: minimo 8 caracteres")
            return 1
        auth.set_password(seed)
        print("senha do painel definida a partir de PANEL_PASSWORD")

    public = args.host not in ("127.0.0.1", "localhost", "::1")
    if public and not auth.enabled:
        import secrets as _secrets

        generated = _secrets.token_urlsafe(12)
        auth.set_password(generated)
        bar = "=" * 62
        print(bar)
        print("  senha do painel gerada automaticamente")
        print(f"  SENHA: {generated}")
        print("  anote agora — ela nao aparece de novo")
        print("  troque depois com:  python cortai.py passwd")
        print(bar)
        print("", flush=True)

    if public and not args.secure_cookie:
        print("aviso: sem TLS, a senha trafega em texto claro na rede.")
        print("       use um proxy com HTTPS na frente (nginx/caddy) e --secure-cookie")
    serve(
        cfg,
        db_for(cfg),
        port=args.port,
        open_browser=not args.no_browser,
        host=args.host,
        auth=auth,
        cookie_secure=args.secure_cookie,
    )
    return 0


def cmd_youtube(cfg: Config, args: argparse.Namespace) -> int:
    """Configura a publicacao no YouTube (OAuth2)."""
    import json as _json

    from cortai import publish_youtube as yt

    if args.action == "status":
        print(_json.dumps(yt.status(), indent=2, ensure_ascii=False))
        return 0
    try:
        result = yt.authorize(port=args.port)
    except Exception as exc:
        print(f"erro: {exc}")
        return 1
    print(f"autorizado. token salvo em {result['token_path']}")
    print("para usar no servidor, copie esse arquivo para o mesmo caminho la.")
    return 0


def cmd_queue(cfg: Config, args: argparse.Namespace) -> int:
    """Mostra/processa a fila de publicacao."""
    import json as _json

    from cortai.publish import run_queue

    db = db_for(cfg)
    if args.drain:
        results = run_queue(db, cfg, limit=args.limit)
        print(_json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    rows = db.conn().execute(
        "SELECT id, clip_id, state, attempts, next_try, publish_at, error"
        " FROM publish_queue ORDER BY id DESC LIMIT 20"
    ).fetchall()
    if not rows:
        print("fila vazia")
        return 0
    import time as _t

    for r in rows:
        when = _t.strftime("%d/%m %H:%M", _t.localtime(r["next_try"]))
        print(f"#{r['id']} clipe {r['clip_id']} {r['state']:<10} tent {r['attempts']} prox {when}"
              + (f" | {r['error'][:50]}" if r["error"] else ""))
    return 0


def cmd_purge(cfg: Config, args: argparse.Namespace) -> int:
    """Aplica a retencao: apaga clipes antigos, orfaos, log e custo."""
    import json as _json

    from cortai.maintenance import purge

    report = purge(cfg, db_for(cfg), dry_run=args.dry_run)
    print(_json.dumps(report, indent=2, ensure_ascii=False))
    if args.dry_run:
        print("\n(simulacao: nada foi apagado; rode sem --dry-run para aplicar)")
    return 0


def cmd_publish(cfg: Config, args: argparse.Namespace) -> int:
    from cortai.publish import publish_clip

    db = db_for(cfg)
    try:
        state = publish_clip(db, cfg.data, args.clip, privacy=args.privacy, background=False)
    except Exception as exc:
        print(f"erro: {exc}")
        return 1
    print(f"publicado: {state.get('url')}")
    return 0


def cmd_passwd(cfg: Config, args: argparse.Namespace) -> int:
    import getpass

    from cortai.auth import Auth, config_path

    auth = Auth(config_path(cfg))
    pw = getpass.getpass("nova senha do painel: ")
    if len(pw) < 8:
        print("senha curta: minimo 8 caracteres")
        return 1
    if pw != getpass.getpass("repita: "):
        print("nao confere")
        return 1
    auth.set_password(pw)
    print(f"senha definida ({auth.path})")
    return 0


def cmd_facecam(cfg: Config, args: argparse.Namespace) -> int:
    """Detecta (ou redetecta) a facecam de uma live, para conferir o enquadramento."""
    from cortai.facecam import FacecamCache, detect
    from cortai.ring import RingBuffer

    if args.file:
        window = Path(args.file).expanduser().resolve()
        if not window.exists():
            print(f"arquivo nao existe: {window}")
            return 1
    elif not args.slug:
        print("informe o slug da live ou use --file gravacao.mp4")
        return 1
    else:
        work = cfg.work_dir / args.slug
        ring = RingBuffer(work / "ring", keep_seconds=int(cfg["live"]["buffer_seconds"]))
        window = work / "facecam_probe.mp4"
        if window.exists():
            window.unlink()
        if not ring.materialize(25, window):
            print(f"sem buffer suficiente para {args.slug} (a live esta rodando?)")
            return 1

    rect = detect(window, samples=int(cfg["facecam"].get("samples", 20)),
                  pad=float(cfg["facecam"].get("pad", 2.6)))
    if not rect:
        print("nenhuma facecam detectada (rosto nao aparece ou nao esta num canto)")
        return 1

    print(f"facecam: x={rect['x']:.0f} y={rect['y']:.0f} "
          f"lado={rect['w']:.0f}px  confianca={rect['confidence']}")
    if not args.file:
        cache = FacecamCache(cfg.work_dir / args.slug, cfg["facecam"])
        cache.current = rect
        from pipeline.util import save_json

        save_json(cache.path, rect)
        print(f"salvo em {cache.path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="lives", description=__doc__)
    parser.add_argument("--config", default=None)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_add = sub.add_parser("add", help="cadastra uma live")
    p_add.add_argument("--url", required=True)
    p_add.add_argument("--platform", default=None)
    p_add.add_argument("--slug", default=None)
    p_add.add_argument("--title", default="")

    p_rm = sub.add_parser("rm", help="para uma live")
    p_rm.add_argument("slug")

    sub.add_parser("list", help="lista lives")

    p_run = sub.add_parser("run", help="roda o supervisor")
    p_run.add_argument("--only", default=None)
    p_run.add_argument(
        "--source", default=None, help="override: arquivo/lavfi no lugar do stream"
    )
    p_run.add_argument("--once", action="store_true", help="roda por um ciclo e sai")
    p_run.add_argument("--minutes", type=float, default=None, help="duracao maxima")

    p_clips = sub.add_parser("clips", help="lista clipes gerados")
    p_clips.add_argument("--limit", type=int, default=20)

    sub.add_parser("doctor", help="checa ambiente")
    sub.add_parser("selftest", help="teste E2E offline")

    p_face = sub.add_parser("facecam", help="detecta a facecam de uma live")
    p_face.add_argument("slug", nargs="?", default=None)
    p_face.add_argument("--file", default=None, help="video local em vez do buffer")

    p_serve = sub.add_parser("serve", help="painel web para acompanhar")
    p_serve.add_argument("--port", type=int, default=8787)
    p_serve.add_argument("--host", default="127.0.0.1", help="0.0.0.0 para expor na rede")
    p_serve.add_argument("--secure-cookie", action="store_true", help="use atras de HTTPS")
    p_serve.add_argument("--no-browser", action="store_true")

    sub.add_parser("passwd", help="define a senha do painel")

    p_yt = sub.add_parser("youtube", help="configura publicacao no YouTube")
    p_yt.add_argument("action", choices=["auth", "status"])
    p_yt.add_argument("--port", type=int, default=0, help="porta do retorno do OAuth")

    p_pub = sub.add_parser("publish", help="envia um clipe para o YouTube")
    p_pub.add_argument("--clip", type=int, required=True)
    p_pub.add_argument("--privacy", default=None, choices=["public", "unlisted", "private"])

    p_purge = sub.add_parser("purge", help="apaga clipes antigos e limpa o banco")
    p_purge.add_argument("--dry-run", action="store_true", help="so mostra o que sairia")

    p_queue = sub.add_parser("queue", help="fila de publicacao")
    p_queue.add_argument("--drain", action="store_true", help="processa os vencidos agora")
    p_queue.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(argv)
    cfg = Config.load(Path(args.config) if args.config else None)

    handlers = {
        "add": cmd_add,
        "rm": cmd_rm,
        "list": cmd_list,
        "run": cmd_run,
        "clips": cmd_clips,
        "doctor": cmd_doctor,
        "selftest": cmd_selftest,
        "facecam": cmd_facecam,
        "serve": cmd_serve,
        "passwd": cmd_passwd,
        "youtube": cmd_youtube,
        "publish": cmd_publish,
        "purge": cmd_purge,
        "queue": cmd_queue,
    }
    return handlers[args.cmd](cfg, args)


if __name__ == "__main__":
    sys.exit(main())
