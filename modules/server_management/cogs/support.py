"""Support tickets recorded per server; private response by default."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.helpers.rate_limit import enforce_hourly_limit

class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Open a support ticket for this server.")
    @app_commands.guild_only()
    async def ticket(self, interaction: discord.Interaction, subject: app_commands.Range[str,1,120], description: app_commands.Range[str,1,1500]):
        try:
            await enforce_hourly_limit(self.bot.storage,"tickets",interaction.guild_id,interaction.user.id,limit=3,label="tickets")
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)
            return
        ident = await self.bot.storage.execute(
            "INSERT INTO tickets(guild_id,user_id,subject,description) VALUES(?,?,?,?)",
            (interaction.guild_id,interaction.user.id,subject[:120],description[:1500]))
        await interaction.response.send_message(f"Ticket #{ident} recorded. Staff can review it with /tickets.",ephemeral=True)

    @app_commands.command(description="Show the latest stored moderation actions.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def logs(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows("SELECT action,created_at FROM actions WHERE guild_id=? ORDER BY id DESC LIMIT 10",(interaction.guild_id,))
        await interaction.response.send_message("\n".join(f"{r['created_at']}: {r['action']}" for r in rows) or "No logged actions.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Support(bot))
