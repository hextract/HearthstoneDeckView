from concurrent.futures import ThreadPoolExecutor

import requests

from db.config import FOLDER
from framework.wiki_downloader import download_from_wiki


class GRequestsDownloader:
    def save_photo(self, slug, response, name, save_url):
        with open(f"{FOLDER}{slug}.png", "wb") as photo:
            if response is not None:
                photo.write(response.content)
            else:
                try:
                    response = requests.get(save_url)
                    photo.write(response.content)
                except:
                    download_from_wiki(slug, name)

    def get_and_save_photos(self, responses, cards):
        for response, card in zip(responses, cards):
            self.save_photo(card["slug"], response, card["name"], card["image"])

    def _fetch(self, url):
        try:
            return requests.get(url)
        except:
            return None

    def process_cards(self, cards):
        with ThreadPoolExecutor() as executor:
            responses = list(executor.map(self._fetch, (card["image"] for card in cards)))

        self.get_and_save_photos(responses, cards)
