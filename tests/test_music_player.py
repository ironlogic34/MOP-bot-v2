"""Music queue caps, skip/loop semantics and URL gate. FFmpeg and Discord voice are faked."""
import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from modules.music.services import player as player_module
from modules.music.services.player import Player, MAX_QUEUE_PER_GUILD, MAX_QUEUE_PER_USER, FFMPEG_BEFORE_OPTIONS

class QueueCapTests(unittest.TestCase):
    def test_per_user_cap(self):
        p = Player()
        for i in range(MAX_QUEUE_PER_USER):
            p.enqueue(1, f"https://a.example/{i}.mp3", 42)
        with self.assertRaises(ValueError):
            p.enqueue(1, "https://a.example/x.mp3", 42)
        p.enqueue(1, "https://a.example/y.mp3", 43)   # other users unaffected

    def test_per_guild_cap(self):
        p = Player()
        for i in range(MAX_QUEUE_PER_GUILD):
            p.enqueue(1, f"https://a.example/{i}.mp3", 1000 + i)   # distinct users
        with self.assertRaises(ValueError):
            p.enqueue(1, "https://a.example/over.mp3", 5)
        p.enqueue(2, "https://a.example/other-guild.mp3", 5)       # guilds are isolated

    def test_ffmpeg_is_limited_to_https(self):
        self.assertIn("-protocol_whitelist https,tls,tcp", FFMPEG_BEFORE_OPTIONS)

class UrlGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_non_https_credentials_and_unlisted_hosts(self):
        with patch.dict(os.environ, {"MUSIC_ALLOWED_HOSTS": "cdn.example"}):
            for bad in ("http://cdn.example/a.mp3", "file:///etc/passwd", "https://user:pw@cdn.example/a.mp3",
                        "https://evil.example/a.mp3", "https:///a.mp3"):
                with self.assertRaises(ValueError, msg=bad):
                    await Player.validate_url(bad)
        with patch.dict(os.environ, {"MUSIC_ALLOWED_HOSTS": ""}):
            with self.assertRaises(ValueError):
                await Player.validate_url("https://cdn.example/a.mp3")

    async def test_rejects_allowlisted_host_resolving_to_private_address(self):
        fake_loop = MagicMock()
        fake_loop.getaddrinfo = AsyncMock(return_value=[(2, 1, 6, "", ("127.0.0.1", 443))])
        with patch.dict(os.environ, {"MUSIC_ALLOWED_HOSTS": "cdn.example"}), \
             patch.object(asyncio, "get_running_loop", return_value=fake_loop):
            with self.assertRaisesRegex(ValueError, "Private"):
                await Player.validate_url("https://cdn.example/a.mp3")

class PlaybackFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.p = Player()
        self.guild = MagicMock()
        self.guild.id = 1
        self.voice = MagicMock()
        self.voice.is_connected.return_value = True
        self.guild.voice_client = self.voice
        patcher = patch.object(Player, "validate_url", AsyncMock(side_effect=lambda url: url))
        patcher.start()
        self.addCleanup(patcher.stop)
        for name in ("FFmpegPCMAudio", "PCMVolumeTransformer"):
            patcher = patch.object(player_module.discord, name, MagicMock())
            patcher.start()
            self.addCleanup(patcher.stop)

    async def test_loop_requeues_but_skip_does_not(self):
        self.p.enqueue(1, "https://a.example/1.mp3", 7)
        self.p.enqueue(1, "https://a.example/2.mp3", 7)
        self.p.loop[1] = True
        await self.p.play_next(self.guild)
        self.assertEqual(self.p.current[1], "https://a.example/1.mp3")
        await self.p._finished(self.guild, None)                 # natural end while looping
        self.assertEqual(self.p.current[1], "https://a.example/1.mp3")
        self.p.skipped.add(1)
        await self.p._finished(self.guild, None)                 # skip while looping must advance
        self.assertEqual(self.p.current[1], "https://a.example/2.mp3")

    async def test_invalid_queued_track_is_skipped_not_fatal(self):
        async def check(url):
            if "bad" in url:
                raise ValueError("blocked")
            return url
        with patch.object(Player, "validate_url", AsyncMock(side_effect=check)):
            self.p.enqueue(1, "https://a.example/bad.mp3", 7)
            self.p.enqueue(1, "https://a.example/good.mp3", 7)
            await self.p.play_next(self.guild)
        self.assertEqual(self.p.current[1], "https://a.example/good.mp3")

    async def test_queue_drains_and_clears_current(self):
        self.p.enqueue(1, "https://a.example/1.mp3", 7)
        await self.p.play_next(self.guild)
        await self.p._finished(self.guild, None)
        self.assertNotIn(1, self.p.current)

    async def test_reset_clears_everything(self):
        self.p.enqueue(1, "https://a.example/1.mp3", 7)
        self.p.loop[1] = True
        self.p.skipped.add(1)
        self.p.reset(1)
        self.assertEqual((self.p.queue(1), self.p.loop[1], 1 in self.p.skipped), ([], False, False))

if __name__ == "__main__":
    unittest.main()
