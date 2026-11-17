"""Publicacao no YouTube: OAuth2 (uma vez) + upload resumivel.

Como usar:
  1. baixe o client_secret.json do Google Cloud e ponha na raiz do projeto
  2. python cortai.py youtube auth      (abre o navegador, autoriza, salva o token)
  3. python cortai.py publish --clip 15 --privacy unlisted
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from pipeline.util import ROOT, log

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRET = ROOT / "client_secret.json"
TOKEN_PATH = ROOT / "work" / "youtube_token.json"

# aceita o arquivo na raiz (uso local) ou em work/ (que e volume no Docker)
CLIENT_SECRET_CANDIDATES = [ROOT / "client_secret.json", ROOT / "work" / "client_secret.json"]


class YouTubeError(RuntimeError):
    pass


def client_secret_path() -> Path | None:
    for path in CLIENT_SECRET_CANDIDATES:
        if path.is_file():
            return path
    return None


def client_secret_ok() -> bool:
    path = client_secret_path()
    if not path:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return False
    return "installed" in data or "web" in data


def authorized() -> bool:
    if not TOKEN_PATH.exists():
        return False
    try:
        data = json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception:
        return False
    return bool(data.get("refresh_token") or data.get("token"))


def status() -> dict[str, Any]:
    path = client_secret_path()
    # para PUBLICAR basta o token: ele carrega client_id/secret para o refresh.
    # o client_secret.json so e necessario para autorizar uma vez.
    return {
        "client_secret": client_secret_ok(),
        "client_secret_path": str(path) if path else None,
        "can_authorize": client_secret_ok(),
        "authorized": authorized(),
        "ready": authorized(),
        "token_path": str(TOKEN_PATH),
    }


def _credentials():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    if not TOKEN_PATH.exists():
        raise YouTubeError("sem token: rode 'python cortai.py youtube auth'")
    creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
    if not creds.valid:
        if not creds.refresh_token:
            raise YouTubeError("token sem refresh: rode 'python cortai.py youtube auth' de novo")
        creds.refresh(Request())
        TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    return creds


def authorize(port: int = 0) -> dict[str, Any]:
    """Abre o navegador, autoriza e salva o token. Precisa rodar uma vez."""
    if not client_secret_ok():
        raise YouTubeError(
            "client_secret.json nao encontrado. Coloque na raiz do projeto ou em work/. "
            "Veja o README, secao 'Publicar no YouTube'."
        )
    from google_auth_oauthlib.flow import InstalledAppFlow

    secret_file = client_secret_path()
    flow = InstalledAppFlow.from_client_secrets_file(str(secret_file), SCOPES)
    creds = flow.run_local_server(
        port=port,
        open_browser=True,
        authorization_prompt_message="Autorize no navegador que abrir...",
        success_message="Autorizado. Pode fechar esta aba.",
    )
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json(), encoding="utf-8")
    log(f"[youtube] token salvo em {TOKEN_PATH}")
    return {"ok": True, "token_path": str(TOKEN_PATH)}


def upload(
    video: Path,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy: str = "unlisted",
    category_id: str = "20",
    publish_at: str | None = None,
    progress: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Envia o arquivo e devolve {'id', 'url'}. publish_at = ISO8601 agendado."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not video.exists():
        raise YouTubeError(f"arquivo nao existe: {video}")

    creds = _credentials()
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": [t.lstrip("#") for t in (tags or [])][:30],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": ("private" if publish_at else
                              (privacy if privacy in ("public", "unlisted", "private") else "unlisted")),
            "selfDeclaredMadeForKids": False,
        },
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at
    media = MediaFileUpload(str(video), mimetype="video/mp4", chunksize=-1, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        try:
            chunk, response = request.next_chunk()
        except HttpError as exc:
            reason = ""
            try:
                reason = json.loads(exc.content.decode()).get("error", {}).get("errors", [{}])[0].get("reason", "")
            except Exception:
                pass
            if reason == "quotaExceeded":
                raise YouTubeError("cota diaria do YouTube esgotada (volta em 24h)") from exc
            if reason == "uploadLimitExceeded":
                raise YouTubeError("limite de uploads do canal atingido por hoje") from exc
            if reason == "youtubeSignupRequired":
                raise YouTubeError("a conta Google nao tem canal no YouTube") from exc
            raise YouTubeError(f"erro do YouTube ({reason or exc.status_code})") from exc
        if chunk and progress:
            progress(float(chunk.progress() or 0.0))

    vid = response.get("id")
    return {"id": vid, "url": f"https://youtu.be/{vid}", "title": title}
