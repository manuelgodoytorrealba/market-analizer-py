import json
import unittest

from app.models.entities import Opportunity
from app.services.buy_shortlist import build_buy_shortlist, evaluate_buy_decision


class BuyShortlistTests(unittest.TestCase):
    def test_rejects_hard_filter_failures(self) -> None:
        cases = [
            (_opportunity(confidence="medium"), "confidence_not_high"),
            (_opportunity(capital_risk="high"), "capital_risk_high"),
            (_opportunity(speed_category="slow"), "market_speed_slow"),
            (_opportunity(competition_pressure=10.0), "competition_pressure_high"),
            (_opportunity(risk_score=8.0), "risk_score_too_high"),
        ]

        for opportunity, expected_reason in cases:
            decision = evaluate_buy_decision(opportunity)
            self.assertFalse(decision.approved)
            self.assertEqual(decision.reason, expected_reason)

    def test_approves_and_attaches_buy_evidence(self) -> None:
        opportunity = _opportunity(
            title="iPhone 15 128GB",
            roi=0.35,
            market_speed_score=6.5,
            confidence_score=8.5,
            risk_score=2.0,
            competition_pressure=4.0,
            capital_efficiency_score=7.0,
        )

        shortlist = build_buy_shortlist([opportunity])

        self.assertEqual(shortlist, [opportunity])
        evidence = json.loads(shortlist[0].evidence_json)
        self.assertEqual(evidence["buy_decision"], "approved")
        self.assertIn("approved", evidence["buy_reason"])
        self.assertGreater(evidence["buy_score"], 0)

    def test_shortlist_limits_and_sorts_by_buy_score(self) -> None:
        opportunities = [
            _opportunity(title=f"item {index}", roi=0.20 + (index * 0.03), market_speed_score=5.0 + index)
            for index in range(7)
        ]

        shortlist = build_buy_shortlist(opportunities)

        self.assertEqual(len(shortlist), 5)
        buy_scores = [
            json.loads(opportunity.evidence_json)["buy_score"]
            for opportunity in shortlist
        ]
        self.assertEqual(buy_scores, sorted(buy_scores, reverse=True))


def _opportunity(
    *,
    title: str = "Buy candidate",
    confidence: str = "high",
    capital_risk: str = "medium",
    speed_category: str = "medium",
    competition_pressure: float = 4.0,
    risk_score: float = 2.0,
    roi: float = 0.3,
    market_speed_score: float = 6.0,
    confidence_score: float = 8.0,
    capital_efficiency_score: float = 6.0,
) -> Opportunity:
    evidence = {
        "roi": roi,
        "market_speed_score": market_speed_score,
        "speed_category": speed_category,
        "confidence_score": confidence_score,
        "risk_score": risk_score,
        "competition_pressure": competition_pressure,
        "capital_efficiency_score": capital_efficiency_score,
        "capital_risk": capital_risk,
        "investment_size": "medium",
    }
    return Opportunity(
        title=title,
        source="wallapop",
        buy_price=300.0,
        estimated_sale_price=430.0,
        expected_profit=100.0,
        profit_estimate=100.0,
        score=100.0,
        confidence=confidence,
        url="https://example.com",
        evidence_json=json.dumps(evidence),
    )


if __name__ == "__main__":
    unittest.main()
