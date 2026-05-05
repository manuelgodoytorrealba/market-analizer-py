import unittest

from app.models.entities import Listing
from app.services.analyzer import build_market_stats
from app.services.semantic_classifier import classify_listing_semantics


class SemanticClassifierTests(unittest.TestCase):
    def test_classifier_marks_controller_as_not_target_console(self) -> None:
        item = Listing(
            source="wallapop",
            external_id="1",
            title="Mando de PS5",
            normalized_name="ps5",
            price=40.0,
            url="https://example.com/1",
            is_active=True,
        )

        semantic = classify_listing_semantics(item)

        self.assertFalse(semantic.is_target_match)
        self.assertFalse(semantic.is_safe_listing)
        self.assertEqual(semantic.reason, "accessory_only")

    def test_market_stats_include_mean_and_mode_bucket(self) -> None:
        stats = build_market_stats([100.0, 110.0, 110.0, 120.0, 150.0])

        self.assertIsNotNone(stats)
        self.assertEqual(stats.mean_price, 110.0)
        self.assertEqual(stats.median_price, 110.0)
        self.assertEqual(stats.mode_price, 110.0)
        self.assertEqual(stats.mode_count, 2)


if __name__ == "__main__":
    unittest.main()
