"""Safe, bounded text input validation."""
import re
import unicodedata

def bounded_text(value: str, *, min_length: int = 1, max_length: int = 500, label: str = "Text") -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = unicodedata.normalize("NFKC", value).strip()
    if not min_length <= len(value) <= max_length:
        raise ValueError(f"{label} must contain {min_length}–{max_length} characters.")
    if any(unicodedata.category(char) in ("Cc", "Cs") for char in value):
        raise ValueError(f"{label} contains unsupported control characters.")
    return value

def normalized_product_name(value: str) -> str:
    """Global product-name uniqueness key; collapse whitespace and casefold."""
    value = bounded_text(value, min_length=2, max_length=70, label="Product name")
    return " ".join(value.casefold().split())

def parse_discord_id(value: str) -> int:
    value = value.strip()
    if not re.fullmatch(r"[0-9]{15,22}", value):
        raise ValueError("Enter a valid Discord snowflake ID.")
    return int(value)

def positive_amount(value: int, *, maximum: int = 100_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"Amount must be between 1 and {maximum:,}.")
    return value
