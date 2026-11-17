from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parent.parent


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def load_dotenv(path: Path | None = None) -> None:
    """Carrega .env simples (KEY=value) sem depender de python-dotenv."""
    p = path or (ROOT / ".env")
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = val


def find_exe(name: str) -> str:
    """Acha ffmpeg/ffprobe mesmo quando o PATH do processo esta desatualizado."""
    found = shutil.which(name)
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        Path(local) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe",
        Path(r"C:\ProgramData\chocolatey\bin") / f"{name}.exe",
        Path("/usr/bin") / name,
        Path("/usr/local/bin") / name,
    ]
    if local:
        packages = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if packages.exists():
            candidates += sorted(packages.glob(f"Gyan.FFmpeg*/**/bin/{name}.exe"))
    for c in candidates:
        if c.exists():
            return str(c)
    raise FileNotFoundError(
        f"{name} nao encontrado. Instale com: winget install Gyan.FFmpeg"
    )


def run(cmd: Sequence[str], quiet: bool = True) -> str:
    cmd = [str(c) for c in cmd]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-25:]
        raise RuntimeError(
            f"comando falhou ({proc.returncode}): {' '.join(cmd[:4])} ...\n"
            + "\n".join(tail)
        )
    if not quiet and proc.stderr:
        log(proc.stderr)
    return proc.stdout


def load_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    # utf-8-sig: aceita arquivo salvo no Notepad (com BOM)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def hhmmss(seconds: float) -> str:
    seconds = max(0.0, seconds)
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:d}:{s:02d}"


def clip_tag(seconds: float) -> str:
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{s:02d}"
