import datetime
import os
import random

import discord
from discord import app_commands
from discord.ext import commands

from db.config import TOKEN
from image_creator import create_picture

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix="/",
                      activity=discord.Game(name="Analyzing decks"),
                      intents=intents)


async def generate_and_save(deck_code):
    image = await create_picture(deck_code)

    if not image:
        return

    x, y = image.size
    image = image.resize((int(x / 1.2), int(y / 1.2)))

    name = random.randint(1000000, 10000000)

    image.save(f"{name}.png", format="PNG")

    return name


@client.event
async def on_ready():
    print("Logged in as")
    print(client.user.name)
    print(client.user.id)
    print(discord.__version__)
    print("------")

    try:
        synced = await client.tree.sync()
        print(f"synced {len(synced)} commands")
        print("\n\n---------\n\n")
    except Exception as e:
        print("sync error:", e)

    print("Servers connected to:")
    sum_servers, sum_members = 0, 0
    for guild in sorted(client.guilds, key=lambda cl: cl.member_count):
        sum_servers += 1
        sum_members += guild.member_count
        print(guild.name, "-----", guild.member_count, "members")

    print(f"ALL: {sum_servers} servers, {sum_members} members")
    print("\n\n---------\n\n")


@client.tree.command(name="deck", description="Generates picture of deck by"
                                              'its code. Same as "/code"')
@app_commands.describe(deck_code="Generates picture of deck by its code."
                                 " May take a while")
async def deck(interaction: discord.Interaction, deck_code: str):
    await interaction.response.send_message("_Waiting for image to "
                                            "generate... "
                                            "It will be here soon_")
    name = await generate_and_save(deck_code)

    await interaction.edit_original_response(
        content="",
        attachments=[discord.File(f"{name}.png")]
    )

    os.remove(f"{name}.png")


@client.tree.command(name="code", description="Generates picture of deck by "
                                              'its code. Same as "/deck"')
@app_commands.describe(deck_code="Generates picture of deck by its code."
                                 " May take a while")
async def code(interaction: discord.Interaction, deck_code: str):
    await interaction.response.send_message("_Waiting for image to "
                                            "generate... "
                                            "It will be here soon_")
    name = await generate_and_save(deck_code)

    await interaction.edit_original_response(
        content="",
        attachments=[discord.File(f"{name}.png")]
    )

    os.remove(f"{name}.png")


@client.command(name='deck')
async def deck(ctx, deck_code):
    name = await generate_and_save(deck_code)

    await ctx.send(file=discord.File(f"{name}.png"))

    os.remove(f"{name}.png")


@client.event
async def on_message(message: discord.message.Message):
    if message.author.bot:
        return
    text = message.content.split()

    start_time = datetime.datetime.now()

    for word in text:
        if word[:2] == "AA":
            ctx: discord.ext.commands.context.Context = \
                await client.get_context(message)

            name = await generate_and_save(word)

            await ctx.send(file=discord.File(f"{name}.png"))

            os.remove(f"{name}.png")

            print(datetime.datetime.now() - start_time)


client.run(TOKEN)
