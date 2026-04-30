import json
from dataclasses import dataclass

from app.models.entities import Opportunity

BUY_SHORTLIST_LIMIT = 5


@dataclass(frozen=True)
class BuyDecision:
    approved: bool
    reason: str
    buy_score: float
    evidence: dict


def build_buy_shortlist(opportunities: list[Opportunity]) -> list[Opportunity]:
    approved: list[tuple[Opportunity, BuyDecision]] = []

    for opportunity in opportunities:
        decision = evaluate_buy_decision(opportunity)
        if decision.approved:
            _attach_buy_evidence(opportunity, decision)
            approved.append((opportunity, decision))

    approved.sort(
        key=lambda pair: (
            pair[1].buy_score,
            _as_float(pair[1].evidence.get("roi")),
            _as_float(pair[1].evidence.get("market_speed_score")),
        ),
        reverse=True,
    )

    return [opportunity for opportunity, _ in approved[:BUY_SHORTLIST_LIMIT]]


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


def compute_buy_score(opportunity: Opportunity, evidence: dict) -> float:
    roi = _as_float(evidence.get("roi"))
    market_speed = _as_float(evidence.get("market_speed_score"))
    confidence = _as_float(evidence.get("confidence_score"))
    risk = _as_float(evidence.get("risk_score"))
    competition = _competition_pressure_value(evidence)
    capital = _as_float(evidence.get("capital_efficiency_score"))

    score = (
        (min(roi / 0.5, 1.0) * 35.0)
        + (market_speed * 3.0)
        + (confidence * 2.0)
        + (capital * 2.0)
        - (risk * 3.0)
        - (competition * 1.8)
    )
    return round(max(score, 0.0), 2)


def rejected_buy_decisions(opportunities: list[Opportunity], limit: int = 10) -> list[tuple[Opportunity, BuyDecision]]:
    rejected: list[tuple[Opportunity, BuyDecision]] = []
    for opportunity in opportunities:
        decision = evaluate_buy_decision(opportunity)
        if not decision.approved:
            rejected.append((opportunity, decision))
        if len(rejected) >= limit:
            break
    return rejected


def _hard_rejection_reason(opportunity: Opportunity, evidence: dict) -> str | None:
    if (opportunity.confidence or "").lower() != "high":
        return "confidence_not_high"

    capital_risk = str(evidence.get("capital_risk") or "").lower()
    if capital_risk in {"high", "very_high"}:
        return f"capital_risk_{capital_risk}"

    if str(evidence.get("speed_category") or "").lower() == "slow":
        return "market_speed_slow"

    competition_pressure = _competition_pressure_value(evidence)
    if competition_pressure >= 10.0:
        return "competition_pressure_high"

    if _as_float(evidence.get("risk_score")) >= 8.0:
        return "risk_score_too_high"

    return None


def _buy_reason(opportunity: Opportunity, evidence: dict, buy_score: float) -> str:
    roi = _as_float(evidence.get("roi"))
    speed = evidence.get("speed_category", "n/d")
    capital = evidence.get("investment_size", "n/d")
    profit = opportunity.profit_estimate or 0.0
    return (
        f"approved: ROI {roi:.2f}, {speed} speed, {capital} capital, "
        f"{profit:.2f}EUR expected profit, buy_score {buy_score:.2f}"
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


def _competition_pressure_value(evidence: dict) -> float:
    value = evidence.get("competition_pressure")
    if isinstance(value, str) and value.lower() == "high":
        return 10.0
    return _as_float(value)


def _as_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
