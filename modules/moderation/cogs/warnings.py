"""Persistent per-server warnings and moderation summaries."""
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands
from modules.moderation.services.sanctions import schedule_unban
from modules.moderation.services.warning_policy import (
    ESCALATION_BAN, ESCALATION_HOURS, ESCALATION_TIMEOUT, active_warning_count, choose_escalation,
    clamp_expiry_days, clamp_threshold, clear_user_warnings, clear_warning)
from shared.ui.pagination import Paginator
from shared.validators.permissions import require_role_hierarchy as check_hierarchy

class Warnings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Issue a persistent warning to a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: app_commands.Range[str,1,500]):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        ident = await self.bot.storage.execute("INSERT INTO warnings(guild_id,user_id,moderator_id,reason) VALUES(?,?,?,?)",
            (interaction.guild_id,member.id,interaction.user.id,reason))
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,member.id,"warn",reason)
        settings = await self.bot.storage.settings(interaction.guild_id)
        threshold = clamp_threshold(settings.get("warning_threshold",3))
        expiry = clamp_expiry_days(settings.get("warning_expiry_days",0))
        count = await active_warning_count(self.bot.storage,interaction.guild_id,member.id,expiry)
        if count < threshold:
            await interaction.response.send_message(f"Warning #{ident} recorded for {member.mention} ({count}/{threshold}).",ephemeral=True)
            return
        configured = settings.get("warning_escalation",ESCALATION_TIMEOUT)
        mode = choose_escalation(configured,interaction.user.guild_permissions.ban_members)
        try:
            if mode == ESCALATION_BAN:
                await interaction.guild.ban(member,reason=f"MOP warning threshold ({threshold}) reached")
                await schedule_unban(self.bot.storage,interaction.guild_id,member.id,ESCALATION_HOURS*60,"Warning escalation")
            else:
                await member.timeout(timedelta(hours=ESCALATION_HOURS),reason=f"MOP warning threshold ({threshold}) reached")
        except (discord.Forbidden,discord.HTTPException):
            await interaction.response.send_message(f"Warning #{ident} saved. Automatic {mode} failed; check MOP's permissions and role position.",ephemeral=True)
            return
        await clear_user_warnings(self.bot.storage,interaction.guild_id,member.id)
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,member.id,"warning_escalation",f"{threshold} warnings, {ESCALATION_HOURS}-hour {mode}")
        note = ""
        if configured == ESCALATION_BAN and mode != ESCALATION_BAN:
            note = " (This server escalates to a ban, but you lack Ban Members, so a timeout was applied instead.)"
        await interaction.response.send_message(f"Warning #{ident} saved. Threshold reached: {ESCALATION_HOURS}-hour {mode} applied.{note}",ephemeral=True)

    @app_commands.command(description="Clear one warning by its ID so it no longer counts.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unwarn(self, interaction: discord.Interaction, warning_id: int):
        if not await clear_warning(self.bot.storage,interaction.guild_id,warning_id):
            await interaction.response.send_message("No active warning with that ID in this server.",ephemeral=True)
            return
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,None,"unwarn",f"#{warning_id}")
        await interaction.response.send_message(f"Warning #{warning_id} cleared.",ephemeral=True)

    @app_commands.command(description="Configure warning threshold, expiry and escalation.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.choices(escalation=[app_commands.Choice(name="24-hour timeout",value=ESCALATION_TIMEOUT),
                                      app_commands.Choice(name="24-hour ban (needs Ban Members)",value=ESCALATION_BAN)])
    async def warnconfig(self, interaction: discord.Interaction, threshold: app_commands.Range[int,1,20]|None=None,
                         expiry_days: app_commands.Range[int,0,3650]|None=None, escalation: app_commands.Choice[str]|None=None):
        if threshold is not None:
            await self.bot.storage.set_setting(interaction.guild_id,"warning_threshold",threshold)
        if expiry_days is not None:
            await self.bot.storage.set_setting(interaction.guild_id,"warning_expiry_days",expiry_days)
        if escalation is not None:
            await self.bot.storage.set_setting(interaction.guild_id,"warning_escalation",escalation.value)
        settings = await self.bot.storage.settings(interaction.guild_id)
        expiry = clamp_expiry_days(settings.get("warning_expiry_days",0))
        await interaction.response.send_message(
            f"Threshold: {clamp_threshold(settings.get('warning_threshold',3))} | Expiry: {str(expiry)+' days' if expiry else 'never'} | "
            f"Escalation: {settings.get('warning_escalation',ESCALATION_TIMEOUT)}",ephemeral=True)

    @app_commands.command(description="Show recorded warnings for a member.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnhistory(self, interaction: discord.Interaction, member: discord.Member):
        rows = await self.bot.storage.rows("SELECT id,reason,created_at,active FROM warnings WHERE guild_id=? AND user_id=? ORDER BY id DESC LIMIT 100",
            (interaction.guild_id,member.id))
        view = Paginator(f"Warnings: {member}",[f"#{r['id']} {r['created_at']}{'' if r['active'] else ' (cleared)'}: {discord.utils.escape_markdown(r['reason'])}" for r in rows],owner_id=interaction.user.id)
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
