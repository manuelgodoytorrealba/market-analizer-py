import json
from dataclasses import dataclass

from app.core.config import get_settings
from app.models.entities import Opportunity

MAX_SINGLE_ITEM_CAPITAL_RATIO = 0.5
HIGH_CONVICTION_MIN_ROI = 0.20
HIGH_CONVICTION_MAX_RISK = 4.0
HIGH_CONVICTION_BLOCK_RISK = 6.0


@dataclass(frozen=True)
class CapitalPlan:
    capital_available: float
    capital_used_total: float
    capital_remaining: float
    expected_profit_total: float
    roi_total: float
    items: list[dict]


def build_buy_plan(shortlist: list[Opportunity], capital_available: float) -> CapitalPlan:
    capital_available = max(float(capital_available or 0.0), 0.0)
    remaining = capital_available
    items: list[dict] = []
    high_conviction_buy_score = get_settings().capital_strategy_high_conviction_buy_score
    high_conviction_max_ratio = get_settings().capital_strategy_high_conviction_max_ratio

    candidates = sorted(
        shortlist,
        key=lambda opportunity: (
            _as_float(_load_evidence(opportunity.evidence_json).get("buy_score")),
            _as_float(_load_evidence(opportunity.evidence_json).get("roi")),
            -_as_float(opportunity.buy_price),
        ),
        reverse=True,
    )

    for opportunity in candidates:
        evidence = _load_evidence(opportunity.evidence_json)
        buy_price = _as_float(opportunity.buy_price)
        conviction = _evaluate_high_conviction(opportunity, evidence, high_conviction_buy_score)
        max_ratio = high_conviction_max_ratio if conviction["high_conviction"] else MAX_SINGLE_ITEM_CAPITAL_RATIO
        max_item_capital = capital_available * max_ratio

        if buy_price <= 0:
            continue
        if buy_price > max_item_capital:
            continue
        if buy_price > remaining:
            continue

        item = _build_plan_item(
            opportunity=opportunity,
            capital_available=capital_available,
            capital_used=buy_price,
            priority=len(items) + 1,
            conviction=conviction,
        )
        _attach_investment_evidence(opportunity, item)
        items.append(item)
        remaining -= buy_price

    capital_used_total = round(sum(item["capital_used"] for item in items), 2)
    expected_profit_total = round(sum(item["expected_profit"] for item in items), 2)
    roi_total = round(expected_profit_total / capital_used_total, 4) if capital_used_total > 0 else 0.0

    return CapitalPlan(
        capital_available=round(capital_available, 2),
        capital_used_total=capital_used_total,
        capital_remaining=round(capital_available - capital_used_total, 2),
        expected_profit_total=expected_profit_total,
        roi_total=roi_total,
        items=items,
    )


def explain_capital_rejections(shortlist: list[Opportunity], capital_available: float) -> list[dict]:
    capital_available = max(float(capital_available or 0.0), 0.0)
    high_conviction_buy_score = get_settings().capital_strategy_high_conviction_buy_score
    high_conviction_max_ratio = get_settings().capital_strategy_high_conviction_max_ratio
    rejections: list[dict] = []

    for opportunity in shortlist:
        evidence = _load_evidence(opportunity.evidence_json)
        conviction = _evaluate_high_conviction(opportunity, evidence, high_conviction_buy_score)
        max_ratio = high_conviction_max_ratio if conviction["high_conviction"] else MAX_SINGLE_ITEM_CAPITAL_RATIO
        max_item_capital = capital_available * max_ratio
        buy_price = _as_float(opportunity.buy_price)
        if buy_price <= 0:
            reason = "invalid_buy_price"
        elif buy_price > max_item_capital:
            reason = "exceeds_single_item_cap"
        else:
            reason = "eligible"

        if reason != "eligible":
            rejections.append(
                {
                    "title": opportunity.title,
                    "buy_price": buy_price,
                    "reason": reason,
                    "max_single_item_capital": round(max_item_capital, 2),
                    "high_conviction": conviction["high_conviction"],
                    "capital_rule_override": conviction["capital_rule_override"],
                    "override_reason": conviction["override_reason"],
                }
            )

    return rejections


def _build_plan_item(
    *,
    opportunity: Opportunity,
    capital_available: float,
    capital_used: float,
    priority: int,
    conviction: dict,
) -> dict:
    evidence = _load_evidence(opportunity.evidence_json)
    roi = _as_float(evidence.get("roi"))
    expected_profit = _as_float(opportunity.profit_estimate)
    capital_allocation = capital_used / capital_available if capital_available > 0 else 0.0
    label = "high conviction buy" if conviction["high_conviction"] else "buy"
    reason = (
        f"{label}: {capital_allocation:.0%} of capital, ROI {roi:.2f}, "
        f"{expected_profit:.2f}EUR expected profit"
    )

    return {
        "title": opportunity.title,
        "buy_price": round(capital_used, 2),
        "units": 1,
        "capital_used": round(capital_used, 2),
        "expected_profit": round(expected_profit, 2),
        "roi": round(roi, 4),
        "priority": priority,
        "url": opportunity.url,
        "investment_decision": "buy",
        "investment_reason": reason,
        "capital_allocation": round(capital_allocation, 4),
        "buy_score": _as_float(evidence.get("buy_score")),
        "high_conviction": conviction["high_conviction"],
        "capital_rule_override": conviction["capital_rule_override"],
        "override_reason": conviction["override_reason"],
    }


def _attach_investment_evidence(opportunity: Opportunity, item: dict) -> None:
    evidence = _load_evidence(opportunity.evidence_json)
    evidence["investment_decision"] = item["investment_decision"]
    evidence["investment_reason"] = item["investment_reason"]
    evidence["capital_allocation"] = item["capital_allocation"]
    evidence["high_conviction"] = item["high_conviction"]
    evidence["capital_rule_override"] = item["capital_rule_override"]
    evidence["override_reason"] = item["override_reason"]
    opportunity.evidence_json = json.dumps(evidence)


def _evaluate_high_conviction(opportunity: Opportunity, evidence: dict, buy_score_threshold: float) -> dict:
    confidence = (opportunity.confidence or "").lower()
    risk_score = _as_float(evidence.get("risk_score"))
    speed_category = str(evidence.get("speed_category") or "").lower()
    roi = _as_float(evidence.get("roi"))
    buy_score = _as_float(evidence.get("buy_score"))

    high_conviction = (
        confidence == "high"
        and risk_score <= HIGH_CONVICTION_MAX_RISK
        and risk_score < HIGH_CONVICTION_BLOCK_RISK
        and speed_category != "slow"
        and roi >= HIGH_CONVICTION_MIN_ROI
        and buy_score >= buy_score_threshold
    )

    if high_conviction:
        return {
            "high_conviction": True,
            "capital_rule_override": True,
            "override_reason": (
                f"high conviction: confidence high, risk {risk_score:.2f}, "
                f"speed {speed_category or 'n/d'}, ROI {roi:.2f}, buy_score {buy_score:.2f}"
            ),
        }

    return {
        "high_conviction": False,
        "capital_rule_override": False,
        "override_reason": "",
    }


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
