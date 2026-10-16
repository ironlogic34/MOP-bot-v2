"""Consistent formatting for Discord messages."""
from datetime import datetime, timezone

def compact_number(number: int) -> str:
    return f"{number:,}"

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    values = ((days, "d"), (hours, "h"), (minutes, "m"), (secs, "s"))
    return " ".join(f"{value}{suffix}" for value, suffix in values if value) or "0s"

def truncate(text: str, limit: int = 1900) -> str:
    if limit < 4:
        raise ValueError("Truncation limit must be at least 4.")
    return text if len(text) <= limit else text[:limit - 1] + "…"
