"""Regression coverage for global virtual credit and sanitized error storage."""
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.economy.services.ledger import Ledger
from modules.economy.services.credit import initialize, borrow, repay, adjust, reset
from modules.error_handling.repositories.error_records import initialize as initialize_errors, record

class CreditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.storage=Database(str(Path(self.temp.name)/"mop.db"))
        await self.storage.open()
        self.ledger=Ledger(self.storage)
        await self.ledger.initialize()
        await initialize(self.storage)
        await initialize_errors(self.storage)

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def test_borrow_repay_and_limits(self):
        await borrow(self.storage,123,1000)
        self.assertEqual((await self.ledger.account(123))["wallet"],1000)
        await repay(self.storage,123,250)
        self.assertEqual((await self.ledger.account(123))["wallet"],750)
        rows=await self.storage.rows("SELECT outstanding FROM point_loans WHERE user_id=?",(123,))
        self.assertEqual(rows[0]["outstanding"],750)
        with self.assertRaises(ValueError):
            await borrow(self.storage,123,5000)
        with self.assertRaises(ValueError):
            await repay(self.storage,123,1000)

    async def test_adjust_and_reset_audit(self):
        await adjust(self.storage,999,123,400,"manual grant")
        self.assertEqual((await self.ledger.account(123))["wallet"],400)
        self.assertEqual(await reset(self.storage,999,123,"reset"),400)
        self.assertEqual((await self.ledger.account(123))["wallet"],0)
        rows=await self.storage.rows("SELECT COUNT(*) AS n FROM point_adjustments WHERE user_id=?",(123,))
        self.assertEqual(rows[0]["n"],2)

    async def test_error_record(self):
        await record(self.storage,1,"ping",ValueError("invalid"))
        rows=await self.storage.rows("SELECT guild_id,error_type,summary FROM error_records")
        self.assertEqual((rows[0]["guild_id"],rows[0]["error_type"]),(1,"ValueError"))
        self.assertEqual(rows[0]["summary"],"invalid")
