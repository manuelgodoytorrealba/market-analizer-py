import json
import unittest

from app.models.entities import Listing
from app.services.analyzer import (
    analyze_opportunities,
    compute_capital_efficiency,
    roi_score,
)


class AnalyzerV5CapitalEfficiencyTests(unittest.TestCase):
    def test_roi_score_uses_profit_over_buy_price(self) -> None:
        self.assertEqual(roi_score(100.0, 200.0), 0.5)
        self.assertEqual(roi_score(300.0, 2000.0), 0.15)
        self.assertEqual(roi_score(100.0, 0.0), 0.0)

    def test_capital_efficiency_prefers_fast_low_capital_roi(self) -> None:
        efficient = compute_capital_efficiency(
            item_price=200.0,
            profit_estimate=90.0,
            market_speed_score=6.0,
            speed_category="medium",
        )
        inefficient = compute_capital_efficiency(
            item_price=1800.0,
            profit_estimate=250.0,
            market_speed_score=3.0,
            speed_category="slow",
        )

        self.assertGreater(efficient["score"], inefficient["score"])
        self.assertEqual(efficient["capital_risk"], "low")
        self.assertEqual(inefficient["capital_risk"], "very_high")
        self.assertGreater(inefficient["capital_penalty"], 0)

    def test_evidence_includes_capital_efficiency_signals(self) -> None:
        listings = [
            _listing(1, "RTX 3070 Gaming OC", 190),
            _listing(2, "RTX 3070 Founders", 280),
            _listing(3, "RTX 3070 Asus", 300),
            _listing(4, "RTX 3070 MSI", 310),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        evidence = json.loads(opportunities[0].evidence_json)
        self.assertEqual(opportunities[0].metric_name, "wallapop_flipping_v5")
        self.assertIn("roi", evidence)
        self.assertIn("capital_efficiency_score", evidence)
        self.assertIn("investment_size", evidence)
        self.assertIn("capital_risk", evidence)


def _listing(index: int, title: str, price: float) -> Listing:
    return Listing(
        id=index,
        source="wallapop",
        external_id=str(index),
        title=title,
        normalized_name="rtx 3070",
        search_query="rtx 3070",
        price=price,
        shipping_cost=7.0,
        url=f"https://example.com/{index}",
        is_active=True,
    )


if __name__ == "__main__":
    unittest.main()
