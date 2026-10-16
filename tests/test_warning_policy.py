"""Warning expiry, clearing and escalation-scope tests (no Discord connection)."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from core.database import Database
from modules.moderation.services.warning_policy import (
    ESCALATION_BAN, ESCALATION_TIMEOUT, active_warning_count, choose_escalation,
    clamp_expiry_days, clamp_threshold, clear_user_warnings, clear_warning)

class EscalationScopeTests(unittest.TestCase):
    def test_ban_requires_opt_in_and_issuer_permission(self):
        self.assertEqual(choose_escalation(ESCALATION_BAN, True), ESCALATION_BAN)
        # A mod with only Timeout Members must never trigger a ban.
        self.assertEqual(choose_escalation(ESCALATION_BAN, False), ESCALATION_TIMEOUT)
        self.assertEqual(choose_escalation(ESCALATION_TIMEOUT, True), ESCALATION_TIMEOUT)
        self.assertEqual(choose_escalation(None, True), ESCALATION_TIMEOUT)
        self.assertEqual(choose_escalation("anything-else", True), ESCALATION_TIMEOUT)

    def test_clamps(self):
        self.assertEqual((clamp_threshold(0), clamp_threshold(99), clamp_threshold("x")), (1, 20, 3))
        self.assertEqual((clamp_expiry_days(-5), clamp_expiry_days(99999), clamp_expiry_days(None)), (0, 3650, 0))

class WarningStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "w.db"))
        await self.storage.open()

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def add(self, guild, user, days_ago=0):
        stamp = (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S")
        await self.storage.execute("INSERT INTO warnings(guild_id,user_id,moderator_id,reason,created_at) VALUES(?,?,?,?,?)", (guild, user, 1, "r", stamp))

    async def test_expiry_excludes_old_warnings(self):
        await self.add(1, 5, 100)
        await self.add(1, 5, 10)
        await self.add(1, 5, 0)
        self.assertEqual(await active_warning_count(self.storage, 1, 5, 0), 3)
        self.assertEqual(await active_warning_count(self.storage, 1, 5, 30), 2)
        self.assertEqual(await active_warning_count(self.storage, 1, 5, 5), 1)

    async def test_unwarn_is_guild_scoped_and_single_use(self):
        await self.add(1, 5)
        await self.add(2, 5)
        first = (await self.storage.rows("SELECT id FROM warnings WHERE guild_id=1"))[0]["id"]
        self.assertFalse(await clear_warning(self.storage, 2, first))   # wrong guild
        self.assertTrue(await clear_warning(self.storage, 1, first))
        self.assertFalse(await clear_warning(self.storage, 1, first))   # already cleared
        self.assertEqual(await active_warning_count(self.storage, 1, 5), 0)
        self.assertEqual(await active_warning_count(self.storage, 2, 5), 1)

    async def test_escalation_reset_only_touches_that_user_and_guild(self):
        await self.add(1, 5)
        await self.add(1, 6)
        await self.add(2, 5)
        await clear_user_warnings(self.storage, 1, 5)
        self.assertEqual(await active_warning_count(self.storage, 1, 5), 0)
        self.assertEqual(await active_warning_count(self.storage, 1, 6), 1)
        self.assertEqual(await active_warning_count(self.storage, 2, 5), 1)

if __name__ == "__main__":
    unittest.main()
