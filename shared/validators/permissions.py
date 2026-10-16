"""Runtime permission checks that cannot be bypassed by direct slash invocation."""
import discord
from discord import app_commands

def require_guild(interaction: discord.Interaction) -> discord.Guild:
    if interaction.guild is None:
        raise app_commands.CheckFailure("This command is only available inside a server.")
    return interaction.guild

def require_permission(interaction: discord.Interaction, **required: bool) -> discord.Member:
    require_guild(interaction)
    if not isinstance(interaction.user, discord.Member):
        raise app_commands.CheckFailure("Member context is required.")
    permissions = interaction.user.guild_permissions
    if not all(getattr(permissions, key, False) == expected for key, expected in required.items()):
        raise app_commands.CheckFailure("You lack the required server permissions.")
    return interaction.user

def require_server_owner(interaction: discord.Interaction) -> discord.Member:
    guild = require_guild(interaction)
    if interaction.user.id != guild.owner_id:
        raise app_commands.CheckFailure("Only this server's owner may perform this action.")
    return interaction.user

def require_role_hierarchy(actor: discord.Member, target: discord.Member, bot: discord.Member) -> None:
    if actor.guild.id != target.guild.id or bot.guild.id != target.guild.id:
        raise app_commands.CheckFailure("Members must belong to the same server.")
    if target.id == actor.guild.owner_id or target.id == bot.id:
        raise app_commands.CheckFailure("This member cannot be moderated.")
    if actor.id != actor.guild.owner_id and target.top_role >= actor.top_role:
        raise app_commands.CheckFailure("Your highest role must be above the target's.")
    if target.top_role >= bot.top_role:
        raise app_commands.CheckFailure("MOP's highest role must be above the target's.")
