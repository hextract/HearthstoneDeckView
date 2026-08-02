import os

import certifi

os.environ.setdefault("SSL_CERT_FILE", certifi.where())

from .service import create_picture

__all__ = ["create_picture"]
