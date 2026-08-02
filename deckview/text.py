def extract_deck_codes(text):
    if not text:
        return []
    return [word for word in text.split() if word.startswith("AA")]
