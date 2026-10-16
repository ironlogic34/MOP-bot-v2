"""Server-scoped moderation audit viewer."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.ui.pagination import Paginator

class Audit(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Review recent recorded moderation actions.")
    @app_commands.default_permissions(view_audit_log=True)
    @app_commands.checks.has_permissions(view_audit_log=True)
    @app_commands.guild_only()
    async def audit(self,interaction:discord.Interaction,member:discord.Member|None=None):
        if member:
            rows=await self.bot.storage.rows("SELECT action,detail,created_at FROM actions WHERE guild_id=? AND (actor_id=? OR target_id=?) ORDER BY id DESC LIMIT 100",(interaction.guild_id,member.id,member.id))
        else:
            rows=await self.bot.storage.rows("SELECT action,detail,created_at FROM actions WHERE guild_id=? ORDER BY id DESC LIMIT 100",(interaction.guild_id,))
        lines=[f"{r['created_at']} • **{r['action']}**: {discord.utils.escape_markdown(r['detail'][:150])}" for r in rows]
        view=Paginator("MOP moderation audit",lines,owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

async def setup(bot):
    await bot.add_cog(Audit(bot))
