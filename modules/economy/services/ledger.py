"""Atomic global virtual-points ledger. No real-world currency."""
import asyncio
from datetime import datetime, timezone
from core.database import Database

SCHEMA = """
CREATE TABLE IF NOT EXISTS economy_accounts(user_id INTEGER PRIMARY KEY, wallet INTEGER NOT NULL DEFAULT 0 CHECK(wallet>=0), savings INTEGER NOT NULL DEFAULT 0 CHECK(savings>=0), last_daily TEXT, last_work TEXT);
CREATE TABLE IF NOT EXISTS economy_transfers(id INTEGER PRIMARY KEY AUTOINCREMENT, sender INTEGER NOT NULL, receiver INTEGER NOT NULL, amount INTEGER NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS market_items(id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, name TEXT NOT NULL, normalized_name TEXT NOT NULL UNIQUE, description TEXT NOT NULL, price INTEGER NOT NULL CHECK(price>0), stock INTEGER NOT NULL CHECK(stock>=0), active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS inventory(user_id INTEGER NOT NULL, item_id INTEGER NOT NULL, quantity INTEGER NOT NULL CHECK(quantity>=0), PRIMARY KEY(user_id,item_id));
CREATE TABLE IF NOT EXISTS economy_transactions(id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, action TEXT NOT NULL, amount INTEGER NOT NULL, item_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
"""

class Ledger:
    def __init__(self, storage: Database):
        self.storage = storage

    async def initialize(self):
        async with self.storage.lock:
            await self.storage.db.executescript(SCHEMA)
            async with self.storage.db.execute("PRAGMA table_info(inventory)") as cursor:
            columns = {row["name"] for row in await cursor.fetchall()}
        if "cost_total" not in columns:
            await self.storage.db.execute("ALTER TABLE inventory ADD COLUMN cost_total INTEGER NOT NULL DEFAULT 0 CHECK(cost_total>=0)")
            await self.storage.db.execute("""UPDATE inventory SET cost_total=quantity*
                COALESCE((SELECT price FROM market_items WHERE market_items.id=inventory.item_id),0)""")
        await self.storage.db.commit()

    async def account(self, user_id):
        await self.storage.execute("INSERT OR IGNORE INTO economy_accounts(user_id) VALUES(?)",(user_id,))
        rows=await self.storage.rows("SELECT * FROM economy_accounts WHERE user_id=?",(user_id,))
        return rows[0]

    async def move(self, user_id, source, target, amount):
        if source not in ("wallet","savings") or target not in ("wallet","savings") or source==target or amount<=0:
            raise ValueError("Invalid account transfer.")
        await self.account(user_id)
        async with self.storage.lock:
            db=self.storage.db
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur=await db.execute(f"UPDATE economy_accounts SET {source}={source}-?,{target}={target}+? WHERE user_id=? AND {source}>=?",(amount,amount,user_id,amount))
                if cur.rowcount!=1:
                    raise ValueError("Insufficient balance.")
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def transfer(self, sender, receiver, amount):
        if sender==receiver or amount<=0:
            raise ValueError("Invalid transfer.")
        await self.account(sender)
        await self.account(receiver)
        async with self.storage.lock:
            db=self.storage.db
            await db.execute("BEGIN IMMEDIATE")
            try:
                cur=await db.execute("UPDATE economy_accounts SET wallet=wallet-? WHERE user_id=? AND wallet>=?",(amount,sender,amount))
                if cur.rowcount!=1:
                    raise ValueError("Insufficient points.")
                await db.execute("UPDATE economy_accounts SET wallet=wallet+? WHERE user_id=?",(amount,receiver))
                await db.execute("INSERT INTO economy_transfers(sender,receiver,amount) VALUES(?,?,?)",(sender,receiver,amount))
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def reward(self, user_id, column, amount, cooldown_seconds):
        if column not in ("last_daily","last_work"):
            raise ValueError("Invalid reward.")
        await self.account(user_id)
        now=datetime.now(timezone.utc)
        async with self.storage.lock:
            db=self.storage.db
            await db.execute("BEGIN IMMEDIATE")
            try:
                async with db.execute(f"SELECT {column} FROM economy_accounts WHERE user_id=?",(user_id,)) as cur:
                    row=await cur.fetchone()
                if row[0] and (now-datetime.fromisoformat(row[0])).total_seconds()<cooldown_seconds:
                    raise ValueError("Reward is still on cooldown.")
                await db.execute(f"UPDATE economy_accounts SET wallet=wallet+?,{column}=? WHERE user_id=?",(amount,now.isoformat(),user_id))
                await db.execute("INSERT INTO economy_transactions(user_id,action,amount) VALUES(?,?,?)",(user_id,column,amount))
                await db.commit()
            except Exception:
                await db.rollback()
                raise

    async def buy(self,user_id,item_id,quantity):
        if quantity<=0 or quantity>100:
            raise ValueError("Quantity must be 1 to 100.")
        await self.account(user_id)
        async with self.storage.lock:
            db=self.storage.db
            await db.execute("BEGIN IMMEDIATE")
            try:
                async with db.execute("SELECT price,stock,active FROM market_items WHERE id=?",(item_id,)) as cur:
                    item=await cur.fetchone()
                if not item or not item["active"] or item["stock"]<quantity:
                    raise ValueError("Item unavailable or insufficient stock.")
                cost=item["price"]*quantity
                cur=await db.execute("UPDATE economy_accounts SET wallet=wallet-? WHERE user_id=? AND wallet>=?",(cost,user_id,cost))
                if cur.rowcount!=1:
                    raise ValueError("Insufficient points.")
                await db.execute("UPDATE market_items SET stock=stock-? WHERE id=?",(quantity,item_id))
                await db.execute("INSERT INTO inventory(user_id,item_id,quantity,cost_total) VALUES(?,?,?,?) ON CONFLICT(user_id,item_id) DO UPDATE SET quantity=quantity+excluded.quantity,cost_total=cost_total+excluded.cost_total",(user_id,item_id,quantity,cost))
                await db.execute("INSERT INTO economy_transactions(user_id,action,amount,item_id) VALUES(?,?,?,?)",(user_id,"buy",-cost,item_id))
                await db.commit()
                return cost
            except Exception:
                await db.rollback()
                raise

    async def sell(self,user_id,item_id,quantity):
        if quantity<=0 or quantity>100:
            raise ValueError("Quantity must be 1 to 100.")
        await self.account(user_id)
        async with self.storage.lock:
            db=self.storage.db
            await db.execute("BEGIN IMMEDIATE")
            try:
                async with db.execute("SELECT id FROM market_items WHERE id=?",(item_id,)) as cur:
                    item=await cur.fetchone()
                if not item:
                    raise ValueError("Item does not exist.")
                async with db.execute("SELECT quantity,cost_total FROM inventory WHERE user_id=? AND item_id=?",(user_id,item_id)) as cur:
                    holding=await cur.fetchone()
                if not holding or holding["quantity"]<quantity:
                    raise ValueError("Insufficient inventory.")
                basis=holding["cost_total"]*quantity//holding["quantity"]
                cur=await db.execute("UPDATE inventory SET quantity=quantity-?,cost_total=cost_total-? WHERE user_id=? AND item_id=? AND quantity>=?",(quantity,basis,user_id,item_id,quantity))
                if cur.rowcount!=1:
                    raise ValueError("Insufficient inventory.")
                payout=basis*75//100
                await db.execute("UPDATE economy_accounts SET wallet=wallet+? WHERE user_id=?",(payout,user_id))
                await db.execute("UPDATE market_items SET stock=stock+? WHERE id=?",(quantity,item_id))
                await db.execute("INSERT INTO economy_transactions(user_id,action,amount,item_id) VALUES(?,?,?,?)",(user_id,"sell",payout,item_id))
                await db.commit()
                return payout
            except Exception:
                await db.rollback()
                raise
