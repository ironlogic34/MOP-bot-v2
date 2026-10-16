"""Resale price-inflation exploit regression."""
import tempfile
import unittest
from pathlib import Path
from core.database import Database
from modules.economy.services.ledger import Ledger

class ResaleCostBasisTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Database(str(Path(self.tmp.name)/"test.db"))
        await self.db.open()
        self.ledger=Ledger(self.db)
        await self.ledger.initialize()
        await self.ledger.account(101)
        await self.db.execute("UPDATE economy_accounts SET wallet=100 WHERE user_id=101")
        self.item=await self.db.execute("INSERT INTO market_items(guild_id,owner_id,name,normalized_name,description,price,stock) VALUES(1,10,'A','a','item',1,10)")

    async def asyncTearDown(self):
        await self.db.close()
        self.tmp.cleanup()

    async def test_price_inflation_exploit_and_inactive_resale(self):
        self.assertEqual(await self.ledger.buy(101,self.item,1),1)
        await self.db.execute("UPDATE market_items SET price=100000000,active=0 WHERE id=?",(self.item,))
        self.assertEqual(await self.ledger.sell(101,self.item,1),0)
        self.assertEqual((await self.ledger.account(101))["wallet"],99)

    async def test_weighted_basis_and_partial_sales(self):
        await self.ledger.buy(101,self.item,2)
        await self.db.execute("UPDATE market_items SET price=8 WHERE id=?",(self.item,))
        await self.ledger.buy(101,self.item,2)
        rows=await self.db.rows("SELECT quantity,cost_total FROM inventory WHERE user_id=101 AND item_id=?",(self.item,))
        self.assertEqual((rows[0]["quantity"],rows[0]["cost_total"]),(4,18))
        self.assertEqual(await self.ledger.sell(101,self.item,2),6)
        rows=await self.db.rows("SELECT quantity,cost_total FROM inventory WHERE user_id=101 AND item_id=?",(self.item,))
        self.assertEqual((rows[0]["quantity"],rows[0]["cost_total"]),(2,9))
