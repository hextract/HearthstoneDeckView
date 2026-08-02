import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import requests

from deckview.card_cache import CardImageCache


class FakeResponse:
    content = b"complete-image"

    @staticmethod
    def raise_for_status():
        return None


class CardCacheTests(unittest.TestCase):
    def test_cached_cards_are_not_downloaded_again(self):
        card = {"slug": "test-card", "name": "Test Card", "image": "https://image"}
        with tempfile.TemporaryDirectory() as directory:
            downloader = CardImageCache(Path(directory))
            with patch(
                "deckview.card_cache.requests.get",
                return_value=FakeResponse(),
            ) as get:
                downloader.populate([card, card])
                downloader.populate([card])

            self.assertEqual((Path(directory) / "test-card.png").read_bytes(), b"complete-image")
            get.assert_called_once()

    def test_overlapping_requests_only_publish_complete_files(self):
        card = {"slug": "shared-card", "name": "Shared Card", "image": "https://image"}
        with tempfile.TemporaryDirectory() as directory:
            downloaders = [CardImageCache(Path(directory)) for _ in range(4)]
            with patch(
                "deckview.card_cache.requests.get",
                return_value=FakeResponse(),
            ) as get:
                with ThreadPoolExecutor(max_workers=4) as executor:
                    list(executor.map(lambda item: item.populate([card]), downloaders))

            folder = Path(directory)
            self.assertEqual((folder / "shared-card.png").read_bytes(), b"complete-image")
            self.assertEqual(list(folder.glob("*.tmp")), [])
            get.assert_called_once()

    def test_slug_cannot_escape_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            downloader = CardImageCache(Path(directory))
            with self.assertRaises(ValueError):
                downloader.populate([{
                    "slug": "../escape", "name": "Bad", "image": "https://image"
                }])

    def test_transient_ssl_error_is_retried(self):
        card = {"slug": "retry-card", "name": "Retry", "image": "https://image"}
        with tempfile.TemporaryDirectory() as directory:
            downloader = CardImageCache(Path(directory))
            with (
                patch(
                    "deckview.card_cache.requests.get",
                    side_effect=[requests.exceptions.SSLError(), FakeResponse()],
                ) as get,
                patch("deckview.card_cache.time.sleep") as sleep,
            ):
                downloader.populate([card])

            self.assertEqual((Path(directory) / "retry-card.png").read_bytes(), b"complete-image")
            self.assertEqual(get.call_count, 2)
            sleep.assert_called_once_with(0.5)


if __name__ == "__main__":
    unittest.main()
