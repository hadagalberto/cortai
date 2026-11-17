"""Resolve a URL do stream (streamlink -> yt-dlp) e monta o comando ffmpeg de captura."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from pipeline.util import find_exe, log

from .ring import RingBuffer


def streamlink_cmd() -> list[str] | None:
    """Acha o streamlink mesmo com Scripts/ fora do PATH."""
    exe = shutil.which("streamlink")
    if exe:
        return [exe]
    try:
        import sysconfig

        for scripts in {sysconfig.get_path("scripts"), str(Path.home() / "AppData/Roaming/Python/Python315/Scripts")}:
            if not scripts:
                continue
            cand = Path(scripts) / "streamlink.exe"
            if cand.exists():
                return [str(cand)]
    except Exception:
        pass
    try:
        import streamlink_cli  # noqa: F401

        return [sys.executable, "-m", "streamlink"]
    except Exception:
        return None


def resolve_stream_url(url: str, quality: str = "best") -> str:
    """Devolve a URL direta (m3u8/flv) que o ffmpeg consome."""
    sl = streamlink_cmd()
    if sl:
        proc = subprocess.run(
            [*sl, "--stream-url", url, quality],
            capture_output=True,
            text=True,
            timeout=90,
        )
        out = (proc.stdout or "").strip().splitlines()
        if proc.returncode == 0 and out:
            return out[-1]

    import yt_dlp

    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True}) as ydl:
        info = ydl.extract_info(url, download=False)
        if info.get("_type") == "playlist":
            info = info["entries"][0]
        direct = info.get("url")
        if not direct:
            raise RuntimeError("nao foi possivel resolver URL do stream")
        return direct


def build_capture_cmd(
    ring: RingBuffer,
    url: str | None = None,
    source: str | None = None,
    headers: dict[str, str] | None = None,
    realtime: bool = True,
) -> list[str]:
    cmd = [find_exe("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "warning"]

    if source:
        # override util para testes: arquivo local ou input lavfi
        if source.startswith(("lavfi:", "testsrc", "color=")):
            spec = source.split("lavfi:", 1)[-1]
            cmd += (["-re"] if realtime else []) + ["-f", "lavfi", "-i", spec]
        else:
            cmd += (["-re"] if realtime else []) + [
                *(["-stream_loop", "-1"] if realtime else []),
                "-i",
                source,
            ]
    else:
        if not url:
            raise ValueError("capture sem url e sem source")
        if url.startswith("http") and headers:
            hdr = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            cmd += ["-headers", hdr]
        cmd += [
            "-reconnect",
            "1",
            "-reconnect_streamed",
            "1",
            "-reconnect_delay_max",
            "10",
            "-i",
            url,
        ]

    cmd += ring.sink_args()
    return cmd


def capture_process(cmd: list[str], log_path: Path) -> subprocess.Popen:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    fh = log_path.open("ab")
    log(f"[capture] ffmpeg iniciado ({log_path.name})")
    return subprocess.Popen(
        cmd,
        stdout=fh,
        stderr=fh,
        stdin=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
