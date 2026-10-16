"""Reusable confirm/cancel dialog with owner-only controls."""
import asyncio
import discord

class Confirmation(discord.ui.View):
    def __init__(self, owner_id: int, *, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.owner_id = owner_id
        self.result: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("Only the requester may use this confirmation.", ephemeral=True)
            return False
        return True

    async def _finish(self, interaction: discord.Interaction, result: bool):
        self.result = result
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finish(interaction, True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._finish(interaction, False)
