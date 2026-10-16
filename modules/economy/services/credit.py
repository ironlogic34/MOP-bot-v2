"""Global interest-free virtual Points credit and loan service."""
from datetime import datetime, timedelta, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS point_loans(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 user_id INTEGER NOT NULL, principal INTEGER NOT NULL CHECK(principal>0),
 outstanding INTEGER NOT NULL CHECK(outstanding>=0),
 issued_at TEXT NOT NULL, due_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','repaid'))
);
CREATE INDEX IF NOT EXISTS idx_point_loans_user ON point_loans(user_id,status);
CREATE TABLE IF NOT EXISTS point_adjustments(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 actor_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
 delta INTEGER NOT NULL,reason TEXT NOT NULL,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

async def initialize(storage):
    async with storage.lock:
        await storage.db.executescript(SCHEMA)
        await storage.db.commit()

async def adjust(storage,actor_id,user_id,delta,reason):
    if not delta or abs(delta)>100000000:
        raise ValueError("Adjustment must be between -100,000,000 and +100,000,000 Points.")
    if not reason.strip():
        raise ValueError("A reason is required.")
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute("INSERT OR IGNORE INTO economy_accounts(user_id) VALUES(?)",(user_id,))
            cur=await db.execute("UPDATE economy_accounts SET wallet=wallet+? WHERE user_id=? AND wallet+?>=0",(delta,user_id,delta))
            if cur.rowcount!=1:
                raise ValueError("Insufficient wallet Points for adjustment.")
            await db.execute("INSERT INTO point_adjustments(actor_id,user_id,delta,reason) VALUES(?,?,?,?)",(actor_id,user_id,delta,reason[:300]))
            await db.commit()
        except Exception:
            await db.rollback()
            raise

async def reset(storage,actor_id,user_id,reason):
    if not reason.strip():
        raise ValueError("A reason is required.")
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute("INSERT OR IGNORE INTO economy_accounts(user_id) VALUES(?)",(user_id,))
            async with db.execute("SELECT wallet,savings FROM economy_accounts WHERE user_id=?",(user_id,)) as cur:
                row=await cur.fetchone()
            delta=-(row["wallet"]+row["savings"])
            await db.execute("UPDATE economy_accounts SET wallet=0,savings=0 WHERE user_id=?",(user_id,))
            await db.execute("INSERT INTO point_adjustments(actor_id,user_id,delta,reason) VALUES(?,?,?,?)",(actor_id,user_id,delta,reason[:300]))
            await db.commit()
            return -delta
        except Exception:
            await db.rollback()
            raise

async def borrow(storage,user_id,amount):
    if not 1<=amount<=5000:
        raise ValueError("Loan amount must be between 1 and 5,000 Points.")
    now=datetime.now(timezone.utc)
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute("INSERT OR IGNORE INTO economy_accounts(user_id) VALUES(?)",(user_id,))
            async with db.execute("SELECT COALESCE(SUM(outstanding),0) AS owed FROM point_loans WHERE user_id=? AND status='active'",(user_id,)) as cur:
                owed=(await cur.fetchone())["owed"]
            if owed+amount>5000:
                raise ValueError("Maximum outstanding credit is 5,000 Points.")
            await db.execute("UPDATE economy_accounts SET wallet=wallet+? WHERE user_id=?",(amount,user_id))
            await db.execute("INSERT INTO point_loans(user_id,principal,outstanding,issued_at,due_at) VALUES(?,?,?,?,?)",(user_id,amount,amount,now.isoformat(),(now+timedelta(days=14)).isoformat()))
            await db.commit()
        except Exception:
            await db.rollback()
            raise

async def repay(storage,user_id,amount):
    if not 1<=amount<=5000:
        raise ValueError("Repayment must be between 1 and 5,000 Points.")
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute("SELECT id,outstanding FROM point_loans WHERE user_id=? AND status='active' ORDER BY id",(user_id,)) as cur:
                loans=await cur.fetchall()
            if sum(r["outstanding"] for r in loans)<amount:
                raise ValueError("Repayment exceeds outstanding debt.")
            cur=await db.execute("UPDATE economy_accounts SET wallet=wallet-? WHERE user_id=? AND wallet>=?",(amount,user_id,amount))
            if cur.rowcount!=1:
                raise ValueError("Insufficient wallet Points.")
            remaining=amount
            for loan in loans:
                if not remaining:
                    break
                paid=min(remaining,loan["outstanding"])
                remaining-=paid
                await db.execute("UPDATE point_loans SET outstanding=outstanding-?,status=CASE WHEN outstanding-?=0 THEN 'repaid' ELSE 'active' END WHERE id=?",(paid,paid,loan["id"]))
            await db.commit()
        except Exception:
            await db.rollback()
            raise
