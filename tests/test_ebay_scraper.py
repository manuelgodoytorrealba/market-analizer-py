from pathlib import Path
import unittest

from app.scrapers.ebay import EbayScraper


class EbayScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = EbayScraper()

    def test_parse_price_handles_euro_formats(self) -> None:
        self.assertEqual(self.scraper._parse_price("1.234,56 EUR"), 1234.56)
        self.assertEqual(self.scraper._parse_price("289,99 €"), 289.99)

    def test_invalid_titles_are_filtered(self) -> None:
        self.assertFalse(self.scraper._is_valid_listing("PS5 caja vacia", 100.0))
        self.assertFalse(self.scraper._is_valid_listing("Steam Deck auction", 300.0))

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


if __name__ == "__main__":
    unittest.main()
