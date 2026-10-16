"""Global virtual economy accounts and rewards."""
import discord
from discord import app_commands
from discord.ext import commands
from modules.economy.services.ledger import Ledger

class Accounts(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.ledger=bot.ledger

    @app_commands.command(description="View your global MOP Points.")
    async def balance(self,interaction:discord.Interaction,user:discord.User|None=None):
        user=user or interaction.user
        row=await self.ledger.account(user.id)
        await interaction.response.send_message(f"{user.mention}: {row['wallet']} Points | Savings: {row['savings']}",ephemeral=True)

    @app_commands.command(description="Claim a daily virtual Points reward.")
    async def daily(self,interaction:discord.Interaction):
        try:
            await self.ledger.reward(interaction.user.id,"last_daily",100,86400)
            await interaction.response.send_message("Claimed 100 Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Earn Points through a cooldown-based task.")
    async def work(self,interaction:discord.Interaction):
        try:
            await self.ledger.reward(interaction.user.id,"last_work",25,3600)
            await interaction.response.send_message("Earned 25 Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Move Points into savings.")
    async def deposit(self,interaction:discord.Interaction,amount:app_commands.Range[int,1,100000000]):
        try:
            await self.ledger.move(interaction.user.id,"wallet","savings",amount)
            await interaction.response.send_message(f"Deposited {amount} Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Move Points out of savings.")
    async def withdraw(self,interaction:discord.Interaction,amount:app_commands.Range[int,1,100000000]):
        try:
            await self.ledger.move(interaction.user.id,"savings","wallet",amount)
            await interaction.response.send_message(f"Withdrew {amount} Points.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Transfer Points to another user.")
    async def transfer(self,interaction:discord.Interaction,user:discord.User,amount:app_commands.Range[int,1,100000000]):
        if user.bot:
            await interaction.response.send_message("Cannot transfer Points to bots.",ephemeral=True)
            return
        try:
            await self.ledger.transfer(interaction.user.id,user.id,amount)
            await interaction.response.send_message(f"Transferred {amount} Points to {user.mention}.",ephemeral=True)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)

    @app_commands.command(description="Show the highest global Point balances.")
    async def leaderboard(self,interaction:discord.Interaction):
        rows=await self.bot.storage.rows("SELECT user_id,wallet FROM economy_accounts ORDER BY wallet DESC LIMIT 10")
        await interaction.response.send_message("\n".join(f"{i}. <@{r['user_id']}>: {r['wallet']}" for i,r in enumerate(rows,1)) or "No accounts yet.",ephemeral=True)

    @app_commands.command(description="View your global economy account.")
    async def economy(self,interaction:discord.Interaction):
        row=await self.ledger.account(interaction.user.id)
        await interaction.response.send_message(f"Global MOP Points: {row['wallet']} | Savings: {row['savings']}\nUse /daily, /work, /market and /inventory.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Accounts(bot))
