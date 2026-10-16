"""Persistent scheduled sanctions; server scoped and restart safe."""
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS sanctions (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
 action TEXT NOT NULL CHECK(action IN ('unban')),
 due_at TEXT NOT NULL, reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','done','cancelled')),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_sanctions_due ON sanctions(status,due_at);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def schedule_unban(storage, guild_id: int, user_id: int, minutes: int, reason: str):
    if minutes <= 0 or minutes > 525600:
        raise ValueError("Timed bans must be between 1 minute and 365 days.")
    due = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    async with storage.lock:
        await storage.db.execute("BEGIN IMMEDIATE")
        try:
            await storage.db.execute("UPDATE sanctions SET status='cancelled' WHERE guild_id=? AND user_id=? AND action='unban' AND status='pending'", (guild_id,user_id))
            await storage.db.execute("INSERT INTO sanctions(guild_id,user_id,action,due_at,reason) VALUES(?,?,?,?,?)", (guild_id,user_id,'unban',due,reason))
            await storage.db.commit()
        except Exception:
            await storage.db.rollback()
            raise

async def cancel_unban(storage,guild_id,user_id):
    await storage.execute("UPDATE sanctions SET status='cancelled' WHERE guild_id=? AND user_id=? AND action='unban' AND status='pending'",(guild_id,user_id))
