"""Persistent server ticket and appeal records with safe per-guild ownership."""
from datetime import datetime,timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS ticket_messages(
 id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id INTEGER NOT NULL,
 author_id INTEGER NOT NULL, message TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS ban_appeals(
 id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL,
 user_id INTEGER NOT NULL, reason TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending',
 created_at TEXT NOT NULL,
 resolved_at TEXT, reviewer_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_appeals_guild ON ban_appeals(guild_id,status);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def create_appeal(storage,guild_id,user_id,reason):
    now=datetime.now(timezone.utc)
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute("SELECT created_at FROM ban_appeals WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 3",(guild_id,user_id)) as cur:
                rows=await cur.fetchall()
            if len(rows)>=3:
                raise ValueError("Maximum of three appeals per server.")
            if rows and (now-datetime.fromisoformat(rows[0]["created_at"])).total_seconds()<86400:
                raise ValueError("Wait 24 hours between appeals.")
            cur=await db.execute("INSERT INTO ban_appeals(guild_id,user_id,reason,created_at) VALUES(?,?,?,?)",(guild_id,user_id,reason[:1500],now.isoformat()))
            await db.commit()
            return cur.lastrowid
        except Exception:
            await db.rollback()
            raise
