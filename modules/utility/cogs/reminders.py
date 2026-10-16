"""Persistent scheduled reminders and private moderation notifications."""
import asyncio
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands, tasks

class Reminders(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.worker.start()

    async def cog_unload(self):
        self.worker.cancel()

    @app_commands.command(description="Send a reminder after a number of minutes.")
    async def timer(self,interaction:discord.Interaction,minutes:app_commands.Range[int,1,10080],message:app_commands.Range[str,1,500]):
        when=(datetime.now(timezone.utc)+timedelta(minutes=minutes)).isoformat()
        await self.bot.storage.execute("INSERT INTO reminders(user_id,channel_id,due_at,message) VALUES(?,?,?,?)",
          (interaction.user.id,interaction.channel_id,when,message))
        await interaction.response.send_message(f"Reminder scheduled in {minutes} minutes.",ephemeral=True)

    @app_commands.command(description="Privately report a concern to this server's staff.")
    @app_commands.guild_only()
    async def notify(self,interaction:discord.Interaction,description:app_commands.Range[str,5,1000]):
        ident=await self.bot.storage.execute("INSERT INTO reports(guild_id,user_id,description) VALUES(?,?,?)",
          (interaction.guild_id,interaction.user.id,description))
        await interaction.response.send_message(f"Report #{ident} recorded for staff review.",ephemeral=True)

    @tasks.loop(seconds=30)
    async def worker(self):
        now=datetime.now(timezone.utc).isoformat()
        rows=await self.bot.storage.rows("SELECT id,user_id,channel_id,message FROM reminders WHERE due_at<=? AND sent=0 ORDER BY id LIMIT 20",(now,))
        for row in rows:
            claimed=await self.bot.storage.execute("UPDATE reminders SET sent=1 WHERE id=? AND sent=0",(row["id"],))
            try:
                user=await self.bot.fetch_user(row["user_id"])
                await user.send(f"⏰ Reminder: {row['message']}")
            except discord.HTTPException:
                pass

    @worker.before_loop
    async def before_worker(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Reminders(bot))
