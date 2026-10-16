SCHEMA = """
CREATE TABLE IF NOT EXISTS reminders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, channel_id INTEGER, due_at TEXT NOT NULL, message TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, description TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""
async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()
