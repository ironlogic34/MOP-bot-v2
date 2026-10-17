"""Staff views of member tickets and reports (previously write-only)."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.ui.pagination import Paginator

def _short(text, limit=160):
    return discord.utils.escape_markdown(text[:limit]).replace("\n", " ")

class StaffInbox(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Staff: list open support tickets for this server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def tickets(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows(
            "SELECT id,user_id,subject,description,created_at FROM tickets WHERE guild_id=? AND status='open' ORDER BY id DESC LIMIT 100",
            (interaction.guild_id,))
        lines = [f"#{r['id']} <@{r['user_id']}> • {_short(r['subject'], 60)} — {_short(r['description'], 120)}" for r in rows]
        view = Paginator("Open tickets", lines, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)

    @app_commands.command(description="Staff: close a support ticket by ID.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def closeticket(self, interaction: discord.Interaction, ticket_id: int):
        async with self.bot.storage.lock:
            cur = await self.bot.storage.db.execute(
                "UPDATE tickets SET status='closed' WHERE id=? AND guild_id=? AND status='open'", (ticket_id, interaction.guild_id))
            await self.bot.storage.db.commit()
            closed = cur.rowcount == 1
        if not closed:
            await interaction.response.send_message("No open ticket with that ID in this server.", ephemeral=True)
            return
        await self.bot.storage.log(interaction.guild_id, interaction.user.id, None, "ticket_closed", f"#{ticket_id}")
        await interaction.response.send_message(f"Ticket #{ticket_id} closed.", ephemeral=True)

    @app_commands.command(description="Staff: view the latest member reports for this server.")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.has_permissions(moderate_members=True)
    async def reports(self, interaction: discord.Interaction):
        rows = await self.bot.storage.rows(
            "SELECT id,user_id,description,created_at FROM reports WHERE guild_id=? ORDER BY id DESC LIMIT 100", (interaction.guild_id,))
        lines = [f"#{r['id']} {r['created_at']} <@{r['user_id']}>: {_short(r['description'], 200)}" for r in rows]
        view = Paginator("Member reports", lines, owner_id=interaction.user.id)
        await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(StaffInbox(bot))
