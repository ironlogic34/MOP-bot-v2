"""Voice playback using direct, approved HTTPS audio streams.

Anyone in the voice channel may queue tracks (bounded per user and per server).
Controls that affect everyone (pause, resume, skip, stop, volume, shuffle, loop)
need Manage Channels, the server's DJ role, or being the only listener.
"""
import random
import discord
from discord import app_commands
from discord.ext import commands

class Playback(commands.Cog):
    def __init__(self,bot):
        self.bot=bot
        self.player=bot.player

    @staticmethod
    def member_channel(interaction):
        if not isinstance(interaction.user,discord.Member) or not interaction.user.voice or not interaction.user.voice.channel:
            raise app_commands.CheckFailure("Join a voice channel first.")
        return interaction.user.voice.channel

    async def voice(self,interaction):
        """Return the guild's voice client, connecting only when queueing a track."""
        channel=self.member_channel(interaction)
        voice=interaction.guild.voice_client
        if voice and voice.channel!=channel:
            raise app_commands.CheckFailure("Join the bot's current voice channel.")
        if not voice:
            voice=await channel.connect()
        return voice

    def connected_voice(self,interaction):
        """Return the existing voice client; never joins a channel."""
        channel=self.member_channel(interaction)
        voice=interaction.guild.voice_client
        if not voice or not voice.is_connected():
            raise app_commands.CheckFailure("MOP is not playing in a voice channel.")
        if voice.channel!=channel:
            raise app_commands.CheckFailure("Join the bot's current voice channel.")
        return voice

    async def controller(self,interaction):
        """connected_voice() plus the DJ gate for commands that affect everyone."""
        voice=self.connected_voice(interaction)
        member=interaction.user
        perms=member.guild_permissions
        if perms.manage_channels or perms.administrator:
            return voice
        role_id=(await self.bot.storage.settings(interaction.guild_id)).get("dj_role")
        if role_id and any(role.id==role_id for role in member.roles):
            return voice
        listeners=[m for m in voice.channel.members if not m.bot]
        if len(listeners)==1 and listeners[0].id==member.id:
            return voice
        raise app_commands.CheckFailure("You need Manage Channels or the server's DJ role to control playback (or be the only listener).")

    @app_commands.command(description="Queue an approved direct HTTPS audio stream.")
    @app_commands.guild_only()
    async def play(self,interaction:discord.Interaction,url:str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.player.validate_url(url)
            self.player.check_capacity(interaction.guild_id,interaction.user.id)
        except ValueError as exc:
            raise app_commands.CheckFailure(str(exc))
        voice=await self.voice(interaction)
        try:
            self.player.enqueue(interaction.guild_id,url,interaction.user.id)
        except ValueError as exc:
            raise app_commands.CheckFailure(str(exc))
        if not voice.is_playing() and not voice.is_paused():
            await self.player.play_next(interaction.guild)
        await interaction.followup.send("Audio queued.",ephemeral=True)

    @app_commands.command(description="Pause current music playback.")
    @app_commands.guild_only()
    async def pause(self,interaction:discord.Interaction):
        voice=await self.controller(interaction)
        if voice.is_playing():
            voice.pause()
        await interaction.response.send_message("Paused.",ephemeral=True)

    @app_commands.command(description="Resume paused music playback.")
    @app_commands.guild_only()
    async def resume(self,interaction:discord.Interaction):
        voice=await self.controller(interaction)
        if voice.is_paused():
            voice.resume()
        await interaction.response.send_message("Resumed.",ephemeral=True)

    @app_commands.command(description="Skip the current track.")
    @app_commands.guild_only()
    async def skip(self,interaction:discord.Interaction):
        voice=await self.controller(interaction)
        if voice.is_playing() or voice.is_paused():
            self.player.skipped.add(interaction.guild_id)
            voice.stop()
        await interaction.response.send_message("Skipped.",ephemeral=True)

    @app_commands.command(description="Stop playback, clear the queue and disconnect.")
    @app_commands.guild_only()
    async def stop(self,interaction:discord.Interaction):
        voice=await self.controller(interaction)
        self.player.reset(interaction.guild_id)
        await voice.disconnect(force=True)
        await interaction.response.send_message("Playback stopped.",ephemeral=True)

    @app_commands.command(description="Adjust MOP's stream output volume from 0 to 100.")
    @app_commands.guild_only()
    async def volume(self,interaction:discord.Interaction,percent:app_commands.Range[int,0,100]):
        voice=await self.controller(interaction)
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
        await interaction.response.send_message("\n".join(f"{i}. {url}" for i,(url,_) in enumerate(items[:15],1))[:1900] or "Queue empty.",ephemeral=True)

    @app_commands.command(description="Toggle repeating the current track.")
    @app_commands.guild_only()
    async def loop(self,interaction:discord.Interaction):
        await self.controller(interaction)
        enabled=not self.player.loop.get(interaction.guild_id,False)
        self.player.loop[interaction.guild_id]=enabled
        await interaction.response.send_message(f"Track loop {'on' if enabled else 'off'}.",ephemeral=True)

    @app_commands.command(description="Shuffle the pending queue.")
    @app_commands.guild_only()
    async def shuffle(self,interaction:discord.Interaction):
        await self.controller(interaction)
        random.shuffle(self.player.queue(interaction.guild_id))
        await interaction.response.send_message("Queue shuffled.",ephemeral=True)

    @app_commands.command(description="Set (or clear) the role allowed to control music playback.")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def djrole(self,interaction:discord.Interaction,role:discord.Role|None=None):
        await self.bot.storage.set_setting(interaction.guild_id,"dj_role",role.id if role else None)
        await interaction.response.send_message(f"DJ role: {role.mention}." if role else "DJ role cleared.",ephemeral=True,allowed_mentions=discord.AllowedMentions.none())

    @app_commands.command(description="Show the basic music controller.")
    @app_commands.guild_only()
    async def music(self,interaction:discord.Interaction):
        voice=interaction.guild.voice_client
        status="Connected" if voice and voice.is_connected() else "Disconnected"
        await interaction.response.send_message(f"**MOP Music** • {status}\nUse /play with a direct HTTPS audio URL, /queue, /skip, /volume and /stop.",ephemeral=True)

async def setup(bot):
    await bot.add_cog(Playback(bot))
