"""Marketplace buy/sell regression tests, including the reprice-then-sell exploit."""
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.economy.services.ledger import Ledger
from modules.economy.services.credit import adjust

OWNER, BUYER = 1001, 1002

class LedgerMarketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.storage = Database(str(Path(self.temp.name) / "mop.db"))
        await self.storage.open()
        self.ledger = Ledger(self.storage)
        await self.ledger.initialize()
        await self.storage.execute(
            "INSERT INTO market_items(guild_id,owner_id,name,normalized_name,description,price,stock) VALUES(1,?,?,?,?,?,?)",
            (OWNER, "Sword", "sword", "a sword", 100, 50))
        await adjust(self.storage, 9, OWNER, 1000, "test grant")
        await adjust(self.storage, 9, BUYER, 1000, "test grant")

    async def asyncTearDown(self):
        await self.storage.close()
        self.temp.cleanup()

    async def wallet(self, user):
        return (await self.ledger.account(user))["wallet"]

    async def test_repricing_cannot_mint_points(self):
        await self.ledger.buy(OWNER, 1, 1)
        self.assertEqual(await self.wallet(OWNER), 900)
        await self.storage.execute("UPDATE market_items SET price=100000000 WHERE id=1")
        payout = await self.ledger.sell(OWNER, 1, 1)
        self.assertEqual(payout, 75)
        self.assertEqual(await self.wallet(OWNER), 975)

    async def test_deactivation_does_not_trap_holders(self):
        await self.ledger.buy(BUYER, 1, 2)
        await self.storage.execute("UPDATE market_items SET active=0 WHERE id=1")
        self.assertEqual(await self.ledger.sell(BUYER, 1, 2), 150)

    async def test_price_drop_does_not_cut_payout(self):
        await self.ledger.buy(BUYER, 1, 1)
        await self.storage.execute("UPDATE market_items SET price=1 WHERE id=1")
        self.assertEqual(await self.ledger.sell(BUYER, 1, 1), 75)

    async def test_partial_sales_track_average_cost(self):
        await self.ledger.buy(BUYER, 1, 1)
        await self.storage.execute("UPDATE market_items SET price=300 WHERE id=1")
        await self.ledger.buy(BUYER, 1, 1)
        total = (await self.storage.rows("SELECT cost_total,quantity FROM inventory WHERE user_id=?", (BUYER,)))[0]
        self.assertEqual((total["cost_total"], total["quantity"]), (400, 2))
        first = await self.ledger.sell(BUYER, 1, 1)
        second = await self.ledger.sell(BUYER, 1, 1)
        self.assertEqual(first + second, 300)
        left = (await self.storage.rows("SELECT cost_total,quantity FROM inventory WHERE user_id=?", (BUYER,)))[0]
        self.assertEqual((left["cost_total"], left["quantity"]), (0, 0))

    async def test_cannot_sell_more_than_held_or_unowned(self):
        with self.assertRaises(ValueError):
            await self.ledger.sell(BUYER, 1, 1)
        await self.ledger.buy(BUYER, 1, 1)
        with self.assertRaises(ValueError):
            await self.ledger.sell(BUYER, 1, 2)

    async def test_buy_checks_stock_and_balance(self):
        with self.assertRaises(ValueError):
            await self.ledger.buy(BUYER, 1, 51)
        await self.storage.execute("UPDATE market_items SET price=5000 WHERE id=1")
        with self.assertRaises(ValueError):
            await self.ledger.buy(BUYER, 1, 1)

class LegacyMigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_backfill_is_capped_by_recorded_spend(self):
        temp = tempfile.TemporaryDirectory()
        try:
            storage = Database(str(Path(temp.name) / "legacy.db"))
            await storage.open()
            # Legacy shape: inventory without cost_total, listing already repriced.
            await storage.db.executescript("""
                CREATE TABLE market_items(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, name TEXT NOT NULL, normalized_name TEXT NOT NULL UNIQUE, description TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>0), stock INTEGER NOT NULL CHECK(stock>=0), active INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE inventory(user_id INTEGER NOT NULL, item_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>=0), PRIMARY KEY(user_id,item_id));
                CREATE TABLE economy_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, action TEXT NOT NULL, amount INTEGER NOT NULL, item_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
                INSERT INTO market_items(guild_id,owner_id,name,normalized_name,description,price,stock) VALUES(1,5,'Gem','gem','x',99999999,10);
                INSERT INTO inventory(user_id,item_id,quantity) VALUES(5,1,2);
                INSERT INTO economy_transactions(user_id,action,amount,item_id) VALUES(5,'buy',-20,1);
            """)
            await storage.db.commit()
            await Ledger(storage).initialize()
            row = (await storage.rows("SELECT cost_total FROM inventory WHERE user_id=5"))[0]
            self.assertEqual(row["cost_total"], 20)
            await storage.close()
        finally:
            temp.cleanup()

if __name__ == "__main__":
    unittest.main()
