"""Per-user, per-server submission limits backed by the table's own created_at column."""

_TABLES = {"tickets", "reports"}   # fixed allow-list: the name is interpolated into SQL

async def enforce_hourly_limit(storage, table, guild_id, user_id, limit=3, label="submissions"):
    if table not in _TABLES:
        raise ValueError("Unsupported rate-limit table.")
    rows = await storage.rows(
        f"SELECT COUNT(*) AS n FROM {table} WHERE guild_id=? AND user_id=? AND created_at>=datetime('now','-60 minutes')",
        (guild_id, user_id))
    if rows[0]["n"] >= limit:
        raise ValueError(f"You can send at most {limit} {label} per hour in this server. Please wait before sending another.")
