import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message

from ..config import TELEGRAM_TOKEN
from ..output import create_png
from ..text import extract_deck_codes

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN is not configured")

bot = Bot(
    token=TELEGRAM_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dispatcher = Dispatcher()
router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_handler(message: Message):
    first_name = message.from_user.first_name if message.from_user else "there"
    await message.answer(
        f"Hi {first_name}!\n"
        "Send me a Hearthstone deck code and I will generate a deck image. "
        "You can also add me to a group to detect deck codes automatically."
    )


@router.message(F.text)
async def message_handler(message: Message):
    for deck_code in extract_deck_codes(message.text):
        try:
            image = await create_png(deck_code, scale=2 / 3)
            if image is None:
                return
            await message.answer_photo(
                BufferedInputFile(image, filename=f"{deck_code}.png")
            )
        except Exception:
            logger.exception("Failed to process Telegram deck code")
            await message.answer("Could not generate this deck image. Please try again.")


async def run():
    dispatcher.include_router(router)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()
