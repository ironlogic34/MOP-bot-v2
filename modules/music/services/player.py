"""One audio session per guild, for authorized direct audio URLs only."""
import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit
import discord

class Player:
    def __init__(self):
        self.queues={}
        self.volume={}
        self.loop={}
        self.current={}

    @staticmethod
    async def validate_url(url):
        parsed=urlsplit(url)
        if parsed.scheme!="https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Use a public HTTPS direct audio URL.")
        host=parsed.hostname
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
        return self.queues.setdefault(guild_id,[])

    async def play_next(self,guild):
        voice=guild.voice_client
        if not voice or not voice.is_connected():
            return
        queue=self.queue(guild.id)
        if not queue:
            self.current.pop(guild.id,None)
            return
        url=queue.pop(0)
        self.current[guild.id]=url
        source=discord.FFmpegPCMAudio(url,options="-vn",before_options="-nostdin -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")
        source=discord.PCMVolumeTransformer(source,volume=self.volume.get(guild.id,0.7))
        def after(error):
            if error:
                import logging
                logging.getLogger("mop.music").error("Playback failed: %s",error)
            if self.loop.get(guild.id) and self.current.get(guild.id):
                self.queue(guild.id).insert(0,self.current[guild.id])
            asyncio.run_coroutine_threadsafe(self.play_next(guild),guild._state.loop)
        voice.play(source,after=after)
