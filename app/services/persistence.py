import json
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Listing, Opportunity, ScrapeRun
from app.services.analyzer import analyze_opportunities


@dataclass(frozen=True)
class SyncSummary:
    inserted: int
    updated: int
    deactivated: int
    total_seen: int


def sync_source_listings(
    db: Session,
    source: str,
    scraped_items: list[dict],
    seen_at: datetime | None = None,
) -> SyncSummary:
    timestamp = seen_at or datetime.now(UTC)
    deduped_items: dict[str, dict] = {}

    for item in scraped_items:
        external_id = str(item["external_id"])
        deduped_items[external_id] = item

    external_ids = list(deduped_items.keys())
    existing_by_external_id: dict[str, Listing] = {}

    if external_ids:
        existing_rows = (
            db.query(Listing)
            .filter(Listing.source == source, Listing.external_id.in_(external_ids))
            .all()
        )
        existing_by_external_id = {row.external_id: row for row in existing_rows}

    inserted = 0
    updated = 0

    for external_id, item in deduped_items.items():
        existing = existing_by_external_id.get(external_id)

        if existing is None:
            db.add(
                Listing(
                    source=source,
                    external_id=external_id,
                    title=str(item["title"]),
                    normalized_name=str(item.get("normalized_name") or ""),
                    price=float(item["price"]),
                    url=str(item["url"]),
                    location=str(item.get("location") or ""),
                    search_query=str(item.get("search_query") or ""),
                    buy_it_now=bool(item.get("buy_it_now", True)),
                    is_active=True,
                    first_seen_at=timestamp,
                    last_seen_at=timestamp,
                )
            )
            inserted += 1
            continue

        changed = False
        new_values = {
            "title": str(item["title"]),
            "normalized_name": str(item.get("normalized_name") or ""),
            "price": float(item["price"]),
            "url": str(item["url"]),
            "location": str(item.get("location") or ""),
            "search_query": str(item.get("search_query") or ""),
            "buy_it_now": bool(item.get("buy_it_now", True)),
            "is_active": True,
            "last_seen_at": timestamp,
        }
        for field_name, field_value in new_values.items():
            if getattr(existing, field_name) != field_value:
                setattr(existing, field_name, field_value)
                changed = True

        if changed:
            updated += 1

    deactivated = 0
    if external_ids:
        active_rows = (
            db.query(Listing)
            .filter(Listing.source == source, Listing.is_active.is_(True))
            .all()
        )
        seen_external_ids = set(external_ids)

        for row in active_rows:
            if row.external_id in seen_external_ids:
                continue
            row.is_active = False
            deactivated += 1

    db.commit()

    return SyncSummary(
        inserted=inserted,
        updated=updated,
        deactivated=deactivated,
        total_seen=len(external_ids),
    )


def refresh_opportunities(db: Session) -> list[Opportunity]:
    active_listings = (
        db.query(Listing)
        .filter(Listing.is_active.is_(True))
        .order_by(Listing.last_seen_at.desc(), Listing.id.desc())
        .all()
    )
    opportunities = analyze_opportunities(active_listings)

    db.query(Opportunity).delete()
    db.flush()

    for opportunity in opportunities:
        db.add(opportunity)

    db.commit()

    return (
        db.query(Opportunity)
        .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
        .all()
    )


def record_scrape_run(
    db: Session,
    *,
    source: str,
    status: str,
    queries: list[str],
    summary: SyncSummary,
    opportunities_generated: int,
    errors_count: int,
    duration_seconds: float,
    notes: str = "",
) -> ScrapeRun:
    scrape_run = ScrapeRun(
        source=source,
        status=status,
        query_count=len(queries),
        queries_json=json.dumps(queries),
        listings_seen=summary.total_seen,
        inserted=summary.inserted,
        updated=summary.updated,
        deactivated=summary.deactivated,
        opportunities_generated=opportunities_generated,
        errors_count=errors_count,
        duration_seconds=duration_seconds,
        notes=notes,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
    )
    db.add(scrape_run)
    db.commit()
    db.refresh(scrape_run)
    return scrape_run
