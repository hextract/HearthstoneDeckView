import ssl
from contextlib import asynccontextmanager

import certifi
from vkbottle.http import AiohttpClient


class CertifiAiohttpClient(AiohttpClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_context = ssl.create_default_context(cafile=certifi.where())

    @asynccontextmanager
    async def request(self, *args, **kwargs):
        kwargs.setdefault("ssl", self.ssl_context)
        async with super().request(*args, **kwargs) as response:
            yield response
