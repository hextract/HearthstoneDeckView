import asyncio
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import certifi
import requests

from .config import CARDS_DIR


class CardImageCache:
    _executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="card-download")
    _path_locks = {}
    _path_locks_guard = threading.Lock()

    def __init__(self, directory=CARDS_DIR, timeout=20):
        self.directory = Path(directory)
        self.timeout = timeout

    def _path_for(self, slug):
        if not slug or Path(slug).name != slug or slug in {".", ".."}:
            raise ValueError(f"Unsafe card slug: {slug!r}")
        return self.directory / f"{slug}.png"

    @staticmethod
    def _is_cached(path):
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False

    def _fetch(self, card):
        urls = list(dict.fromkeys(
            url for url in (card.get("image"), card.get("imageGold")) if url
        ))
        last_error = None
        for url in urls:
            for attempt in range(4):
                try:
                    response = requests.get(
                        url,
                        timeout=self.timeout,
                        verify=certifi.where(),
                        headers={"User-Agent": "Deckview/0.3"},
                    )
                    response.raise_for_status()
                    if not response.content:
                        raise ValueError("Empty image response")
                    return response.content
                except (requests.RequestException, ValueError) as error:
                    last_error = error
                    if attempt < 3:
                        time.sleep(0.5 * 2 ** attempt)
        raise RuntimeError(f"Could not download card {card['slug']}") from last_error

    def _publish(self, card, target):
        content = self._fetch(card)
        temporary_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=self.directory,
                prefix=f".{card['slug']}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_name = temporary.name
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_name, target)
        finally:
            if temporary_name:
                try:
                    os.unlink(temporary_name)
                except FileNotFoundError:
                    pass

    def _cache_card(self, card):
        target = self._path_for(card["slug"])
        with self._path_locks_guard:
            path_lock = self._path_locks.setdefault(target, threading.Lock())
        with path_lock:
            if not self._is_cached(target):
                self._publish(card, target)

    def populate(self, cards):
        self.directory.mkdir(parents=True, exist_ok=True)
        unique_cards = {card["slug"]: card for card in cards}
        missing = [
            card
            for card in unique_cards.values()
            if not self._is_cached(self._path_for(card["slug"]))
        ]
        futures = [self._executor.submit(self._cache_card, card) for card in missing]
        for future in futures:
            future.result()

    async def populate_async(self, cards):
        await asyncio.to_thread(self.populate, cards)
