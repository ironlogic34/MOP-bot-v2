"""Last.fm API features are optional; music playback does not require tokens."""
import os
from urllib.parse import quote
import discord
from discord import app_commands
from discord.ext import commands

class LastFM(commands.Cog):
    @app_commands.command(description="Check whether Last.fm integration is configured.")
    async def fm(self,interaction:discord.Interaction):
        ready=bool(os.getenv("LASTFM_API_KEY"))
        await interaction.response.send_message("Last.fm API key configured; account linking is not implemented yet." if ready else "Last.fm is not configured. Music playback still works.",ephemeral=True)

    @app_commands.command(description="View Last.fm linking status.")
    async def lastfm(self,interaction:discord.Interaction):
        await interaction.response.send_message("Last.fm account authorization and scrobbling are not yet implemented.",ephemeral=True)

    @app_commands.command(description="Find song lyrics through an external search.")
    async def lyrics(self,interaction:discord.Interaction,title:str):
        url="https://www.google.com/search?q="+quote(title+" lyrics")
        await interaction.response.send_message(f"Lyrics search: {url}",ephemeral=True)

async def setup(bot):
    await bot.add_cog(LastFM())
