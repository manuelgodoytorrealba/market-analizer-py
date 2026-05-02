import unicodedata
from dataclasses import dataclass

from app.models.entities import Listing
from app.services.normalizer import detect_category


@dataclass(frozen=True)
class CategoryFilterResult:
    is_valid: bool
    category: str
    category_filter_reason: str | None
    category_risk_flags: list[str]
    risk_score_boost: float


BLOCKING_TERMS: dict[str, dict[str, str]] = {
    "smartphones": {
        "para piezas": "blocked_for_parts",
        "para reparar": "blocked_for_repair",
        "no funciona": "blocked_not_working",
        "icloud": "blocked_icloud",
        "bloqueado": "blocked_locked",
        "pantalla rota": "blocked_broken_screen",
        "solo placa": "blocked_board_only",
    },
    "laptops": {
        "pantalla": "blocked_screen_only",
        "teclado": "blocked_keyboard_only",
        "solo carcasa": "blocked_case_only",
        "placa base": "blocked_motherboard_only",
        "sin bateria": "blocked_missing_battery",
        "no enciende": "blocked_not_powering_on",
        "para reparar": "blocked_for_repair",
    },
    "gpus": {
        "no da video": "blocked_no_video",
        "para reparar": "blocked_for_repair",
        "sin probar": "blocked_untested",
        "defectuosa": "blocked_defective",
        "mineria danada": "blocked_mining_damaged",
    },
    "consoles": {
        "sin mando": "blocked_missing_controller",
        "solo consola": "blocked_console_only",
        "no lee discos": "blocked_disc_reader",
        "para reparar": "blocked_for_repair",
    },
    "cameras": {
        "solo lente": "blocked_lens_only",
        "solo objetivo": "blocked_lens_only",
        "no enciende": "blocked_not_powering_on",
        "para piezas": "blocked_for_parts",
        "para reparar": "blocked_for_repair",
    },
    "audio": {
        "solo auricular": "blocked_single_earbud",
        "no carga": "blocked_not_charging",
        "no funciona": "blocked_not_working",
    },
}


RISK_TERMS: dict[str, float] = {
    "bateria 80": 1.5,
    "bateria al 80": 1.5,
    "bateria 81": 1.25,
    "bateria 82": 1.0,
    "pequeno golpe": 1.0,
    "golpe": 1.0,
    "marcas de uso": 0.75,
    "leer": 1.0,
    "solo hoy": 0.5,
}


CATEGORY_RISK_TERMS: dict[str, dict[str, float]] = {
    "cameras": {
        "solo cuerpo": 2.5,
    },
    "laptops": {
        "sin cargador": 1.25,
    },
    "consoles": {
        "sin caja": 0.5,
        "sin cables": 1.0,
    },
    "gpus": {
        "mineria": 1.5,
    },
    "smartphones": {
        "sin face id": 2.0,
        "face id no funciona": 3.0,
    },
    "audio": {
        "sin caja": 0.5,
    },
}


def is_valid_category_listing(item: Listing) -> bool:
    return evaluate_category_listing(item).is_valid


def evaluate_category_listing(item: Listing) -> CategoryFilterResult:
    category = detect_category(item.title, item.search_query or item.normalized_name)
    text = _listing_text(item)
    reason = _blocking_reason(category, text)
    risk_flags, risk_score_boost = _risk_flags(category, text)

    return CategoryFilterResult(
        is_valid=reason is None,
        category=category,
        category_filter_reason=reason,
        category_risk_flags=risk_flags,
        risk_score_boost=round(min(risk_score_boost, 5.0), 2),
    )


def _blocking_reason(category: str, text: str) -> str | None:
    for term, reason in BLOCKING_TERMS.get(category, {}).items():
        if term in text:
            return reason
    return None


def _risk_flags(category: str, text: str) -> tuple[list[str], float]:
    flags: list[str] = []
    score = 0.0

    for term, value in RISK_TERMS.items():
        if term in text:
            flags.append(term.replace(" ", "_"))
            score += value

    for term, value in CATEGORY_RISK_TERMS.get(category, {}).items():
        if term in text:
            flags.append(term.replace(" ", "_"))
            score += value

    return flags, score


def _listing_text(item: Listing) -> str:
    values = [
        item.title,
        item.normalized_name,
        item.search_query,
        getattr(item, "description", ""),
        getattr(item, "snippet", ""),
        getattr(item, "summary", ""),
    ]
    return _normalize_text(" ".join(str(value) for value in values if value))


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))
