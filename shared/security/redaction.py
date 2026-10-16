"""Redact common credential patterns from diagnostic text."""
import os
import re

KEY_PATTERN = re.compile(r"(?i)(\b(?:authorization|token|api[_-]?key|api[_-]?secret|password|client[_-]?secret)\b\s*[:=]\s*)(?:bearer\s+)?([^\s,;]+)")
DISCORD_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{20,30}\.[A-Za-z0-9_-]{5,10}\.[A-Za-z0-9_-]{20,60}(?![A-Za-z0-9_-])")

def redact_secrets(message: object) -> str:
    text = str(message)
    for name in ("DISCORD_TOKEN", "LASTFM_API_KEY", "LASTFM_API_SECRET"):
        secret = os.getenv(name)
        if secret and len(secret) >= 4:
            text = text.replace(secret, "[REDACTED]")
    text = DISCORD_TOKEN_PATTERN.sub("[REDACTED_TOKEN]", text)
    return KEY_PATTERN.sub(lambda match: match.group(1) + "[REDACTED]", text)
