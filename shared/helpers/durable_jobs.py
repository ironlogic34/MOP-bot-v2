"""SQLite-backed durable event outbox for retryable module work."""
import json
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS shared_jobs(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 event TEXT NOT NULL,
 payload TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0,
 last_error TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS shared_jobs_pending ON shared_jobs(state,id);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def enqueue(storage, event, payload):
    if not isinstance(payload,dict) or len(json.dumps(payload))>16000:
        raise ValueError("Job payload must be a JSON object of at most 16 KB.")
    return await storage.execute(
        "INSERT INTO shared_jobs(event,payload) VALUES(?,?)",
        (event[:100],json.dumps(payload)))

async def process_pending(storage, handlers, limit=25):
    rows=await storage.rows("SELECT id,event,payload,attempts FROM shared_jobs WHERE state='pending' AND attempts<5 ORDER BY id LIMIT ?",(limit,))
    completed=0
    for row in rows:
        handler=handlers.get(row["event"])
        if handler is None:
            continue
        try:
            await handler(**json.loads(row["payload"]))
        except Exception as exc:
            from shared.security.redaction import redact_secrets
            await storage.execute("UPDATE shared_jobs SET attempts=attempts+1,last_error=? WHERE id=?",(redact_secrets(exc)[:300],row["id"]))
        else:
            await storage.execute("UPDATE shared_jobs SET state='done',attempts=attempts+1 WHERE id=?",(row["id"],))
            completed+=1
    return completed
