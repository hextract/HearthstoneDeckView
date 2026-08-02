import tempfile
import unittest
from pathlib import Path

from deckview.config import DEFAULT_CACHE_DIR


class ConfigTests(unittest.TestCase):
    def test_default_cache_is_platform_neutral(self):
        self.assertEqual(DEFAULT_CACHE_DIR, Path(tempfile.gettempdir()) / "deckview")


if __name__ == "__main__":
    unittest.main()
