"""Case-insensitive whole-word automation, scoped to each guild."""
import re
import discord
from discord import app_commands
from discord.ext import commands
from core.permissions import require_staff

class Automation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(description="Add or update an automatic reply rule.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def autoresponder(self, interaction: discord.Interaction, trigger: str, response: str):
        require_staff(interaction)
        await self.bot.storage.execute("INSERT OR REPLACE INTO responders(guild_id,trigger,response) VALUES(?,?,?)",
                                       (interaction.guild_id,trigger.casefold()[:100],response[:1800]))
        await interaction.response.send_message("Reply rule saved.",ephemeral=True)

    @app_commands.command(description="Add an automatic reaction rule.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def autoreact(self, interaction: discord.Interaction, trigger: str, emoji: str):
        require_staff(interaction)
        await self.bot.storage.execute("INSERT OR IGNORE INTO reactions(guild_id,trigger,emoji) VALUES(?,?,?)",
                                       (interaction.guild_id,trigger.casefold()[:100],emoji[:100]))
        await interaction.response.send_message("Reaction rule saved.",ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot:
            return
        text = message.content.casefold()
        rules = await self.bot.storage.rows("SELECT trigger,response FROM responders WHERE guild_id=?",(message.guild.id,))
        for rule in rules:
            if re.search(r"(?<!\w)"+re.escape(rule["trigger"])+r"(?!\w)",text):
                await message.reply(rule["response"],mention_author=False,allowed_mentions=discord.AllowedMentions.none())
                break
        reactions = await self.bot.storage.rows("SELECT trigger,emoji FROM reactions WHERE guild_id=?",(message.guild.id,))
        added = set()
        for rule in reactions:
            if len(added)>=4:
                break
            if rule["emoji"] not in added and re.search(r"(?<!\w)"+re.escape(rule["trigger"])+r"(?!\w)",text):
                try:
                    await message.add_reaction(rule["emoji"])
                    added.add(rule["emoji"])
                except (discord.HTTPException, discord.Forbidden):
                    continue

async def setup(bot):
    await bot.add_cog(Automation(bot))
