QUERY_CATALOG: dict[str, list[str]] = {
    "iphone": [
        "iphone 11 128gb",
        "iphone 11 pro 256gb",
        "iphone 12 128gb",
        "iphone 12 pro 128gb",
        "iphone 12 pro max 128gb",
        "iphone 13 128gb",
        "iphone 13 pro 128gb",
        "iphone 13 pro max 128gb",
        "iphone 14 128gb",
        "iphone 14 pro 128gb",
        "iphone 14 pro max 128gb",
        "iphone 15 128gb",
        "iphone 15 pro 128gb",
        "iphone 15 pro 256gb",
        "iphone 15 pro max 256gb",
    ],
    "consoles": [
        "ps4 slim",
        "ps4 pro",
        "ps5",
        "ps5 digital",
        "xbox series s",
        "xbox series x",
        "nintendo switch",
        "nintendo switch oled",
        "nintendo switch lite",
        "nintendo ds",
    ],
    "gpus": [
        "rtx 3060",
        "rtx 3060 ti",
        "rtx 3070",
        "rtx 3070 ti",
        "rtx 3080",
        "rtx 3090",
    ],
    "laptops": [
        "macbook air m1",
        "macbook air m2",
        "macbook pro m1",
        "macbook pro m2",
        "macbook pro 14 m1",
        "macbook pro 16 m1",
        "asus rog laptop",
        "lenovo legion",
        "msi gaming laptop",
    ],
    "audio": [
        "airpods pro",
        "airpods pro 2",
        "sony wh-1000xm4",
        "sony wh-1000xm5",
    ],
    "cameras": [
        "sony a7 iii",
        "sony a7 iv",
        "canon eos r",
        "canon eos rp",
    ],
}


def build_query_catalog() -> dict[str, list[str]]:
    return {category: list(queries) for category, queries in QUERY_CATALOG.items()}


def build_queries(*, include_categories: list[str] | None = None) -> list[str]:
    catalog = build_query_catalog()
    categories = include_categories or list(catalog)
    queries: list[str] = []

    for category in categories:
        queries.extend(catalog.get(category, []))

    return _dedupe_preserving_order(queries)


def build_wallapop_queries() -> list[str]:
    return build_queries()


def build_ebay_queries() -> list[str]:
    return build_queries(include_categories=["iphone"])


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result
