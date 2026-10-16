"""Global interest-free virtual Points credit and loan service.

Loans are interest-free but not free money: borrowers must have an established
Discord account and some earning history, overdue loans are collected from the
borrower's wallet then savings, and borrowing is blocked while any loan is
overdue. Borrowed Points cannot be transferred away (see Ledger.transfer).
"""
from datetime import datetime, timedelta, timezone

MAX_CREDIT = 5000
LOAN_TERM_DAYS = 14
MIN_ACCOUNT_AGE_DAYS = 30
MIN_DAILY_CLAIMS = 3

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

async def borrow(storage,user_id,amount,*,account_age_days):
    if not 1<=amount<=MAX_CREDIT:
        raise ValueError(f"Loan amount must be between 1 and {MAX_CREDIT:,} Points.")
    if account_age_days<MIN_ACCOUNT_AGE_DAYS:
        raise ValueError(f"Your Discord account must be at least {MIN_ACCOUNT_AGE_DAYS} days old to borrow.")
    now=datetime.now(timezone.utc)
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            await db.execute("INSERT OR IGNORE INTO economy_accounts(user_id) VALUES(?)",(user_id,))
            async with db.execute("SELECT COUNT(*) AS n FROM economy_transactions WHERE user_id=? AND action='last_daily'",(user_id,)) as cur:
                claims=(await cur.fetchone())["n"]
            if claims<MIN_DAILY_CLAIMS:
                raise ValueError(f"Claim /daily at least {MIN_DAILY_CLAIMS} times before borrowing ({claims} so far).")
            async with db.execute("SELECT 1 FROM point_loans WHERE user_id=? AND status='active' AND due_at<=? LIMIT 1",(user_id,now.isoformat())) as cur:
                if await cur.fetchone():
                    raise ValueError("You have an overdue loan. Repay it before borrowing again.")
            async with db.execute("SELECT COALESCE(SUM(outstanding),0) AS owed FROM point_loans WHERE user_id=? AND status='active'",(user_id,)) as cur:
                owed=(await cur.fetchone())["owed"]
            if owed+amount>MAX_CREDIT:
                raise ValueError(f"Maximum outstanding credit is {MAX_CREDIT:,} Points.")
            await db.execute("UPDATE economy_accounts SET wallet=wallet+? WHERE user_id=?",(amount,user_id))
            await db.execute("INSERT INTO point_loans(user_id,principal,outstanding,issued_at,due_at) VALUES(?,?,?,?,?)",(user_id,amount,amount,now.isoformat(),(now+timedelta(days=LOAN_TERM_DAYS)).isoformat()))
            await db.commit()
        except Exception:
            await db.rollback()
            raise

async def collect_overdue(storage,now=None):
    """Collect overdue loans from wallet, then savings. Returns Points collected."""
    now=now or datetime.now(timezone.utc)
    collected=0
    async with storage.lock:
        db=storage.db
        await db.execute("BEGIN IMMEDIATE")
        try:
            async with db.execute("SELECT id,user_id,outstanding FROM point_loans WHERE status='active' AND due_at<=? ORDER BY due_at,id",(now.isoformat(),)) as cur:
                loans=await cur.fetchall()
            for loan in loans:
                async with db.execute("SELECT wallet,savings FROM economy_accounts WHERE user_id=?",(loan["user_id"],)) as cur:
                    account=await cur.fetchone()
                if account is None:
                    continue
                from_wallet=min(account["wallet"],loan["outstanding"])
                from_savings=min(account["savings"],loan["outstanding"]-from_wallet)
                paid=from_wallet+from_savings
                if not paid:
                    continue
                await db.execute("UPDATE economy_accounts SET wallet=wallet-?,savings=savings-? WHERE user_id=?",(from_wallet,from_savings,loan["user_id"]))
                await db.execute("UPDATE point_loans SET outstanding=outstanding-?,status=CASE WHEN outstanding-?=0 THEN 'repaid' ELSE 'active' END WHERE id=?",(paid,paid,loan["id"]))
                collected+=paid
            await db.commit()
        except Exception:
            await db.rollback()
            raise
    return collected

async def repay(storage,user_id,amount):
    if not 1<=amount<=MAX_CREDIT:
        raise ValueError(f"Repayment must be between 1 and {MAX_CREDIT:,} Points.")
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
