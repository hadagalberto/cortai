"""Chat ao vivo como sinal extra (opcional). Twitch/YouTube via chat-downloader."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

import numpy as np

from pipeline.chat import HYPE
from pipeline.util import log


class LiveChat(threading.Thread):
    """Acumula mensagens por segundo em memoria. Nunca derruba o worker."""

    def __init__(self, url: str, stop: threading.Event, max_age_s: int = 1800):
        super().__init__(daemon=True, name=f"chat-{url[-12:]}")
        self.url = url
        self.stop = stop
        self.buckets: dict[int, list[int]] = {}
        self.max_age_s = max_age_s
        self.total = 0
        self.alive = False

    def run(self) -> None:
        try:
            from chat_downloader import ChatDownloader
        except Exception:
            log("[chat] chat-downloader ausente -> sinal de chat desligado")
            return

        backoff = 5
        while not self.stop.is_set():
            try:
                chat = ChatDownloader().get_chat(self.url, message_groups=["messages"])
                self.alive = True
                backoff = 5
                for msg in chat:
                    if self.stop.is_set():
                        return
                    ts = int(time.time())
                    is_hype = bool(HYPE.search(msg.get("message") or ""))
                    bucket = self.buckets.setdefault(ts, [0, 0])
                    bucket[0] += 1
                    if is_hype:
                        bucket[1] += 1
                    self.total += 1
                    self._prune(ts)
            except Exception as exc:
                self.alive = False
                log(f"[chat] reconectando ({exc.__class__.__name__}) em {backoff}s")
                self.stop.wait(backoff)
                backoff = min(60, backoff * 2)

    def _prune(self, now: int) -> None:
        if self.total % 2000:
            return
        cutoff = now - self.max_age_s
        for ts in [t for t in self.buckets if t < cutoff]:
            del self.buckets[ts]

    def snapshot(self, start_wall: float, seconds: int) -> dict[str, Any] | None:
        """Alinha contagem de chat com a janela de video."""
        if not self.buckets:
            return None
        start = int(start_wall)
        rate = np.zeros(seconds, dtype=np.float64)
        hype = np.zeros(seconds, dtype=np.float64)
        for i in range(seconds):
            b = self.buckets.get(start + i)
            if b:
                rate[i] = b[0]
                hype[i] = b[1]
        if rate.sum() == 0 and hype.sum() == 0:
            return None
        return {"rate": rate, "hype": hype, "messages": int(self.total)}
