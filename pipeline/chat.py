"""Sinal de chat (Twitch VOD). Opcional: sem a lib, o pipeline segue so com audio."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from .util import log

# palavras/emotes que marcam reacao na comunidade BR/global
HYPE = re.compile(
    r"\b(kkk+|rs+|lol|lmao|omg|wtf|caralho|puta|nossa|meu deus|insano|"
    r"nunca vi|clipa|clip|viral|monstro|gg|ez|pog|poggers|kekw|"
    r"jesus|cristo|impossivel|impossible|no way|holY|que isso)\b",
    re.IGNORECASE,
)


def twitch_vod_id(url: str) -> str | None:
    m = re.search(r"twitch\.tv/videos/(\d+)", url or "")
    return m.group(1) if m else None


def collect(url: str | None, seconds: int) -> dict[str, Any] | None:
    vid = twitch_vod_id(url or "")
    if not vid:
        return None
    try:
        from chat_downloader import ChatDownloader
    except Exception:
        log("[chat] chat-downloader ausente -> seguindo so com audio")
        return None

    log(f"[chat] baixando replay do chat (vod {vid})")
    try:
        chat = ChatDownloader().get_chat(f"https://www.twitch.tv/videos/{vid}")
        rate = np.zeros(seconds, dtype=np.float64)
        hype = np.zeros(seconds, dtype=np.float64)
        n = 0
        for msg in chat:
            t = msg.get("time_in_seconds")
            if t is None:
                continue
            i = int(t)
            if i < 0 or i >= seconds:
                continue
            rate[i] += 1
            n += 1
            body = msg.get("message") or ""
            if HYPE.search(body) or (body.isupper() and len(body) > 6):
                hype[i] += 1
    except Exception as exc:  # rede, geo-block, vod expirado...
        log(f"[chat] falhou ({exc.__class__.__name__}: {exc}) -> seguindo so com audio")
        return None

    if n == 0:
        return None
    log(f"[chat] {n} mensagens")
    return {"rate": rate, "hype": hype, "messages": n}
