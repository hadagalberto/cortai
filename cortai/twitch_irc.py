"""Chat ao vivo do Twitch por IRC anonimo (read-only).

Substitui o chat-downloader na live do Twitch: aquela lib pode bloquear sem
excecao e sem entregar mensagem, e o sinal de chat morria em silencio.
Aqui todo estado e visivel: conectado, mensagens recebidas, ultimo erro.
"""

from __future__ import annotations

import re
import socket
import ssl
import threading
import time
from collections import deque
from typing import Any

import numpy as np

from pipeline.chat import HYPE
from pipeline.util import log

HOST = "irc.chat.twitch.tv"
PORT = 6697
ANON = "justinfan12345"


def channel_from_url(url: str) -> str | None:
    m = re.search(r"twitch\.tv/([A-Za-z0-9_]{2,})", url or "")
    return m.group(1).lower() if m else None


class TwitchIRC(threading.Thread):
    def __init__(self, channel: str, stop: threading.Event, max_age_s: int = 3600):
        super().__init__(daemon=True, name=f"irc-{channel}")
        self.channel = channel
        self.stop = stop
        self.max_age_s = max_age_s
        self.buckets: dict[int, list[int]] = {}
        self.total = 0
        self.connected = False
        self.last_error: str | None = None
        self.connected_since: float | None = None
        self._sock: socket.socket | None = None
        self._lock = threading.Lock()

    # -- rede ----------------------------------------------------------
    def _connect(self) -> None:
        raw = socket.create_connection((HOST, PORT), timeout=30)
        self._sock = ssl.create_default_context().wrap_socket(raw, server_hostname=HOST)
        self._sock.settimeout(60)
        self._send(f"PASS {ANON}")
        self._send(f"NICK {ANON}")
        self._send(f"JOIN #{self.channel}")
        self.connected = True
        self.connected_since = time.time()
        self.last_error = None
        log(f"[chat] irc conectado em #{self.channel}")

    def _send(self, line: str) -> None:
        if self._sock:
            try:
                self._sock.sendall((line + "\r\n").encode("utf-8"))
            except OSError:
                pass

    # -- loop ----------------------------------------------------------
    def run(self) -> None:
        backoff = 3.0
        while not self.stop.is_set():
            try:
                if not self.connected:
                    self._connect()
                    backoff = 3.0
                buf = b""
                while not self.stop.is_set():
                    chunk = self._sock.recv(8192) if self._sock else b""
                    if not chunk:
                        raise ConnectionError("conexao fechada pelo servidor")
                    buf += chunk
                    while b"\r\n" in buf:
                        line, buf = buf.split(b"\r\n", 1)
                        self._handle(line.decode("utf-8", "replace"))
            except Exception as exc:
                self.connected = False
                self.last_error = f"{exc.__class__.__name__}: {exc}"
                log(f"[chat] caiu ({self.last_error}) -> retry em {backoff:.0f}s")
                try:
                    if self._sock:
                        self._sock.close()
                except OSError:
                    pass
                self._sock = None
                self.stop.wait(backoff)
                backoff = min(30.0, backoff * 1.8)

    def _handle(self, line: str) -> None:
        if line.startswith("PING"):
            self._send("PONG :tmi.twitch.tv")
            return
        if " PRIVMSG " not in line:
            return
        _, _, body = line.partition(" PRIVMSG ")
        _, _, message = body.partition(" :")
        now = int(time.time())
        hype = bool(HYPE.search(message))
        with self._lock:
            bucket = self.buckets.setdefault(now, [0, 0])
            bucket[0] += 1
            if hype:
                bucket[1] += 1
            self.total += 1
            if self.total % 2000 == 0:
                cutoff = now - self.max_age_s
                for ts in [t for t in self.buckets if t < cutoff]:
                    del self.buckets[ts]

    # -- consulta ------------------------------------------------------
    def snapshot(self, start_wall: float, seconds: int) -> dict[str, Any] | None:
        with self._lock:
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
            total = self.total
        if rate.sum() == 0 and hype.sum() == 0:
            return None
        return {"rate": rate, "hype": hype, "messages": int(total)}

    def status(self) -> dict[str, Any]:
        with self._lock:
            buckets = len(self.buckets)
        return {
            "connected": self.connected,
            "messages": self.total,
            "seconds_with_chat": buckets,
            "last_error": self.last_error,
            "uptime_s": round(time.time() - self.connected_since) if self.connected_since else 0,
        }
