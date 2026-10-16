"""Persistent ban-appeal records with safe per-guild ownership."""
from datetime import datetime,timedelta,timezone

MIN_GAP_HOURS = 24
WINDOW_DAYS = 30
MAX_PER_WINDOW = 3

SCHEMA = """
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
    """One pending appeal at a time, 24h apart, at most 3 per rolling 30 days (per server)."""
    now=datetime.now(timezone.utc)
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute("SELECT created_at,status FROM ban_appeals WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 50",(guild_id,user_id)) as cur:
                rows=await cur.fetchall()
            if any(r["status"]=="pending" for r in rows):
                raise ValueError("You already have a pending appeal for this server.")
            created=[datetime.fromisoformat(r["created_at"]) for r in rows]
            if created and now-created[0]<timedelta(hours=MIN_GAP_HOURS):
                raise ValueError(f"Wait {MIN_GAP_HOURS} hours between appeals.")
            if sum(1 for c in created if now-c<timedelta(days=WINDOW_DAYS))>=MAX_PER_WINDOW:
                raise ValueError(f"Maximum of {MAX_PER_WINDOW} appeals per {WINDOW_DAYS} days for this server.")
            cur=await db.execute("INSERT INTO ban_appeals(guild_id,user_id,reason,created_at) VALUES(?,?,?,?)",(guild_id,user_id,reason[:1500],now.isoformat()))
            await db.commit()
            return cur.lastrowid
        except Exception:
            await db.rollback()
            raise
