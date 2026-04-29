import importlib
import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta


class PersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        os.environ["MARKET_ANALYZER_DB_URL"] = f"sqlite:///{self.tmpdir.name}/test.db"

        import app.config as config_module
        import app.db as db_module

        config_module.get_settings.cache_clear()
        self.config_module = importlib.reload(config_module)
        self.db_module = importlib.reload(db_module)

    def tearDown(self) -> None:
        self.db_module.engine.dispose()
        self.config_module.get_settings.cache_clear()
        os.environ.pop("MARKET_ANALYZER_DB_URL", None)
        self.tmpdir.cleanup()

    def test_sync_updates_existing_and_deactivates_missing(self) -> None:
        from app.models import Listing
        from app.services.persistence import sync_source_listings

        self.db_module.init_db()
        db = self.db_module.SessionLocal()

        old_seen = datetime.now(UTC) - timedelta(days=1)
        db.add(
            Listing(
                source="ebay",
                external_id="keep",
                title="Steam Deck 256GB",
                normalized_name="steam deck 256gb",
                price=400.0,
                currency="EUR",
                url="https://example.com/keep",
                image_url="https://example.com/keep.jpg",
                location="ES",
                seller_location="Madrid, Spain",
                shipping_region="local",
                condition="used",
                shipping_cost=5.0,
                is_active=True,
                first_seen_at=old_seen,
                last_seen_at=old_seen,
            )
        )
        db.add(
            Listing(
                source="ebay",
                external_id="gone",
                title="Steam Deck 64GB",
                normalized_name="steam deck 64gb",
                price=250.0,
                currency="EUR",
                url="https://example.com/gone",
                image_url="https://example.com/gone.jpg",
                location="ES",
                seller_location="Paris, France",
                shipping_region="eu",
                condition="used",
                shipping_cost=12.5,
                is_active=True,
                first_seen_at=old_seen,
                last_seen_at=old_seen,
            )
        )
        db.commit()

        summary = sync_source_listings(
            db,
            source="ebay",
            scraped_items=[
                {
                    "external_id": "keep",
                    "title": "Steam Deck 256GB impecable",
                    "normalized_name": "steam deck 256gb",
                    "price": 380.0,
                    "currency": "EUR",
                    "url": "https://example.com/keep",
                    "image_url": "https://example.com/keep_new.jpg",
                    "location": "Madrid",
                    "seller_location": "Madrid, Spain",
                    "shipping_region": "local",
                    "condition": "refurb",
                    "shipping_cost": 5.0,
                },
                {
                    "external_id": "new",
                    "title": "Steam Deck OLED 512GB",
                    "normalized_name": "steam deck oled 512gb",
                    "price": 520.0,
                    "currency": "EUR",
                    "url": "https://example.com/new",
                    "image_url": "https://example.com/new.jpg",
                    "location": "Madrid",
                    "seller_location": "Berlin, Germany",
                    "shipping_region": "eu",
                    "condition": "used",
                    "shipping_cost": 12.5,
                },
            ],
        )

        kept = db.query(Listing).filter(Listing.external_id == "keep").one()
        gone = db.query(Listing).filter(Listing.external_id == "gone").one()
        new = db.query(Listing).filter(Listing.external_id == "new").one()

        self.assertEqual(summary.inserted, 1)
        self.assertEqual(summary.updated, 1)
        self.assertEqual(summary.deactivated, 1)
        self.assertEqual(kept.price, 380.0)
        self.assertEqual(kept.condition, "refurb")
        self.assertEqual(kept.currency, "EUR")
        self.assertEqual(kept.image_url, "https://example.com/keep_new.jpg")
        self.assertEqual(kept.seller_location, "Madrid, Spain")
        self.assertEqual(kept.shipping_region, "local")
        self.assertEqual(kept.shipping_cost, 5.0)
        self.assertTrue(new.is_active)
        self.assertFalse(gone.is_active)

        db.close()

    def test_refresh_opportunities_preserves_manual_decision(self) -> None:
        from app.models import Listing, Opportunity
        from app.services.persistence import refresh_opportunities

        self.db_module.init_db()
        db = self.db_module.SessionLocal()

        listing = Listing(
            id=1,
            source="ebay",
            external_id="iphone-13-128-1",
            title="iPhone 13 128GB usado",
            normalized_name="iphone 13 128gb",
            price=430.0,
            currency="EUR",
            url="https://example.com/1",
            image_url="https://example.com/1.jpg",
            seller_location="Madrid, Spain",
            shipping_region="local",
            condition="used",
            shipping_cost=5.0,
            is_active=True,
        )
        db.add(listing)
        db.add_all(
            [
                Listing(
                    source="ebay",
                    external_id="iphone-13-128-2",
                    title="iPhone 13 128GB azul",
                    normalized_name="iphone 13 128gb",
                    price=610.0,
                    currency="EUR",
                    url="https://example.com/2",
                    image_url="https://example.com/2.jpg",
                    seller_location="Paris, France",
                    shipping_region="eu",
                    condition="used",
                    shipping_cost=12.5,
                    is_active=True,
                ),
                Listing(
                    source="ebay",
                    external_id="iphone-13-128-3",
                    title="iPhone 13 128GB negro",
                    normalized_name="iphone 13 128gb",
                    price=640.0,
                    currency="EUR",
                    url="https://example.com/3",
                    image_url="https://example.com/3.jpg",
                    seller_location="Berlin, Germany",
                    shipping_region="eu",
                    condition="used",
                    shipping_cost=12.5,
                    is_active=True,
                ),
                Opportunity(
                    title="iPhone 13 128GB usado",
                    source="ebay",
                    listing_id=1,
                    normalized_name="iphone 13 128gb",
                    buy_price=430.0,
                    estimated_resale_price=610.0,
                    profit_estimate=90.7,
                    fees_estimate=79.3,
                    shipping_estimate=10.0,
                    estimated_sale_price=610.0,
                    expected_profit=90.7,
                    score=100.0,
                    url="https://example.com/1",
                    manual_decision="accepted",
                ),
            ]
        )
        db.commit()

        opportunities = refresh_opportunities(db)

        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0].manual_decision, "accepted")

        db.close()

    def test_record_scrape_run_persists_summary_json(self) -> None:
        import json

        from app.services.persistence import SyncSummary, record_scrape_run

        self.db_module.init_db()
        db = self.db_module.SessionLocal()

        run = record_scrape_run(
            db,
            source="wallapop",
            status="success",
            queries=["iphone 14 128gb"],
            summary=SyncSummary(inserted=2, updated=1, deactivated=0, total_seen=3),
            listings_normalized=2,
            opportunities_generated=1,
            errors_count=0,
            duration_seconds=3.5,
            summary_json=json.dumps(
                {
                    "raw_results": 5,
                    "valid_results": 2,
                    "discard_reasons": {"unsupported_model": 2, "invalid_price": 1},
                    "quality_signals": {"location_present": 1, "shipping_region_unknown": 1},
                }
            ),
        )

        self.assertIn("\"raw_results\": 5", run.summary_json)

        db.close()


if __name__ == "__main__":
    unittest.main()
