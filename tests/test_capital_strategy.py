import json
import unittest

from app.models.entities import Opportunity
from app.services.capital_strategy import build_buy_plan, explain_capital_rejections


class CapitalStrategyTests(unittest.TestCase):
    def test_builds_plan_with_capital_limit_and_priority(self) -> None:
        opportunities = [
            _opportunity("low priority", buy_price=200.0, profit=60.0, roi=0.30, buy_score=20.0),
            _opportunity("best fit", buy_price=240.0, profit=90.0, roi=0.375, buy_score=40.0),
            _opportunity("too expensive", buy_price=300.0, profit=120.0, roi=0.40, buy_score=80.0, risk_score=6.0),
        ]

        plan = build_buy_plan(opportunities, capital_available=500.0)

        self.assertEqual([item["title"] for item in plan.items], ["best fit", "low priority"])
        self.assertEqual(plan.capital_used_total, 440.0)
        self.assertEqual(plan.capital_remaining, 60.0)
        self.assertEqual(plan.expected_profit_total, 150.0)
        self.assertAlmostEqual(plan.roi_total, 0.3409)

    def test_high_conviction_overrides_single_item_cap(self) -> None:
        opportunities = [
            _opportunity("MacBook Pro M1", buy_price=420.0, profit=87.5, roi=0.2083, buy_score=34.48),
            _opportunity("MacBook Pro M1 8GB", buy_price=450.0, profit=57.5, roi=0.1278, buy_score=27.47),
        ]

        plan = build_buy_plan(opportunities, capital_available=500.0)
        rejections = explain_capital_rejections(opportunities, capital_available=500.0)

        self.assertEqual([item["title"] for item in plan.items], ["MacBook Pro M1"])
        self.assertEqual(plan.capital_used_total, 420.0)
        self.assertEqual(plan.capital_remaining, 80.0)
        self.assertTrue(plan.items[0]["high_conviction"])
        self.assertTrue(plan.items[0]["capital_rule_override"])
        self.assertEqual(rejections[0]["title"], "MacBook Pro M1 8GB")
        self.assertFalse(rejections[0]["high_conviction"])

    def test_high_conviction_does_not_override_unsafe_risk_or_confidence(self) -> None:
        opportunities = [
            _opportunity("risky", buy_price=420.0, profit=120.0, roi=0.2857, buy_score=60.0, risk_score=6.0),
            _opportunity("medium confidence", buy_price=420.0, profit=120.0, roi=0.2857, buy_score=60.0, confidence="medium"),
        ]

        plan = build_buy_plan(opportunities, capital_available=500.0)
        rejections = explain_capital_rejections(opportunities, capital_available=500.0)

        self.assertEqual(plan.items, [])
        self.assertEqual({rejection["reason"] for rejection in rejections}, {"exceeds_single_item_cap"})
        self.assertFalse(any(rejection["high_conviction"] for rejection in rejections))

    def test_attaches_investment_evidence_to_selected_items(self) -> None:
        opportunity = _opportunity("iPhone 15", buy_price=220.0, profit=80.0, roi=0.3636, buy_score=50.0)

        plan = build_buy_plan([opportunity], capital_available=500.0)

        self.assertEqual(len(plan.items), 1)
        evidence = json.loads(opportunity.evidence_json)
        self.assertEqual(evidence["investment_decision"], "buy")
        self.assertIn("buy:", evidence["investment_reason"])
        self.assertEqual(evidence["capital_allocation"], 0.44)
        self.assertTrue(evidence["high_conviction"])
        self.assertTrue(evidence["capital_rule_override"])


def _opportunity(
    title: str,
    *,
    buy_price: float,
    profit: float,
    roi: float,
    buy_score: float,
    risk_score: float = 2.0,
    confidence: str = "high",
) -> Opportunity:
    evidence = {
        "buy_score": buy_score,
        "roi": roi,
        "market_speed_score": 6.0,
        "speed_category": "medium",
        "risk_score": risk_score,
    }
    return Opportunity(
        title=title,
        source="wallapop",
        buy_price=buy_price,
        estimated_sale_price=buy_price + profit,
        expected_profit=profit,
        profit_estimate=profit,
        score=100.0,
        confidence=confidence,
        url="https://example.com",
        evidence_json=json.dumps(evidence),
    )


if __name__ == "__main__":
    unittest.main()
