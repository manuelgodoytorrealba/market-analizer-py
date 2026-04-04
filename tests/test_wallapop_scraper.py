import unittest

from app.scrapers.wallapop import WallapopScraper


class WallapopScraperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = WallapopScraper()

    def test_builds_stable_external_id(self) -> None:
        external_id = self.scraper._build_external_id(
            "https://es.wallapop.com/item/iphone-13-pro-128gb-123456789?utm_source=test"
        )
        self.assertEqual(external_id, "123456789")

    def test_builds_seo_search_url_for_supported_query(self) -> None:
        url = self.scraper._build_search_url("iphone 13 pro 128gb")
        self.assertEqual(url, "https://es.wallapop.com/moviles-telefonos/iphone-13-pro-128-gb")

    def test_normalizes_candidate_with_national_shipping_defaults(self) -> None:
        candidate = {
            "id": "123456789",
            "title": "iPhone 13 Pro 128GB usado",
            "price": {"amount": 640},
            "web_slug": "iphone-13-pro-128gb-123456789",
            "location": {"city": "Madrid", "region": "Madrid", "country": "Spain"},
            "images": [{"original": "https://images.example.com/1.jpg"}],
        }

        normalized = self.scraper._normalize_candidate(candidate, "iphone 13 pro 128gb")

        self.assertIsNotNone(normalized)
        assert normalized is not None
        self.assertEqual(normalized["source"], "wallapop")
        self.assertEqual(normalized["external_id"], "123456789")
        self.assertEqual(normalized["currency"], "EUR")
        self.assertEqual(normalized["shipping_region"], "national")
        self.assertEqual(normalized["shipping_cost"], 7.0)
        self.assertEqual(normalized["seller_location"], "Madrid, Madrid, Spain")

    def test_builds_listing_url_from_title_slug_when_only_id_is_available(self) -> None:
        candidate = {
            "id": "123456789",
            "title": "iPhone 13 Azul 128Gb 100% Batería Perfecto",
        }

        url = self.scraper._build_url(candidate)

        self.assertEqual(
            url,
            "https://es.wallapop.com/item/iphone-13-azul-128gb-100-bateria-perfecto-123456789",
        )

    def test_collects_items_from_next_data_payload(self) -> None:
        payload = {
            "props": {
                "pageProps": {
                    "items": [
                        {"id": "1", "title": "iPhone 13 128GB", "price": {"amount": 500}},
                        {"id": "2", "title": "iPhone 14 256GB", "price": {"amount": 700}},
                    ]
                }
            }
        }

        items = self.scraper._collect_items_from_json(payload)

        self.assertEqual(len(items), 2)

    def test_extracts_items_from_api_payload(self) -> None:
        payload = {
            "search_objects": [
                {"id": "1", "title": "iPhone 13 128GB", "price": {"amount": 500}},
                {"id": "2", "title": "iPhone 14 Pro 256GB", "price": {"amount": 900}},
            ]
        }

        items = self.scraper._extract_candidates_from_api_payload(payload)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["id"], "1")

    def test_reports_quality_signals_for_invalid_candidate(self) -> None:
        candidate = {
            "id": "987654321",
            "title": "iPhone XR roto",
            "price": None,
        }

        listing, discard_reason, quality_signals = self.scraper._normalize_candidate_with_reason(
            candidate,
            "iphone 13 128gb",
        )

        self.assertIsNone(listing)
        self.assertEqual(discard_reason, "invalid_price")
        self.assertEqual(quality_signals["missing_price_usable"], 1)

    def test_reports_normalization_failure_for_unsupported_model(self) -> None:
        candidate = {
            "id": "123123123",
            "title": "iPhone 11 128GB usado",
            "price": {"amount": 300},
            "web_slug": "iphone-11-128gb-123123123",
            "location": {"city": "Madrid", "country": "Spain"},
        }

        listing, discard_reason, quality_signals = self.scraper._normalize_candidate_with_reason(
            candidate,
            "iphone 13 128gb",
        )

        self.assertIsNone(listing)
        self.assertEqual(discard_reason, "unsupported_model")
        self.assertEqual(quality_signals["location_present"], 1)
        self.assertEqual(quality_signals["normalization_failed"], 1)


if __name__ == "__main__":
    unittest.main()
