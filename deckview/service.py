import asyncio

from .blizzard import BlizzardClient
from .card_cache import CardImageCache
from .config import CARDS_DIR, CLIENT_ID, CLIENT_SECRET
from .renderer import render_deck


async def retrieve_deck(deck_code, client):
    response = await client.get_deck(deck_code)
    if "error" in response:
        return None

    sideboard = []
    for group in response.get("sideboardCards", []):
        sideboard_card = group["sideboardCard"]
        if sideboard_card["id"] == 102983:
            for card in response["cards"]:
                if card["id"] == 102983:
                    modules = group["cardsInSideboard"]
                    card["manaCost"] = sum(module["manaCost"] for module in modules)
                    functional_ids = sorted(
                        module["id"]
                        for module in modules
                        if module["isZilliaxFunctionalModule"]
                    )
                    response["zilliax"] = "-".join(map(str, functional_ids))
                    break
        sideboard.extend(group["cardsInSideboard"])

    missing_cards = []
    if len(response["cards"]) < response["cardCount"]:
        missing_cards = await asyncio.gather(*(
            client.get_card(card_id) for card_id in response["invalidCardIds"]
        ))
        response["cards"].extend(missing_cards)

    for card in sideboard:
        card["slug"] += "-side"

    class_id = response["class"]["id"]
    return response, class_id, sideboard


async def create_picture(deck_code):
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("CLIENT_ID and CLIENT_SECRET are not configured")
    client = BlizzardClient(CLIENT_ID, CLIENT_SECRET)
    deck = await retrieve_deck(deck_code, client)
    if deck is None:
        return None

    response, class_id, sideboard = deck
    cache = CardImageCache(CARDS_DIR)
    await cache.populate_async(response["cards"] + sideboard)
    return await asyncio.to_thread(
        render_deck,
        response,
        class_id,
        sideboard,
        CARDS_DIR,
    )
