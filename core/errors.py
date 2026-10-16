import logging
from shared.security.redaction import redact_secrets
from modules.error_handling.repositories.error_records import record
from discord import app_commands

log = logging.getLogger("mop.errors")

async def handle_error(interaction, error):
    if isinstance(error, app_commands.CommandInvokeError):
        error = error.original
    if isinstance(error, app_commands.CheckFailure):
        message = str(error) or "Permission denied."
    elif isinstance(error, app_commands.CommandOnCooldown):
        message = f"Slow down. Try again in {int(error.retry_after) + 1}s."
    else:
        log.error("Command failed: %s: %s", interaction.command, redact_secrets(error))
        try:
            await record(interaction.client.storage, interaction.guild_id, getattr(interaction.command, "name", "unknown"), error)
        except Exception:
            log.exception("Error persistence failed")
        message = "Command failed. The error was logged."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except Exception:
        log.exception("Could not respond to error")
