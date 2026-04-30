# app/services/filters.py


def is_valid_listing(item) -> bool:
    try:
        price = float(item.price)
    except Exception:
        return False

    # ❌ basura típica
    if price < 30:
        return False

    if price > 5000:
        return False

    title = (item.title or "").lower()

    bad_words = [
        "leer",
        "caja",
        "solo caja",
        "sin",
        "no funciona",
        "roto",
        "averiado",
        "para piezas",
    ]

    if any(word in title for word in bad_words):
        return False

    return True
