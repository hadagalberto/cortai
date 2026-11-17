"""Autenticacao do painel: senha com PBKDF2, sessao assinada, bloqueio por tentativa."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

ITERATIONS = 200_000
SESSION_TTL = 12 * 3600
MAX_FAILS = 5
LOCK_SECONDS = 300


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), ITERATIONS
    )
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters, salt, digest = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        calc = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iters)
        )
        return hmac.compare_digest(calc.hex(), digest)
    except Exception:
        return False


class Auth:
    """Estado de autenticacao persistido em work/panel_auth.json."""

    def __init__(self, path: Path):
        self.path = path
        self.password_hash: str | None = None
        self.secret: str = secrets.token_hex(32)
        self.ttl = SESSION_TTL
        self._fails: dict[str, list[float]] = {}
        self._load()

    # -- persistencia ---------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.password_hash = data.get("password_hash")
            self.secret = data.get("secret") or self.secret
            self.ttl = int(data.get("ttl") or SESSION_TTL)
        except Exception:
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {
                    "password_hash": self.password_hash,
                    "secret": self.secret,
                    "ttl": self.ttl,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            pass

    def set_password(self, password: str) -> None:
        self.password_hash = hash_password(password)
        self.save()

    @property
    def enabled(self) -> bool:
        return bool(self.password_hash)

    # -- sessao ---------------------------------------------------------
    def _sign(self, payload: str) -> str:
        return hmac.new(
            self.secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    def issue(self) -> str:
        exp = int(time.time()) + self.ttl
        payload = str(exp)
        return f"{payload}.{self._sign(payload)}"

    def validate(self, token: str | None) -> bool:
        if not token or "." not in token:
            return False
        payload, _, sig = token.partition(".")
        if not hmac.compare_digest(sig, self._sign(payload)):
            return False
        try:
            return int(payload) > time.time()
        except ValueError:
            return False

    # -- anti forca bruta -----------------------------------------------
    def locked(self, ip: str) -> int:
        """Devolve segundos restantes de bloqueio (0 = liberado)."""
        now = time.time()
        hits = [t for t in self._fails.get(ip, []) if now - t < LOCK_SECONDS]
        self._fails[ip] = hits
        if len(hits) >= MAX_FAILS:
            return int(LOCK_SECONDS - (now - hits[0])) + 1
        return 0

    def record_fail(self, ip: str) -> None:
        self._fails.setdefault(ip, []).append(time.time())

    def clear_fails(self, ip: str) -> None:
        self._fails.pop(ip, None)

    # -- login ----------------------------------------------------------
    def login(self, ip: str, password: str) -> tuple[bool, str | None]:
        """Devolve (ok, token_ou_msg)."""
        wait = self.locked(ip)
        if wait:
            return False, f"muitas tentativas. tente em {wait}s"
        if not self.enabled:
            return False, "senha nao configurada (python lives.py passwd)"
        if not verify_password(password, self.password_hash or ""):
            self.record_fail(ip)
            return False, "senha incorreta"
        self.clear_fails(ip)
        return True, self.issue()


def config_path(cfg: Any) -> Path:
    return Path(cfg.work_dir) / "panel_auth.json"
