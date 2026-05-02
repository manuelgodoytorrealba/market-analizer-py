import json
import unittest

from app.models.entities import Opportunity
from app.services.decision_engine import build_decision_engine_from_opportunities


class DecisionEngineTests(unittest.TestCase):
    def test_builds_shortlist_buy_plan_and_validation(self) -> None:
        opportunities = [
            _opportunity(
                "MacBook Pro M1 2020 Plata",
                buy_price=420.0,
                profit=87.5,
                roi=0.2083,
                buy_score=34.48,
            ),
            _opportunity(
                "MacBook Pro M1 8GB RAM 256GB",
                buy_price=450.0,
                profit=57.5,
                roi=0.1278,
                buy_score=27.47,
            ),
        ]

        result = build_decision_engine_from_opportunities(
            opportunities,
            capital_available=500.0,
        )

        self.assertEqual(len(result.opportunities), 2)
        self.assertEqual(len(result.shortlist), 2)
        self.assertEqual([item["title"] for item in result.buy_plan.items], ["MacBook Pro M1 2020 Plata"])
        self.assertEqual(result.buy_plan.capital_used_total, 420.0)
        self.assertEqual(len(result.validation), 1)
        self.assertTrue(result.validation[0]["validation"].safe_to_buy)
        self.assertEqual(len(result.capital_rejections), 1)


def _opportunity(
    title: str,
    *,
    buy_price: float,
    profit: float,
    roi: float,
    buy_score: float,
) -> Opportunity:
    evidence = {
        "title": title,
        "description": "Equipo en buen estado con cargador.",
        "buy_score": buy_score,
        "roi": roi,
        "market_speed_score": 5.5,
        "speed_category": "medium",
        "confidence_score": 8.33,
        "risk_score": 2.94,
        "competition_pressure": 7.6,
        "capital_efficiency_score": 4.62,
        "capital_risk": "medium",
        "investment_size": "medium",
    }
    return Opportunity(
        title=title,
        source="wallapop",
        buy_price=buy_price,
        estimated_sale_price=buy_price + profit,
        estimated_resale_price=buy_price + profit,
        expected_profit=profit,
        profit_estimate=profit,
        score=100.0,
        confidence="high",
        url=f"https://example.com/{title.replace(' ', '-').lower()}",
        evidence_json=json.dumps(evidence),
    )


if __name__ == "__main__":
    unittest.main()
