"""Per-guild SQLite storage, created automatically."""
import asyncio
import json
from pathlib import Path
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(guild_id INTEGER PRIMARY KEY, value TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS warnings(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, moderator_id INTEGER, reason TEXT, active INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, actor_id INTEGER, target_id INTEGER, action TEXT, detail TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS activity(guild_id INTEGER, user_id INTEGER, words INTEGER DEFAULT 0, messages INTEGER DEFAULT 0, PRIMARY KEY(guild_id,user_id));
CREATE TABLE IF NOT EXISTS responders(guild_id INTEGER, trigger TEXT, response TEXT, PRIMARY KEY(guild_id,trigger));
CREATE TABLE IF NOT EXISTS reactions(guild_id INTEGER, trigger TEXT, emoji TEXT, PRIMARY KEY(guild_id,trigger,emoji));
CREATE TABLE IF NOT EXISTS tickets(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER, user_id INTEGER, subject TEXT, description TEXT, status TEXT DEFAULT 'open', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""
class Database:
    def __init__(self, path):
        self.path = Path(path)
        self.db = None
        self.lock = asyncio.Lock()

    async def open(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.path)
        self.db.row_factory = aiosqlite.Row
        await self.db.executescript(SCHEMA)
        await self.db.commit()

    async def close(self):
        if self.db:
            await self.db.close()

    async def execute(self, sql, params=()):
        async with self.lock:
            cur = await self.db.execute(sql, params)
            await self.db.commit()
            return cur.lastrowid

    async def rows(self, sql, params=()):
        async with self.lock:
            async with self.db.execute(sql, params) as cur:
                return await cur.fetchall()

    async def settings(self, guild_id):
        await self.execute("INSERT OR IGNORE INTO settings(guild_id) VALUES(?)", (guild_id,))
        row = await self.rows("SELECT value FROM settings WHERE guild_id=?", (guild_id,))
        return json.loads(row[0]["value"])

    async def set_setting(self, guild_id, key, value):
        async with self.lock:
            await self.db.execute("INSERT OR IGNORE INTO settings(guild_id) VALUES(?)", (guild_id,))
            async with self.db.execute("SELECT value FROM settings WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
            settings = json.loads(row["value"])
            settings[key] = value
            await self.db.execute("UPDATE settings SET value=? WHERE guild_id=?", (json.dumps(settings), guild_id))
            await self.db.commit()

    async def log(self, guild_id, actor, target, action, detail=""):
        await self.execute("INSERT INTO actions(guild_id,actor_id,target_id,action,detail) VALUES(?,?,?,?,?)", (guild_id,actor,target,action,detail))
