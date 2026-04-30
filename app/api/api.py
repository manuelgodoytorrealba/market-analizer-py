import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter

from app.models.entities import Opportunity
from app.services.decision_engine import build_decision_engine

router = APIRouter()


@router.get("/decision-engine")
def decision_engine_endpoint() -> dict[str, Any]:
    result = build_decision_engine()
    buy_plan = result.buy_plan

    return {
        "opportunities": [_serialize_opportunity(opportunity) for opportunity in result.opportunities],
        "shortlist": [_serialize_opportunity(opportunity) for opportunity in result.shortlist],
        "buy_plan": buy_plan.items,
        "validation": [_serialize_validation(item) for item in result.validation],
        "summary": {
            "capital_available": buy_plan.capital_available,
            "capital_used": buy_plan.capital_used_total,
            "capital_remaining": buy_plan.capital_remaining,
            "expected_profit": buy_plan.expected_profit_total,
            "roi_total": buy_plan.roi_total,
        },
    }


def _serialize_opportunity(opportunity: Opportunity) -> dict[str, Any]:
    return {
        "id": opportunity.id,
        "title": opportunity.title,
        "source": opportunity.source,
        "listing_id": opportunity.listing_id,
        "normalized_name": opportunity.normalized_name,
        "search_query": opportunity.search_query,
        "opportunity_type": opportunity.opportunity_type,
        "buy_price": opportunity.buy_price,
        "estimated_resale_price": opportunity.estimated_resale_price,
        "profit_estimate": opportunity.profit_estimate,
        "discount_pct": opportunity.discount_pct,
        "comparable_count": opportunity.comparable_count,
        "confidence": opportunity.confidence,
        "score": opportunity.score,
        "url": opportunity.url,
        "reasoning_summary": opportunity.reasoning_summary,
        "manual_decision": opportunity.manual_decision,
        "created_at": _serialize_value(opportunity.created_at),
        "evidence": _load_evidence(opportunity.evidence_json),
    }


def _serialize_validation(item: dict) -> dict[str, Any]:
    opportunity = item.get("opportunity")
    validation = item.get("validation")

    return {
        "opportunity": _serialize_opportunity(opportunity) if opportunity is not None else None,
        "validation": _serialize_value(validation),
    }


def _load_evidence(evidence_json: str | None) -> dict[str, Any]:
    if not evidence_json:
        return {}
    try:
        data = json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _serialize_value(value: Any) -> Any:
    if is_dataclass(value):
        return {
            key: _serialize_value(item)
            for key, item in asdict(value).items()
        }
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _serialize_value(item)
            for key, item in value.items()
        }
    return value
