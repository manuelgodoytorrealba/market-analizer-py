import unittest

from app.models import Listing
from app.services.analyzer import analyze_opportunities


class AnalyzerTests(unittest.TestCase):
    def test_analyzer_finds_discounted_listing_for_comparable_group(self) -> None:
        listings = [
            Listing(
                source="ebay",
                external_id="1",
                title="Nintendo Switch OLED blanca 64GB",
                normalized_name="nintendo switch oled 64gb",
                price=210.0,
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="2",
                title="Nintendo Switch OLED con caja 64GB",
                normalized_name="nintendo switch oled 64gb",
                price=270.0,
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3",
                title="Nintendo Switch OLED nueva 64GB",
                normalized_name="nintendo switch oled 64gb",
                price=290.0,
                url="https://example.com/3",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].buy_price, 210.0)

    def test_analyzer_does_not_mix_incompatible_storage_variants(self) -> None:
        listings = [
            Listing(
                source="ebay",
                external_id="1",
                title="iPhone 13 128GB azul",
                normalized_name="iphone 13 128gb",
                price=420.0,
                url="https://example.com/1",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="2",
                title="iPhone 13 256GB azul",
                normalized_name="iphone 13 256gb",
                price=520.0,
                url="https://example.com/2",
                is_active=True,
            ),
            Listing(
                source="ebay",
                external_id="3",
                title="iPhone 13 256GB rojo",
                normalized_name="iphone 13 256gb",
                price=540.0,
                url="https://example.com/3",
                is_active=True,
            ),
        ]

        opportunities = analyze_opportunities(listings)

        self.assertEqual(opportunities, [])


if __name__ == "__main__":
    unittest.main()
