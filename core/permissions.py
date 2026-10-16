import discord
from discord import app_commands

def require_staff(interaction: discord.Interaction):
    if not isinstance(interaction.user, discord.Member):
        raise app_commands.CheckFailure("Server only.")
    if not (interaction.user.guild_permissions.manage_guild or interaction.user.guild_permissions.moderate_members):
        raise app_commands.CheckFailure("Staff permissions required.")

def check_hierarchy(actor: discord.Member, target: discord.Member, bot: discord.Member):
    if target.id == actor.guild.owner_id:
        raise app_commands.CheckFailure("Cannot moderate server owner.")
    if actor.id != actor.guild.owner_id and target.top_role >= actor.top_role:
        raise app_commands.CheckFailure("Target role is too high.")
    if target.top_role >= bot.top_role:
        raise app_commands.CheckFailure("Bot role is too low.")
