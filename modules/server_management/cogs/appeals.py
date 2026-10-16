"""Appeal intake for banned users and staff review."""
import discord
from discord import app_commands
from discord.ext import commands
from modules.server_management.services.support_records import create_appeal
from shared.ui.pagination import Paginator

class Appeals(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Submit a ban appeal by server ID, or review your server's appeals.")
    async def appeal(self,interaction:discord.Interaction,guild_id:str|None=None,reason:app_commands.Range[str,10,1500]|None=None):
        if guild_id and reason:
            if not guild_id.isdecimal():
                await interaction.response.send_message("Enter a numeric server ID.",ephemeral=True)
                return
            guild=self.bot.get_guild(int(guild_id))
            if guild is None:
                await interaction.response.send_message("MOP is not in that server.",ephemeral=True)
                return
            try:
                await guild.fetch_ban(discord.Object(id=interaction.user.id))
            except discord.NotFound:
                await interaction.response.send_message("You are not currently banned from that server.",ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.response.send_message("MOP cannot verify bans in that server.",ephemeral=True)
                return
            try:
                ident=await create_appeal(self.bot.storage,guild.id,interaction.user.id,reason)
            except ValueError as exc:
                await interaction.response.send_message(str(exc),ephemeral=True)
                return
            await interaction.response.send_message(f"Appeal #{ident} submitted for staff review.",ephemeral=True)
            return
        if not interaction.guild or not isinstance(interaction.user,discord.Member) or not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("To submit an appeal, provide both guild_id and reason. Staff can review pending appeals inside their server.",ephemeral=True)
            return
        rows=await self.bot.storage.rows("SELECT id,user_id,reason,created_at FROM ban_appeals WHERE guild_id=? AND status='pending' ORDER BY id DESC LIMIT 100",(interaction.guild_id,))
        view=Paginator("Pending appeals",[f"#{r['id']} <@{r['user_id']}>: {discord.utils.escape_markdown(r['reason'][:180])}" for r in rows],owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

    @app_commands.command(description="Staff: accept or reject a pending ban appeal.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def resolveappeal(self,interaction:discord.Interaction,appeal_id:int,accept:bool):
        rows=await self.bot.storage.rows("SELECT user_id,status FROM ban_appeals WHERE id=? AND guild_id=?",(appeal_id,interaction.guild_id))
        if not rows or rows[0]["status"]!="pending":
            await interaction.response.send_message("Pending appeal not found in this server.",ephemeral=True)
            return
        if accept:
            try:
                await interaction.guild.unban(discord.Object(id=rows[0]["user_id"]),reason=f"Appeal #{appeal_id} accepted")
            except discord.NotFound:
                pass
        await self.bot.storage.execute("UPDATE ban_appeals SET status=?,resolved_at=CURRENT_TIMESTAMP,reviewer_id=? WHERE id=? AND guild_id=? AND status='pending'",("accepted" if accept else "rejected",interaction.user.id,appeal_id,interaction.guild_id))
        await interaction.response.send_message(f"Appeal #{appeal_id} {'accepted' if accept else 'rejected'}.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Appeals(bot))
