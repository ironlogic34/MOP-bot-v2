"""MOP V2: public multi-server Discord bot."""
import asyncio
import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
from core.database import Database
from core.errors import handle_error
from modules.error_handling.repositories.error_records import initialize as initialize_errors
from shared.helpers.events import EventBus
from modules.economy.services.ledger import Ledger
from modules.moderation.services.sanctions import initialize as initialize_sanctions
from modules.moderation.services.channel_overwrites import initialize as initialize_locks
from modules.utility.services.schema import initialize as initialize_utility
from modules.music.services.player import Player
from modules.error_handling.services.monitor import install_loop_handler

EXTENSIONS = (
    "modules.moderation.cogs.members",
    "modules.moderation.cogs.audit",
    "modules.moderation.cogs.sanction_worker",
    "modules.moderation.cogs.channels",
    "modules.moderation.cogs.advanced_channels",
    "modules.moderation.cogs.warnings",
    "modules.moderation.cogs.history",
    "modules.general.cogs.general",
    "modules.server_management.cogs.configuration",
    "modules.server_management.cogs.automation",
    "modules.server_management.cogs.leveling",
    "modules.server_management.cogs.support",
    "modules.utility.cogs.reminders",
    "modules.utility.cogs.channel_tools",
    "modules.utility.cogs.conversion",
    "modules.music.cogs.playback",
    "modules.music.cogs.lastfm",
    "modules.economy.cogs.accounts",
    "modules.economy.cogs.market",
    "modules.help.cogs.help",
    "modules.error_handling.cogs.error_monitor",
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
        self.ledger = Ledger(self.storage)
        self.player = Player()
        self.events = EventBus()

    async def setup_hook(self):
        install_loop_handler(asyncio.get_running_loop())
        await self.storage.open()
        await self.ledger.initialize()
        await initialize_sanctions(self.storage)
        await initialize_locks(self.storage)
        await initialize_errors(self.storage)
        await initialize_utility(self.storage)
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
