import asyncio
from io import BytesIO

from .service import create_picture


def _encode_png(image, scale):
    if scale != 1:
        image = image.resize((
            round(image.width * scale),
            round(image.height * scale),
        ))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


async def create_png(deck_code, scale=1):
    image = await create_picture(deck_code)
    if image is None:
        return None
    return await asyncio.to_thread(_encode_png, image, scale)
