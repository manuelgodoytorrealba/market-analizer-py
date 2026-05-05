from dataclasses import dataclass, field
import re
import unicodedata

from app.models.entities import Listing


@dataclass(frozen=True)
class SemanticClassification:
    is_target_match: bool
    is_damaged_or_parts_only: bool
    is_safe_listing: bool
    language_code: str
    confidence: float
    reason: str | None
    labels: tuple[str, ...] = ()
    backend: str = "heuristic-fallback"
    model_name: str = "semantic_listing_classifier_stub"
    details: dict[str, object] = field(default_factory=dict)


class SemanticListingClassifier:
    """
    Lightweight semantic guardrail for marketplace listings.

    This is intentionally a narrow interface so we can swap the fallback
    heuristics for a real multilingual model later without changing the
    analyzer pipeline.
    """

    def __init__(self) -> None:
        self.backend = "heuristic-fallback"
        self.model_name = "semantic_listing_classifier_stub"

    def classify(self, item: Listing) -> SemanticClassification:
        text = self._listing_text(item)
        language_code = self._detect_language_code(text)
        target_match, target_reason = self._detect_target_match(text)
        damaged, damage_reason = self._detect_damage(text)

        labels: list[str] = []
        labels.append("target_match" if target_match else "accessory_or_wrong_item")
        labels.append("damaged_or_parts_only" if damaged else "looks_working")

        confidence = self._confidence(target_match, damaged, text)
        safe_listing = target_match and not damaged
        reason = damage_reason or target_reason

        return SemanticClassification(
            is_target_match=target_match,
            is_damaged_or_parts_only=damaged,
            is_safe_listing=safe_listing,
            language_code=language_code,
            confidence=confidence,
            reason=reason,
            labels=tuple(labels),
            backend=self.backend,
            model_name=self.model_name,
            details={
                "target_reason": target_reason,
                "damage_reason": damage_reason,
                "normalized_text": text,
            },
        )

    def _listing_text(self, item: Listing) -> str:
        values = [
            item.title,
            item.normalized_name,
            item.search_query,
            getattr(item, "description", ""),
            getattr(item, "snippet", ""),
            getattr(item, "summary", ""),
        ]
        return _normalize_text(" ".join(str(value) for value in values if value))

    def _detect_language_code(self, text: str) -> str:
        if not text:
            return "unknown"

        spanish_markers = [
            " para ",
            " no funciona",
            " bloqueado",
            " solo ",
            " mando",
            " piezas",
            " repar",
            " usado",
        ]
        english_markers = [
            " for parts",
            " not working",
            " controller",
            " damaged",
            " broken",
            " locked",
            " only ",
        ]

        spanish_hits = sum(1 for marker in spanish_markers if marker in f" {text} ")
        english_hits = sum(1 for marker in english_markers if marker in f" {text} ")

        if spanish_hits > english_hits:
            return "es"
        if english_hits > spanish_hits:
            return "en"
        return "und"

    def _detect_target_match(self, text: str) -> tuple[bool, str | None]:
        if not text:
            return False, "empty_text"

        accessory_only_terms = [
            "mando",
            "controller",
            "joycon",
            "cargador",
            "cable",
            "funda",
            "case",
            "solo mando",
            "solo controller",
            "only controller",
            "only accessory",
            "accessory only",
        ]
        if any(term in text for term in accessory_only_terms):
            return False, "accessory_only"

        return True, None

    def _detect_damage(self, text: str) -> tuple[bool, str | None]:
        if not text:
            return False, None

        hard_block_terms = [
            "no funciona",
            "not working",
            "for parts",
            "para piezas",
            "piezas",
            "bloqueado",
            "locked",
            "roto",
            "broken",
            "averiado",
            "damaged",
            "sin probar",
            "untested",
            "reparar",
            "repair",
            "repuesto",
            "replacement",
            "placa base",
            "motherboard",
        ]
        accessory_only_terms = [
            "solo mando",
            "only controller",
            "solo consola",
            "console only",
            "solo pieza",
            "parts only",
        ]

        for term in hard_block_terms:
            if term in text:
                return True, term

        for term in accessory_only_terms:
            if term in text:
                return True, term

        return False, None

    def _confidence(self, target_match: bool, damaged: bool, text: str) -> float:
        score = 0.55
        if target_match:
            score += 0.2
        if damaged:
            score += 0.2
        if len(text.split()) > 6:
            score += 0.05
        if any(char.isdigit() for char in text):
            score += 0.05
        return round(min(score, 0.98), 2)


def classify_listing_semantics(item: Listing) -> SemanticClassification:
    return get_semantic_classifier().classify(item)


def get_semantic_classifier() -> SemanticListingClassifier:
    return _SEMANTIC_CLASSIFIER


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", (text or "").lower())
    ascii_text = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", ascii_text).strip()


_SEMANTIC_CLASSIFIER = SemanticListingClassifier()
