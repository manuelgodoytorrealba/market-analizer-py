from pathlib import Path
import unittest

from app.scrapers.ebay import EbayHTMLScraper, build_ebay_provider


class EbayScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = EbayHTMLScraper()

    def test_parse_price_handles_euro_formats(self) -> None:
        self.assertEqual(self.scraper._parse_price("1.234,56 EUR"), 1234.56)
        self.assertEqual(self.scraper._parse_price("289,99 €"), 289.99)

    def test_invalid_titles_are_filtered(self) -> None:
        self.assertFalse(self.scraper._is_valid_listing("PS5 caja vacia", 100.0))
        self.assertFalse(self.scraper._is_valid_listing("Steam Deck auction", 300.0))
        self.assertFalse(self.scraper._is_valid_listing("iPhone 13 broken", 300.0))
        self.assertFalse(self.scraper._is_valid_listing("iPhone 13 icloud locked", 300.0))

    def test_auction_detection_is_conservative(self) -> None:
        self.assertTrue(
            self.scraper._is_auction_listing(
                "PS5 Subasta",
                "<html><body>Current bid: 210 EUR</body></html>",
            )
        )
        self.assertFalse(
            self.scraper._is_auction_listing(
                "PS5 Digital Edition",
                "<html><body>Compra ahora 399 EUR</body></html>",
            )
        )

    def test_detects_challenge_page(self) -> None:
        html = Path("data/raw/ebay_debug_steam_deck_current.html").read_text(
            encoding="utf-8"
        )
        self.assertTrue(self.scraper._is_challenge_page(html))

    def test_extract_candidates_from_mobile_fixture(self) -> None:
        html = Path("data/raw/ebay_debug_steam_deck_mobile.html").read_text(
            encoding="utf-8"
        )
        extraction = self.scraper._extract_candidates_from_search(html)
        self.assertGreater(extraction["strategy_counts"]["mobile_cards"], 0)
        self.assertGreater(len(extraction["candidates"]), 0)
        self.assertIn("steam deck", extraction["candidates"][0]["title"].lower())

    def test_classifies_european_shipping_regions(self) -> None:
        self.assertEqual(self.scraper._classify_shipping_region("Madrid, Spain"), "local")
        self.assertEqual(self.scraper._classify_shipping_region("Paris, France"), "eu")
        self.assertEqual(self.scraper._classify_shipping_region("Toronto, Canada"), "international")

    def test_builds_stable_external_id_from_item_url(self) -> None:
        self.assertEqual(
            self.scraper._build_external_id("https://www.ebay.es/itm/Apple-iPhone/123456789012?hash=item"),
            "123456789012",
        )

    def test_build_provider_defaults_to_html(self) -> None:
        provider = build_ebay_provider()
        self.assertTrue(hasattr(provider, "fetch_listings"))


if __name__ == "__main__":
    unittest.main()
