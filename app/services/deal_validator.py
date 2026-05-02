import json
import re
from dataclasses import dataclass

from app.models.entities import Opportunity

SCAM_UNDERPRICE_THRESHOLD = 0.45
SPARSE_TEXT_LENGTH = 35

SCAM_TERMS = (
    "envio solo",
    "pago bizum",
    "reserva",
    "demasiado barato",
    "sin garantia",
)

DEFECT_TERMS = (
    "bateria",
    "batería",
    "golpe",
    "detalle",
    "rayado",
    "arañazo",
    "pantalla",
    "teclado",
    "no funciona",
    "para reparar",
    "bloqueado",
    "icloud",
)

POOR_LISTING_TERMS = (
    "leer",
    "preguntar",
    "mas info",
    "más info",
    "sin descripcion",
    "sin descripción",
)


@dataclass(frozen=True)
class DealValidation:
    safe_to_buy: bool
    warnings: list[str]
    confidence_manual: str
    notes: str


def validate_deal(opportunity: Opportunity) -> DealValidation:
    evidence = _load_evidence(opportunity.evidence_json)
    title = str(evidence.get("title") or opportunity.title or "")
    description = str(
        evidence.get("description")
        or evidence.get("snippet")
        or evidence.get("text")
        or ""
    )
    combined_text = _normalize_text(f"{title} {description}")
    risk_score = _as_float(evidence.get("risk_score"))
    price = _as_float(evidence.get("item_price") or opportunity.buy_price)
    p25 = _as_float(evidence.get("p25"))
    warnings: list[str] = []

    if _looks_too_cheap(price, p25):
        warnings.append("posible scam: precio demasiado bajo vs mercado")

    for term in SCAM_TERMS:
        if term in combined_text:
            warnings.append(f"posible scam: contiene '{term}'")
            break

    for term in DEFECT_TERMS:
        if term in combined_text:
            warnings.append(f"posible defecto: revisar '{term}'")
            break

    if not description.strip() or len(combined_text) < SPARSE_TEXT_LENGTH:
        warnings.append("listing pobre: poca informacion para validar estado")
    else:
        for term in POOR_LISTING_TERMS:
            if term in combined_text:
                warnings.append(f"listing pobre: contiene '{term}'")
                break

    confidence_manual = _manual_confidence(risk_score, warnings)
    safe_to_buy = confidence_manual != "low" and not _has_blocking_warning(warnings)
    notes = _build_notes(
        opportunity=opportunity,
        evidence=evidence,
        warnings=warnings,
        safe_to_buy=safe_to_buy,
        confidence_manual=confidence_manual,
    )

    return DealValidation(
        safe_to_buy=safe_to_buy,
        warnings=warnings,
        confidence_manual=confidence_manual,
        notes=notes,
    )


def _manual_confidence(risk_score: float, warnings: list[str]) -> str:
    if risk_score >= 7.0 or any(warning.startswith("posible scam") for warning in warnings):
        return "low"
    if risk_score >= 4.5 or len(warnings) >= 2:
        return "medium"
    return "high"


def _build_notes(
    *,
    opportunity: Opportunity,
    evidence: dict,
    warnings: list[str],
    safe_to_buy: bool,
    confidence_manual: str,
) -> str:
    profit = _as_float(opportunity.profit_estimate)
    roi = _as_float(evidence.get("roi"))
    risk = _as_float(evidence.get("risk_score"))
    speed = evidence.get("speed_category", "n/d")

    if safe_to_buy:
        base = (
            f"Buen candidato: profit {profit:.2f}EUR, ROI {roi:.2f}, "
            f"riesgo {risk:.2f}, velocidad {speed}."
        )
        if warnings:
            return f"{base} Antes de cerrar, validar: {', '.join(warnings)}."
        return f"{base} Validar bateria/estado fisico y numero de serie antes de pagar."

    return (
        f"No compraria sin verificacion extra: confianza manual {confidence_manual}, "
        f"riesgo {risk:.2f}. Motivos: {', '.join(warnings) or 'senales insuficientes'}."
    )


def _looks_too_cheap(price: float, p25: float) -> bool:
    return price > 0 and p25 > 0 and price < (p25 * SCAM_UNDERPRICE_THRESHOLD)


def _has_blocking_warning(warnings: list[str]) -> bool:
    return any(warning.startswith("posible scam") for warning in warnings)


def _normalize_text(value: str) -> str:
    normalized = value.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _load_evidence(evidence_json: str | None) -> dict:
    if not evidence_json:
        return {}
    try:
        data = json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
