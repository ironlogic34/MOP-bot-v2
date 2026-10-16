"""Global virtual Points credit, loans and restricted administration."""
import os
import discord
from discord import app_commands
from discord.ext import commands
from modules.economy.services.credit import adjust,reset,borrow,repay

class Credit(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(description="View your interest-free virtual credit balance.")
    async def credit(self,interaction:discord.Interaction):
        rows=await self.bot.storage.rows("SELECT COALESCE(SUM(outstanding),0) AS owed FROM point_loans WHERE user_id=? AND status='active'",(interaction.user.id,))
        owed=rows[0]["owed"]
        await interaction.response.send_message(f"Outstanding: {owed} Points. Available: {5000-owed} Points. No interest or real currency.",ephemeral=True)

    @app_commands.command(description="Borrow or repay interest-free virtual Points.")
    @app_commands.choices(action=[app_commands.Choice(name="Borrow",value="borrow"),app_commands.Choice(name="Repay",value="repay")])
    async def loan(self,interaction:discord.Interaction,action:app_commands.Choice[str],amount:app_commands.Range[int,1,5000]):
        try:
            if action.value=="borrow":
                await borrow(self.bot.storage,interaction.user.id,amount)
            else:
                await repay(self.bot.storage,interaction.user.id,amount)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)
            return
        await interaction.response.send_message(f"{action.value.title()} completed: {amount} virtual Points.",ephemeral=True)

    def authorized(self,interaction):
        configured={x.strip() for x in os.getenv("MOP_OWNER_IDS","").split(",") if x.strip().isdigit()}
        if str(interaction.user.id) not in configured:
            raise app_commands.CheckFailure("This operation is restricted to configured MOP bot operators.")

    @app_commands.command(description="Operator: adjust a user's global Points wallet.")
    async def addbalance(self,interaction:discord.Interaction,user:discord.User,amount:app_commands.Range[int,-100000000,100000000],reason:app_commands.Range[str,1,300]):
        self.authorized(interaction)
        try:
            await adjust(self.bot.storage,interaction.user.id,user.id,amount,reason)
        except ValueError as exc:
            await interaction.response.send_message(str(exc),ephemeral=True)
            return
        await interaction.response.send_message(f"Adjusted {user.id} by {amount} Points. Audit saved.",ephemeral=True)

    @app_commands.command(description="Operator: reset a user's wallet and savings.")
    async def resetbalance(self,interaction:discord.Interaction,user:discord.User,reason:app_commands.Range[str,1,300]):
        self.authorized(interaction)
        cleared=await reset(self.bot.storage,interaction.user.id,user.id,reason)
        await interaction.response.send_message(f"Reset {user.id}; cleared {cleared} Points. Outstanding loans are unaffected.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Credit(bot))
