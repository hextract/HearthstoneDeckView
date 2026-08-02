import asyncio
import unittest
from unittest.mock import patch

from deckview.blizzard import BlizzardClient


class BlizzardAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        BlizzardClient._tokens.clear()

    async def test_access_token_is_reused_across_requests(self):
        first = BlizzardClient("client", "secret")
        second = BlizzardClient("client", "secret")

        with patch.object(
            BlizzardClient, "_request_access_token", return_value=("token", 3600)
        ) as convert:
            await asyncio.gather(
                first._authenticate(), second._authenticate()
            )

        self.assertEqual(first.session.headers["Authorization"], "Bearer token")
        self.assertEqual(second.session.headers["Authorization"], "Bearer token")
        convert.assert_called_once()


if __name__ == "__main__":
    unittest.main()
