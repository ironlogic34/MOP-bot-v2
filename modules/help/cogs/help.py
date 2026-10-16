"""Category-wise compact command directory, generated from registered commands."""
import discord
from discord import app_commands
from discord.ext import commands
from shared.ui.pagination import Paginator

CATEGORIES={
    "Moderation":("ban","unban","kick","mute","unmute","warn","warnhistory","modhistory","lock","unlock","slowmode","cleanup","nsfw","sfw","role","nickname","history","stat","mkdstat"),
    "General":("ping","userinfo","bug","echo"),
    "Server Management":("customise","welcome","invite","autoresponder","autoreact","level","rankcard","ticket","logs"),
    "Utility":("timer","notify","pin","unpin","img2gif"),
    "Music":("music","play","pause","resume","skip","queue","nowplaying","volume","loop","shuffle","lyrics","fm","lastfm","stop"),
    "Economy":("economy","balance","daily","work","deposit","withdraw","transfer","leaderboard","market","inventory","buy","sell","additem"),
    "Help":("help",),
}

class CategoryPicker(discord.ui.Select):
    def __init__(self,bot):
        self.bot=bot
        super().__init__(placeholder="Select command category",options=[discord.SelectOption(label=k,value=k) for k in CATEGORIES])
    async def callback(self,interaction:discord.Interaction):
        known={cmd.name:cmd for cmd in self.bot.tree.get_commands()}
        entries=[]
        for name in CATEGORIES[self.values[0]]:
            cmd=known.get(name)
            if cmd:
                entries.append(f"**/{name}** — {cmd.description[:100]}")
        view=Paginator(f"MOP Help • {self.values[0]}",entries,owner_id=interaction.user.id,page_size=7)
        await interaction.response.send_message(embed=view.embed(),view=view,ephemeral=True)

class HelpView(discord.ui.View):
    def __init__(self,bot):
        super().__init__(timeout=180)
        self.add_item(CategoryPicker(bot))

class Help(commands.Cog):
    def __init__(self,bot):
        self.bot=bot

    @app_commands.command(name="help",description="Browse MOP commands by category with short descriptions.")
    async def help_command(self,interaction:discord.Interaction):
        await interaction.response.send_message("**MOP Help Center**\nSelect a category below to see its commands.",view=HelpView(self.bot),ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
