"""/leave bookkeeping: restore may only undo an opt-out MOP recorded."""
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.server_management.services.member_rules import initialize, record_opt_out, get_opt_out, delete_opt_out

class OptOutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "r.db"))
        await self.storage.open()
        await initialize(self.storage)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def test_restore_without_recorded_opt_out_finds_nothing(self):
        # A staff-muted member who never opted out has nothing to "restore".
        self.assertEqual(await get_opt_out(self.storage, 1, 2, 3), (False, None))

    async def test_original_value_round_trips(self):
        for original in (None, True, False):
            await record_opt_out(self.storage, 1, 2, 3, original)
            self.assertEqual(await get_opt_out(self.storage, 1, 2, 3), (True, original))
            await delete_opt_out(self.storage, 1, 2, 3)
            self.assertEqual(await get_opt_out(self.storage, 1, 2, 3), (False, None))

    async def test_second_opt_out_cannot_overwrite_the_saved_original(self):
        self.assertTrue(await record_opt_out(self.storage, 1, 2, 3, True))
        self.assertFalse(await record_opt_out(self.storage, 1, 2, 3, False))
        self.assertEqual(await get_opt_out(self.storage, 1, 2, 3), (True, True))

    async def test_scoped_per_guild_channel_and_user(self):
        await record_opt_out(self.storage, 1, 2, 3, None)
        self.assertEqual(await get_opt_out(self.storage, 9, 2, 3), (False, None))
        self.assertEqual(await get_opt_out(self.storage, 1, 9, 3), (False, None))
        self.assertEqual(await get_opt_out(self.storage, 1, 2, 9), (False, None))

if __name__ == "__main__":
    unittest.main()
