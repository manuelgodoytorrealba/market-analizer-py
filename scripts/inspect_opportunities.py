import json
import sys
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

VENV_PYTHON = ROOT_DIR / ".venv" / "bin" / "python"
if VENV_PYTHON.exists() and Path(sys.prefix).resolve() != (ROOT_DIR / ".venv").resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])

from app.db.session import SessionLocal
from app.core.config import get_settings
from app.models.entities import Opportunity
from app.services.buy_shortlist import build_buy_shortlist, rejected_buy_decisions
from app.services.capital_strategy import build_buy_plan, explain_capital_rejections
from app.services.deal_validator import validate_deal


def _format_eur(value: float | None) -> str:
    if value is None:
        return "n/d"
    return f"{value:.2f}EUR"


def main() -> int:
    db = SessionLocal()
    try:
        opportunities = (
            db.query(Opportunity)
            .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
            .all()
        )

        print("--- TOP OPPORTUNITIES (ALL)")
        print()

        if not opportunities:
            print("No opportunities found.")
            return 0

        _print_opportunities(opportunities[:10])

        print("--- BUY SHORTLIST (REAL DECISIONS)")
        print()
        shortlist = build_buy_shortlist(opportunities)
        if shortlist:
            _print_opportunities(shortlist, include_buy=True)
        else:
            print("No approved buy decisions found.")
            print()

        capital_available = get_settings().capital_strategy_available
        buy_plan = build_buy_plan(shortlist, capital_available)
        _print_buy_plan(buy_plan, explain_capital_rejections(shortlist, capital_available))
        _print_deal_validation(shortlist, buy_plan)

        print("--- DISCARDED FROM BUY SHORTLIST")
        print()
        for index, (opportunity, decision) in enumerate(
            rejected_buy_decisions(opportunities, limit=10),
            start=1,
        ):
            evidence = decision.evidence
            print(f"{index}. {opportunity.title}")
            print(f"   Rejected: {decision.reason}")
            print(f"   Confidence: {opportunity.confidence or 'n/d'} | Risk: {evidence.get('risk_score', 'n/d')} | Speed: {evidence.get('speed_category', 'n/d')} | Capital risk: {evidence.get('capital_risk', 'n/d')}")
            print()
    finally:
        db.close()

    return 0


def _load_evidence(evidence_json: str | None) -> dict:
    if not evidence_json:
        return {}
    try:
        data = json.loads(evidence_json)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _print_opportunities(opportunities: list[Opportunity], include_buy: bool = False) -> None:
    for index, opportunity in enumerate(opportunities, start=1):
        evidence = _load_evidence(opportunity.evidence_json)
        print(f"{index}. {opportunity.title}")
        print(f"   Category: {evidence.get('category', 'unknown')}")
        print(f"   Speed: {evidence.get('speed_category', 'n/d')} ({evidence.get('market_speed_score', 'n/d')})")
        print(f"   ROI: {evidence.get('roi', 'n/d')} | Capital: {evidence.get('capital_efficiency_score', 'n/d')} ({evidence.get('investment_size', 'n/d')})")
        if include_buy:
            print(f"   Buy score: {evidence.get('buy_score', 'n/d')}")
            print(f"   Buy reason: {evidence.get('buy_reason', 'n/d')}")
        print(f"   Buy: {_format_eur(opportunity.buy_price)}")
        print(f"   Ref: {_format_eur(opportunity.estimated_resale_price)}")
        print(f"   Profit: {_format_eur(opportunity.profit_estimate)}")
        print(f"   Score: {opportunity.score:.2f}")
        print(f"   Confidence: {opportunity.confidence or 'n/d'}")
        print(f"   URL: {opportunity.url}")
        print(f"   Reason: {opportunity.reasoning_summary or 'n/d'}")
        print()


def _print_buy_plan(buy_plan, capital_rejections: list[dict]) -> None:
    print(f"--- BUY PLAN (CAPITAL {buy_plan.capital_available:.0f}EUR)")
    print()

    if buy_plan.items:
        for item in buy_plan.items:
            print(f"{item['priority']}. {item['title']}")
            print(f"   Buy: {_format_eur(item['buy_price'])}")
            print(f"   Units: {item['units']}")
            print(f"   Capital used: {_format_eur(item['capital_used'])} ({item['capital_allocation']:.0%})")
            print(f"   Expected profit: {_format_eur(item['expected_profit'])}")
            print(f"   ROI: {item['roi']:.2f}")
            if item.get("high_conviction"):
                print("   HIGH CONVICTION BUY")
                print(f"   Override: {item.get('override_reason', 'n/d')}")
            print(f"   URL: {item['url']}")
            print(f"   Reason: {item['investment_reason']}")
            print()
    else:
        print("No buy fits the current capital rules.")
        print()

    print(f"Capital used total: {_format_eur(buy_plan.capital_used_total)}")
    print(f"Expected profit total: {_format_eur(buy_plan.expected_profit_total)}")
    print(f"Capital remaining: {_format_eur(buy_plan.capital_remaining)}")
    print(f"Portfolio ROI: {buy_plan.roi_total:.2f}")
    print()

    if capital_rejections:
        print("Skipped by capital strategy:")
        for rejection in capital_rejections[:5]:
            print(
                f"- {rejection['title']} | Buy: {_format_eur(rejection['buy_price'])} | "
                f"Reason: {rejection['reason']} | Max item: {_format_eur(rejection['max_single_item_capital'])} | "
                f"High conviction: {rejection['high_conviction']}"
            )
        print()


def _print_deal_validation(shortlist: list[Opportunity], buy_plan) -> None:
    print("--- DEAL VALIDATION")
    print()

    if not buy_plan.items:
        print("No buy plan items to validate.")
        print()
        return

    opportunities_by_url = {opportunity.url: opportunity for opportunity in shortlist}
    for item in buy_plan.items:
        opportunity = opportunities_by_url.get(item["url"])
        if opportunity is None:
            continue

        validation = validate_deal(opportunity)
        print(f"{item['priority']}. {opportunity.title}")
        print(f"   Safe to buy: {validation.safe_to_buy}")
        print(f"   Manual confidence: {validation.confidence_manual}")
        if validation.warnings:
            print(f"   Warnings: {', '.join(validation.warnings)}")
        else:
            print("   Warnings: none")
        print(f"   Notes: {validation.notes}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
