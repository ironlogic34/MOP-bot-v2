"""Support tickets recorded per server; private response by default."""
import discord
from discord import app_commands
from discord.ext import commands

class Support(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Open a support ticket for this server.")
    @app_commands.guild_only()
    async def ticket(self, interaction: discord.Interaction, subject: str, description: str):
        ident = await self.bot.storage.execute(
            "INSERT INTO tickets(guild_id,user_id,subject,description) VALUES(?,?,?,?)",
            (interaction.guild_id,interaction.user.id,subject[:120],description[:1500]))
        await interaction.response.send_message(f"Ticket #{ident} recorded. A staff notification interface is planned for a later implementation phase.",ephemeral=True)

    @app_commands.command(description="Show the latest stored moderation actions.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def logs(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows("SELECT action,created_at FROM actions WHERE guild_id=? ORDER BY id DESC LIMIT 10",(interaction.guild_id,))
        await interaction.response.send_message("\n".join(f"{r['created_at']}: {r['action']}" for r in rows) or "No logged actions.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Support(bot))
