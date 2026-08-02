import asyncio
import logging
from io import BytesIO

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from ..config import (
    DISCORD_LOGIN_TIMEOUT,
    DISCORD_MESSAGE_CONTENT_INTENT,
    DISCORD_TOKEN,
)
from ..output import create_png
from ..text import extract_deck_codes

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is not configured")

intents = discord.Intents.default()
intents.message_content = DISCORD_MESSAGE_CONTENT_INTENT
client = commands.Bot(
    command_prefix="/",
    activity=discord.Game(name="Analyzing decks"),
    intents=intents,
)
logger = logging.getLogger(__name__)
commands_synced = False


async def _deck_file(deck_code):
    image = await create_png(deck_code, scale=5 / 6)
    if image is None:
        return None
    return discord.File(BytesIO(image), filename=f"{deck_code}.png")


async def _slash_deck(interaction, deck_code):
    await interaction.response.send_message("Generating deck image…")
    try:
        image = await _deck_file(deck_code)
        if image is None:
            await interaction.edit_original_response(content="Invalid deck code.")
            return
        await interaction.edit_original_response(content=None, attachments=[image])
    except Exception:
        logger.exception("Failed to process Discord slash command")
        await interaction.edit_original_response(
            content="Could not generate this deck image. Please try again."
        )


@client.event
async def on_ready():
    global commands_synced
    logger.info(
        "Discord ready as %s (%s), connected to %s guilds",
        client.user,
        client.user.id,
        len(client.guilds),
    )
    if not commands_synced:
        try:
            synced = await client.tree.sync()
            commands_synced = True
            logger.info("Synchronized %s Discord application commands", len(synced))
        except Exception:
            logger.exception("Could not synchronize Discord application commands")


@client.event
async def on_connect():
    logger.info("Discord gateway connected; waiting for READY")


@client.event
async def on_disconnect():
    logger.warning("Discord gateway disconnected; reconnecting")


@client.tree.command(name="deck", description="Generate a deck image from its code")
@app_commands.describe(deck_code="Hearthstone deck code")
async def deck_command(interaction: discord.Interaction, deck_code: str):
    await _slash_deck(interaction, deck_code)


@client.tree.command(name="code", description="Generate a deck image from its code")
@app_commands.describe(deck_code="Hearthstone deck code")
async def code_command(interaction: discord.Interaction, deck_code: str):
    await _slash_deck(interaction, deck_code)


@client.command(name="deck")
async def prefix_deck(context, deck_code):
    status = await context.send("Generating deck image…")
    try:
        image = await _deck_file(deck_code)
        if image is None:
            await status.edit(content="Invalid deck code.")
            return
        await status.edit(content=None, attachments=[image])
    except Exception:
        logger.exception("Failed to process Discord prefix command")
        await status.edit(
            content="Could not generate this deck image. Please try again."
        )


@client.listen("on_message")
async def message_handler(message):
    if message.author.bot or message.content.startswith("/deck"):
        return
    for deck_code in extract_deck_codes(message.content):
        status = await message.channel.send("Generating deck image…")
        try:
            image = await _deck_file(deck_code)
            if image is None:
                await status.edit(content="Invalid deck code.")
                continue
            await status.edit(content=None, attachments=[image])
        except Exception:
            logger.exception("Failed to process Discord deck code")
            await status.edit(
                content="Could not generate this deck image. Please try again."
            )


async def run():
    logger.info("Starting Discord adapter")
    if not DISCORD_MESSAGE_CONTENT_INTENT:
        logger.info(
            "Discord Message Content intent is disabled; slash commands are available, "
            "but automatic deck-code detection and prefix commands are disabled"
        )
    try:
        try:
            await asyncio.wait_for(
                client.login(DISCORD_TOKEN),
                timeout=DISCORD_LOGIN_TIMEOUT,
            )
        except TimeoutError as error:
            raise RuntimeError(
                f"Discord login timed out after {DISCORD_LOGIN_TIMEOUT:g}s. "
                "Check the network connection to Discord."
            ) from error
        except discord.LoginFailure as error:
            raise RuntimeError("Discord rejected DISCORD_TOKEN") from error
        except (aiohttp.ClientError, OSError) as error:
            raise RuntimeError(
                f"Discord login failed: {error}. "
                "Check the network connection to Discord."
            ) from error

        logger.info("Discord login succeeded; connecting to the gateway")
        await client.connect(reconnect=True)
    finally:
        logger.info("Stopping Discord adapter")
        if not client.is_closed():
            await client.close()
