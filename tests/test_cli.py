import unittest

from deckview.cli import _normalize_platforms


class CliTests(unittest.TestCase):
    def test_normalizes_aliases_and_duplicates(self):
        self.assertEqual(
            _normalize_platforms(["telegram", "vk", "telegram"]),
            ["tg", "vk"],
        )

    def test_all_selects_every_platform(self):
        self.assertEqual(_normalize_platforms(["all"]), ["vk", "tg", "ds"])

    def test_rejects_unknown_platform(self):
        with self.assertRaises(ValueError):
            _normalize_platforms(["email"])
