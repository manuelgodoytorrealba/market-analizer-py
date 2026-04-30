import re
import unicodedata

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
    "m3",
    "ti",
    "series",
}

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "smartphones": [r"\biphone\s*\d+"],
    "consoles": [
        r"\bps[45]\b",
        r"\bplaystation\s*[45]\b",
        r"\bxbox\s+series\s+[sx]\b",
        r"\bnintendo\s+switch\b",
        r"\bnintendo\s+ds\b",
    ],
    "gpus": [r"\brtx\s*\d{3,4}\s*(?:ti|super)?\b"],
    "laptops": [
        r"\bmacbook\b",
        r"\basus\s+rog\b",
        r"\blenovo\s+legion\b",
        r"\bmsi\s+gaming\b",
        r"\bgaming\s+laptop\b",
    ],
    "audio": [
        r"\bairpods\b",
        r"\bsony\s+wh[-\s]?1000xm[45]\b",
    ],
    "cameras": [
        r"\bsony\s+a7\s*(?:iii|iv|3|4)\b",
        r"\bcanon\s+eos\s+r[p]?\b",
        r"\bcanon\s+eos\s+r\d{1,3}\b",
    ],
    "wearables": [r"\bapple\s+watch\b"],
    "sneakers": [r"\b(?:nike|jordan|yeezy)\b"],
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
        return _with_subcategory(
            f"{iphone['model']} {iphone['capacity']}",
            title,
            fallback_query,
        )

    text = _normalize_text(f"{title} {fallback_query or ''}")

    category_key = _build_category_comparable_key(text)
    if category_key:
        return _with_subcategory(category_key, title, fallback_query)

    return _with_subcategory(
        build_normalized_name(title, fallback_query),
        title,
        fallback_query,
    )


def detect_category(title: str, fallback_query: str | None = None) -> str:
    text = _normalize_text(f"{title} {fallback_query or ''}")

    for category, patterns in CATEGORY_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return category

    return "unknown"


def detect_category_confidence(title: str, fallback_query: str | None = None) -> float:
    text = _normalize_text(f"{title} {fallback_query or ''}")
    category = detect_category(title, fallback_query)
    if category == "unknown":
        return 0.0

    pattern_matches = sum(
        1
        for pattern in CATEGORY_PATTERNS.get(category, [])
        if re.search(pattern, text)
    )
    query_bonus = 1 if fallback_query and category != "unknown" else 0
    return min(1.0, round(0.65 + (pattern_matches * 0.2) + (query_bonus * 0.15), 2))


def detect_subcategory(title: str, fallback_query: str | None = None) -> str | None:
    text = _normalize_text(f"{title} {fallback_query or ''}")
    category = detect_category(title, fallback_query)

    if category == "cameras":
        if _has_any(text, ["solo lente", "solo objetivo"]):
            return "camera_lens"
        if _has_any(text, ["solo cuerpo", "body only"]):
            return "camera_body"
        if _has_any(text, ["con lente", "con objetivo", "kit", "objetivo incluido"]):
            return "camera_kit"
        return "camera_body"

    if category == "laptops":
        if _has_any(
            text,
            [
                "pantalla",
                "teclado",
                "solo carcasa",
                "placa base",
                "sin bateria",
                "no enciende",
                "para reparar",
            ],
        ):
            return "parts"
        return "full_laptop"

    if category == "consoles":
        if _has_any(text, ["sin mando", "solo consola"]):
            return "no_controller"
        return "full_console"

    if category == "gpus":
        if _has_any(
            text,
            ["no da video", "para reparar", "sin probar", "defectuosa", "mineria danada"],
        ):
            return "for_parts"
        return "working"

    if category == "smartphones":
        if _has_any(
            text,
            [
                "para piezas",
                "para reparar",
                "no funciona",
                "icloud",
                "bloqueado",
                "pantalla rota",
                "solo placa",
                "roto",
                "averiado",
            ],
        ):
            return "damaged"
        return "complete"

    return None


# -----------------------------
# 🔥 DETECCIÓN DE PRODUCTO
# -----------------------------


def _detect_base_product(text: str) -> str | None:
    category = detect_category(text)
    if category == "smartphones" and "iphone" in text:
        return "iphone"
    if category == "gpus":
        return "rtx"
    if category == "consoles":
        return "console"
    if category == "laptops":
        return "laptop"
    if category == "audio":
        return "audio"
    if category == "cameras":
        return "camera"
    if category in {"wearables", "sneakers"}:
        return category
    return None


def _build_category_comparable_key(text: str) -> str | None:
    console = _console_key(text)
    if console:
        return console

    gpu = _gpu_key(text)
    if gpu:
        return gpu

    laptop = _laptop_key(text)
    if laptop:
        return laptop

    audio = _audio_key(text)
    if audio:
        return audio

    camera = _camera_key(text)
    if camera:
        return camera

    return None


def _with_subcategory(
    comparable_key: str,
    title: str,
    fallback_query: str | None = None,
) -> str:
    if not comparable_key:
        return comparable_key

    subcategory = detect_subcategory(title, fallback_query)
    if not subcategory:
        return comparable_key

    return f"{comparable_key}__{subcategory}"


def _console_key(text: str) -> str | None:
    if re.search(r"\bps5\b|\bplaystation\s*5\b", text):
        return "ps5 digital" if "digital" in text else "ps5"
    if re.search(r"\bps4\b|\bplaystation\s*4\b", text):
        if "pro" in text:
            return "ps4 pro"
        if "slim" in text:
            return "ps4 slim"
        return "ps4"
    if re.search(r"\bxbox\s+series\s+s\b", text):
        return "xbox series s"
    if re.search(r"\bxbox\s+series\s+x\b", text):
        return "xbox series x"
    if "nintendo switch" in text:
        if "oled" in text:
            return "nintendo switch oled"
        if "lite" in text:
            return "nintendo switch lite"
        return "nintendo switch"
    if "nintendo ds" in text:
        return "nintendo ds"
    return None


def _gpu_key(text: str) -> str | None:
    match = re.search(r"\brtx\s*(\d{3,4})(?:\s*(ti|super))?\b", text)
    if not match:
        return None
    suffix = f" {match.group(2)}" if match.group(2) else ""
    return f"rtx {match.group(1)}{suffix}".strip()


def _laptop_key(text: str) -> str | None:
    chip_match = re.search(r"\bm([123])\b", text)
    chip = f" m{chip_match.group(1)}" if chip_match else ""
    size_match = re.search(r"\b(13|14|15|16)\b", text)
    size = f" {size_match.group(1)}" if size_match else ""

    if "macbook air" in text:
        return f"macbook air{size}{chip}".strip()
    if "macbook pro" in text:
        return f"macbook pro{size}{chip}".strip()
    if "asus rog" in text:
        return "asus rog laptop"
    if "lenovo legion" in text:
        return "lenovo legion laptop"
    if "msi gaming" in text:
        return "msi gaming laptop"
    return None


def _audio_key(text: str) -> str | None:
    if "airpods pro" in text:
        return "airpods pro 2" if re.search(r"\b(?:2|segunda|2nd)\b", text) else "airpods pro"
    sony = re.search(r"\bsony\s+wh[-\s]?(1000xm[45])\b", text)
    if sony:
        return f"sony wh-{sony.group(1)}"
    return None


def _camera_key(text: str) -> str | None:
    sony = re.search(r"\bsony\s+a7\s*(iii|iv|3|4)\b", text)
    if sony:
        generation = sony.group(1)
        generation = "iii" if generation == "3" else "iv" if generation == "4" else generation
        return f"sony a7 {generation}"
    if re.search(r"\bcanon\s+eos\s+rp\b", text):
        return "canon eos rp"
    canon_r_number = re.search(r"\bcanon\s+eos\s+(r\d{1,3})\b", text)
    if canon_r_number:
        return f"canon eos {canon_r_number.group(1)}"
    if re.search(r"\bcanon\s+eos\s+r\b", text):
        return "canon eos r"
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
    text = _normalize_text(text)
    return [t for t in text.split() if t not in STOPWORDS and len(t) > 1]


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    ascii_text = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def _has_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


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
