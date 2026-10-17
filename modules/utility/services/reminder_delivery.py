"""Reminder delivery with bounded retries. reminders.sent: 0 pending, 1 delivered, 2 gave up.

A reminder is marked delivered only after the send succeeded. Transient failures are
retried every few minutes up to MAX_ATTEMPTS; permanent ones (DMs closed, user gone)
give up immediately.
"""
from datetime import datetime, timedelta, timezone

MAX_ATTEMPTS = 3
RETRY_MINUTES = 5

class PermanentDeliveryError(Exception):
    """The reminder can never be delivered (e.g. the user has DMs closed)."""

async def deliver_due(storage, send, now=None, limit=20):
    """send(user_id, message) is an async callable. Returns the number delivered."""
    now = now or datetime.now(timezone.utc)
    rows = await storage.rows(
        "SELECT id,user_id,message,attempts FROM reminders WHERE sent=0 AND due_at<=? ORDER BY id LIMIT ?",
        (now.isoformat(), limit))
    delivered = 0
    for row in rows:
        try:
            await send(row["user_id"], row["message"])
        except PermanentDeliveryError:
            await storage.execute("UPDATE reminders SET sent=2,attempts=attempts+1 WHERE id=?", (row["id"],))
        except Exception:
            attempts = row["attempts"] + 1
            if attempts >= MAX_ATTEMPTS:
                await storage.execute("UPDATE reminders SET sent=2,attempts=? WHERE id=?", (attempts, row["id"]))
            else:
                retry_at = (now + timedelta(minutes=RETRY_MINUTES)).isoformat()
                await storage.execute("UPDATE reminders SET attempts=?,due_at=? WHERE id=?", (attempts, retry_at, row["id"]))
        else:
            await storage.execute("UPDATE reminders SET sent=1,attempts=attempts+1 WHERE id=?", (row["id"],))
            delivered += 1
    return delivered
