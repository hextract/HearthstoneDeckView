import asyncio
import threading
import time

import requests


class BlizzardClient:
    _tokens = {}
    _token_lock = threading.Lock()

    def __init__(
        self,
        client_id,
        client_secret,
        locale="en_US",
        base_url="https://us.api.blizzard.com/hearthstone",
    ):
        self.session = requests.Session()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.locale = locale
        self.base_url = base_url

    def _request_access_token(self):
        response = self.session.post(
            "https://oauth.battle.net/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        return data["access_token"], data.get("expires_in", 3600)

    def _get_access_token(self):
        cache_key = (self.client_id, self.client_secret)
        with self._token_lock:
            cached = self._tokens.get(cache_key)
            if cached and cached[1] > time.monotonic():
                return cached[0]

            token, expires_in = self._request_access_token()
            valid_for = max(0, int(expires_in) - 60)
            self._tokens[cache_key] = (token, time.monotonic() + valid_for)
            return token

    async def _authenticate(self):
        if self.access_token is None:
            self.access_token = await asyncio.to_thread(self._get_access_token)
            self.session.headers["Authorization"] = f"Bearer {self.access_token}"

    async def _get(self, path, params):
        await self._authenticate()
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(2):
            try:
                response = await asyncio.to_thread(
                    self.session.get, url, params=params, timeout=20
                )
            except requests.RequestException:
                if attempt == 1:
                    raise
                await asyncio.sleep(0.5)
                continue

            if response.status_code < 500 or attempt == 1:
                return response
            await asyncio.sleep(0.5)

        raise RuntimeError("Blizzard request retry loop ended unexpectedly")

    async def get_deck(self, deck_code):
        response = await self._get(
            "deck", {"locale": self.locale, "code": deck_code}
        )
        return response.json()

    async def get_card(self, card_id):
        response = await self._get(
            f"cards/{card_id}", {"locale": self.locale}
        )
        return response.json()
