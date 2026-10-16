"""Restart-safe scheduled unbans. Failed API requests remain pending for retry."""
from datetime import datetime, timezone
import logging
import discord
from discord.ext import commands, tasks

log = logging.getLogger("mop.sanctions")

class SanctionWorker(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.run_due.start()

    async def cog_unload(self):
        self.run_due.cancel()

    @tasks.loop(seconds=30)
    async def run_due(self):
        rows=await self.bot.storage.rows(
            "SELECT id,guild_id,user_id FROM sanctions WHERE status='pending' AND due_at<=? ORDER BY id LIMIT 50",
            (datetime.now(timezone.utc).isoformat(),))
        for row in rows:
            guild=self.bot.get_guild(row['guild_id'])
            if guild is None:
                continue
            try:
                await guild.unban(discord.Object(id=row['user_id']),reason="MOP timed ban expired")
            except discord.NotFound:
                pass
            except (discord.Forbidden,discord.HTTPException):
                log.exception("Unable to expire sanction %s",row['id'])
                continue
            await self.bot.storage.execute("UPDATE sanctions SET status='done' WHERE id=? AND status='pending'",(row['id'],))

    @run_due.before_loop
    async def before_run_due(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(SanctionWorker(bot))
