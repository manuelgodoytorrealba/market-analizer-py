import json
import unittest

from app.models.entities import Listing
from app.services.analyzer import analyze_opportunities, compute_market_speed


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


class AnalyzerV4MarketSpeedTests(unittest.TestCase):
    def test_market_speed_penalizes_saturated_ranges(self) -> None:
        fast_market = [
            _listing(1, "RTX 3070 Gaming OC", 250),
            _listing(2, "RTX 3070 Founders", 310),
            _listing(3, "RTX 3070 Asus", 320),
        ]
        saturated_market = [
            _listing(index, "RTX 3070 Gaming OC", 300 + (index % 3))
            for index in range(1, 18)
        ]

        fast_speed = compute_market_speed(fast_market)
        saturated_speed = compute_market_speed(saturated_market)

        self.assertGreater(fast_speed["score"], saturated_speed["score"])
        self.assertEqual(saturated_speed["speed_category"], "slow")
        self.assertGreater(saturated_speed["competition_density"], 0.8)

    def test_evidence_includes_market_speed_signals(self) -> None:
        listings = [
            _listing(1, "RTX 3070 Gaming OC", 190),
            _listing(2, "RTX 3070 Founders", 280),
            _listing(3, "RTX 3070 Asus", 300),
            _listing(4, "RTX 3070 MSI", 310),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        evidence = json.loads(opportunities[0].evidence_json)
        self.assertIn(opportunities[0].metric_name, {"wallapop_flipping_v4", "wallapop_flipping_v5"})
        self.assertIn("market_speed_score", evidence)
        self.assertIn("competition_density", evidence)
        self.assertIn("speed_category", evidence)
        self.assertIn(evidence["speed_category"], {"fast", "medium", "slow"})


if __name__ == "__main__":
    unittest.main()
