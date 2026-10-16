"""Appeal intake for banned users and staff review."""
import discord
from discord import app_commands
from discord.ext import commands
from modules.moderation.services.sanctions import cancel_unban
from modules.server_management.services.support_records import create_appeal
from shared.helpers.durable_jobs import enqueue
from shared.ui.pagination import Paginator

# Same wording for every failure so /appeal cannot be used to probe which servers
# MOP is in or who is banned where.
GENERIC_FAILURE = "MOP cannot accept an appeal for that server. Check the server ID, and that you are banned there."

class Appeals(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Submit a ban appeal by server ID, or review your server's appeals.")
    async def appeal(self,interaction:discord.Interaction,guild_id:str|None=None,reason:app_commands.Range[str,10,1500]|None=None):
        if guild_id and reason:
            guild=self.bot.get_guild(int(guild_id)) if guild_id.isdecimal() and len(guild_id)<=20 else None
            if guild is None:
                await interaction.response.send_message(GENERIC_FAILURE,ephemeral=True)
                return
            try:
                await guild.fetch_ban(discord.Object(id=interaction.user.id))
            except (discord.NotFound,discord.Forbidden,discord.HTTPException):
                await interaction.response.send_message(GENERIC_FAILURE,ephemeral=True)
                return
            try:
                ident=await create_appeal(self.bot.storage,guild.id,interaction.user.id,reason)
            except ValueError as exc:
                await interaction.response.send_message(str(exc),ephemeral=True)
                return
            await enqueue(self.bot.storage,"appeal_notify",{"guild_id":guild.id,"appeal_id":ident})
            await interaction.response.send_message(f"Appeal #{ident} submitted for staff review.",ephemeral=True)
            return
        if not interaction.guild or not isinstance(interaction.user,discord.Member) or not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("To submit an appeal, provide both guild_id and reason. Staff can review pending appeals inside their server.",ephemeral=True)
            return
        rows=await self.bot.storage.rows("SELECT id,user_id,reason,created_at FROM ban_appeals WHERE guild_id=? AND status='pending' ORDER BY id DESC LIMIT 100",(interaction.guild_id,))
        view=Paginator("Pending appeals",[f"#{r['id']} <@{r['user_id']}>: {discord.utils.escape_markdown(r['reason'][:180])}" for r in rows],owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

    @app_commands.command(description="Staff: set the channel where new ban appeals are posted.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def appealchannel(self,interaction:discord.Interaction,channel:discord.TextChannel):
        me=channel.permissions_for(interaction.guild.me)
        if not (me.view_channel and me.send_messages and me.embed_links):
            raise app_commands.CheckFailure("MOP needs View Channel, Send Messages and Embed Links there.")
        await self.bot.storage.set_setting(interaction.guild_id,"appeal_channel",channel.id)
        await interaction.response.send_message(f"New appeals will be posted in {channel.mention}.",ephemeral=True)

    @app_commands.command(description="Staff: accept or reject a pending ban appeal.")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.checks.has_permissions(ban_members=True)
    async def resolveappeal(self,interaction:discord.Interaction,appeal_id:int,accept:bool):
        rows=await self.bot.storage.rows("SELECT user_id,status FROM ban_appeals WHERE id=? AND guild_id=?",(appeal_id,interaction.guild_id))
        if not rows or rows[0]["status"]!="pending":
            await interaction.response.send_message("Pending appeal not found in this server.",ephemeral=True)
            return
        user_id=rows[0]["user_id"]
        if accept:
            try:
                await interaction.guild.unban(discord.Object(id=user_id),reason=f"Appeal #{appeal_id} accepted")
            except discord.NotFound:
                pass
            except (discord.Forbidden,discord.HTTPException):
                await interaction.response.send_message("MOP could not unban this user (check its Ban Members permission). The appeal is still pending.",ephemeral=True)
                return
            await cancel_unban(self.bot.storage,interaction.guild_id,user_id)
        await self.bot.storage.execute("UPDATE ban_appeals SET status=?,resolved_at=CURRENT_TIMESTAMP,reviewer_id=? WHERE id=? AND guild_id=? AND status='pending'",("accepted" if accept else "rejected",interaction.user.id,appeal_id,interaction.guild_id))
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,user_id,"appeal_accepted" if accept else "appeal_rejected",f"#{appeal_id}")
        await enqueue(self.bot.storage,"appeal_result_dm",{"user_id":user_id,"guild_id":interaction.guild_id,"accepted":bool(accept)})
        await interaction.response.send_message(f"Appeal #{appeal_id} {'accepted' if accept else 'rejected'}.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Appeals(bot))
