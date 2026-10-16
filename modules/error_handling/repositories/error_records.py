"""Persistent, bounded error records without raw tokens or traceback dumps."""
from shared.security.redaction import redact_secrets

SCHEMA = """
CREATE TABLE IF NOT EXISTS error_records (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 guild_id INTEGER, command_name TEXT,
 error_type TEXT NOT NULL, summary TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_error_records_guild ON error_records(guild_id,id);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def record(storage, guild_id, command_name, error):
    error_type = type(error).__name__[:100]
    summary = redact_secrets(str(error))[:500]
    return await storage.execute(
        "INSERT INTO error_records(guild_id,command_name,error_type,summary) VALUES(?,?,?,?)",
        (guild_id, str(command_name)[:100],error_type,summary))
