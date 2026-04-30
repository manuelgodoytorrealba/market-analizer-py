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
    "vendo",
    "leer",
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
    "m1",
    "m2",
}

# 🔥 NUEVO: categorías base (simple pero potente)
CATEGORY_PATTERNS = {
    "iphone": r"iphone\s*\d+",
    "macbook": r"macbook",
    "gpu": r"rtx\s*\d{3,4}",
    "playstation": r"\bps[45]\b",
    "xbox": r"xbox",
    "switch": r"nintendo\s*switch",
    "sneaker": r"(nike|jordan|yeezy)",
    "airpods": r"airpods",
    "watch": r"apple\s*watch",
}

# -----------------------------
# 🔥 CORE NORMALIZER
# -----------------------------


def build_normalized_name(title: str, fallback_query: str | None = None) -> str:
    # 1. Primero intenta iPhone (lo mantenemos)
    iphone = extract_iphone_specs(title, fallback_query)
    if iphone:
        return iphone["normalized_name"]

    # 2. Normalización genérica
    tokens = _tokenize(f"{title} {fallback_query or ''}")

    if not tokens:
        return ""

    base = _detect_base_product(title.lower())
    capacities = _extract_capacities(tokens)
    qualifiers = [t for t in tokens if t in QUALIFIER_TOKENS]

    # 🔥 prioridad: base → modelo → atributos
    normalized = _unique(
        ([base] if base else []) + tokens[:3] + capacities + qualifiers
    )

    return " ".join(normalized[:6]).strip()


def build_family_key(title: str, fallback_query: str | None = None) -> str:
    iphone = extract_iphone_specs(title, fallback_query)
    if iphone:
        return iphone["model"]

    normalized = build_normalized_name(title, fallback_query)
    tokens = normalized.split()

    # 🔥 quitar capacidades y ruido
    family = [
        t
        for t in tokens
        if not re.fullmatch(r"\d+(gb|tb)", t) and t not in QUALIFIER_TOKENS
    ]

    return " ".join(family[:3])


def build_comparable_key(title: str, fallback_query: str | None = None) -> str:
    iphone = extract_iphone_specs(title, fallback_query)
    if iphone:
        return f"{iphone['model']} {iphone['capacity']}"

    # 🔥 ahora todos los productos tienen comparable key
    return build_normalized_name(title, fallback_query)


# -----------------------------
# 🔥 DETECCIÓN DE PRODUCTO
# -----------------------------


def _detect_base_product(text: str) -> str | None:
    for key, pattern in CATEGORY_PATTERNS.items():
        if re.search(pattern, text):
            return key
    return None


# -----------------------------
# 🔥 IPHONE (LO MANTENEMOS)
# -----------------------------


def extract_iphone_specs(title: str, fallback_query: str | None = None):
    text = (title + " " + (fallback_query or "")).lower()

    if "iphone" not in text:
        return None

    model_match = re.search(r"iphone\s*(\d+)", text)
    if not model_match:
        return None

    model = model_match.group(1)

    if int(model) < 11:
        return None

    variant = "pro" if "pro" in text else ""
    capacity_match = re.search(r"(128gb|256gb|512gb)", text)

    if not capacity_match:
        return None

    capacity = capacity_match.group(1)

    model_name = f"iphone {model} {variant}".strip()
    normalized_name = f"{model_name} {capacity}"

    return {
        "model": model_name,
        "capacity": capacity,
        "normalized_name": normalized_name,
    }


# -----------------------------
# 🔧 HELPERS
# -----------------------------


def _extract_capacities(tokens):
    return [t for t in tokens if re.fullmatch(r"\d+(gb|tb)", t)]


def _tokenize(text: str):
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return [t for t in text.split() if t not in STOPWORDS and len(t) > 1]


def _unique(tokens):
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


# -----------------------------
# 🔥 CONDITION (compatibilidad)
# -----------------------------

CONDITION_KEYWORDS = {
    "new": {"nuevo", "nueva", "precintado", "precintada", "sealed"},
    "used": {"usado", "usada", "segunda", "mano"},
    "refurb": {"reacondicionado", "refurbished", "renewed"},
}


def infer_condition(title: str, fallback_query: str | None = None) -> str | None:
    text = f"{title} {fallback_query or ''}".lower()

    for condition, keywords in CONDITION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return condition

    return None
