"""Reminder delivery retries and per-user submission limits."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core.database import Database
from modules.utility.services.schema import initialize
from modules.utility.services.reminder_delivery import MAX_ATTEMPTS, PermanentDeliveryError, deliver_due
from shared.helpers.rate_limit import enforce_hourly_limit

class ReminderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "u.db"))
        await self.storage.open()
        await initialize(self.storage)
        self.now = datetime.now(timezone.utc)
        await self.storage.execute("INSERT INTO reminders(user_id,due_at,message) VALUES(?,?,?)",
                                   (5, (self.now - timedelta(minutes=1)).isoformat(), "stand up"))

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def row(self):
        return (await self.storage.rows("SELECT sent,attempts,due_at FROM reminders"))[0]

    async def test_success_marks_delivered_once(self):
        sent = []
        async def ok(user_id, message): sent.append((user_id, message))
        self.assertEqual(await deliver_due(self.storage, ok, now=self.now), 1)
        self.assertEqual(await deliver_due(self.storage, ok, now=self.now), 0)
        self.assertEqual(sent, [(5, "stand up")])
        self.assertEqual((await self.row())["sent"], 1)

    async def test_transient_failure_is_not_lost_and_retries(self):
        calls = {"n": 0}
        async def flaky(user_id, message):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("503")
        await deliver_due(self.storage, flaky, now=self.now)
        row = await self.row()
        self.assertEqual((row["sent"], row["attempts"]), (0, 1))
        self.assertEqual(await deliver_due(self.storage, flaky, now=self.now), 0)   # not due yet
        later = datetime.fromisoformat(row["due_at"]) + timedelta(seconds=1)
        self.assertEqual(await deliver_due(self.storage, flaky, now=later), 1)
        self.assertEqual((await self.row())["sent"], 1)

    async def test_gives_up_after_max_attempts(self):
        async def broken(user_id, message): raise RuntimeError("down")
        now = self.now
        for _ in range(MAX_ATTEMPTS):
            await deliver_due(self.storage, broken, now=now)
            now = datetime.fromisoformat((await self.row())["due_at"]) + timedelta(seconds=1)
        row = await self.row()
        self.assertEqual((row["sent"], row["attempts"]), (2, MAX_ATTEMPTS))

    async def test_permanent_failure_gives_up_immediately(self):
        async def closed(user_id, message): raise PermanentDeliveryError()
        await deliver_due(self.storage, closed, now=self.now)
        self.assertEqual((await self.row())["sent"], 2)

    async def test_migration_adds_attempts_to_legacy_table(self):
        legacy = Database(str(Path(self.temp.name) / "legacy.db"))
        await legacy.open()
        await legacy.db.executescript("CREATE TABLE reminders(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, channel_id INTEGER, due_at TEXT NOT NULL, message TEXT NOT NULL, sent INTEGER NOT NULL DEFAULT 0);")
        await legacy.db.commit()
        await initialize(legacy)
        await initialize(legacy)   # idempotent
        columns = {r["name"] for r in await legacy.rows("PRAGMA table_info(reminders)")}
        self.assertIn("attempts", columns)
        await legacy.close()

class RateLimitTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "r.db"))
        await self.storage.open()
        await initialize(self.storage)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def add_report(self, guild, user, minutes_ago=0):
        stamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).strftime("%Y-%m-%d %H:%M:%S")
        await self.storage.execute("INSERT INTO reports(guild_id,user_id,description,created_at) VALUES(?,?,?,?)", (guild, user, "x", stamp))

    async def test_blocks_fourth_in_an_hour_but_not_other_scopes(self):
        for _ in range(3):
            await self.add_report(1, 5)
        with self.assertRaises(ValueError):
            await enforce_hourly_limit(self.storage, "reports", 1, 5, limit=3, label="reports")
        await enforce_hourly_limit(self.storage, "reports", 2, 5)      # other guild
        await enforce_hourly_limit(self.storage, "reports", 1, 6)      # other user

    async def test_old_submissions_age_out(self):
        for _ in range(3):
            await self.add_report(1, 5, minutes_ago=120)
        await enforce_hourly_limit(self.storage, "reports", 1, 5)

    async def test_table_name_is_allow_listed(self):
        with self.assertRaises(ValueError):
            await enforce_hourly_limit(self.storage, "sqlite_master; DROP TABLE reports", 1, 5)

if __name__ == "__main__":
    unittest.main()
