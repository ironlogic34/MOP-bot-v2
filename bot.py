"""MOP V2: public multi-server Discord bot."""
import asyncio
import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from core.database import Database
from core.errors import handle_error

EXTENSIONS = (
    "modules.moderation.cogs.members",
    "modules.moderation.cogs.channels",
    "modules.moderation.cogs.warnings",
    "modules.moderation.cogs.history",
    "modules.general.cogs.general",
    "modules.server_management.cogs.configuration",
    "modules.server_management.cogs.automation",
    "modules.server_management.cogs.leveling",
    "modules.server_management.cogs.support",
)

class MopBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.presences = True
        super().__init__(command_prefix=commands.when_mentioned, intents=intents)
        self.storage = Database(os.getenv("DATABASE_PATH", "data/mop.sqlite3"))
        self.tree.on_error = handle_error

    async def setup_hook(self):
        await self.storage.open()
        for extension in EXTENSIONS:
            await self.load_extension(extension)
        await self.tree.sync()

    async def on_guild_join(self, guild):
        await self.storage.settings(guild.id)

    async def close(self):
        try:
            await self.storage.close()
        finally:
            await super().close()

async def main():
    load_dotenv()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "replace_me":
        raise RuntimeError("Set DISCORD_TOKEN in .env")
    async with MopBot() as bot:
        await bot.start(token)

if __name__ == "__main__":
    asyncio.run(main())
