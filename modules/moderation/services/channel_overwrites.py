"""Restore original overwrites rather than accidentally granting channel access."""
import json
import discord

SCHEMA = """
CREATE TABLE IF NOT EXISTS channel_locks(
 guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, role_id INTEGER NOT NULL,
 original_value INTEGER, PRIMARY KEY(guild_id,channel_id,role_id)
);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def lock_channel(storage, channel: discord.TextChannel, role: discord.Role, actor):
    overwrite = channel.overwrites_for(role)
    rows = await storage.rows("SELECT original_value FROM channel_locks WHERE guild_id=? AND channel_id=? AND role_id=?",(channel.guild.id,channel.id,role.id))
    if rows:
        return False
    previous = overwrite.send_messages
    saved = None if previous is None else int(previous)
    await channel.set_permissions(role, overwrite=_modified(overwrite,False), reason=f"MOP lock by {actor}")
    await storage.execute("INSERT INTO channel_locks(guild_id,channel_id,role_id,original_value) VALUES(?,?,?,?)",(channel.guild.id,channel.id,role.id,saved))
    return True

def _modified(overwrite, value):
    overwrite.send_messages = value
    return overwrite

async def unlock_channel(storage, channel: discord.TextChannel, role: discord.Role, actor):
    rows = await storage.rows("SELECT original_value FROM channel_locks WHERE guild_id=? AND channel_id=? AND role_id=?",(channel.guild.id,channel.id,role.id))
    if not rows:
        return False
    value = rows[0]["original_value"]
    overwrite = channel.overwrites_for(role)
    overwrite.send_messages = None if value is None else bool(value)
    await channel.set_permissions(role,overwrite=overwrite,reason=f"MOP unlock by {actor}")
    await storage.execute("DELETE FROM channel_locks WHERE guild_id=? AND channel_id=? AND role_id=?",(channel.guild.id,channel.id,role.id))
    return True
