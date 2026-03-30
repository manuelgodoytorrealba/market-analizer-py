import re


STOPWORDS = {
    "con",
    "sin",
    "para",
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "nuevo",
    "nueva",
    "usado",
    "usada",
    "precintado",
    "precintada",
    "caja",
    "original",
    "mando",
    "bundle",
    "pack",
    "leer",
    "vendo",
    "blanca",
    "blanco",
    "negra",
    "negro",
    "roja",
    "rojo",
    "azul",
    "verde",
    "gris",
    "silver",
    "space",
    "gray",
}

QUALIFIER_TOKENS = {
    "oled",
    "slim",
    "digital",
    "disc",
    "wifi",
    "cellular",
    "mini",
    "pro",
    "max",
    "ultra",
    "lcd",
    "m1",
    "m2",
}

FAMILY_EXCLUDED_TOKENS = {
    "oled",
    "slim",
    "digital",
    "disc",
    "wifi",
    "cellular",
}


def build_normalized_name(title: str, fallback_query: str | None = None) -> str:
    title_tokens = _tokenize(title)
    query_tokens = _tokenize(fallback_query or "")

    if not title_tokens and not query_tokens:
        return ""

    selected: list[str] = []

    for token in query_tokens:
        if token in title_tokens:
            selected.append(token)

    if not selected:
        selected.extend(query_tokens[:4])

    capacities = _extract_capacities(title_tokens + query_tokens)
    qualifiers = [
        token for token in title_tokens if token in QUALIFIER_TOKENS and token not in selected
    ]
    remaining: list[str] = []
    if not selected:
        remaining = [
            token
            for token in title_tokens
            if token not in capacities and token not in qualifiers
        ]

    normalized_tokens = _unique(selected + capacities + qualifiers + remaining[:3])
    return " ".join(normalized_tokens[:7]).strip()


def build_family_key(title: str, fallback_query: str | None = None) -> str:
    normalized_name = build_normalized_name(title, fallback_query=fallback_query)
    if not normalized_name:
        return ""

    family_tokens = [
        token
        for token in normalized_name.split()
        if token not in FAMILY_EXCLUDED_TOKENS
        and re.fullmatch(r"\d+(?:gb|tb)", token) is None
    ]
    return " ".join(family_tokens[:5]).strip()


def _extract_capacities(tokens: list[str]) -> list[str]:
    return [token for token in tokens if re.fullmatch(r"\d+(?:gb|tb)", token) is not None]


def _tokenize(text: str) -> list[str]:
    normalized = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    return [
        token
        for token in normalized.split()
        if token not in STOPWORDS and (len(token) > 1 or any(char.isdigit() for char in token))
    ]


def _unique(tokens: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        result.append(token)

    return result
