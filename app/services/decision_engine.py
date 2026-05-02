from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import Opportunity
from app.services.buy_shortlist import build_buy_shortlist, rejected_buy_decisions
from app.services.capital_strategy import build_buy_plan, explain_capital_rejections
from app.services.deal_validator import validate_deal


@dataclass(frozen=True)
class DecisionEngineResult:
    opportunities: list[Opportunity]
    shortlist: list[Opportunity]
    buy_plan: object
    validation: list[dict]
    shortlist_rejections: list[dict]
    capital_rejections: list[dict]


def build_decision_engine(
    db: Session | None = None,
    *,
    capital_available: float | None = None,
) -> DecisionEngineResult:
    owns_session = db is None
    session = db or SessionLocal()

    try:
        opportunities = (
            session.query(Opportunity)
            .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
            .all()
        )

        return build_decision_engine_from_opportunities(
            opportunities,
            capital_available=capital_available,
        )

    finally:
        if owns_session:
            session.close()


def build_decision_engine_from_opportunities(
    opportunities: list[Opportunity],
    *,
    capital_available: float | None = None,
) -> DecisionEngineResult:
    settings = get_settings()

    capital = (
        settings.capital_strategy_available
        if capital_available is None
        else capital_available
    )

    shortlist = build_buy_shortlist(opportunities)
    buy_plan = build_buy_plan(shortlist, capital)

    planned_opportunities = _opportunities_for_buy_plan(shortlist, buy_plan)

    validation = [
        {
            "opportunity": opportunity,
            "validation": validate_deal(opportunity),
        }
        for opportunity in planned_opportunities
    ]

    shortlist_rejections = [
        {
            "opportunity": opportunity,
            "decision": decision,
        }
        for opportunity, decision in rejected_buy_decisions(opportunities, limit=20)
    ]

    capital_rejections = explain_capital_rejections(shortlist, capital)

    return DecisionEngineResult(
        opportunities=opportunities,
        shortlist=shortlist,
        buy_plan=buy_plan,
        validation=validation,
        shortlist_rejections=shortlist_rejections,
        capital_rejections=capital_rejections,
    )


def _opportunities_for_buy_plan(
    shortlist: list[Opportunity],
    buy_plan,
) -> list[Opportunity]:
    if not buy_plan or not getattr(buy_plan, "items", None):
        return []

    urls_in_plan = {item.get("url") for item in buy_plan.items if item.get("url")}

    return [opportunity for opportunity in shortlist if opportunity.url in urls_in_plan]
