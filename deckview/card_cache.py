import asyncio
import os
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import certifi
import requests
from PIL import Image

from .config import CARDS_DIR


@lru_cache(maxsize=1)
def _card_ids():
    response = requests.get(
        "https://api.hearthstonejson.com/v1/latest/enUS/cards.json",
        timeout=20,
        verify=certifi.where(),
    )
    response.raise_for_status()
    return {
        card["dbfId"]: card["id"]
        for card in response.json()
    }


class CardImageCache:
    _executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="card-download")
    _path_locks = {}
    _path_locks_guard = threading.Lock()
    _card_ids_lock = threading.Lock()

    def __init__(self, directory=CARDS_DIR, timeout=20):
        self.directory = Path(directory)
        self.timeout = timeout

    def _path_for(self, slug):
        if not slug or Path(slug).name != slug or slug in {".", ".."}:
            raise ValueError(f"Unsafe card slug: {slug!r}")
        return self.directory / f"{slug}.png"

    @staticmethod
    def _is_cached(path, card=None):
        try:
            if not path.is_file() or path.stat().st_size == 0:
                return False
            if card and card.get("cardTypeId") == 3 and card.get("collectible"):
                return path.with_suffix(".hero-render-v1").is_file()
            return True
        except OSError:
            return False

    def _fetch_urls(self, urls, validate=False):
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
                    if validate:
                        with Image.open(BytesIO(response.content)) as image:
                            image.verify()
                    return response.content
                except (requests.RequestException, ValueError, OSError) as error:
                    last_error = error
                    if attempt < 3:
                        time.sleep(0.5 * 2 ** attempt)
        raise RuntimeError("Could not download card image") from last_error

    def _fetch_render(self, card):
        with self._card_ids_lock:
            card_id = _card_ids().get(card.get("id"))
        if not card_id:
            raise ValueError(f"No full card render for {card.get('id')}")
        return self._fetch_urls([
            "https://art.hearthstonejson.com/v1/render/latest/enUS/512x/"
            f"{card_id}.png"
        ], validate=True)

    def _fetch(self, card):
        is_hero = card.get("cardTypeId") == 3 and card.get("collectible")
        if not is_hero:
            urls = list(dict.fromkeys(
                url for url in (card.get("image"), card.get("imageGold")) if url
            ))
            if urls:
                try:
                    return self._fetch_urls(urls)
                except RuntimeError:
                    pass
        try:
            return self._fetch_render(card)
        except (requests.RequestException, ValueError, RuntimeError, OSError) as error:
            raise RuntimeError(f"Could not download card {card['slug']}") from error

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
            if card.get("cardTypeId") == 3 and card.get("collectible"):
                target.with_suffix(".hero-render-v1").touch()
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
            if not self._is_cached(target, card):
                self._publish(card, target)

    def populate(self, cards):
        self.directory.mkdir(parents=True, exist_ok=True)
        unique_cards = {card["slug"]: card for card in cards}
        missing = [
            card
            for card in unique_cards.values()
            if not self._is_cached(self._path_for(card["slug"]), card)
        ]
        futures = [self._executor.submit(self._cache_card, card) for card in missing]
        for future in futures:
            future.result()

    async def populate_async(self, cards):
        await asyncio.to_thread(self.populate, cards)
