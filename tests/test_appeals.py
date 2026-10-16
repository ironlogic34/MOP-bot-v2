"""Appeal limits: one pending, 24h gap, three per rolling 30 days, per server."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core.database import Database
from modules.server_management.services.support_records import initialize, create_appeal

class AppealTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "a.db"))
        await self.storage.open()
        await initialize(self.storage)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def age(self, appeal_id, hours):
        stamp = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        await self.storage.execute("UPDATE ban_appeals SET created_at=? WHERE id=?", (stamp, appeal_id))

    async def resolve(self, appeal_id, status="rejected"):
        await self.storage.execute("UPDATE ban_appeals SET status=? WHERE id=?", (status, appeal_id))

    async def test_only_one_pending_at_a_time(self):
        first = await create_appeal(self.storage, 1, 5, "please unban me, i was wrong")
        await self.age(first, 48)
        with self.assertRaisesRegex(ValueError, "pending"):
            await create_appeal(self.storage, 1, 5, "second while first pending")

    async def test_24_hour_gap_after_resolution(self):
        first = await create_appeal(self.storage, 1, 5, "first appeal reason here")
        await self.resolve(first)
        with self.assertRaisesRegex(ValueError, "24 hours"):
            await create_appeal(self.storage, 1, 5, "too soon after the last")
        await self.age(first, 25)
        self.assertIsInstance(await create_appeal(self.storage, 1, 5, "now allowed again"), int)

    async def test_three_per_rolling_window_and_old_appeals_age_out(self):
        ids = []
        for _ in range(3):
            ident = await create_appeal(self.storage, 1, 5, "appeal reason text")
            await self.resolve(ident)
            await self.age(ident, 30)
            ids.append(ident)
        with self.assertRaisesRegex(ValueError, "Maximum"):
            await create_appeal(self.storage, 1, 5, "fourth in the window")
        for ident in ids:
            await self.age(ident, 24 * 31)
        self.assertIsInstance(await create_appeal(self.storage, 1, 5, "old ones aged out"), int)

    async def test_accepted_then_rebanned_user_can_appeal_again_later(self):
        first = await create_appeal(self.storage, 1, 5, "accepted appeal earlier")
        await self.resolve(first, "accepted")
        await self.age(first, 24 * 40)
        self.assertIsInstance(await create_appeal(self.storage, 1, 5, "banned again, appealing"), int)

    async def test_limits_are_per_server_and_per_user(self):
        await create_appeal(self.storage, 1, 5, "server one appeal")
        self.assertIsInstance(await create_appeal(self.storage, 2, 5, "server two appeal"), int)
        self.assertIsInstance(await create_appeal(self.storage, 1, 6, "another user appeal"), int)

if __name__ == "__main__":
    unittest.main()
