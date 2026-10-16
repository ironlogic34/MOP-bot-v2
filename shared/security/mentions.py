"""Prevent user-generated content from pinging a whole server."""
import discord

SAFE_MENTIONS = discord.AllowedMentions.none()

def safe_user_text(text: str, *, max_length: int = 1800) -> str:
    """Escape Markdown and neutralize mentions for embed descriptions."""
    return discord.utils.escape_mentions(discord.utils.escape_markdown(text[:max_length]))
