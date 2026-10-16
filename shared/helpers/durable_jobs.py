"""SQLite-backed durable job outbox: at-least-once delivery with bounded retries.

Semantics
- enqueue() persists a job; process_pending() runs due jobs through handlers.
- A job is claimed (pending -> running) before its handler runs, so two overlapping
  passes cannot run the same job twice.
- A failing handler is retried with exponential backoff (30s, 60s, 120s, ...) and
  becomes terminal 'failed' after MAX_ATTEMPTS. Failed jobs are kept for diagnosis.
- Jobs left 'running' by a crash are returned to 'pending' on initialize(), so a
  handler may run more than once and must be idempotent or tolerate repeats.
- Jobs for events with no registered handler are left untouched and never block others.
"""
import json
from datetime import datetime, timedelta, timezone
from shared.security.redaction import redact_secrets

MAX_ATTEMPTS = 5
BASE_BACKOFF_SECONDS = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_jobs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event TEXT NOT NULL,
 payload TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending' CHECK(state IN ('pending','running','done','failed')),
 attempts INTEGER NOT NULL DEFAULT 0,
 run_after TEXT,
 claimed_at TEXT,
 last_error TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS shared_jobs_pending ON shared_jobs(state,run_after,id);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        # Anything still 'running' belongs to a process that died mid-handler.
        await storage.db.execute("UPDATE shared_jobs SET state='pending',claimed_at=NULL WHERE state='running'")
        await storage.db.commit()

async def enqueue(storage, event, payload):
    if not isinstance(event, str) or not event.strip():
        raise ValueError("Job event name is required.")
    if not isinstance(payload, dict) or len(json.dumps(payload)) > 16000:
        raise ValueError("Job payload must be a JSON object of at most 16 KB.")
    return await storage.execute(
        "INSERT INTO shared_jobs(event,payload) VALUES(?,?)",
        (event[:100], json.dumps(payload)))

async def _claim(storage, job_id, stamp):
    async with storage.lock:
        cur = await storage.db.execute(
            "UPDATE shared_jobs SET state='running',claimed_at=? WHERE id=? AND state='pending'", (stamp, job_id))
        await storage.db.commit()
        return cur.rowcount == 1

async def _finish(storage, job_id, attempts):
    await storage.execute(
        "UPDATE shared_jobs SET state='done',attempts=?,claimed_at=NULL,last_error=NULL WHERE id=?", (attempts, job_id))

async def _fail(storage, job_id, attempts, error, now):
    message = redact_secrets(error)[:300]
    if attempts >= MAX_ATTEMPTS:
        await storage.execute(
            "UPDATE shared_jobs SET state='failed',attempts=?,claimed_at=NULL,last_error=? WHERE id=?",
            (attempts, message, job_id))
        return
    retry_at = (now + timedelta(seconds=BASE_BACKOFF_SECONDS * 2 ** (attempts - 1))).isoformat()
    await storage.execute(
        "UPDATE shared_jobs SET state='pending',attempts=?,run_after=?,claimed_at=NULL,last_error=? WHERE id=?",
        (attempts, retry_at, message, job_id))

async def process_pending(storage, handlers, limit=25, now=None):
    """Run due jobs. handlers maps event name -> async callable(**payload). Returns completed count."""
    names = list(handlers)
    if not names:
        return 0
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat()
    marks = ",".join("?" * len(names))
    rows = await storage.rows(
        f"SELECT id,event,payload,attempts FROM shared_jobs WHERE state='pending' AND event IN ({marks}) "
        "AND (run_after IS NULL OR run_after<=?) ORDER BY id LIMIT ?",
        (*names, stamp, limit))
    completed = 0
    for row in rows:
        if not await _claim(storage, row["id"], stamp):
            continue
        attempts = row["attempts"] + 1
        try:
            await handlers[row["event"]](**json.loads(row["payload"]))
        except Exception as exc:
            await _fail(storage, row["id"], attempts, exc, now)
        else:
            await _finish(storage, row["id"], attempts)
            completed += 1
    return completed
