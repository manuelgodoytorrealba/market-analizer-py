import logging
import time

from app.db import SessionLocal, init_db
from app.scrapers.ebay import EbayScraper
from app.services.persistence import (
    record_scrape_run,
    refresh_opportunities,
    sync_source_listings,
)


QUERIES = [
    "nintendo switch oled",
    "steam deck",
    "iphone 13 128gb",
    "iphone 14 128gb",
    "rtx 3080",
    "rtx 3070",
    "ps5",
    "macbook air m1",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    started_at = time.perf_counter()
    init_db()
    db = SessionLocal()
    scraper = EbayScraper()
    scraped_items: list[dict] = []
    errors_count = 0
    notes: list[str] = []

    try:
        for query in QUERIES:
            try:
                logger.info("Scanning query=%s", query)
                results = scraper.scrape(query)
                scraped_items.extend(results)
                logger.info("Query=%s results=%s", query, len(results))
            except Exception as exc:
                errors_count += 1
                notes.append(f"{query}: {exc}")
                logger.exception("Query failed query=%s", query)

        summary = sync_source_listings(db, source="ebay", scraped_items=scraped_items)
        opportunities = refresh_opportunities(db)
        duration_seconds = time.perf_counter() - started_at
        run = record_scrape_run(
            db,
            source="ebay",
            status="partial_success" if errors_count else "success",
            queries=QUERIES,
            summary=summary,
            opportunities_generated=len(opportunities),
            errors_count=errors_count,
            duration_seconds=duration_seconds,
            notes="\n".join(notes),
        )

        logger.info(
            "Sync completed run_id=%s inserted=%s updated=%s deactivated=%s total_seen=%s opportunities=%s",
            run.id,
            summary.inserted,
            summary.updated,
            summary.deactivated,
            summary.total_seen,
            len(opportunities),
        )

        for opportunity in opportunities[:10]:
            logger.info(
                "Opportunity title=%s buy=%.2f sale=%.2f profit=%.2f score=%.2f",
                opportunity.title,
                opportunity.buy_price,
                opportunity.estimated_sale_price,
                opportunity.expected_profit,
                opportunity.score,
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
