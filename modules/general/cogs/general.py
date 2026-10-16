"""General public and staff commands."""
import time
import discord
from discord import app_commands
from discord.ext import commands
from core.permissions import require_staff
from shared.security.mentions import SAFE_MENTIONS

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Check gateway latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"MOP gateway latency: {round(self.bot.latency*1000)} ms.",ephemeral=True)

    @app_commands.command(description="Show public Discord member information.")
    @app_commands.guild_only()
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member | None = None):
        member = member or interaction.user
        embed = discord.Embed(title=f"User: {member.display_name}")
        embed.add_field(name="User ID",value=str(member.id))
        embed.add_field(name="Joined Discord",value=discord.utils.format_dt(member.created_at,"D"))
        embed.add_field(name="Joined server",value=discord.utils.format_dt(member.joined_at,"D") if member.joined_at else "Unknown")
        embed.set_thumbnail(url=member.display_avatar.url)
        await interaction.response.send_message(embed=embed,ephemeral=True)

    @app_commands.command(description="Show a summary of the bot's current status.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_guild=True)
    async def bug(self, interaction: discord.Interaction):
        await interaction.response.send_message("Error details are written to the application logs. This initial build does not yet provide an error-log viewer.",ephemeral=True)

    @app_commands.command(description="Send a staff announcement to a channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def echo(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel | None = None):
        require_staff(interaction)
        channel = channel or interaction.channel
        await channel.send(message,allowed_mentions=SAFE_MENTIONS)
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,channel.id,"echo",message[:200])
        await interaction.response.send_message("Announcement sent.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(General(bot))
