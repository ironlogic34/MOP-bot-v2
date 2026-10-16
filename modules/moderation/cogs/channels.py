"""Channel moderation with explicit permission requirements."""
import discord
from discord import app_commands
from discord.ext import commands

class Channels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Set Discord channel slowmode in seconds (0 to disable).")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int,0,21600]):
        channel = interaction.channel
        if not isinstance(channel, discord.TextChannel):
            raise app_commands.CheckFailure("Text channels only.")
        await channel.edit(slowmode_delay=seconds)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, channel.id, "slowmode", str(seconds))
        await interaction.response.send_message(f"Slowmode: {seconds}s.", ephemeral=True)

    @app_commands.command(description="Lock a text channel for the default role.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        channel = channel or interaction.channel
        await channel.set_permissions(interaction.guild.default_role, send_messages=False, reason=f"Locked by {interaction.user}")
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, channel.id, "lock")
        await interaction.response.send_message(f"Locked {channel.mention}.", ephemeral=True)

    @app_commands.command(description="Clear the explicit send-message deny for everyone.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        channel = channel or interaction.channel
        overwrite = channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite, reason=f"Unlocked by {interaction.user}")
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, channel.id, "unlock")
        await interaction.response.send_message(f"Unlocked {channel.mention}.", ephemeral=True)

    @app_commands.command(description="Remove recent messages from this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def cleanup(self, interaction: discord.Interaction, count: app_commands.Range[int,1,100]):
        if not isinstance(interaction.channel, discord.TextChannel):
            raise app_commands.CheckFailure("Text channels only.")
        await interaction.response.defer(ephemeral=True)
        removed = await interaction.channel.purge(limit=count, bulk=False)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, interaction.channel_id, "cleanup", str(len(removed)))
        await interaction.followup.send(f"Removed {len(removed)} messages.", ephemeral=True)

    @app_commands.command(description="Mark this channel NSFW.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def nsfw(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        channel = channel or interaction.channel
        await channel.edit(nsfw=True)
        await interaction.response.send_message("Channel marked age-restricted.", ephemeral=True)

    @app_commands.command(description="Remove the NSFW flag from a channel.")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_channels=True)
    async def sfw(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        channel = channel or interaction.channel
        await channel.edit(nsfw=False)
        await interaction.response.send_message("Channel NSFW flag removed.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Channels(bot))
