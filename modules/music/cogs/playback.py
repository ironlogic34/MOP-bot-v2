"""Voice playback using direct, approved HTTPS audio streams."""
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from modules.music.services.player import Player

class Playback(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.player=bot.player

    async def voice(self,interaction):
        if not isinstance(interaction.user,discord.Member) or not interaction.user.voice or not interaction.user.voice.channel:
            raise app_commands.CheckFailure("Join a voice channel first.")
        voice=interaction.guild.voice_client
        if voice and voice.channel!=interaction.user.voice.channel:
            raise app_commands.CheckFailure("Join the bot's current voice channel.")
        if not voice:
            voice=await interaction.user.voice.channel.connect()
        return voice

    @app_commands.command(description="Queue an approved direct HTTPS audio stream.")
    @app_commands.guild_only()
    async def play(self,interaction:discord.Interaction,url:str):
        await interaction.response.defer(ephemeral=True)
        await self.player.validate_url(url)
        voice=await self.voice(interaction)
        self.player.queue(interaction.guild_id).append(url)
        if not voice.is_playing() and not voice.is_paused():
            await self.player.play_next(interaction.guild)
        await interaction.followup.send("Audio queued.",ephemeral=True)

    @app_commands.command(description="Pause current music playback.")
    @app_commands.guild_only()
    async def pause(self,interaction:discord.Interaction):
        voice=await self.voice(interaction)
        if voice.is_playing():
            voice.pause()
        await interaction.response.send_message("Paused.",ephemeral=True)

    @app_commands.command(description="Resume paused music playback.")
    @app_commands.guild_only()
    async def resume(self,interaction:discord.Interaction):
        voice=await self.voice(interaction)
        if voice.is_paused():
            voice.resume()
        await interaction.response.send_message("Resumed.",ephemeral=True)

    @app_commands.command(description="Skip the current track.")
    @app_commands.guild_only()
    async def skip(self,interaction:discord.Interaction):
        voice=await self.voice(interaction)
        if voice.is_playing() or voice.is_paused():
            voice.stop()
        await interaction.response.send_message("Skipped.",ephemeral=True)

    @app_commands.command(description="Stop playback, clear the queue and disconnect.")
    @app_commands.guild_only()
    async def stop(self,interaction:discord.Interaction):
        voice=await self.voice(interaction)
        self.player.queue(interaction.guild_id).clear()
        self.player.loop[interaction.guild_id]=False
        await voice.disconnect(force=True)
        await interaction.response.send_message("Playback stopped.",ephemeral=True)

    @app_commands.command(description="Adjust MOP's stream output volume from 0 to 100.")
    @app_commands.guild_only()
    async def volume(self,interaction:discord.Interaction,percent:app_commands.Range[int,0,100]):
        voice=await self.voice(interaction)
        self.player.volume[interaction.guild_id]=percent/100
        if isinstance(voice.source,discord.PCMVolumeTransformer):
            voice.source.volume=percent/100
        await interaction.response.send_message(f"MOP volume: {percent}%.",ephemeral=True)

    @app_commands.command(description="View the current audio stream.")
    @app_commands.guild_only()
    async def nowplaying(self,interaction:discord.Interaction):
        url=self.player.current.get(interaction.guild_id)
        await interaction.response.send_message(f"Playing: {url}" if url else "Nothing playing.",ephemeral=True)

    @app_commands.command(description="View upcoming audio streams.")
    @app_commands.guild_only()
    async def queue(self,interaction:discord.Interaction):
        items=self.player.queue(interaction.guild_id)
        await interaction.response.send_message("\n".join(f"{i}. {url}" for i,url in enumerate(items[:15],1))[:1900] or "Queue empty.",ephemeral=True)

    @app_commands.command(description="Toggle repeating the current track.")
    @app_commands.guild_only()
    async def loop(self,interaction:discord.Interaction):
        enabled=not self.player.loop.get(interaction.guild_id,False)
        self.player.loop[interaction.guild_id]=enabled
        await interaction.response.send_message(f"Track loop {'on' if enabled else 'off'}.",ephemeral=True)

    @app_commands.command(description="Shuffle the pending queue.")
    @app_commands.guild_only()
    async def shuffle(self,interaction:discord.Interaction):
        import random
        random.shuffle(self.player.queue(interaction.guild_id))
        await interaction.response.send_message("Queue shuffled.",ephemeral=True)

    @app_commands.command(description="Show the basic music controller.")
    @app_commands.guild_only()
    async def music(self,interaction:discord.Interaction):
        voice=interaction.guild.voice_client
        status="Connected" if voice and voice.is_connected() else "Disconnected"
        await interaction.response.send_message(f"**MOP Music** • {status}\nUse /play with a direct HTTPS audio URL, /queue, /skip, /volume and /stop.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Playback(bot))
