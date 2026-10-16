"""Per-server configuration, welcome/leave messages and invites."""
import discord
from discord import app_commands
from discord.ext import commands

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="View this server's MOP configuration.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def customise(self, interaction: discord.Interaction):
        data = await self.bot.storage.settings(interaction.guild_id)
        lines = [f"{k}: {v}" for k,v in sorted(data.items())]
        await interaction.response.send_message("\n".join(lines)[:1900] or "No custom settings yet.",ephemeral=True)

    @app_commands.command(description="Set the welcome channel and message.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def welcome(self, interaction: discord.Interaction, channel: discord.TextChannel, message: str):
        await self.bot.storage.set_setting(interaction.guild_id,"welcome",{"channel":channel.id,"message":message[:1000]})
        await interaction.response.send_message("Welcome message configured.",ephemeral=True)

    @app_commands.command(description="Create an invite to the current server.")
    @app_commands.guild_only()
    async def invite(self, interaction: discord.Interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise app_commands.CheckFailure("Use a text channel.")
        invite = await channel.create_invite(max_age=3600,max_uses=1,reason=f"Requested by {interaction.user}")
        await interaction.response.send_message(invite.url,ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        settings = await self.bot.storage.settings(member.guild.id)
        welcome = settings.get("welcome")
        if not welcome:
            return
        channel = member.guild.get_channel(welcome["channel"])
        if channel:
            text = welcome["message"].replace("{user}",member.mention).replace("{server}",member.guild.name)
            await channel.send(text,allowed_mentions=discord.AllowedMentions(users=True,roles=False,everyone=False))

async def setup(bot):
    await bot.add_cog(Configuration(bot))
