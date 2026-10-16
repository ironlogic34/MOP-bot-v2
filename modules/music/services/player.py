"""One audio session per guild, for authorized direct audio URLs only."""
import asyncio
import logging
import os
import ipaddress
import socket
from urllib.parse import urlsplit
import discord

log=logging.getLogger("mop.music")

MAX_QUEUE_PER_GUILD=50
MAX_QUEUE_PER_USER=5
# Only plain HTTPS may be opened by FFmpeg: this blocks file://, concat:, data:,
# http:// (and other schemes) even if a URL or a redirect tries to use them.
FFMPEG_BEFORE_OPTIONS="-nostdin -protocol_whitelist https,tls,tcp -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

class Player:
    def __init__(self):
        self.queues={}
        self.volume={}
        self.loop={}
        self.current={}
        self.current_entry={}
        self.skipped=set()

    @staticmethod
    async def validate_url(url):
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use a public HTTPS direct audio URL.")
        host=parsed.hostname.lower().rstrip(".")
        allowed={h.strip().lower() for h in os.getenv("MUSIC_ALLOWED_HOSTS","").split(",") if h.strip()}
        if not allowed or host not in allowed:
            raise ValueError("Audio host not approved. Configure MUSIC_ALLOWED_HOSTS with trusted hosts first.")
        try:
            addresses=await asyncio.get_running_loop().getaddrinfo(host,443,type=socket.SOCK_STREAM)
        except OSError:
            raise ValueError("Cannot resolve audio host.")
        for addr in addresses:
            ip=ipaddress.ip_address(addr[4][0])
            if not ip.is_global:
                raise ValueError("Private and internal network addresses are blocked.")
        if len(url)>1800:
            raise ValueError("URL too long.")
        return url

    def queue(self,guild_id):
        """Pending entries as (url, requester_id) tuples."""
        return self.queues.setdefault(guild_id,[])

    def check_capacity(self,guild_id,user_id):
        queue=self.queue(guild_id)
        if len(queue)>=MAX_QUEUE_PER_GUILD:
            raise ValueError(f"The queue is full ({MAX_QUEUE_PER_GUILD} tracks).")
        if sum(1 for _,uid in queue if uid==user_id)>=MAX_QUEUE_PER_USER:
            raise ValueError(f"You can have at most {MAX_QUEUE_PER_USER} tracks queued.")

    def enqueue(self,guild_id,url,user_id):
        self.check_capacity(guild_id,user_id)
        self.queue(guild_id).append((url,user_id))

    async def play_next(self,guild):
        voice=guild.voice_client
        if not voice or not voice.is_connected():
            return
        queue=self.queue(guild.id)
        while queue:
            entry=queue.pop(0)
            try:
                # Re-check right before FFmpeg resolves the host, shrinking the
                # window between validation and use.
                await self.validate_url(entry[0])
            except ValueError as exc:
                log.warning("Skipping queued track: %s",exc)
                continue
            self.current[guild.id]=entry[0]
            self.current_entry[guild.id]=entry
            source=discord.FFmpegPCMAudio(entry[0],options="-vn",before_options=FFMPEG_BEFORE_OPTIONS)
            source=discord.PCMVolumeTransformer(source,volume=self.volume.get(guild.id,0.7))
            loop=asyncio.get_running_loop()
            def after(error,guild=guild):
                # Runs on FFmpeg's thread; do all state changes on the event loop.
                asyncio.run_coroutine_threadsafe(self._finished(guild,error),loop)
            voice.play(source,after=after)
            return
        self.current.pop(guild.id,None)
        self.current_entry.pop(guild.id,None)

    async def _finished(self,guild,error):
        if error:
            log.error("Playback failed: %s",error)
        entry=self.current_entry.get(guild.id)
        skipped=guild.id in self.skipped
        self.skipped.discard(guild.id)
        if self.loop.get(guild.id) and entry and not skipped and not error:
            self.queue(guild.id).insert(0,entry)
        await self.play_next(guild)

    def reset(self,guild_id):
        self.queue(guild_id).clear()
        self.loop[guild_id]=False
        self.current.pop(guild_id,None)
        self.current_entry.pop(guild_id,None)
        self.skipped.discard(guild_id)
