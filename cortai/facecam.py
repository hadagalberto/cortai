"""Detecta o retangulo da facecam do streamer (canto, quadrado) e cacheia por stream.

Amostragem via ffmpeg (nao confia em seek de VideoCapture: MPEG-TS mente sobre
frame count). Deteccao em resolucao nativa — rosto de facecam em 1080p tem ~60px
e sobrevive mal a downscale. Prioriza clusters colados em borda, porque rosto de
personagem de cutscene tambem dispara o detector e fica no meio da tela.
"""

from __future__ import annotations

import base64
import json
import shutil
import statistics
import time
from pathlib import Path
from typing import Any

from pipeline.util import ROOT, find_exe, log, run, save_json

from . import jev

MODEL_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
MODEL_PATH = ROOT / "models" / "yunet.onnx"


def ensure_model() -> Path | None:
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size > 100_000:
        return MODEL_PATH
    try:
        import requests

        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        log("[facecam] baixando modelo YuNet (~230 KB)")
        resp = requests.get(MODEL_URL, timeout=90)
        resp.raise_for_status()
        MODEL_PATH.write_bytes(resp.content)
        return MODEL_PATH
    except Exception as exc:
        log(f"[facecam] modelo indisponivel ({exc}) -> deteccao desligada")
        return None


def _cv():
    import cv2

    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    except Exception:
        pass
    return cv2


def _probe_size(video: Path) -> tuple[int, int]:
    out = run(
        [
            find_exe("ffprobe"),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(video),
        ]
    )
    w, h = out.strip().splitlines()[0].split(",")[:2]
    return int(w), int(h)


def _sample_frames(
    video: Path, samples: int, tmp_dir: Path, width: int | None = None
) -> list[Path]:
    """Extrai N frames espalhados pelo video. width=None usa resolucao nativa."""
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    duration = max(1.0, _duration(video))
    step = max(0.35, duration / samples)
    vf = [f"fps=1/{step:.3f}"]
    if width:
        vf.append(f"scale={width}:-2")
    run(
        [
            find_exe("ffmpeg"),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(video),
            "-vf",
            ",".join(vf),
            "-frames:v",
            str(samples),
            "-q:v",
            "2",
            str(tmp_dir / "f%04d.jpg"),
        ]
    )
    return sorted(tmp_dir.glob("f*.jpg"))


def _duration(video: Path) -> float:
    out = run(
        [
            find_exe("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(video),
        ]
    )
    try:
        return float(out.strip().splitlines()[0])
    except Exception:
        return 30.0


def _cluster(boxes: list[dict[str, Any]], tol: float) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    for box in boxes:
        cx, cy = box["cx"], box["cy"]
        placed = False
        for cluster in clusters:
            mcx = statistics.fmean(b["cx"] for b in cluster)
            mcy = statistics.fmean(b["cy"] for b in cluster)
            if abs(cx - mcx) < tol and abs(cy - mcy) < tol:
                cluster.append(box)
                placed = True
                break
        if not placed:
            clusters.append([box])
    return clusters


def _near_edge(box: dict[str, float], W: int, H: int, frac: float = 0.28) -> bool:
    cx, cy = box["cx"] / W, box["cy"] / H
    return cx < frac or cx > 1 - frac or cy < frac or cy > 1 - frac


def _in_corner(box: dict[str, float], W: int, H: int, frac: float = 0.30) -> bool:
    cx, cy = box["cx"] / W, box["cy"] / H
    near_x = cx < frac or cx > 1 - frac
    near_y = cy < frac or cy > 1 - frac
    return near_x and near_y


def _snap(x: float, y: float, side: float, W: int, H: int, margin: float = 0.22):
    """Facecam quase sempre encosta na borda: encosta quando esta perto."""
    if x < margin * W:
        x = 0.0
    elif x + side > (1 - margin) * W:
        x = W - side
    if y < margin * H:
        y = 0.0
    elif y + side > (1 - margin) * H:
        y = H - side
    x = max(0.0, min(x, W - side))
    y = max(0.0, min(y, H - side))
    return x, y


def detect(
    video: Path,
    samples: int = 20,
    pad: float = 3.4,
    min_frame_hits: float = 0.3,
    conf: float = 0.55,
    debug: bool = False,
) -> dict[str, Any] | None:
    """Devolve a facecam dominante em coordenadas da fonte, ou None."""
    model = ensure_model()
    if not model:
        return None
    try:
        cv2 = _cv()
    except Exception:
        return None

    tmp = video.parent / "_facecam_frames"
    frames = _sample_frames(video, samples, tmp)
    if not frames:
        if debug:
            return {"error": "nenhum frame extraido"}
        return None

    W, H = _probe_size(video)
    detector = cv2.FaceDetectorYN.create(str(model), "", (320, 320), conf, 0.3, 5000)

    per_frame: list[list[dict[str, float]]] = []
    for idx, path in enumerate(frames):
        img = cv2.imread(str(path))
        if img is None:
            continue
        h, w = img.shape[:2]
        scale = W / w if w else 1.0
        detector.setInputSize((w, h))
        try:
            _n, faces = detector.detect(img)
        except Exception:
            continue
        boxes: list[dict[str, float]] = []
        for f in (faces if faces is not None else []):
            fx, fy, fw, fh = (float(v) * scale for v in f[:4])
            cx, cy = fx + fw / 2, fy + fh / 2
            if fw < 0.02 * W or fw > 0.5 * W:  # ignora ruido e rosto gigante
                continue
            boxes.append(
                {"x": fx, "y": fy, "w": fw, "h": fh, "cx": cx, "cy": cy,
                 "conf": float(f[-1]), "frame": idx}
            )
        per_frame.append(boxes)

    shutil.rmtree(tmp, ignore_errors=True)

    all_boxes = [b for fb in per_frame for b in fb]
    result: dict[str, Any] = {
        "frames": len(per_frame),
        "faces": len(all_boxes),
        "faces_per_frame": round(len(all_boxes) / max(1, len(per_frame)), 2),
    }
    if not all_boxes:
        if debug:
            return {**result, "error": "nenhum rosto detectado"}
        return None

    sizes = sorted(b["w"] for b in all_boxes)
    med_w = sizes[len(sizes) // 2]
    # tolerancia amarrada ao tamanho do rosto: rosto de facecam quase nao anda,
    # rosto de personagem de cutscene passeia pela tela.
    tol = max(22.0, min(0.05 * W, med_w * 1.4))
    clusters = _cluster(all_boxes, tol=tol)

    counted: list[dict[str, Any]] = []
    for cluster in clusters:
        distinct = len({b["frame"] for b in cluster})
        fx = statistics.median(b["x"] for b in cluster)
        fy = statistics.median(b["y"] for b in cluster)
        fw = statistics.median(b["w"] for b in cluster)
        fh = statistics.median(b["h"] for b in cluster)
        center = {"cx": fx + fw / 2, "cy": fy + fh / 2}
        spread = statistics.pstdev([b["cx"] for b in cluster]) + statistics.pstdev(
            [b["cy"] for b in cluster]
        )
        counted.append(
            {
                "frames": distinct,
                "share": round(distinct / max(1, len(per_frame)), 2),
                "edge": _near_edge(center, W, H),
                "corner": _in_corner(center, W, H),
                "spread": round(spread, 1),
                "x": fx, "y": fy, "w": fw, "h": fh,
                "conf": statistics.fmean(b["conf"] for b in cluster),
            }
        )

    result["clusters"] = [
        {k: (round(v, 1) if isinstance(v, float) else v) for k, v in c.items()}
        for c in sorted(counted, key=lambda c: c["frames"], reverse=True)[:4]
    ]

    need = max(3, int(min_frame_hits * len(per_frame)))
    max_spread = max(24.0, 0.045 * W)  # cabeca de gente de verdade se mexe
    max_face = 0.12 * W  # rosto de facecam e pequeno; close de personagem nao

    def quality(c: dict[str, Any]) -> float:
        if c["frames"] < need or not c["edge"]:
            return -1.0
        if c["spread"] > max_spread:
            return -1.0
        if c["w"] > max_face:
            return -1.0  # close de personagem do jogo, nao facecam
        if c["share"] < 0.45:
            return -1.0
        return c["share"] + (0.2 if c["corner"] else 0.0)

    best = max(counted, key=quality) if counted else None
    if best is None or quality(best) < 0:
        if debug:
            return {**result, "error": f"nenhum cluster estavel de canto (need {need} frames)"}
        return None

    primary = _rect_from_cluster(best, pad, W, H)

    alternates = [
        _rect_from_cluster(c, pad, W, H)
        for c in counted
        if c is not best
        and quality(c) >= 0
        and abs(c["w"] - best["w"]) <= 0.4 * best["w"]  # mesma camera, outro canto
    ][:2]

    rect: dict[str, Any] = {
        **primary,
        "source_w": W,
        "source_h": H,
        "confidence": best["share"],
        "frames_hit": best["frames"],
        "frames_total": len(per_frame),
        "face_px": round(max(best["w"], best["h"]), 1),
        "alternates": alternates,
        "detected_at": time.time(),
    }
    if debug:
        rect["debug"] = result
    return rect


def _rect_from_cluster(
    c: dict[str, Any], pad: float, W: int, H: int
) -> dict[str, float]:
    side = min(max(c["w"], c["h"]) * pad, 0.5 * W)
    cx = c["x"] + c["w"] / 2
    cy = c["y"] + c["h"] / 2
    x, y = _snap(cx - side / 2, cy - side / 2, side, W, H)
    return {"x": round(x, 1), "y": round(y, 1), "w": round(side, 1), "h": round(side, 1)}


def detect_in_range(
    video: Path,
    start_s: float,
    dur_s: float,
    samples: int = 14,
    pad: float = 3.4,
) -> dict[str, Any] | None:
    """Deteccao do zero dentro de um trecho especifico (o clipe aprovado)."""
    tmp = video.parent / "_facecam_range.mp4"
    try:
        run(
            [
                find_exe("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{max(0.0, start_s):.3f}",
                "-t",
                f"{max(1.0, dur_s):.3f}",
                "-i",
                str(video),
                "-c",
                "copy",
                "-avoid_negative_ts",
                "make_zero",
                str(tmp),
            ]
        )
        return detect(tmp, samples=samples, pad=pad)
    except Exception:
        return None
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def confirm(
    video: Path,
    start_s: float,
    dur_s: float,
    rect: dict[str, Any],
    frames_n: int = 3,
    hit_ratio: float = 0.5,
    max_shift: float = 0.18,
) -> dict[str, Any] | None:
    """Confere se a facecam esta realmente num dos retangulos durante ESTE trecho.

    O streamer troca a posicao da cam entre cena e gameplay, entao tentamos o
    retangulo principal e os alternativos (guardados na deteccao). Sem isso o PIP
    mostra o chao. Devolve o rect vencedor (recentrado) ou None.
    """
    model = ensure_model()
    if not model or not rect:
        return None
    try:
        cv2 = _cv()
    except Exception:
        return None

    candidates: list[dict[str, Any]] = [rect]
    for alt in rect.get("alternates") or []:
        candidates.append({**alt, "source_w": rect.get("source_w"), "source_h": rect.get("source_h")})

    tmp = video.parent / "_facecam_confirm"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    step = max(0.4, dur_s / max(1, frames_n))
    try:
        run(
            [
                find_exe("ffmpeg"),
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{max(0.0, start_s):.3f}",
                "-t",
                f"{max(0.4, dur_s):.3f}",
                "-i",
                str(video),
                "-vf",
                f"fps=1/{step:.3f}",
                "-frames:v",
                str(frames_n),
                "-q:v",
                "2",
                str(tmp / "c%03d.jpg"),
            ]
        )
        shots = [p for p in sorted(tmp.glob("c*.jpg")) if p.stat().st_size > 0]
        if not shots:
            return None

        probe_w, probe_h = _probe_size(video)
        W = int(rect.get("source_w") or probe_w)
        H = int(rect.get("source_h") or probe_h)
        detector = cv2.FaceDetectorYN.create(str(model), "", (320, 320), 0.55, 0.3, 5000)

        best: tuple[float, dict[str, Any]] | None = None
        for cand in candidates:
            side = int(min(cand["w"], cand["h"]))
            if side < 24:
                continue
            x0 = max(0, min(int(cand["x"]), W - side))
            y0 = max(0, min(int(cand["y"]), H - side))
            hits = 0
            shifts: list[tuple[float, float]] = []
            for shot in shots:
                img = cv2.imread(str(shot))
                if img is None:
                    continue
                crop = img[y0 : y0 + side, x0 : x0 + side]
                if crop.size == 0:
                    continue
                detector.setInputSize((crop.shape[1], crop.shape[0]))
                try:
                    _n, faces = detector.detect(crop)
                except Exception:
                    continue
                if faces is None or not len(faces):
                    continue
                fx, fy, fw, fh = (float(v) for v in faces[0][:4])
                if fw > 0.85 * side:
                    continue
                hits += 1
                shifts.append(
                    (
                        (fx + fw / 2) - crop.shape[1] / 2,
                        (fy + fh / 2) - crop.shape[0] / 2,
                    )
                )
            ratio = hits / len(shots)
            if ratio < hit_ratio or not shifts:
                continue
            if best is None or ratio > best[0]:
                dx = statistics.fmean(s[0] for s in shifts)
                dy = statistics.fmean(s[1] for s in shifts)
                limit = side * max_shift
                dx = max(-limit, min(limit, dx))
                dy = max(-limit, min(limit, dy))
                x = max(0, min(int(x0 + dx), W - side))
                y = max(0, min(int(y0 + dy), H - side))
                best = (
                    ratio,
                    {
                        "x": float(x),
                        "y": float(y),
                        "w": float(side),
                        "h": float(side),
                        "source_w": W,
                        "source_h": H,
                        "confidence": round(ratio, 2),
                        "confirmed_hits": hits,
                        "confirmed_frames": len(shots),
                    },
                )
        return best[1] if best else None
    except Exception:
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def detect_jev(video: Path, samples: int = 3) -> dict[str, Any] | None:
    """Facecam via Jev: pergunta 'tem facecam?' e 'onde esta?' numa chamada.

    Sem heuristica de canto, sem limite de tamanho de rosto, sem supor posicao.
    """
    if not jev.ready():
        return None
    tmp = video.parent / "_facecam_jev"
    try:
        frames = _sample_frames(video, samples, tmp, width=768)
        if not frames:
            return None
        b64: list[str] = []
        for p in frames:
            b64.append(base64.b64encode(p.read_bytes()).decode("ascii"))
        state: list[Any] = [
            "Frames de uma live de jogo. Queremos achar a webcam do streamer "
            "(a janela com a pessoa real), se ela existir."
        ] + [jev.image_part(b) for b in b64]

        res = jev.decide(
            state,
            {
                "tem": {
                    "type": "noul",
                    "instructions": "Existe uma webcam do streamer sobreposta na imagem?",
                },
                "cam": {"type": "box", "instructions": "a webcam do streamer na imagem"},
            },
        )
        if not res:
            return None
        answers = res["answers"]
        tem = float((answers.get("tem") or {}).get("noul") or 0.0)
        boxans = answers.get("cam") or {}
        if tem < 0.5 or boxans.get("type") != "box":
            log(f"[facecam] jev: sem facecam (p={tem:.2f})")
            return None

        W, H = _probe_size(video)
        rect = jev.box_to_pixels(boxans["box"], W, H)
        if rect["w"] < 40 or rect["w"] > 0.6 * W:
            return None
        return {
            **rect,
            "source_w": W,
            "source_h": H,
            "confidence": round(float(boxans.get("confidence") or tem), 3),
            "frames_hit": len(frames),
            "frames_total": len(frames),
            "face_px": round(rect["w"], 1),
            "provider": "jev",
            "detected_at": time.time(),
        }
    except Exception as exc:
        log(f"[facecam] jev falhou: {exc}")
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


class FacecamCache:
    """Uma deteccao por stream, revalidada de tempo em tempo."""

    def __init__(self, work_dir: Path, cfg: dict[str, Any]):
        self.path = work_dir / "facecam.json"
        self.cfg = cfg
        self.current: dict[str, Any] | None = None
        self.checked_at = 0.0
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("w"):
                self.current = data
                self.checked_at = float(data.get("detected_at", 0))
        except Exception:
            pass

    def invalidate(self) -> None:
        """Forca nova deteccao no proximo ciclo (layout mudou)."""
        self.checked_at = 0.0

    def get(self, window: Path, force: bool = False) -> dict[str, Any] | None:
        if not self.cfg.get("enabled", True):
            return None
        refresh = float(self.cfg.get("refresh_s", 900))
        stale = force or time.time() - self.checked_at > refresh
        if self.current and not stale:
            return self.current

        rect = (
            detect_jev(window, samples=int(self.cfg.get("jev_samples", 3)))
            if str(self.cfg.get("provider", "yunet")) == "jev"
            else detect(
                window,
                samples=int(self.cfg.get("samples", 20)),
                pad=float(self.cfg.get("pad", 2.6)),
                min_frame_hits=float(self.cfg.get("min_frame_hits", 0.3)),
            )
        )
        self.checked_at = time.time()
        if rect:
            moved = self.current is None or abs(rect["x"] - self.current.get("x", -1e9)) > 8
            if moved:
                log(
                    f"[facecam] {rect['w']:.0f}px em ({rect['x']:.0f},{rect['y']:.0f}) "
                    f"rosto {rect['face_px']:.0f}px, "
                    f"{rect['frames_hit']}/{rect['frames_total']} frames"
                )
            self.current = rect
            save_json(self.path, rect)
        elif not self.current:
            self.checked_at = 0.0  # tenta de novo no proximo ciclo
        return self.current
