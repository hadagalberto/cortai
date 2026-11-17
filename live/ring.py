"""Buffer circular em disco: ffmpeg grava segmentos, GC mantem so os ultimos N minutos."""

from __future__ import annotations

import time
from pathlib import Path

from pipeline.util import find_exe, log, run

SEGMENT_SECONDS = 6


class RingBuffer:
    def __init__(
        self,
        root: Path,
        keep_seconds: int = 600,
        segment_seconds: int = SEGMENT_SECONDS,
    ):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.keep_seconds = keep_seconds
        self.segment_seconds = segment_seconds
        self.pattern = str(root / "seg_%08d.ts")
        self.list_path = root / "segments.csv"

    # -- ffmpeg output args --------------------------------------------
    def sink_args(self) -> list[str]:
        return [
            "-f",
            "segment",
            "-segment_time",
            str(self.segment_seconds),
            "-reset_timestamps",
            "0",
            "-segment_format",
            "mpegts",
            "-segment_list_type",
            "csv",
            "-segment_list",
            str(self.list_path),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-ar",
            "48000",
            "-ac",
            "2",
            self.pattern,
        ]

    # -- index ---------------------------------------------------------
    def segments(self) -> list[Path]:
        return sorted(
            self.root.glob("seg_*.ts"), key=lambda p: p.name
        )

    def gc(self) -> int:
        """Remove segmentos mais antigos que keep_seconds. Devolve quantos saiu."""
        segs = self.segments()
        max_files = max(4, int(self.keep_seconds / self.segment_seconds) + 4)
        removed = 0
        while len(segs) > max_files:
            victim = segs.pop(0)
            try:
                victim.unlink()
                removed += 1
            except OSError:
                pass
        return removed

    def window_files(self, span_s: float) -> list[Path]:
        need = max(2, int(span_s / self.segment_seconds) + 2)
        return self.segments()[-need:]

    def reset(self) -> int:
        """Limpa o ring. Obrigatorio ao (re)iniciar a captura.

        O ffmpeg recomeca a numeracao em seg_00000001, entao sem isso a janela
        concatena segmentos novos com antigos de outra sessao.
        """
        removed = 0
        for path in self.segments():
            try:
                path.unlink()
                removed += 1
            except OSError:
                pass
        for extra in (self.list_path, self.root / "segments.csv"):
            try:
                extra.unlink(missing_ok=True)
            except OSError:
                pass
        return removed

    def buffer_seconds(self) -> float:
        return len(self.segments()) * self.segment_seconds

    def newest_age(self) -> float | None:
        """Segundos desde o ultimo segmento. None = ring vazio."""
        segs = self.segments()
        if not segs:
            return None
        return max(0.0, time.time() - segs[-1].stat().st_mtime)

    # -- materializacao ------------------------------------------------
    def materialize(self, span_s: float, out_path: Path) -> Path | None:
        """Concatena os ultimos `span_s` segundos num unico arquivo."""
        files = self.window_files(span_s)
        if len(files) < 2:
            return None
        out_path.parent.mkdir(parents=True, exist_ok=True)
        list_file = out_path.with_suffix(".txt")
        list_file.write_text(
            "\n".join(f"file '{f.resolve().as_posix()}'" for f in files) + "\n",
            encoding="utf-8",
        )
        run(
            [
                find_exe("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_file),
                "-c",
                "copy",
                str(out_path),
            ]
        )
        return out_path

    def wait_until_ready(self, min_seconds: float, timeout: float = 120) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.buffer_seconds() >= min_seconds:
                return True
            time.sleep(2)
        return self.buffer_seconds() >= min_seconds
