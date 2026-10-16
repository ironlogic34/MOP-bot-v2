"""Activity and member history. Only events logged after deployment exist."""
import discord
from discord import app_commands
from discord.ext import commands

class History(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Show recorded member activity and moderation count.")
    @app_commands.guild_only()
    async def stat(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        rows = await self.bot.storage.rows("SELECT words,messages FROM activity WHERE guild_id=? AND user_id=?",(interaction.guild_id,member.id))
        data = rows[0] if rows else {"words":0,"messages":0}
        await interaction.response.send_message(f"{member.mention}: {data['messages']} messages, {data['words']} words recorded.",ephemeral=True)

    @app_commands.command(description="Show a member's recorded activity and warnings.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        activity = await self.bot.storage.rows("SELECT words,messages FROM activity WHERE guild_id=? AND user_id=?",(interaction.guild_id,member.id))
        warns = await self.bot.storage.rows("SELECT COUNT(*) AS n FROM warnings WHERE guild_id=? AND user_id=?",(interaction.guild_id,member.id))
        data = activity[0] if activity else {"words":0,"messages":0}
        await interaction.response.send_message(f"{member.mention}\nRecorded messages: {data['messages']}\nWords: {data['words']}\nWarnings: {warns[0]['n']}\nTracking begins when MOP is deployed.",ephemeral=True)

    @app_commands.command(description="Show recent staff action totals.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mkdstat(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows("SELECT action,COUNT(*) AS n FROM actions WHERE guild_id=? GROUP BY action ORDER BY n DESC",(interaction.guild_id,))
        await interaction.response.send_message("\n".join(f"{r['action']}: {r['n']}" for r in rows) or "No recorded actions.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(History(bot))
