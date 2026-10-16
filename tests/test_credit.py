"""Regression coverage for global virtual credit and sanitized error storage."""
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.economy.services.ledger import Ledger
from datetime import datetime, timedelta, timezone
from modules.economy.services.credit import initialize, borrow, repay, adjust, reset, collect_overdue
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

    async def eligible(self, user_id, claims=3):
        await self.ledger.account(user_id)
        for _ in range(claims):
            await self.storage.execute("INSERT INTO economy_transactions(user_id,action,amount) VALUES(?,?,?)",(user_id,"last_daily",100))

    async def test_borrow_repay_and_limits(self):
        await self.eligible(123)
        await borrow(self.storage,123,1000,account_age_days=60)
        self.assertEqual((await self.ledger.account(123))["wallet"],1000)
        await repay(self.storage,123,250)
        self.assertEqual((await self.ledger.account(123))["wallet"],750)
        rows=await self.storage.rows("SELECT outstanding FROM point_loans WHERE user_id=?",(123,))
        self.assertEqual(rows[0]["outstanding"],750)
        with self.assertRaises(ValueError):
            await borrow(self.storage,123,5000,account_age_days=60)
        with self.assertRaises(ValueError):
            await repay(self.storage,123,1000)

    async def test_new_accounts_and_non_earners_cannot_borrow(self):
        await self.eligible(1)
        with self.assertRaises(ValueError):
            await borrow(self.storage,1,100,account_age_days=3)
        await self.eligible(2,claims=2)
        with self.assertRaises(ValueError):
            await borrow(self.storage,2,100,account_age_days=400)
        self.assertEqual((await self.ledger.account(1))["wallet"],0)
        self.assertEqual((await self.ledger.account(2))["wallet"],0)

    async def test_borrowed_points_cannot_be_transferred_away(self):
        await self.eligible(10)
        await borrow(self.storage,10,5000,account_age_days=90)
        with self.assertRaises(ValueError):
            await self.ledger.transfer(10,11,1)
        await adjust(self.storage,999,10,200,"earned")
        await self.ledger.transfer(10,11,200)
        with self.assertRaises(ValueError):
            await self.ledger.transfer(10,11,1)
        self.assertEqual((await self.ledger.account(11))["wallet"],200)
        await repay(self.storage,10,5000)
        await adjust(self.storage,999,10,50,"earned")
        await self.ledger.transfer(10,11,50)

    async def test_overdue_loans_are_collected_and_block_borrowing(self):
        await self.eligible(20)
        await borrow(self.storage,20,1000,account_age_days=90)
        await self.ledger.move(20,"wallet","savings",400)
        later=datetime.now(timezone.utc)+timedelta(days=15)
        self.assertEqual(await collect_overdue(self.storage,now=later-timedelta(days=2)),0)
        self.assertEqual(await collect_overdue(self.storage,now=later),1000)
        account=await self.ledger.account(20)
        self.assertEqual((account["wallet"],account["savings"]),(0,0))
        rows=await self.storage.rows("SELECT outstanding,status FROM point_loans WHERE user_id=20")
        self.assertEqual((rows[0]["outstanding"],rows[0]["status"]),(0,"repaid"))

    async def test_partial_collection_keeps_loan_overdue(self):
        await self.eligible(30)
        await borrow(self.storage,30,1000,account_age_days=90)
        await self.storage.execute("UPDATE economy_accounts SET wallet=300 WHERE user_id=30")
        later=datetime.now(timezone.utc)+timedelta(days=15)
        self.assertEqual(await collect_overdue(self.storage,now=later),300)
        await self.storage.execute("UPDATE point_loans SET due_at=? WHERE user_id=30",((datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),))
        with self.assertRaises(ValueError):
            await borrow(self.storage,30,100,account_age_days=90)
        rows=await self.storage.rows("SELECT outstanding,status FROM point_loans WHERE user_id=30")
        self.assertEqual((rows[0]["outstanding"],rows[0]["status"]),(700,"active"))

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
