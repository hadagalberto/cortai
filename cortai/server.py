"""Painel web local (stdlib only). `python cortai.py serve` e abre o navegador."""

from __future__ import annotations

import json
import re
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from pipeline.util import log

from .dashboard import snapshot
from .db import DB

from .pages_home import HOME_PAGE as PAGE


LOGIN_PAGE = r"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>cortai — entrar</title>
<style>
:root{--bg:#0b0c0f;--card:#14161b;--line:#23262e;--fg:#e8eaed;--dim:#8b929e;--acc:#ffd400;--bad:#ff5c5c}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-sans-serif,system-ui,Segoe UI,Roboto,sans-serif}
form{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:28px;width:min(92vw,340px)}
h1{margin:0 0 4px;font-size:16px;font-weight:600}
h1 b{color:var(--acc)}
p{margin:0 0 18px;color:var(--dim);font-size:12px}
input{width:100%;padding:11px 13px;border-radius:9px;border:1px solid var(--line);background:#0f1116;color:var(--fg);font-size:14px}
input:focus{outline:none;border-color:#3a3f4b}
button{margin-top:12px;width:100%;padding:11px;border-radius:9px;border:1px solid #2f3540;background:#1b1e25;color:var(--fg);font-weight:600;cursor:pointer}
button:hover{border-color:#4a515f}
.err{margin-top:12px;color:var(--bad);font-size:12px}
</style></head><body>
<form method="post" action="/login">
  <h1>cortai <b>·</b> cortes</h1>
  <p>Painel privado</p>
  <input type="password" name="password" placeholder="Senha" autofocus autocomplete="current-password">
  <button type="submit">Entrar</button>
  {erro}
</form></body></html>"""


def _deep_merge(base: dict, override: dict) -> dict:
    import copy

    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


LIMITS: dict[str, tuple[float, float]] = {
    "live.window_s": (30, 180),
    "live.cycle_s": (5, 60),
    "live.buffer_seconds": (120, 1800),
    "live.min_buffer_s": (20, 300),
    "moments.peak_z": (0.3, 4.0),
    "moments.min_sep_s": (5, 300),
    "moments.context_pre_s": (2, 60),
    "moments.context_post_s": (5, 90),
    "moments.min_clip_s": (5, 60),
    "moments.max_clip_s": (10, 90),
    "classify.min_score": (0, 10),
    "classify.frames": (1, 10),
    "render.fps": (15, 60),
    "render.crf": (14, 32),
    "render.karaoke_size": (40, 140),
    "render.karaoke_words": (1, 6),
    "render.karaoke_margin_v": (40, 700),
    "render.hook_size": (40, 160),
    "render.blur_sigma": (0, 60),
    "render.pip_scale": (0.15, 0.6),
    "render.pip_offset_y": (0, 1200),
    "branding.logo_width": (60, 600),
    "publish.auto_min_score": (0, 10),
    "maintenance.clip_retention_days": (1, 3650),
    "maintenance.keep_unpublished_days": (0, 3650),
    "maintenance.db_retention_days": (7, 3650),
    "maintenance.run_every_hours": (1, 168),
}


def _sanitize_config(data: dict) -> dict:
    """Evita config que quebra o pipeline (numero fora de faixa, enum invalido)."""
    for path, (lo, hi) in LIMITS.items():
        keys = path.split(".")
        node = data
        for key in keys[:-1]:
            node = node.get(key) if isinstance(node, dict) else None
            if not isinstance(node, dict):
                break
        if isinstance(node, dict) and keys[-1] in node:
            try:
                value = float(node[keys[-1]])
                node[keys[-1]] = int(value) if float(value).is_integer() and lo >= 1 else value
                node[keys[-1]] = max(lo, min(hi, node[keys[-1]]))
            except (TypeError, ValueError):
                node[keys[-1]] = lo

    enums = {
        ("render", "mode"): {"pad_blur", "crop"},
        ("render", "pip_position"): {"tl", "tr", "bl", "br"},
        ("branding", "logo_position"): {"tl", "tr", "bl", "br"},
        ("publish", "privacy"): {"public", "unlisted", "private"},
        ("classify", "mode"): {"cascade", "llm", "jev"},
    }
    for (section, key), allowed in enums.items():
        node = data.get(section)
        if isinstance(node, dict) and key in node and node[key] not in allowed:
            node[key] = sorted(allowed)[0]
    return data


def _cookie(token: str, secure: bool, max_age: int) -> str:
    parts = [
        f"cortai_session={token}",
        "Path=/",
        "HttpOnly",
        "SameSite=Strict",
        f"Max-Age={max_age}",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _handler(cfg: Any, db: DB, auth: Any = None, cookie_secure: bool = False):
    out_dir = cfg.out_dir.resolve()
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args: Any) -> None:  # silencia o log de cada request
            return

        # -- helpers de sessao ------------------------------------------
        def _token(self) -> str | None:
            raw = self.headers.get("Cookie") or ""
            for part in raw.split(";"):
                name, _, value = part.strip().partition("=")
                if name == "cortai_session":
                    return value
            return None

        def _authed(self) -> bool:
            if auth is None or not auth.enabled:
                return True  # sem senha configurada: so roda em localhost
            return auth.validate(self._token())

        def _redirect(self, location: str, cookie: str | None = None) -> None:
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.end_headers()

        def _send(self, code: int, body: bytes, ctype: str, cache: bool = False) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store" if not cache else "public, max-age=3600")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])

            if path == "/login":
                body = LOGIN_PAGE.replace("{erro}", "").encode("utf-8")
                self._send(200, body, "text/html; charset=utf-8")
                return

            if path == "/logout":
                self._redirect("/login", _cookie("", cookie_secure, 0))
                return

            if not self._authed():
                if path.startswith("/api/"):
                    self._send(401, b'{"error":"unauthorized"}', "application/json; charset=utf-8")
                    return
                self._redirect("/login")
                return

            if path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path == "/settings":
                from .pages import SETTINGS_PAGE

                self._send(200, SETTINGS_PAGE.encode("utf-8"), "text/html; charset=utf-8")
                return

            if path == "/api/config":
                body = json.dumps(cfg.data, ensure_ascii=False, default=str).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return

            if path == "/api/state":
                body = json.dumps(snapshot(cfg, db), ensure_ascii=False).encode("utf-8")
                self._send(200, body, "application/json; charset=utf-8")
                return

            if path.startswith("/media/"):
                self._serve_media(path)
                return

            if path.startswith("/preview/"):
                self._serve_preview(path)
                return

            self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])
            # sempre drena o corpo: sobra de bytes quebra o keep-alive
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            body = self.rfile.read(length) if length > 0 else b""

            if path == "/login":
                self._handle_login(body)
                return

            if not self._authed():
                self._send(401, b"unauthorized", "text/plain")
                return

            if path == "/api/config":
                self._handle_save_config(body)
                return

            if path == "/api/preview":
                self._handle_preview(body)
                return

            if path == "/api/purge":
                from .maintenance import purge as run_purge

                try:
                    payload = json.loads(body or b"{}")
                    report = run_purge(cfg, db, dry_run=bool(payload.get("dry_run")))
                    self._send(200, json.dumps(report, ensure_ascii=False).encode(),
                               "application/json; charset=utf-8")
                except Exception as exc:
                    self._send(500, json.dumps({"error": str(exc)}).encode(),
                               "application/json; charset=utf-8")
                return

            mtpl = re.match(r"^/api/templates/([^/]+)$", path)
            if mtpl:
                self._handle_save_template(unquote(mtpl.group(1)), body)
                return

            mstpl = re.match(r"^/api/streams/([^/]+)/template$", path)
            if mstpl:
                try:
                    payload = json.loads(body or b"{}")
                    db.set_template(unquote(mstpl.group(1)), payload.get("template"))
                    self._send(200, b'{"ok":true}', "application/json; charset=utf-8")
                except Exception as exc:
                    self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                               "application/json; charset=utf-8")
                return

            m = re.match(r"^/api/clip/(\d+)/feedback$", path)
            if not m:
                if path == "/api/streams":
                    self._handle_add_stream(body)
                    return
                mstop = re.match(r"^/api/streams/([^/]+)/stop$", path)
                if mstop:
                    slug = mstop.group(1)
                    db.set_stream_status(slug, "stopped")
                    body_out = json.dumps({"ok": True, "slug": slug}).encode()
                    self._send(200, body_out, "application/json; charset=utf-8")
                    return
                mpub = re.match(r"^/api/clip/(\d+)/publish$", path)
                if mpub:
                    from .publish import publish_clip

                    try:
                        state = publish_clip(db, cfg, int(mpub.group(1)))
                        code = 202
                    except Exception as exc:
                        state = {"state": "error", "error": str(exc)}
                        code = 400
                    self._send(code, json.dumps(state).encode(), "application/json; charset=utf-8")
                    return
                self._send(404, b"not found", "text/plain")
                return
            try:
                payload = json.loads(body or b"{}")
                vote = int(payload.get("vote", 0))
            except Exception:
                self._send(400, b"bad body", "text/plain")
                return
            ok = db.set_feedback(int(m.group(1)), vote)
            stats = db.feedback_stats()
            body = json.dumps({"ok": ok, **stats}).encode("utf-8")
            self._send(200 if ok else 404, body, "application/json; charset=utf-8")

        def _handle_add_stream(self, body: bytes) -> None:
            from .streams import add

            try:
                payload = json.loads(body or b"{}")
                url = str(payload.get("url") or "").strip()
                title = str(payload.get("title") or "").strip()
                platform = payload.get("platform") or None
                slug, sid = add(db, url, platform, title)
            except ValueError as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            except Exception as exc:
                self._send(500, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            out = json.dumps({"ok": True, "slug": slug, "id": sid}).encode()
            self._send(200, out, "application/json; charset=utf-8")

        def do_DELETE(self) -> None:  # noqa: N802
            path = unquote(self.path.split("?")[0])
            try:
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    self.rfile.read(length)
            except ValueError:
                pass
            if not self._authed():
                self._send(401, b"unauthorized", "text/plain")
                return
            m = re.match(r"^/api/templates/([^/]+)$", path)
            if not m:
                self._send(404, b"not found", "text/plain")
                return
            from pipeline.util import ROOT, load_json
            from .templates import delete as delete_template

            try:
                name = unquote(m.group(1))
                cfg_path = ROOT / "config.json"
                current = load_json(cfg_path, {}) or {}
                if not delete_template(current, name):
                    self._send(400, b'{"ok":false,"error":"template default"}',
                               "application/json; charset=utf-8")
                    return
                cfg_path.write_text(
                    json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                cfg.data = current
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_save_config(self, body: bytes) -> None:
            from pipeline.util import ROOT, load_json

            try:
                payload = json.loads(body or b"{}")
                if not isinstance(payload, dict):
                    raise ValueError("config precisa ser um objeto")
                path = ROOT / "config.json"
                current = load_json(path, {}) or {}
                merged = _deep_merge(current, payload)
                merged = _sanitize_config(merged)
                if path.exists():
                    (ROOT / "config.json.bak").write_text(
                        path.read_text(encoding="utf-8"), encoding="utf-8"
                    )
                path.write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                cfg.data = merged
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_preview(self, body: bytes) -> None:
            from .template_preview import preview_png

            try:
                payload = json.loads(body or b"{}")
                png = preview_png(
                    cfg,
                    str(payload.get("template") or "default"),
                    hook=str(payload.get("hook") or "NAO E POSSIVEL"),
                    layout=str(payload.get("layout") or "pip"),
                    render_override=payload.get("render") or {},
                    branding_override=payload.get("branding") or {},
                )
            except Exception as exc:
                log(f"[preview] {exc}")
                png = None
            if not png:
                self._send(500, b"preview failed", "text/plain")
                return
            self._send(200, png, "image/png")

        def _handle_save_template(self, name: str, body: bytes) -> None:
            from pipeline.util import ROOT, load_json
            from .templates import save as save_template

            try:
                payload = json.loads(body or b"{}")
                path = ROOT / "config.json"
                current = load_json(path, {}) or {}
                save_template(path, current, name, payload or {})
                cfg.data = load_json(path, {}) or {}
            except Exception as exc:
                self._send(400, json.dumps({"ok": False, "error": str(exc)}).encode(),
                           "application/json; charset=utf-8")
                return
            self._send(200, b'{"ok":true}', "application/json; charset=utf-8")

        def _handle_login(self, body: bytes) -> None:
            from urllib.parse import parse_qs

            try:
                form = parse_qs(body.decode("utf-8", "replace"))
            except Exception:
                self._send(400, b"bad body", "text/plain")
                return
            password = (form.get("password") or [""])[0]
            ip = self.client_address[0] if self.client_address else "?"
            ok, result = auth.login(ip, password) if auth else (False, "auth indisponivel")
            if ok:
                self._redirect("/", _cookie(result, cookie_secure, auth.ttl))
                return
            msg = f'<div class="err">{result}</div>'
            body = LOGIN_PAGE.replace("{erro}", msg).encode("utf-8")
            self._send(200, body, "text/html; charset=utf-8")

        def _serve_preview(self, path: str) -> None:
            slug = path.rsplit("/", 1)[-1].removesuffix(".mp4")
            known = {r["slug"] for r in db.streams(None)}
            if slug not in known:
                self._send(404, b"unknown stream", "text/plain")
                return
            from .preview import ensure

            file = ensure(cfg, slug)
            if not file or not file.exists():
                self._send(204, b"", "video/mp4")
                return
            self._send(200, file.read_bytes(), "video/mp4")

        def _serve_media(self, path: str) -> None:
            name = path.rsplit("/", 1)[-1]
            stem, _, ext = name.partition(".")
            try:
                clip_id = int(stem)
            except ValueError:
                self._send(400, b"bad id", "text/plain")
                return
            row = db.clip(clip_id)
            if not row or not row["path"]:
                self._send(404, b"clip not found", "text/plain")
                return

            target = Path(row["path"])
            if ext == "jpg":
                target = target.with_suffix(".jpg")
            if not target.exists() or not target.resolve().is_relative_to(out_dir):
                self._send(404, b"file missing", "text/plain")
                return

            data = target.read_bytes()
            ctype = "video/mp4" if ext == "mp4" else "image/jpeg"
            self._send(200, data, ctype, cache=True)

    return Handler


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request: Any, client_address: Any) -> None:
        """Cliente fechando conexao (reload da pagina, video trocando) nao e erro."""
        return


def serve(
    cfg: Any,
    db: DB,
    port: int = 8787,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    auth: Any = None,
    cookie_secure: bool = False,
) -> None:
    httpd = _Server((host, port), _handler(cfg, db, auth, cookie_secure))
    shown = "127.0.0.1" if host in ("0.0.0.0", "::") else host
    url = f"http://{shown}:{port}/"
    if auth is not None and auth.enabled:
        log(f"[painel] {url}  (senha ativa, ctrl+c para sair)")
    else:
        log(f"[painel] {url}  (SEM SENHA — apenas local)")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log("[painel] encerrado")
    finally:
        httpd.server_close()
