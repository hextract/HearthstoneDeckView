import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from deckview import config


class VKAdapterTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        config.VK_TOKEN = "test"
        cls.adapter = importlib.import_module("deckview.platforms.vk")

    async def test_retries_transient_upload_with_fresh_attempt(self):
        error = self.adapter.VKAPIError[100](error_msg="photo is undefined")
        operation = AsyncMock(side_effect=[error, error, error, "photo1_2"])

        with patch.object(self.adapter.asyncio, "sleep", new=AsyncMock()) as sleep:
            result = await self.adapter._retry_upload(operation)

        self.assertEqual(result, "photo1_2")
        self.assertEqual(operation.await_count, 4)
        self.assertEqual(
            [call.args[0] for call in sleep.await_args_list],
            [0.5, 1.0, 2.0],
        )

    async def test_does_not_retry_permission_error(self):
        error = self.adapter.VKAPIError[10](error_msg="permission denied")
        operation = AsyncMock(side_effect=error)

        with self.assertRaises(self.adapter.VKAPIError[10]):
            await self.adapter._retry_upload(operation)

        operation.assert_awaited_once()

    async def test_photo_falls_back_to_direct_dialog(self):
        error = self.adapter.VKAPIError[10](error_msg="permission denied")
        message = SimpleNamespace(peer_id=2_000_000_001, from_id=123)

        with patch.object(
            self.adapter.photo_uploader,
            "upload",
            new=AsyncMock(side_effect=[error, "photo1_2"]),
        ) as upload:
            result = await self.adapter._upload_photo_once("deck.png", message)

        self.assertEqual(result, "photo1_2")
        self.assertEqual(upload.await_args_list[0].kwargs["peer_id"], message.peer_id)
        self.assertEqual(upload.await_args_list[1].kwargs["peer_id"], message.from_id)


if __name__ == "__main__":
    unittest.main()
