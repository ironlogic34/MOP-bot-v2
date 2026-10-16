"""Staff message pinning utilities."""
import discord
from discord import app_commands
from discord.ext import commands

class ChannelTools(commands.Cog):
    @app_commands.command(description="Pin a message by its ID in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def pin(self,interaction:discord.Interaction,message_id:str):
        message=await interaction.channel.fetch_message(int(message_id))
        await message.pin(reason=f"Pinned by {interaction.user}")
        await interaction.response.send_message("Message pinned.",ephemeral=True)

    @app_commands.command(description="Unpin a message by its ID in this channel.")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def unpin(self,interaction:discord.Interaction,message_id:str):
        message=await interaction.channel.fetch_message(int(message_id))
        await message.unpin(reason=f"Unpinned by {interaction.user}")
        await interaction.response.send_message("Message unpinned.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChannelTools(bot))
