"""Advanced moderation operations with explicit permission checks."""
import discord
from discord import app_commands
from discord.ext import commands
from modules.moderation.services.channel_overwrites import lock_channel,unlock_channel
from shared.ui.confirmation import Confirmation

class AdvancedChannels(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="Lock every text channel, preserving each original permission.")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def lockdown(self,interaction:discord.Interaction,enabled:bool):
        await interaction.response.defer(ephemeral=True)
        changed=0
        failures=0
        for channel in interaction.guild.text_channels:
            try:
                if enabled:
                    result=await lock_channel(self.bot.storage,channel,interaction.guild.default_role,interaction.user)
                else:
                    result=await unlock_channel(self.bot.storage,channel,interaction.guild.default_role,interaction.user)
                changed+=int(result)
            except discord.HTTPException:
                failures+=1
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,None,"lockdown",f"enabled={enabled}; changed={changed}; failures={failures}")
        await interaction.followup.send(f"{'Locked' if enabled else 'Restored'} {changed} channels; {failures} failures.",ephemeral=True)

    @app_commands.command(description="Set a role's send-message permission in this channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True,manage_channels=True)
    @app_commands.checks.has_permissions(manage_roles=True,manage_channels=True)
    async def denyperm(self,interaction:discord.Interaction,role:discord.Role,deny:bool=True):
        channel=interaction.channel
        if not isinstance(channel,discord.TextChannel):
            raise app_commands.CheckFailure("Text channel required.")
        if role >= interaction.guild.me.top_role or (interaction.user.id != interaction.guild.owner_id and role>=interaction.user.top_role):
            raise app_commands.CheckFailure("Role hierarchy prevents this change.")
        overwrite=channel.overwrites_for(role)
        overwrite.send_messages=False if deny else None
        await channel.set_permissions(role,overwrite=overwrite,reason=f"MOP denyperm by {interaction.user}")
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,role.id,"denyperm",f"{channel.id}:{deny}")
        await interaction.response.send_message(f"Updated send permission for {role.mention}.",ephemeral=True)

    @app_commands.command(description="Hide a channel from a role or reveal it again.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.has_permissions(manage_channels=True)
    async def hide(self,interaction:discord.Interaction,role:discord.Role,hidden:bool=True):
        channel=interaction.channel
        if not isinstance(channel,discord.TextChannel):
            raise app_commands.CheckFailure("Text channel required.")
        overwrite=channel.overwrites_for(role)
        overwrite.view_channel=False if hidden else None
        await channel.set_permissions(role,overwrite=overwrite,reason=f"MOP hide by {interaction.user}")
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,role.id,"hide",f"{channel.id}:{hidden}")
        await interaction.response.send_message(f"{'Hidden' if hidden else 'Restored'} channel visibility for {role.mention}.",ephemeral=True)

    @app_commands.command(description="Delete recent messages authored by MOP in this channel.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.has_permissions(manage_messages=True)
    async def botclear(self,interaction:discord.Interaction,count:app_commands.Range[int,1,100]=30):
        await interaction.response.defer(ephemeral=True)
        removed=await interaction.channel.purge(limit=min(count*5,500),check=lambda message:message.author.id==self.bot.user.id,bulk=False)
        await self.bot.storage.log(interaction.guild_id,interaction.user.id,interaction.channel_id,"botclear",str(len(removed)))
        await interaction.followup.send(f"Deleted {len(removed)} MOP messages.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdvancedChannels(bot))
