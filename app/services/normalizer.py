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

IPHONE_NOISE_TOKENS = {
    "apple",
    "smartphone",
    "telefono",
    "phone",
    "movil",
    "mobile",
    "libre",
    "unlocked",
    "sim",
    "free",
    "shipment",
    "shipping",
    "box",
    "only",
    "excellent",
    "good",
    "fair",
}

IPHONE_CONDITION_KEYWORDS = {
    "new": {
        "new",
        "nuevo",
        "nueva",
        "brandnew",
        "brand",
        "sealed",
        "precintado",
        "precintada",
    },
    "refurb": {
        "refurbished",
        "refurb",
        "reacondicionado",
        "reconditioned",
        "renewed",
    },
    "used": {
        "used",
        "usado",
        "usada",
        "secondhand",
        "segunda",
        "mano",
    },
}

SUPPORTED_IPHONE_GENERATIONS = {"12", "13", "14"}
SUPPORTED_IPHONE_CAPACITIES = {"128gb", "256gb"}


def build_normalized_name(title: str, fallback_query: str | None = None) -> str:
    iphone_specs = extract_iphone_specs(title, fallback_query=fallback_query)
    if iphone_specs is not None:
        return iphone_specs["normalized_name"]

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
    iphone_specs = extract_iphone_specs(title, fallback_query=fallback_query)
    if iphone_specs is not None:
        return iphone_specs["model"]

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


def build_comparable_key(title: str, fallback_query: str | None = None) -> str:
    iphone_specs = extract_iphone_specs(title, fallback_query=fallback_query)
    if iphone_specs is None:
        return build_normalized_name(title, fallback_query=fallback_query)
    return f"{iphone_specs['model']} {iphone_specs['capacity']}"


def infer_condition(title: str, fallback_query: str | None = None) -> str | None:
    tokens = set(_tokenize(f"{title} {fallback_query or ''}"))
    for condition in ("refurb", "new", "used"):
        if tokens.intersection(IPHONE_CONDITION_KEYWORDS[condition]):
            return condition
    return None


def extract_iphone_specs(title: str, fallback_query: str | None = None) -> dict[str, str] | None:
    title_lowered = title.lower()
    if "iphone" not in title_lowered:
        return None

    model_match = re.search(r"\biphone\s*(12|13|14)\b", title_lowered)
    if model_match is None:
        return None

    generation = model_match.group(1)
    if generation not in SUPPORTED_IPHONE_GENERATIONS:
        return None

    if re.search(rf"\biphone\s*{generation}\s*mini\b", title_lowered):
        return None
    if re.search(rf"\biphone\s*{generation}\s*pro\s*max\b", title_lowered):
        return None

    title_tokens = _tokenize(title)
    query_tokens = _tokenize(fallback_query or "")
    filtered_title_tokens = [token for token in title_tokens if token not in IPHONE_NOISE_TOKENS]
    model = (
        f"iphone {generation} pro"
        if re.search(rf"\biphone\s*{generation}\s*pro\b", title_lowered)
        else f"iphone {generation}"
    )
    capacity = next(
        (
            token
            for token in filtered_title_tokens
            if token in SUPPORTED_IPHONE_CAPACITIES
        ),
        "",
    )
    if not capacity:
        capacity = next((token for token in query_tokens if token in SUPPORTED_IPHONE_CAPACITIES), "")
    if not capacity:
        return None

    condition = infer_condition(title, fallback_query=fallback_query)
    normalized_name = f"{model} {capacity}"

    return {
        "model": model,
        "capacity": capacity,
        "normalized_name": normalized_name,
        "condition": condition or "",
    }


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
