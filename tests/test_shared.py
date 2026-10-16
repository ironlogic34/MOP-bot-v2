"""Shared helper regression tests; no Discord token needed."""
import unittest
from unittest.mock import patch

from shared.helpers.events import EventBus
from shared.helpers.formatting import format_duration, truncate
from shared.security.redaction import redact_secrets
from shared.validators.text import normalized_product_name, positive_amount, parse_discord_id
from shared.ui.pagination import Paginator
from shared.ui.confirmation import Confirmation

class SharedTests(unittest.TestCase):
    def test_product_name_normalization(self):
        self.assertEqual(normalized_product_name("  Blue   Sword  "), "blue sword")
        with self.assertRaises(ValueError):
            normalized_product_name(" ")

    def test_amount(self):
        self.assertEqual(positive_amount(12), 12)
        for value in (0, -1, True, 100_000_001):
            with self.assertRaises(ValueError):
                positive_amount(value)

    def test_id(self):
        self.assertEqual(parse_discord_id("123456789012345678"), 123456789012345678)
        with self.assertRaises(ValueError):
            parse_discord_id("not-a-discord-id")

    def test_formatting(self):
        self.assertEqual(format_duration(3661), "1h 1m 1s")
        self.assertEqual(truncate("abcdef", 4), "abc…")

    def test_redaction(self):
        with patch.dict("os.environ", {"DISCORD_TOKEN": "super-secret-token"}):
            self.assertNotIn("super-secret-token", redact_secrets("Failure: super-secret-token"))
        self.assertNotIn("abcdef", redact_secrets("api_key=abcdef"))

    def test_pagination(self):
        view = Paginator("Test", [str(i) for i in range(15)], owner_id=123, page_size=7)
        self.assertEqual(view.page_count, 3)
        self.assertEqual(view.page, 0)
        self.assertIn("Page 1/3", view.embed().footer.text)

    def test_confirmation(self):
        view = Confirmation(123)
        self.assertIsNone(view.result)

class AsyncEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_emit(self):
        bus = EventBus()
        calls = []
        async def callback(value):
            calls.append(value)
        bus.subscribe("test", callback)
        self.assertEqual(await bus.emit("test", value=42), 1)
        self.assertEqual(calls, [42])

if __name__ == "__main__":
    unittest.main()
