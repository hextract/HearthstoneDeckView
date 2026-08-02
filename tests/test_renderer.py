import tempfile
import unittest
from pathlib import Path

from PIL import Image

from deckview.renderer import render_deck


class RendererTests(unittest.TestCase):
    def test_renders_deck_from_cached_cards(self):
        cards = [
            {
                "slug": "101966-gold-panner",
                "manaCost": 2,
                "rarityId": 1,
            },
            {
                "slug": "101966-gold-panner",
                "manaCost": 2,
                "rarityId": 1,
            },
            {
                "slug": "78320-plague-strike",
                "manaCost": 2,
                "rarityId": 2,
            },
        ]
        response = {"cards": cards}

        with tempfile.TemporaryDirectory() as directory:
            cards_dir = Path(directory)
            for slug in {card["slug"] for card in cards}:
                Image.new("RGBA", (200, 300), (20, 30, 40, 255)).save(
                    cards_dir / f"{slug}.png"
                )
            image = render_deck(
                response,
                class_id=1,
                sideboard=[],
                cards_dir=cards_dir,
            )

        self.assertEqual(image.mode, "RGBA")
        self.assertEqual(image.size, (3000, 2344))

if __name__ == "__main__":
    unittest.main()
