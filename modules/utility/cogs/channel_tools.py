"""Staff message pinning utilities."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.validators.text import parse_discord_id

def _message_id(value):
    try:
        return parse_discord_id(value)
    except ValueError:
        raise app_commands.CheckFailure("Enter a valid message ID (numbers only).")

async def _fetch(interaction, message_id):
    try:
        return await interaction.channel.fetch_message(message_id)
    except discord.NotFound:
        raise app_commands.CheckFailure("Message not found in this channel.")

class ChannelTools(commands.Cog):
    @app_commands.command(description="Pin a message by its ID in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def pin(self,interaction:discord.Interaction,message_id:str):
        message=await _fetch(interaction,_message_id(message_id))
        try:
            await message.pin(reason=f"Pinned by {interaction.user}")
        except discord.HTTPException:
            raise app_commands.CheckFailure("Could not pin that message (the channel's pin limit may be reached, or MOP lacks permission).")
        await interaction.response.send_message("Message pinned.",ephemeral=True)

    @app_commands.command(description="Unpin a message by its ID in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def unpin(self,interaction:discord.Interaction,message_id:str):
        message=await _fetch(interaction,_message_id(message_id))
        try:
            await message.unpin(reason=f"Unpinned by {interaction.user}")
        except discord.HTTPException:
            raise app_commands.CheckFailure("Could not unpin that message (is it pinned, and does MOP have permission?).")
        await interaction.response.send_message("Message unpinned.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChannelTools(bot))
