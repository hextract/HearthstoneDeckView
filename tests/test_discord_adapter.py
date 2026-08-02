import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from deckview import config


class DiscordAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_acknowledges_before_generating(self):
        config.DISCORD_TOKEN = "test"
        adapter = importlib.import_module("deckview.platforms.discord")
        interaction = SimpleNamespace(
            response=SimpleNamespace(send_message=AsyncMock()),
            edit_original_response=AsyncMock(),
        )

        async def generate(_):
            interaction.response.send_message.assert_awaited_once_with(
                "Generating deck image…"
            )
            return object()

        with patch.object(adapter, "_deck_file", side_effect=generate):
            await adapter._slash_deck(interaction, "deck-code")

        interaction.edit_original_response.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
