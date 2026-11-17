"""Orquestra N workers, um por live. Aceita lives novas/removidas em tempo real."""

from __future__ import annotations

import threading
import time
from typing import Any

from pipeline.util import log

from .asr import ASR
from .db import DB
from .llm import router_from_config
from .worker import StreamWorker


def run(
    cfg: Any,
    db: DB,
    *,
    only: str | None = None,
    source: str | None = None,
    once: bool = False,
    minutes: float | None = None,
) -> int:
    def active_rows() -> dict[str, Any]:
        rows = db.streams("active")
        if only:
            rows = [r for r in rows if r["slug"] == only]
        return {r["slug"]: r for r in rows}

    initial = active_rows()
    if not initial:
        log("[supervisor] nenhuma live ativa. Cadastre no painel ou: python lives.py add --url ...")
        return 1

    router = router_from_config(cfg["llm"])
    asr = ASR(cfg["asr"])
    stop = threading.Event()
    workers: dict[str, StreamWorker] = {}
    events: dict[str, threading.Event] = {}

    def spawn(row: Any, reason: str = "") -> None:
        ev = threading.Event()
        worker = StreamWorker(row, cfg, db, router, asr, ev, source_override=source)
        worker.start()
        workers[row["slug"]] = worker
        events[row["slug"]] = ev
        if reason:
            log(f"[supervisor] {row['slug']} {reason}")

    for row in initial.values():
        spawn(row)
    log(f"[supervisor] {len(workers)} worker(s): {', '.join(workers)}")

    started = time.time()
    once_after = float(cfg["live"]["min_buffer_s"]) + float(cfg["live"]["window_s"]) + 30
    deadline = started + minutes * 60 if minutes else None
    last_report = 0.0
    last_purge = 0.0
    last_queue = 0.0

    try:
        while not stop.is_set():
            time.sleep(5)
            if once and time.time() - started > once_after:
                break
            if deadline and time.time() > deadline:
                log(f"[supervisor] {minutes:.0f} min atingidos, encerrando")
                break

            # config recarregada: mudancas no painel valem sem reiniciar
            live_cfg = cfg
            try:
                from pipeline.config import Config

                live_cfg = Config.load()
            except Exception:
                pass

            # fila de publicacao
            if time.time() - last_queue >= 30:
                last_queue = time.time()
                try:
                    from .publish import run_queue

                    run_queue(db, live_cfg)
                except Exception as exc:
                    log(f"[supervisor] fila de publicacao falhou: {exc}")

            # limpeza automatica
            try:
                every = float((live_cfg["maintenance"] or {}).get("run_every_hours") or 6) * 3600
                if time.time() - last_purge >= every:
                    last_purge = time.time()
                    from .maintenance import purge

                    purge(live_cfg, db)
            except Exception as exc:
                log(f"[supervisor] limpeza falhou: {exc}")

            active = active_rows()
            # entrou live nova no painel
            for slug, row in active.items():
                if slug not in workers:
                    spawn(row, "adicionada no painel")
                    continue
                worker = workers[slug]
                if not worker.is_alive():
                    db.log(slug, "error", "worker morreu, reiniciando")
                    spawn(row, "morreu -> reiniciando")
            # saiu do painel
            for slug in list(workers):
                if slug not in active:
                    events[slug].set()
                    del workers[slug]
                    del events[slug]
                    db.log(slug, "info", "removida do painel, worker encerrado")
                    log(f"[supervisor] {slug} removida -> parando")

            if time.time() - last_report > 60:
                last_report = time.time()
                total = len(db.clips(limit=1000))
                log(
                    f"[supervisor] {time.strftime('%H:%M:%S')} "
                    f"uptime {(time.time() - started) / 60:.0f}min | "
                    f"{len(workers)} live(s) | clips {total}"
                )
    except KeyboardInterrupt:
        log("[supervisor] encerrando...")
    finally:
        stop.set()
        for ev in events.values():
            ev.set()
        for worker in workers.values():
            worker.join(timeout=30)
    return 0


def status(cfg: Any, db: DB) -> None:
    rows = db.streams(None)
    if not rows:
        print("nenhuma live cadastrada")
        return
    print(f"{'slug':<24}{'plataforma':<12}{'status':<10}criada")
    for r in rows:
        print(
            f"{r['slug']:<24}{r['platform']:<12}{r['status']:<10}"
            f"{time.strftime('%d/%m %H:%M', time.localtime(r['created_at']))}"
        )
