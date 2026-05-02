import json
import unittest

from app.models.entities import Listing
from app.services.analyzer import (
    ARBITRAGE_OPPORTUNITY_TYPE,
    GENERIC_OPPORTUNITY_TYPE,
    WALLAPOP_MARKET_OPPORTUNITY_TYPE,
    analyze_opportunities,
)
from app.services.normalizer import extract_iphone_specs


class AnalyzerTests(unittest.TestCase):
    def test_normalizer_extracts_model_capacity_and_condition(self) -> None:
        specs = extract_iphone_specs(
            "Apple iPhone 13 Pro 256GB refurbished libre",
            fallback_query="iphone 13 pro 256gb",
        )

        self.assertIsNotNone(specs)
        self.assertEqual(specs["model"], "iphone 13 pro")
        self.assertEqual(specs["capacity"], "256gb")
        self.assertEqual(specs["condition"], "refurb")

    def test_normalizer_rejects_iphone_11_even_with_iphone_13_query(self) -> None:
        specs = extract_iphone_specs(
            "iPhone 11 blanco 128GB",
            fallback_query="iphone 13 128gb",
        )

        self.assertIsNone(specs)

    def test_normalizer_extracts_supported_generations_without_mixing(self) -> None:
        specs = extract_iphone_specs(
            "Apple iPhone 14 Pro 128GB usado",
            fallback_query="iphone 14 pro 128gb",
        )

        self.assertIsNotNone(specs)
        self.assertEqual(specs["model"], "iphone 14 pro")
        self.assertEqual(specs["capacity"], "128gb")

    def test_normalizer_rejects_mini_and_pro_max_variants(self) -> None:
        self.assertIsNone(
            extract_iphone_specs(
                "iPhone 12 mini 128GB",
                fallback_query="iphone 12 128gb",
            )
        )
        self.assertIsNone(
            extract_iphone_specs(
                "iPhone 14 Pro Max 256GB",
                fallback_query="iphone 14 pro 256gb",
            )
        )

    def test_analyzer_finds_profitable_listing_for_same_model_and_capacity(self) -> None:
        listings = [
            Listing(
                source="ebay",
                external_id="1",
                title="iPhone 13 128GB usado",
                normalized_name="iphone 13 128gb",
                price=430.0,
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="2",
                title="iPhone 13 128GB azul usado",
                normalized_name="iphone 13 128gb",
                price=610.0,
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3",
                title="iPhone 13 128GB libre",
                normalized_name="iphone 13 128gb",
                price=640.0,
                url="https://example.com/3",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].buy_price, 430.0)
        self.assertGreater(opportunities[0].profit_estimate, 20.0)
        self.assertEqual(opportunities[0].estimated_resale_price, 610.0)
        self.assertEqual(opportunities[0].opportunity_type, GENERIC_OPPORTUNITY_TYPE)

    def test_analyzer_does_not_mix_different_models_or_capacities(self) -> None:
        listings = [
            Listing(
                source="ebay",
                external_id="1",
                title="iPhone 13 128GB azul",
                normalized_name="iphone 13 128gb",
                price=430.0,
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="2",
                title="iPhone 13 Pro 128GB azul",
                normalized_name="iphone 13 pro 128gb",
                price=700.0,
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3",
                title="iPhone 13 256GB rojo",
                normalized_name="iphone 13 256gb",
                price=750.0,
                url="https://example.com/3",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="4",
                title="iPhone 13 128GB negro",
                normalized_name="iphone 13 128gb",
                price=610.0,
                url="https://example.com/4",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="5",
                title="iPhone 13 128GB blanco",
                normalized_name="iphone 13 128gb",
                price=640.0,
                url="https://example.com/5",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].normalized_name, "iphone 13 128gb")

    def test_analyzer_supports_iphone_12_and_14_families(self) -> None:
        listings = [
            Listing(
                source="wallapop",
                external_id="1",
                title="iPhone 12 Pro 256GB usado",
                normalized_name="iphone 12 pro 256gb",
                price=430.0,
                shipping_cost=7.0,
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="2",
                title="iPhone 12 Pro 256GB gris",
                normalized_name="iphone 12 pro 256gb",
                price=620.0,
                shipping_cost=12.5,
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3",
                title="iPhone 12 Pro 256GB azul",
                normalized_name="iphone 12 pro 256gb",
                price=640.0,
                shipping_cost=12.5,
                url="https://example.com/3",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3b",
                title="iPhone 12 Pro 256GB plata",
                normalized_name="iphone 12 pro 256gb",
                price=650.0,
                shipping_cost=12.5,
                url="https://example.com/3b",
                is_active=True,
            ),
            Listing(
                source="wallapop",
                external_id="4",
                title="iPhone 14 128GB usado",
                normalized_name="iphone 14 128gb",
                price=520.0,
                shipping_cost=7.0,
                url="https://example.com/4",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="5",
                title="iPhone 14 128GB azul",
                normalized_name="iphone 14 128gb",
                price=710.0,
                shipping_cost=12.5,
                url="https://example.com/5",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="6",
                title="iPhone 14 128GB negro",
                normalized_name="iphone 14 128gb",
                price=760.0,
                shipping_cost=12.5,
                url="https://example.com/6",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="7",
                title="iPhone 14 128GB blanco",
                normalized_name="iphone 14 128gb",
                price=740.0,
                shipping_cost=12.5,
                url="https://example.com/7",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 2)
        self.assertEqual(
            sorted(opportunity.normalized_name for opportunity in opportunities),
            ["iphone 12 pro 256gb", "iphone 14 128gb"],
        )
        arbitrage_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.opportunity_type == ARBITRAGE_OPPORTUNITY_TYPE
        ]
        self.assertEqual(len(arbitrage_opportunities), 2)
        self.assertEqual(
            sorted(opportunity.source for opportunity in arbitrage_opportunities),
            ["wallapop", "wallapop"],
        )
        self.assertTrue(all(opportunity.liquidity_count == 3 for opportunity in arbitrage_opportunities))

    def test_analyzer_generates_wallapop_to_ebay_arbitrage(self) -> None:
        listings = [
            Listing(
                id=11,
                source="wallapop",
                external_id="w1",
                title="iPhone 13 Pro 128GB usado",
                normalized_name="iphone 13 pro 128gb",
                price=420.0,
                shipping_cost=7.0,
                url="https://example.com/w1",
                is_active=True,
            ),
            Listing(
                id=21,
                source="ebay",
                external_id="e1",
                title="iPhone 13 Pro 128GB graphite",
                normalized_name="iphone 13 pro 128gb",
                price=650.0,
                shipping_cost=12.5,
                url="https://example.com/e1",
                is_active=True,
            ),
            Listing(
                id=22,
                source="ebay",
                external_id="e2",
                title="iPhone 13 Pro 128GB sierra blue",
                normalized_name="iphone 13 pro 128gb",
                price=680.0,
                shipping_cost=12.5,
                url="https://example.com/e2",
                is_active=True,
            ),
            Listing(
                id=23,
                source="ebay",
                external_id="e3",
                title="iPhone 13 Pro 128GB silver",
                normalized_name="iphone 13 pro 128gb",
                price=700.0,
                shipping_cost=12.5,
                url="https://example.com/e3",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)
        arbitrage_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.opportunity_type == ARBITRAGE_OPPORTUNITY_TYPE
        ]

        self.assertEqual(len(arbitrage_opportunities), 1)
        opportunity = arbitrage_opportunities[0]
        self.assertEqual(opportunity.source, "wallapop")
        self.assertEqual(opportunity.source_listing_id, 11)
        self.assertEqual(opportunity.comparable_count, 3)
        self.assertEqual(opportunity.liquidity_count, 3)
        self.assertEqual(opportunity.estimated_resale_price, 680.0)
        self.assertGreater(opportunity.profit_estimate, 20.0)

    def test_analyzer_generates_wallapop_market_gap_without_ebay(self) -> None:
        listings = [
            Listing(
                id=101,
                source="wallapop",
                external_id="w101",
                title="iPhone 13 128GB azul",
                normalized_name="iphone 13 128gb",
                price=165.0,
                shipping_cost=7.0,
                url="https://example.com/w101",
                is_active=True,
            ),
            Listing(
                id=102,
                source="wallapop",
                external_id="w102",
                title="iPhone 13 128GB negro",
                normalized_name="iphone 13 128gb",
                price=250.0,
                shipping_cost=7.0,
                url="https://example.com/w102",
                is_active=True,
            ),
            Listing(
                id=103,
                source="wallapop",
                external_id="w103",
                title="iPhone 13 128GB blanco",
                normalized_name="iphone 13 128gb",
                price=260.0,
                shipping_cost=7.0,
                url="https://example.com/w103",
                is_active=True,
            ),
            Listing(
                id=104,
                source="wallapop",
                external_id="w104",
                title="iPhone 13 128GB rojo",
                normalized_name="iphone 13 128gb",
                price=255.0,
                shipping_cost=7.0,
                url="https://example.com/w104",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)
        wallapop_opportunities = [
            opportunity
            for opportunity in opportunities
            if opportunity.opportunity_type == WALLAPOP_MARKET_OPPORTUNITY_TYPE
        ]

        self.assertEqual(len(wallapop_opportunities), 1)
        opportunity = wallapop_opportunities[0]
        self.assertEqual(opportunity.source, "wallapop")
        self.assertEqual(opportunity.source_listing_id, 101)
        self.assertEqual(opportunity.comparable_count, 3)
        self.assertEqual(opportunity.estimated_resale_price, 255.0)
        self.assertGreater(opportunity.profit_estimate, 20.0)

    def test_analyzer_filters_extreme_underprice_as_too_risky(self) -> None:
        listings = [
            Listing(
                id=201,
                source="wallapop",
                external_id="w201",
                title="iPhone 13 128GB urgente",
                normalized_name="iphone 13 128gb",
                price=100.0,
                shipping_cost=7.0,
                url="https://example.com/w201",
                is_active=True,
            ),
            Listing(
                id=202,
                source="wallapop",
                external_id="w202",
                title="iPhone 13 128GB negro",
                normalized_name="iphone 13 128gb",
                price=250.0,
                shipping_cost=7.0,
                url="https://example.com/w202",
                is_active=True,
            ),
            Listing(
                id=203,
                source="wallapop",
                external_id="w203",
                title="iPhone 13 128GB blanco",
                normalized_name="iphone 13 128gb",
                price=255.0,
                shipping_cost=7.0,
                url="https://example.com/w203",
                is_active=True,
            ),
            Listing(
                id=204,
                source="wallapop",
                external_id="w204",
                title="iPhone 13 128GB azul",
                normalized_name="iphone 13 128gb",
                price=260.0,
                shipping_cost=7.0,
                url="https://example.com/w204",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(opportunities, [])

    def test_analyzer_evidence_includes_v3_market_signals(self) -> None:
        listings = [
            Listing(
                id=301,
                source="wallapop",
                external_id="w301",
                title="iPhone 13 128GB urgente",
                normalized_name="iphone 13 128gb",
                price=190.0,
                shipping_cost=7.0,
                url="https://example.com/w301",
                is_active=True,
            ),
            Listing(
                id=302,
                source="wallapop",
                external_id="w302",
                title="iPhone 13 128GB negro",
                normalized_name="iphone 13 128gb",
                price=250.0,
                shipping_cost=7.0,
                url="https://example.com/w302",
                is_active=True,
            ),
            Listing(
                id=303,
                source="wallapop",
                external_id="w303",
                title="iPhone 13 128GB blanco",
                normalized_name="iphone 13 128gb",
                price=255.0,
                shipping_cost=7.0,
                url="https://example.com/w303",
                is_active=True,
            ),
            Listing(
                id=304,
                source="wallapop",
                external_id="w304",
                title="iPhone 13 128GB azul",
                normalized_name="iphone 13 128gb",
                price=260.0,
                shipping_cost=7.0,
                url="https://example.com/w304",
                is_active=True,
            ),
        ]
        setattr(listings[0], "description", "Venta rápida, funciona perfectamente")

        opportunities = analyze_opportunities(listings)
        opportunity = opportunities[0]
        evidence = json.loads(opportunity.evidence_json)

        self.assertEqual(opportunity.metric_name, "wallapop_flipping_v3")
        self.assertIn("price_position", evidence)
        self.assertIn("underpricing_score", evidence)
        self.assertIn("competition_pressure", evidence)
        self.assertIn("liquidity_details", evidence)
        self.assertIn("listing_quality_score", evidence)
        self.assertIn("description_risk_details", evidence)
        self.assertFalse(evidence["extreme_underprice_risk"])


if __name__ == "__main__":
    unittest.main()
