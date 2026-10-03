import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import requests
from PIL import Image

from deckview.card_cache import CardImageCache


class FakeResponse:
    content = b"complete-image"

    @staticmethod
    def raise_for_status():
        return None


class CardCacheTests(unittest.TestCase):
    def test_hero_portrait_cache_is_replaced_with_full_card_render(self):
        card = {
            "id": 103471, "slug": "103471-reno-lone-ranger",
            "cardTypeId": 3, "collectible": 1, "image": "https://portrait",
        }
        image = BytesIO()
        Image.new("RGBA", (512, 776)).save(image, format="PNG")
        response = SimpleNamespace(
            content=image.getvalue(), raise_for_status=lambda: None,
        )
        with tempfile.TemporaryDirectory() as directory:
            downloader = CardImageCache(directory)
            target = Path(directory) / f"{card['slug']}.png"
            target.write_bytes(b"old-hero-portrait")
            with (
                patch("deckview.card_cache._card_ids", return_value={103471: "WW_0700"}),
                patch("deckview.card_cache.requests.get", return_value=response) as get,
            ):
                downloader.populate([card])
                downloader.populate([card])

            self.assertEqual(target.read_bytes(), image.getvalue())
            self.assertTrue(target.with_suffix(".hero-render-v1").is_file())
            get.assert_called_once()
            self.assertEqual(
                get.call_args.args[0],
                "https://art.hearthstonejson.com/v1/render/latest/enUS/512x/WW_0700.png",
            )

    def test_missing_images_use_render_and_cache_it(self):
        for image_url in (None, "https://missing-image"):
            with self.subTest(image_url=image_url), tempfile.TemporaryDirectory() as directory:
                card = {"id": 559, "slug": "559-leeroy-jenkins", "image": image_url}
                image = BytesIO()
                Image.new("RGBA", (512, 768)).save(image, format="PNG")
                response = SimpleNamespace(
                    content=image.getvalue(), raise_for_status=lambda: None,
                )
                failures = [requests.HTTPError("404")] * 4 if image_url else []
                with (
                    patch("deckview.card_cache._card_ids", return_value={559: "EX1_116"}) as ids,
                    patch("deckview.card_cache.requests.get", side_effect=failures + [response]) as get,
                    patch("deckview.card_cache.time.sleep"),
                ):
                    cache = CardImageCache(directory)
                    cache.populate([card])
                    cache.populate([card])
                self.assertEqual(get.call_count, len(failures) + 1)
                self.assertEqual(
                    get.call_args.args[0],
                    "https://art.hearthstonejson.com/v1/render/latest/enUS/512x/EX1_116.png",
                )
                ids.assert_called_once()
                self.assertEqual(
                    (Path(directory) / "559-leeroy-jenkins.png").read_bytes(),
                    image.getvalue(),
                )

    def test_successful_blizzard_image_does_not_load_fallback_metadata(self):
        with (
            patch("deckview.card_cache._card_ids") as ids,
            patch("deckview.card_cache.requests.get", return_value=FakeResponse()),
        ):
            self.assertEqual(CardImageCache()._fetch({"image": "https://image"}), b"complete-image")
        ids.assert_not_called()

    def test_failed_fallback_does_not_publish_cache_file(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("deckview.card_cache._card_ids", return_value={}):
                with self.assertRaisesRegex(RuntimeError, "missing-card"):
                    CardImageCache(directory).populate([{"id": 123, "slug": "missing-card"}])
            self.assertEqual(list(Path(directory).iterdir()), [])

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
