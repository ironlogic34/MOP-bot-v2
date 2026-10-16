"""No slash commands; monitors background tasks and reports failures."""
import logging
from discord.ext import commands

class ErrorMonitor(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.logger=logging.getLogger("mop.monitor")

    @commands.Cog.listener()
    async def on_command_error(self,ctx,error):
        self.logger.error("Text-command error: %s",error,exc_info=(type(error),error,error.__traceback__))

async def setup(bot):
    await bot.add_cog(ErrorMonitor(bot))
