import json
from dataclasses import dataclass

from app.models.entities import Opportunity

BUY_SHORTLIST_LIMIT = 10  # 🔥 subimos el límite


@dataclass(frozen=True)
class BuyDecision:
    approved: bool
    reason: str
    buy_score: float
    evidence: dict


# =========================================
# MAIN
# =========================================


def build_buy_shortlist(opportunities: list[Opportunity]) -> list[Opportunity]:
    approved: list[tuple[Opportunity, BuyDecision]] = []

    for opportunity in opportunities:
        decision = evaluate_buy_decision(opportunity)

        if decision.approved:
            _attach_buy_evidence(opportunity, decision)
            approved.append((opportunity, decision))

    # 🔥 orden por score real
    approved.sort(
        key=lambda pair: pair[1].buy_score,
        reverse=True,
    )

    return [opportunity for opportunity, _ in approved[:BUY_SHORTLIST_LIMIT]]


# =========================================
# CORE DECISION
# =========================================


def evaluate_buy_decision(opportunity: Opportunity) -> BuyDecision:
    evidence = _load_evidence(opportunity.evidence_json)

    rejection_reason = _hard_rejection_reason(opportunity, evidence)

    if rejection_reason:
        return BuyDecision(
            approved=False,
            reason=rejection_reason,
            buy_score=0.0,
            evidence=evidence,
        )

    buy_score = compute_buy_score(opportunity, evidence)

    return BuyDecision(
        approved=True,
        reason=_buy_reason(opportunity, evidence, buy_score),
        buy_score=buy_score,
        evidence=evidence,
    )


# =========================================
# SCORING (más realista)
# =========================================


def compute_buy_score(opportunity: Opportunity, evidence: dict) -> float:
    profit = opportunity.profit_estimate or 0.0
    price = opportunity.buy_price or 1.0

    roi = profit / price if price else 0.0
    comparables = opportunity.comparable_count or 0

    # valores de evidence (si existen)
    market_speed = _as_float(evidence.get("market_speed_score"))
    risk = _as_float(evidence.get("risk_score"))

    score = (
        (min(roi, 1.0) * 40)  # ROI pesa MUCHO
        + (min(profit / 100, 1.0) * 25)  # beneficio absoluto
        + (min(comparables / 20, 1.0) * 15)  # liquidez
        + (market_speed * 10)  # velocidad mercado
        - (risk * 10)  # penalización riesgo
    )

    return round(max(score, 0.0), 2)


# =========================================
# 🔥 HARD FILTERS (MUY relajados ahora)
# =========================================


def _hard_rejection_reason(opportunity: Opportunity, evidence: dict) -> str | None:
    profit = opportunity.profit_estimate or 0.0
    comparables = opportunity.comparable_count or 0

    # ❌ solo rechazamos basura real
    if profit < 20:
        return "profit_too_low"

    if comparables < 2:
        return "not_enough_liquidity"

    # 🔥 eliminamos restricciones agresivas:
    # - confidence
    # - risk fuerte
    # - speed

    return None


# =========================================
# DEBUG / EXPLICACIÓN
# =========================================


def rejected_buy_decisions(opportunities: list[Opportunity], limit: int = 10):
    rejected = []

    for opportunity in opportunities:
        decision = evaluate_buy_decision(opportunity)

        if not decision.approved:
            rejected.append((opportunity, decision))

        if len(rejected) >= limit:
            break

    return rejected


# =========================================
# UTILS
# =========================================


def _buy_reason(opportunity: Opportunity, evidence: dict, buy_score: float) -> str:
    profit = opportunity.profit_estimate or 0.0
    price = opportunity.buy_price or 0.0
    comparables = opportunity.comparable_count or 0

    return (
        f"BUY: profit {profit:.2f}€, price {price:.2f}€, "
        f"comparables {comparables}, score {buy_score:.2f}"
    )


def _attach_buy_evidence(opportunity: Opportunity, decision: BuyDecision) -> None:
    evidence = dict(decision.evidence)

    evidence["buy_decision"] = "approved"
    evidence["buy_reason"] = decision.reason
    evidence["buy_score"] = decision.buy_score

    opportunity.evidence_json = json.dumps(evidence)


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
