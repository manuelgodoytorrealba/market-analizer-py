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
                url="https://example.com/keep",
                location="ES",
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
                url="https://example.com/gone",
                location="ES",
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
                    "url": "https://example.com/keep",
                    "location": "Madrid",
                },
                {
                    "external_id": "new",
                    "title": "Steam Deck OLED 512GB",
                    "normalized_name": "steam deck oled 512gb",
                    "price": 520.0,
                    "url": "https://example.com/new",
                    "location": "Madrid",
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
        self.assertTrue(new.is_active)
        self.assertFalse(gone.is_active)

        db.close()


if __name__ == "__main__":
    unittest.main()
