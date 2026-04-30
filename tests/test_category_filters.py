import json
import unittest

from app.models.entities import Listing
from app.services.analyzer import analyze_opportunities
from app.services.category_filters import evaluate_category_listing


class CategoryFilterTests(unittest.TestCase):
    def test_blocks_category_specific_parts_and_repairs(self) -> None:
        cases = [
            (
                Listing(
                    title="Pantalla MacBook Pro M1 gris espacial",
                    normalized_name="macbook pro m1",
                    search_query="macbook pro m1",
                    price=120,
                    source="wallapop",
                    external_id="1",
                    url="https://example.com/1",
                ),
                "blocked_screen_only",
            ),
            (
                Listing(
                    title="Sony a7 III para reparar",
                    normalized_name="sony a7 iii",
                    search_query="sony a7 iii",
                    price=250,
                    source="wallapop",
                    external_id="2",
                    url="https://example.com/2",
                ),
                "blocked_for_repair",
            ),
            (
                Listing(
                    title="RTX 3070 no da video",
                    normalized_name="rtx 3070",
                    search_query="rtx 3070",
                    price=90,
                    source="wallapop",
                    external_id="3",
                    url="https://example.com/3",
                ),
                "blocked_no_video",
            ),
        ]

        for listing, reason in cases:
            result = evaluate_category_listing(listing)
            self.assertFalse(result.is_valid)
            self.assertEqual(result.category_filter_reason, reason)

    def test_risk_flags_do_not_block_valid_category_listing(self) -> None:
        listing = Listing(
            title="Sony A7 III solo cuerpo con pequeno golpe",
            normalized_name="sony a7 iii",
            search_query="sony a7 iii",
            price=850,
            source="wallapop",
            external_id="4",
            url="https://example.com/4",
        )

        result = evaluate_category_listing(listing)

        self.assertTrue(result.is_valid)
        self.assertIn("solo_cuerpo", result.category_risk_flags)
        self.assertIn("pequeno_golpe", result.category_risk_flags)
        self.assertGreater(result.risk_score_boost, 0)

    def test_analyzer_filters_blocked_listing_and_exposes_category_risk_evidence(self) -> None:
        listings = [
            Listing(
                id=1,
                title="Sony A7 III para reparar",
                normalized_name="sony a7 iii",
                search_query="sony a7 iii",
                price=300,
                shipping_cost=7,
                source="wallapop",
                external_id="1",
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                id=2,
                title="Sony A7 III solo cuerpo pequeno golpe",
                normalized_name="sony a7 iii",
                search_query="sony a7 iii",
                price=700,
                shipping_cost=7,
                source="wallapop",
                external_id="2",
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                id=3,
                title="Sony A7 III camara mirrorless",
                normalized_name="sony a7 iii",
                search_query="sony a7 iii",
                price=900,
                shipping_cost=7,
                source="wallapop",
                external_id="3",
                url="https://example.com/3",
                is_active=True,
            ),
            Listing(
                id=4,
                title="Sony A7 III camara",
                normalized_name="sony a7 iii",
                search_query="sony a7 iii",
                price=920,
                shipping_cost=7,
                source="wallapop",
                external_id="4",
                url="https://example.com/4",
                is_active=True,
            ),
            Listing(
                id=5,
                title="Sony A7 III full frame",
                normalized_name="sony a7 iii",
                search_query="sony a7 iii",
                price=940,
                shipping_cost=7,
                source="wallapop",
                external_id="5",
                url="https://example.com/5",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        self.assertNotEqual(opportunities[0].source_listing_id, 1)
        evidence = json.loads(opportunities[0].evidence_json)
        self.assertIsNone(evidence["category_filter_reason"])
        self.assertIn("solo_cuerpo", evidence["category_risk_flags"])
        self.assertGreater(evidence["category_risk_score_boost"], 0)


if __name__ == "__main__":
    unittest.main()
