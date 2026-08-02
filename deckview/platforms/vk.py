import os
import sys
import tempfile
from time import perf_counter

from loguru import logger
from vkbottle import API, DocMessagesUploader, PhotoMessageUploader, VKAPIError
from vkbottle.bot import Bot, Message

from ..config import BANNED_PEERS, VK_TOKEN
from ..http import CertifiAiohttpClient
from ..output import create_png
from ..text import extract_deck_codes

if not VK_TOKEN:
    raise RuntimeError("VK_TOKEN is not configured")

bot = Bot(api=API(VK_TOKEN, http_client=CertifiAiohttpClient()))
photo_uploader = PhotoMessageUploader(bot.api)
file_uploader = DocMessagesUploader(bot.api)

logger.remove()
logger.add(sys.stderr, level="ERROR", backtrace=False, diagnose=False)


def _forwarded_text(message):
    forwarded = " ".join(
        _forwarded_text(item) for item in (message.fwd_messages or [])
    )
    return f"{message.text or ''} {forwarded}"


def _repost_text(message):
    return " ".join(
        attachment.wall.text or ""
        for attachment in (message.attachments or [])
        if attachment.wall
    )


def _temporary_png(content):
    temporary = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    try:
        temporary.write(content)
        return temporary.name
    except Exception:
        try:
            os.unlink(temporary.name)
        except FileNotFoundError:
            pass
        raise
    finally:
        temporary.close()


@bot.on.message(text="Начать")
async def start_handler(message: Message):
    if message.peer_id < 2_000_000_000:
        return (
            "Привет. Отправь мне код колоды, чтобы я сгенерировал картинку "
            "для удобного отображения. Я также автоматически нахожу коды "
            "колод в активных беседах. Для этого добавьте меня в беседу и "
            "выдайте админские права через кнопку на главной странице сообщества."
        )


async def _upload_photo(image_path, message):
    try:
        return await photo_uploader.upload(
            file_source=image_path,
            peer_id=message.peer_id,
        )
    except VKAPIError[10]:
        return await photo_uploader.upload(
            file_source=image_path,
            peer_id=message.from_id,
        )


async def _handle_deck_code(deck_code, message):
    started = perf_counter()
    try:
        scale = 0.5 if message.peer_id > 2_000_000_000 else 1
        image = await create_png(deck_code, scale=scale)
        if image is None:
            return None
    except Exception:
        logger.exception("Failed to generate deck image")
        return (
            "Возникла ошибка в генерации.\n"
            "Если такое происходит постоянно, обратитесь к автору вместе с кодом."
        )

    image_path = _temporary_png(image)
    try:
        try:
            photo = await _upload_photo(image_path, message)
        except VKAPIError[10]:
            return (
                "Возникла ошибка при отправке кода.\n"
                "Возможно, у вас нет переписки с ботом или проблема на стороне VK."
            )
        except Exception:
            logger.exception("Failed to upload deck image")
            return "Возникла проблема при отправке кода. Возможно, поможет переотправка."

        await message.answer(attachment=str(photo))
        if message.peer_id < 2_000_000_000:
            document = await file_uploader.upload(
                title=f"{deck_code}.png",
                file_source=image_path,
                peer_id=message.peer_id,
            )
            await message.answer(attachment=str(document))
        logger.info("Processed deck in {:.3f}s", perf_counter() - started)
        return None
    finally:
        try:
            os.remove(image_path)
        except FileNotFoundError:
            pass


@bot.on.message()
async def message_handler(message: Message):
    text = f"{_forwarded_text(message)} {_repost_text(message)}"
    for deck_code in extract_deck_codes(text):
        if message.peer_id in BANNED_PEERS:
            return "Группа забанена в Deck Viewer."
        result = await _handle_deck_code(deck_code, message)
        if result:
            return result


async def run():
    try:
        await bot.run_polling()
    finally:
        await bot.api.http_client.close()
