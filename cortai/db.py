"""Estado compartilhado em SQLite. Um arquivo, WAL, seguro entre threads."""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS streams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    slug        TEXT UNIQUE NOT NULL,
    url         TEXT NOT NULL,
    platform    TEXT NOT NULL,
    title       TEXT,
    status      TEXT NOT NULL DEFAULT 'active',
    created_at  REAL NOT NULL,
    last_seen   REAL
);

CREATE TABLE IF NOT EXISTS clips (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stream_id   INTEGER NOT NULL REFERENCES streams(id),
    status      TEXT NOT NULL DEFAULT 'rendered',
    score       REAL,
    title       TEXT,
    hook        TEXT,
    caption     TEXT,
    hashtags    TEXT,
    why         TEXT,
    start_ts    REAL,
    end_ts      REAL,
    path        TEXT,
    thumb       TEXT,
    text        TEXT,
    meta        TEXT,
    published   TEXT,
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clips_status ON clips(status, created_at);
CREATE INDEX IF NOT EXISTS idx_clips_stream ON clips(stream_id, start_ts);

CREATE TABLE IF NOT EXISTS log (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ts      REAL NOT NULL,
    slug    TEXT,
    level   TEXT,
    msg     TEXT
);

CREATE TABLE IF NOT EXISTS usage (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          REAL NOT NULL,
    slug        TEXT,
    kind        TEXT NOT NULL,
    cost_usd    REAL NOT NULL,
    detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_usage_ts ON usage (ts);

CREATE TABLE IF NOT EXISTS publish_queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    clip_id     INTEGER NOT NULL REFERENCES clips(id),
    state       TEXT NOT NULL DEFAULT 'queued',
    attempts    INTEGER NOT NULL DEFAULT 0,
    next_try    REAL NOT NULL,
    publish_at  REAL,
    privacy     TEXT,
    error       TEXT,
    created_at  REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_queue_due ON publish_queue (state, next_try);
"""


class DB:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        with self.conn() as c:
            c.executescript(SCHEMA)
            cols = {r[1] for r in c.execute("PRAGMA table_info(clips)")}
            if "feedback" not in cols:
                c.execute("ALTER TABLE clips ADD COLUMN feedback INTEGER")
            scols = {r[1] for r in c.execute("PRAGMA table_info(streams)")}
            if "template" not in scols:
                c.execute("ALTER TABLE streams ADD COLUMN template TEXT")

    def conn(self) -> sqlite3.Connection:
        c = getattr(self._local, "conn", None)
        if c is None:
            c = sqlite3.connect(self.path, timeout=30, isolation_level=None)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA busy_timeout=15000")
            self._local.conn = c
        return c

    # -- streams -------------------------------------------------------
    def add_stream(self, slug: str, url: str, platform: str, title: str = "") -> int:
        c = self.conn()
        now = time.time()
        c.execute(
            "INSERT INTO streams (slug,url,platform,title,status,created_at,last_seen)"
            " VALUES (?,?,?,?,'active',?,?)"
            " ON CONFLICT(slug) DO UPDATE SET url=excluded.url,"
            " platform=excluded.platform, status='active', last_seen=excluded.last_seen",
            (slug, url, platform, title, now, now),
        )
        row = c.execute("SELECT id FROM streams WHERE slug=?", (slug,)).fetchone()
        return int(row["id"])

    def set_template(self, slug: str, template: str | None) -> None:
        self.conn().execute(
            "UPDATE streams SET template=? WHERE slug=?", (template or None, slug)
        )

    def set_stream_status(self, slug: str, status: str) -> None:
        self.conn().execute(
            "UPDATE streams SET status=?, last_seen=? WHERE slug=?",
            (status, time.time(), slug),
        )

    def streams(self, status: str | None = "active") -> list[sqlite3.Row]:
        if status:
            return list(
                self.conn().execute(
                    "SELECT * FROM streams WHERE status=? ORDER BY id", (status,)
                )
            )
        return list(self.conn().execute("SELECT * FROM streams ORDER BY id"))

    def remove_stream(self, slug: str) -> dict[str, Any]:
        """Apaga o canal e os clipes dele. Devolve os arquivos para quem for limpar."""
        c = self.conn()
        row = c.execute("SELECT id FROM streams WHERE slug=?", (slug,)).fetchone()
        if not row:
            return {"ok": False, "slug": slug, "clips": 0, "files": []}
        sid = int(row["id"])
        clips = list(c.execute("SELECT id, path FROM clips WHERE stream_id=?", (sid,)))
        ids = [int(r["id"]) for r in clips]
        if ids:
            marks = ",".join("?" * len(ids))
            c.execute(f"DELETE FROM publish_queue WHERE clip_id IN ({marks})", ids)
            c.execute(f"DELETE FROM clips WHERE id IN ({marks})", ids)
        c.execute("DELETE FROM streams WHERE id=?", (sid,))
        files = [str(r["path"]) for r in clips if r["path"]]
        return {"ok": True, "slug": slug, "clips": len(ids), "files": files}

    # -- clips ---------------------------------------------------------
    def add_clip(self, stream_id: int, **fields: Any) -> int:
        c = self.conn()
        fields.setdefault("created_at", time.time())
        for key in ("meta", "published"):
            if isinstance(fields.get(key), (dict, list)):
                fields[key] = json.dumps(fields[key], ensure_ascii=False)
        cols = ",".join(["stream_id", *fields.keys()])
        marks = ",".join(["?"] * (len(fields) + 1))
        cur = c.execute(
            f"INSERT INTO clips ({cols}) VALUES ({marks})",
            (stream_id, *fields.values()),
        )
        return int(cur.lastrowid)

    def update_clip(self, clip_id: int, **fields: Any) -> None:
        for key in ("meta", "published"):
            if isinstance(fields.get(key), (dict, list)):
                fields[key] = json.dumps(fields[key], ensure_ascii=False)
        sets = ",".join(f"{k}=?" for k in fields)
        self.conn().execute(
            f"UPDATE clips SET {sets} WHERE id=?", (*fields.values(), clip_id)
        )

    def clips(self, status: str | None = None, limit: int = 50) -> list[sqlite3.Row]:
        if status:
            return list(
                self.conn().execute(
                    "SELECT * FROM clips WHERE status=? ORDER BY created_at DESC LIMIT ?",
                    (status, limit),
                )
            )
        return list(
            self.conn().execute(
                "SELECT * FROM clips ORDER BY created_at DESC LIMIT ?", (limit,)
            )
        )

    def clip(self, clip_id: int) -> sqlite3.Row | None:
        return self.conn().execute(
            "SELECT * FROM clips WHERE id=?", (clip_id,)
        ).fetchone()

    # -- feedback ------------------------------------------------------
    def set_feedback(self, clip_id: int, vote: int) -> bool:
        if vote not in (-1, 0, 1):
            return False
        cur = self.conn().execute(
            "UPDATE clips SET feedback=? WHERE id=?", (vote, clip_id)
        )
        return cur.rowcount > 0

    # -- fila de publicacao --------------------------------------------
    def enqueue_publish(
        self, clip_id: int, privacy: str | None = None, publish_at: float | None = None
    ) -> int:
        now = time.time()
        cur = self.conn().execute(
            "INSERT INTO publish_queue (clip_id,state,attempts,next_try,publish_at,privacy,created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (clip_id, "queued", 0, now, publish_at, privacy, now),
        )
        return int(cur.lastrowid)

    def due_publish_jobs(self, limit: int = 5) -> list[sqlite3.Row]:
        return list(
            self.conn().execute(
                "SELECT * FROM publish_queue WHERE state='queued' AND next_try <= ?"
                " ORDER BY next_try LIMIT ?",
                (time.time(), limit),
            )
        )

    def claim_job(self, job_id: int) -> bool:
        cur = self.conn().execute(
            "UPDATE publish_queue SET state='uploading' WHERE id=? AND state='queued'",
            (job_id,),
        )
        return cur.rowcount > 0

    def finish_job(self, job_id: int, state: str, error: str | None = None,
                   next_try: float | None = None, count_attempt: bool = True) -> None:
        if next_try is None:
            self.conn().execute(
                "UPDATE publish_queue SET state=?, error=? WHERE id=?", (state, error, job_id)
            )
        elif count_attempt:
            self.conn().execute(
                "UPDATE publish_queue SET state=?, error=?, attempts=attempts+1, next_try=?"
                " WHERE id=?",
                (state, error, next_try, job_id),
            )
        else:
            # limite do YouTube nao e falha do clipe: reagenda sem gastar tentativa
            self.conn().execute(
                "UPDATE publish_queue SET state=?, error=?, next_try=? WHERE id=?",
                (state, error, next_try, job_id),
            )

    def pending_publishes(self) -> int:
        row = self.conn().execute(
            "SELECT COUNT(*) n FROM publish_queue WHERE state IN ('queued','uploading')"
        ).fetchone()
        return int(row["n"] or 0)

    # -- dedupe por tempo ----------------------------------------------
    def overlapping_clip(self, stream_id: int, start_ts: float, end_ts: float) -> int | None:
        """Id de um clipe existente que cobre boa parte deste intervalo."""
        rows = self.conn().execute(
            "SELECT id, start_ts, end_ts FROM clips WHERE stream_id=?"
            " AND start_ts IS NOT NULL AND end_ts IS NOT NULL"
            " AND end_ts >= ? AND start_ts <= ?",
            (stream_id, start_ts, end_ts),
        ).fetchall()
        span = max(1.0, end_ts - start_ts)
        for row in rows:
            overlap = min(row["end_ts"], end_ts) - max(row["start_ts"], start_ts)
            if overlap >= 0.5 * span:
                return int(row["id"])
        return None

    def feedback_stats(self) -> dict[str, Any]:
        rows = self.conn().execute(
            "SELECT feedback, COUNT(*) n FROM clips WHERE feedback IS NOT NULL "
            "GROUP BY feedback"
        ).fetchall()
        counts = {int(r["feedback"]): int(r["n"]) for r in rows}
        good = counts.get(1, 0)
        bad = counts.get(-1, 0)
        rated = good + bad
        return {
            "good": good,
            "bad": bad,
            "rated": rated,
            "precision": round(good / rated, 3) if rated else None,
        }

    # -- log -----------------------------------------------------------
    def log(self, slug: str | None, level: str, msg: str) -> None:
        self.conn().execute(
            "INSERT INTO log (ts,slug,level,msg) VALUES (?,?,?,?)",
            (time.time(), slug, level, msg[:2000]),
        )

    # -- custo ---------------------------------------------------------
    def add_usage(
        self, slug: str | None, kind: str, cost_usd: float, detail: Any = None
    ) -> None:
        self.conn().execute(
            "INSERT INTO usage (ts,slug,kind,cost_usd,detail) VALUES (?,?,?,?,?)",
            (
                time.time(),
                slug,
                kind,
                float(cost_usd),
                json.dumps(detail, ensure_ascii=False) if detail else None,
            ),
        )

    def cost_summary(self, since: float = 0.0) -> dict[str, Any]:
        rows = self.conn().execute(
            "SELECT slug, kind, SUM(cost_usd) AS total, COUNT(*) AS n "
            "FROM usage WHERE ts >= ? GROUP BY slug, kind",
            (since,),
        ).fetchall()
        total = 0.0
        by_kind: dict[str, float] = {}
        by_stream: dict[str, float] = {}
        calls = 0
        for r in rows:
            total += r["total"] or 0.0
            by_kind[r["kind"]] = by_kind.get(r["kind"], 0.0) + (r["total"] or 0.0)
            if r["slug"]:
                by_stream[r["slug"]] = by_stream.get(r["slug"], 0.0) + (r["total"] or 0.0)
            calls += r["n"] or 0
        return {
            "usd": round(total, 4),
            "calls": calls,
            "by_kind": {k: round(v, 4) for k, v in by_kind.items()},
            "by_stream": {k: round(v, 4) for k, v in by_stream.items()},
        }
