"""Standardized user-facing embeds."""
import discord
from shared.security.mentions import safe_user_text

def info_embed(title: str, description: str, *, color: int = 0x5865F2) -> discord.Embed:
    return discord.Embed(title=title[:256], description=safe_user_text(description, max_length=4096), color=color)

def error_embed(message: str) -> discord.Embed:
    return info_embed("MOP | Error", message, color=0xED4245)

def success_embed(message: str) -> discord.Embed:
    return info_embed("MOP | Success", message, color=0x57F287)
