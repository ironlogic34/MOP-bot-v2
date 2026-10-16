"""Warning counting, expiry and escalation policy. No Discord imports, so it is unit-testable.

Escalation never exceeds the permissions of the moderator who issued the
crossing warning: banning requires the server to opt in AND the issuing
moderator to hold Ban Members. Otherwise the escalation is a 24-hour timeout,
which is within Timeout Members (the permission /warn itself requires).
"""
from datetime import datetime, timedelta, timezone

DEFAULT_THRESHOLD = 3
ESCALATION_TIMEOUT = "timeout"
ESCALATION_BAN = "ban"
ESCALATION_HOURS = 24

def clamp_threshold(value) -> int:
    try:
        return max(1, min(20, int(value)))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD

def clamp_expiry_days(value) -> int:
    """0 means warnings never expire."""
    try:
        return max(0, min(3650, int(value)))
    except (TypeError, ValueError):
        return 0

def choose_escalation(configured, issuer_can_ban: bool) -> str:
    if configured == ESCALATION_BAN and issuer_can_ban:
        return ESCALATION_BAN
    return ESCALATION_TIMEOUT

async def active_warning_count(storage, guild_id, user_id, expiry_days=0, now=None) -> int:
    cutoff = None
    if expiry_days:
        now = now or datetime.now(timezone.utc)
        # warnings.created_at uses SQLite CURRENT_TIMESTAMP: 'YYYY-MM-DD HH:MM:SS' in UTC.
        cutoff = (now - timedelta(days=expiry_days)).strftime("%Y-%m-%d %H:%M:%S")
    rows = await storage.rows(
        "SELECT COUNT(*) AS n FROM warnings WHERE guild_id=? AND user_id=? AND active=1 AND (? IS NULL OR created_at>=?)",
        (guild_id, user_id, cutoff, cutoff))
    return rows[0]["n"]

async def clear_warning(storage, guild_id, warning_id) -> bool:
    """Deactivate one warning in this guild. Returns False if it was not active here."""
    async with storage.lock:
        cur = await storage.db.execute(
            "UPDATE warnings SET active=0 WHERE id=? AND guild_id=? AND active=1", (warning_id, guild_id))
        await storage.db.commit()
        return cur.rowcount == 1

async def clear_user_warnings(storage, guild_id, user_id):
    await storage.execute("UPDATE warnings SET active=0 WHERE guild_id=? AND user_id=?", (guild_id, user_id))
