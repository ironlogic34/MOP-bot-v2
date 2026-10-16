"""Persistent moderation sanction tests without a Discord connection."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.moderation.services.sanctions import initialize, schedule_unban, cancel_unban

class SanctionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "test.sqlite3"))
        await self.storage.open()
        await initialize(self.storage)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def test_replacing_and_cancelling_timed_bans(self):
        await schedule_unban(self.storage, 100, 200, 60, "first")
        await schedule_unban(self.storage, 100, 200, 120, "second")
        rows = await self.storage.rows("SELECT status,reason FROM sanctions WHERE guild_id=? AND user_id=? ORDER BY id",(100,200))
        self.assertEqual([row["status"] for row in rows],["cancelled","pending"])
        self.assertEqual(rows[1]["reason"],"second")
        await cancel_unban(self.storage,100,200)
        rows = await self.storage.rows("SELECT status FROM sanctions WHERE guild_id=? AND user_id=? ORDER BY id",(100,200))
        self.assertEqual([row["status"] for row in rows],["cancelled","cancelled"])

    async def test_invalid_duration(self):
        for duration in (0,-1,525601):
            with self.assertRaises(ValueError):
                await schedule_unban(self.storage,100,200,duration,"invalid")

    async def test_guild_isolation(self):
        await schedule_unban(self.storage,100,200,10,"guild a")
        await schedule_unban(self.storage,101,200,10,"guild b")
        await cancel_unban(self.storage,100,200)
        rows = await self.storage.rows("SELECT guild_id,status FROM sanctions ORDER BY guild_id")
        self.assertEqual([(r["guild_id"],r["status"]) for r in rows],[(100,"cancelled"),(101,"pending")])
