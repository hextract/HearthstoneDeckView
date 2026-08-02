import unittest
from unittest.mock import AsyncMock

from deckview.service import retrieve_deck


class ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_restores_cards_missing_from_deck_response(self):
        client = AsyncMock()
        client.get_deck.return_value = {
            "cardCount": 15,
            "cards": [],
            "class": {"id": 2},
            "invalidCardIds": [123],
        }
        client.get_card.return_value = {
            "id": 123,
            "slug": "duels-card",
            "classId": 6,
            "manaCost": 1,
            "rarityId": 1,
        }

        response, class_id, sideboard = await retrieve_deck("code", client)

        self.assertEqual(class_id, 2)
        self.assertEqual(len(response["cards"]), 1)
        self.assertEqual(sideboard, [])
