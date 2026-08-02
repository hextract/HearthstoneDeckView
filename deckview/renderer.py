from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from .config import BASE_DIR, CARDS_DIR, CARD_COSTS

FONT = ImageFont.truetype(str(BASE_DIR / "belwe.ttf"), 140)


def count_cards(cards):
    counts = {}
    mana = {}
    for card in cards:
        slug = card["slug"]
        counts[slug] = counts.get(slug, 0) + 1
        mana.setdefault(slug, card["manaCost"])
    return counts, mana


def deck_cost(cards):
    return sum(CARD_COSTS.get(card.get("rarityId"), 0) for card in cards)


def _place_runes(image, response):
    offset = 0
    for rune_name, count in response.get("runeSlots", {}).items():
        for _ in range(count):
            with Image.open(
                BASE_DIR / "death_knight" / f"{rune_name}.png"
            ) as rune_image:
                rune = rune_image.convert("RGBA").resize((200, 200))
            image.paste(rune, (1200 + offset, 2120), mask=rune)
            offset += 200


def _layout(card_count):
    if card_count <= 18:
        return 500, (214, 121)
    if card_count <= 21:
        return 428, (180, 91)
    if card_count <= 32:
        return 375, (141, 80)
    return 300, (124, 70)


def _load_card(slug, response, cards_dir):
    path = cards_dir / f"{slug}.png"
    if slug == "102983-zilliax-deluxe-000" and response.get("zilliax"):
        zilliax_path = BASE_DIR / "zilliax" / f"{response['zilliax']}.png"
        if zilliax_path.exists():
            path = zilliax_path
    with Image.open(path) as card_image:
        return card_image.convert("RGBA")


def _tint_sideboard(image):
    red, green, blue, alpha = image.split()
    red = ImageChops.add(red, Image.new("L", image.size, 100))
    green = ImageChops.add(green, Image.new("L", image.size, 50))
    blue = ImageChops.add(blue, Image.new("L", image.size, 50))
    return Image.merge("RGBA", (red, green, blue, alpha))


def render_deck(response, class_id, sideboard, cards_dir=CARDS_DIR):
    counts, mana = count_cards(response["cards"])
    cost = deck_cost(response["cards"] + sideboard)
    size, label_size = _layout(len(counts) + len(sideboard))
    cell_size = (size, int(size * 1.35))

    with Image.open(BASE_DIR / "labels" / "x2.png") as label_image:
        default_label = label_image.convert("RGBA").resize(label_size)
    with Image.open(BASE_DIR / "backs" / f"{class_id}.png") as background:
        image = background.convert("RGBA")

    sorted_slugs = sorted(counts, key=mana.get)
    stack = deque(sorted_slugs)
    row = 0
    column = 0

    while stack:
        slug = stack.popleft()
        card = _load_card(slug, response, Path(cards_dir))
        alpha_box = card.getchannel("A").getbbox()
        if alpha_box:
            card = card.crop(alpha_box)

        width = size
        height = round(card.height / card.width * width)
        if height > cell_size[1]:
            height = cell_size[1]
            width = round(card.width / card.height * height)
        card = card.resize((width, height))

        if slug.endswith("-side"):
            card = _tint_sideboard(card)

        count = counts.get(slug, 0)
        if count >= 2:
            label = default_label
            if count > 2:
                with Image.open(
                    BASE_DIR / "labels" / f"x{min(count, 9)}.png"
                ) as label_image:
                    label = label_image.convert("RGBA").resize(label_size)
            label_offsets = {
                500: (150, 650),
                428: (126, 555),
                375: (125, 487),
                300: (97, 390),
            }
            x_offset, y_offset = label_offsets[size]
            image.paste(
                label,
                (column + x_offset, row + y_offset),
                mask=label,
            )

        image.paste(card, (column, row), mask=card)
        for sideboard_group in response.get("sideboardCards", []):
            if sideboard_group["sideboardCard"]["slug"] == slug:
                cards = sorted(
                    sideboard_group["cardsInSideboard"],
                    key=lambda item: item["manaCost"],
                )
                stack.extendleft(
                    reversed([
                        item["slug"]
                        for item in cards
                        if not item["isZilliaxCosmeticModule"]
                    ])
                )

        column += cell_size[0]
        if column > 2900:
            column = 0
            row += cell_size[1] + 40

    draw = ImageDraw.Draw(image)
    draw.text(
        (170, 2150),
        str(cost),
        (255, 255, 255),
        FONT,
        stroke_fill=(0, 0, 0),
        stroke_width=5,
    )
    if class_id == 1:
        _place_runes(image, response)
    return image
