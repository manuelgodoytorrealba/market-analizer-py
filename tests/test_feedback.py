import importlib
import json
import os
import shutil
import tempfile
import unittest


class FeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir_path = tempfile.mkdtemp(dir="C:\\tmp")
        os.environ["MARKET_ANALYZER_DB_URL"] = f"sqlite:///{self.tmpdir_path}/test.db"

        import app.core.config as config_module
        import app.db.session as db_module

        config_module.get_settings.cache_clear()
        self.config_module = importlib.reload(config_module)
        self.db_module = importlib.reload(db_module)

    def tearDown(self) -> None:
        self.db_module.engine.dispose()
        self.config_module.get_settings.cache_clear()
        os.environ.pop("MARKET_ANALYZER_DB_URL", None)
        shutil.rmtree(self.tmpdir_path, ignore_errors=True)

    def test_save_feedback_upserts_single_row_per_listing(self) -> None:
        from app.models.entities import Listing, ListingFeedback
        from app.services.feedback import save_listing_feedback

        self.db_module.init_db()
        db = self.db_module.SessionLocal()

        listing = Listing(
            id=1,
            source="wallapop",
            external_id="abc",
            title="PS5 Slim",
            normalized_name="ps5 slim",
            search_query="ps5",
            price=420.0,
            url="https://example.com/1",
            is_active=True,
        )
        db.add(listing)
        db.commit()

        save_listing_feedback(
            db,
            listing=listing,
            feedback_label="match_ok",
            feedback_notes="producto correcto",
        )
        save_listing_feedback(
            db,
            listing=listing,
            feedback_label="accessory_only",
            feedback_notes="era un mando",
        )

        rows = db.query(ListingFeedback).all()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].feedback_label, "accessory_only")
        self.assertEqual(rows[0].feedback_notes, "era un mando")

        db.close()

    def test_export_feedback_dataset_creates_jsonl_rows(self) -> None:
        from app.models.entities import Listing
        from app.services.feedback import export_feedback_dataset, save_listing_feedback

        self.db_module.init_db()
        db = self.db_module.SessionLocal()

        listing = Listing(
            id=1,
            source="wallapop",
            external_id="abc",
            title="iPhone 13 bloqueado",
            normalized_name="iphone 13",
            search_query="iphone 13",
            price=240.0,
            url="https://example.com/1",
            is_active=True,
        )
        db.add(listing)
        db.commit()

        save_listing_feedback(
            db,
            listing=listing,
            feedback_label="locked",
            feedback_notes="icloud lock confirmado",
        )

        output_path = os.path.join(self.tmpdir_path, "feedback.jsonl")
        export_feedback_dataset(db, output_path)

        with open(output_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()

        self.assertEqual(len(lines), 1)
        row = json.loads(lines[0])
        self.assertEqual(row["feedback_label"], "locked")
        self.assertEqual(row["targets"]["is_target_match"], True)
        self.assertEqual(row["targets"]["is_damaged_or_parts_only"], True)
        self.assertIn("iPhone 13 bloqueado", row["text"])

        db.close()


if __name__ == "__main__":
    unittest.main()
