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
CREATE TABLE IF NOT EXISTS bump_reminders(
 guild_id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL, interval_minutes INTEGER NOT NULL,
 next_at TEXT, enabled INTEGER NOT NULL DEFAULT 1
);
"""
async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()
