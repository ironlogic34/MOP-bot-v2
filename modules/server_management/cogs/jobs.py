"""Runs durable background jobs (appeal notifications and result DMs)."""
import logging
import discord
from discord.ext import commands, tasks
from shared.helpers.durable_jobs import process_pending
from shared.security.mentions import SAFE_MENTIONS

log = logging.getLogger("mop.jobs")

class Jobs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.handlers = {
            "appeal_notify": self.appeal_notify,
            "appeal_result_dm": self.appeal_result_dm,
        }
        self.worker.start()

    async def cog_unload(self):
        self.worker.cancel()

    @tasks.loop(seconds=15)
    async def worker(self):
        try:
            await process_pending(self.bot.storage, self.handlers)
        except Exception:
            log.exception("Job worker pass failed")

    @worker.before_loop
    async def before_worker(self):
        await self.bot.wait_until_ready()

    async def appeal_notify(self, guild_id, appeal_id):
        rows = await self.bot.storage.rows("SELECT user_id,reason FROM ban_appeals WHERE id=? AND guild_id=? AND status='pending'", (appeal_id, guild_id))
        if not rows:
            return
        channel_id = (await self.bot.storage.settings(guild_id)).get("appeal_channel")
        guild = self.bot.get_guild(guild_id)
        channel = guild.get_channel(channel_id) if guild and channel_id else None
        if channel is None:
            return  # no staff channel configured (or it was deleted); /appeal still lists it
        embed = discord.Embed(title=f"New ban appeal #{appeal_id}", description=discord.utils.escape_markdown(rows[0]["reason"][:900]))
        embed.add_field(name="User", value=f"<@{rows[0]['user_id']}> ({rows[0]['user_id']})")
        embed.set_footer(text="Review with /resolveappeal")
        try:
            await channel.send(embed=embed, allowed_mentions=SAFE_MENTIONS)
        except discord.Forbidden:
            log.warning("Cannot post appeal #%s in guild %s: missing permissions", appeal_id, guild_id)

    async def appeal_result_dm(self, user_id, guild_id, accepted):
        guild = self.bot.get_guild(guild_id)
        name = discord.utils.escape_markdown(guild.name) if guild else "the server"
        verdict = "accepted. You may rejoin." if accepted else "rejected."
        try:
            user = await self.bot.fetch_user(user_id)
            await user.send(f"Your ban appeal for **{name}** was {verdict}")
        except (discord.Forbidden, discord.NotFound):
            return  # DMs closed or user gone: permanent, do not retry

async def setup(bot):
    await bot.add_cog(Jobs(bot))
