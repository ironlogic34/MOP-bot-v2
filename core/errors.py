import logging
from discord import app_commands

log = logging.getLogger("mop.errors")

async def handle_error(interaction, error):
    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) or "Permission denied."
    else:
        log.exception("Command failed: %s", interaction.command, exc_info=error)
        message = "Command failed. The error was logged."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        log.exception("Could not respond to error")
