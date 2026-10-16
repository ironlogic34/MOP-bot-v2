"""Server-scoped role automation based on tenure, messages and word activity."""
SCHEMA = """
CREATE TABLE IF NOT EXISTS autorole_rules(
 guild_id INTEGER NOT NULL, role_id INTEGER NOT NULL,
 rule TEXT NOT NULL CHECK(rule IN ('join','messages','words','tenure_days')),
 threshold INTEGER NOT NULL DEFAULT 0 CHECK(threshold>=0),
 PRIMARY KEY(guild_id,role_id,rule)
);
CREATE TABLE IF NOT EXISTS user_aliases(
 user_id INTEGER PRIMARY KEY, alias TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS alias_history(
 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, alias TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS channel_opt_outs(
 guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
 original_value INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 PRIMARY KEY(guild_id,channel_id,user_id)
);
CREATE TABLE IF NOT EXISTS bump_reminders(
 guild_id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL, interval_minutes INTEGER NOT NULL,
 next_at TEXT, enabled INTEGER NOT NULL DEFAULT 1
);
"""
async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

# /leave bookkeeping. MOP only ever restores an opt-out it recorded itself, and only
# to the exact send_messages value the member had before, so /leave restore can never
# be used to erase a deny that staff set on the member.
async def record_opt_out(storage,guild_id,channel_id,user_id,original):
    """original: None (inherit), True or False. Returns False if already recorded."""
    saved=None if original is None else int(bool(original))
    async with storage.lock:
        cur=await storage.db.execute("INSERT OR IGNORE INTO channel_opt_outs(guild_id,channel_id,user_id,original_value) VALUES(?,?,?,?)",(guild_id,channel_id,user_id,saved))
        await storage.db.commit()
        return cur.rowcount==1

async def get_opt_out(storage,guild_id,channel_id,user_id):
    """Returns (found, original) where original is None, True or False."""
    rows=await storage.rows("SELECT original_value FROM channel_opt_outs WHERE guild_id=? AND channel_id=? AND user_id=?",(guild_id,channel_id,user_id))
    if not rows:
        return False,None
    value=rows[0]["original_value"]
    return True,(None if value is None else bool(value))

async def delete_opt_out(storage,guild_id,channel_id,user_id):
    await storage.execute("DELETE FROM channel_opt_outs WHERE guild_id=? AND channel_id=? AND user_id=?",(guild_id,channel_id,user_id))
