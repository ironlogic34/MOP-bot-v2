"""Persistent per-server warnings and moderation summaries."""
import discord
from discord import app_commands
from discord.ext import commands
from core.permissions import check_hierarchy
from shared.ui.pagination import Paginator

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Issue a persistent warning to a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        ident = await self.bot.storage.execute("INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)",
            (interaction.guild_id,member.id,interaction.user.id,reason))
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,member.id,"warn",reason)
        await interaction.response.send_message(f"Warning #{ident} recorded for {member.mention}.",ephemeral=True)

    @app_commands.command(description="Show recorded warnings for a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnhistory(self, interaction: discord.Interaction, member: discord.Member):
        rows = await self.bot.storage.rows("SELECT id,reason,created_at FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 100",
            (interaction.guild_id,member.id))
        view = Paginator(f"Warnings: {member}",[f"#{r['id']} {r['created_at']}: {r['reason']}" for r in rows],owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

    @app_commands.command(description="Show moderation actions taken by staff.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def modhistory(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows("SELECT action,actor_id,target_id,created_at FROM actions WHERE guild_id=? ORDER BY id DESC LIMIT 100",(interaction.guild_id,))
        view = Paginator("Moderation history",[f"{r['created_at']} • {r['action']} • <@{r['actor_id']}> → {r['target_id']}" for r in rows],owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

async def setup(bot):
    await bot.add_cog(Warnings(bot))
