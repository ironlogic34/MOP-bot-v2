import unittest
from unittest.mock import AsyncMock, MagicMock
from modules.moderation.services.channel_overwrites import lock_channel,unlock_channel

class OverwriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_lock_and_restore(self):
        storage=MagicMock()
        storage.rows=AsyncMock(side_effect=[[],[{"original_value":1}]])
        storage.execute=AsyncMock()
        channel=MagicMock()
        channel.guild.id=123
        channel.id=456
        channel.set_permissions=AsyncMock()
        role=MagicMock()
        role.id=789
        original=MagicMock()
        original.send_messages=True
        channel.overwrites_for.return_value=original
        self.assertTrue(await lock_channel(storage,channel,role,"mod"))
        self.assertEqual(original.send_messages,False)
        self.assertTrue(await unlock_channel(storage,channel,role,"mod"))
        self.assertEqual(original.send_messages,True)
