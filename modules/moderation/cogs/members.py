"""Member moderation: permission and hierarchy protected."""
from datetime import timedelta
import discord
from discord import app_commands
from discord.ext import commands
from shared.validators.permissions import require_role_hierarchy as check_hierarchy
from shared.validators.text import parse_discord_id

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Ban a member from this server.")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        await interaction.guild.ban(member, reason=reason)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, member.id, "ban", reason)
        await interaction.response.send_message(f"Banned {member.mention}.", ephemeral=True)

    @app_commands.command(description="Unban a user by Discord ID.")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        user = await self.bot.fetch_user(parse_discord_id(user_id))
        await interaction.guild.unban(user)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, user.id, "unban")
        await interaction.response.send_message(f"Unbanned {user}.", ephemeral=True)

    @app_commands.command(description="Kick a member from this server.")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        await member.kick(reason=reason)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, member.id, "kick", reason)
        await interaction.response.send_message(f"Kicked {member}.", ephemeral=True)

    @app_commands.command(description="Timeout a member for a specified number of minutes.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int,1,40320], reason: str = "No reason provided"):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, member.id, "mute", reason)
        await interaction.response.send_message(f"Timed out {member.mention} for {minutes} minutes.", ephemeral=True)

    @app_commands.command(description="Remove a member's timeout.")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        await member.timeout(None)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, member.id, "unmute")
        await interaction.response.send_message(f"Removed timeout for {member.mention}.", ephemeral=True)

    @app_commands.command(description="Change a member's server nickname.")
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.guild_only()
    @app_commands.checks.has_permissions(manage_nicknames=True)
    async def nickname(self, interaction: discord.Interaction, member: discord.Member, name: str):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        await member.edit(nick=name[:32])
        await interaction.response.send_message("Nickname updated.", ephemeral=True)

    @app_commands.command(description="Add or remove a role from a member.")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guild_only()
    @app_commands.choices(operation=[app_commands.Choice(name="Add",value="add"),app_commands.Choice(name="Remove",value="remove")])
    @app_commands.checks.has_permissions(manage_roles=True)
    async def role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role, operation: app_commands.Choice[str]):
        check_hierarchy(interaction.user, member, interaction.guild.me)
        if role >= interaction.guild.me.top_role or (interaction.user.id != interaction.guild.owner_id and role >= interaction.user.top_role):
            raise app_commands.CheckFailure("Role hierarchy prevents this operation.")
        if operation.value == "add":
            await member.add_roles(role)
        else:
            await member.remove_roles(role)
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, member.id, "role", f"{operation.value}:{role.id}")
        await interaction.response.send_message("Role updated.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Members(bot))
