import logging
import time
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Iterable

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.scrapers.ebay import build_ebay_provider
from app.scrapers.wallapop import build_wallapop_provider
from app.services.persistence import (
    record_scrape_run,
    refresh_opportunities,
    sync_source_listings,
)

# Add or remove eBay search coverage here.
EBAY_TARGET_QUERIES = [
    "iphone 13 128gb",
    "iphone 13 pro 128gb",
    "iphone 13 256gb",
    "iphone 13 pro 256gb",
]

# Add or remove Wallapop search coverage here.
WALLAPOP_TARGET_QUERIES = [
    # 📱 iPhones (base actual + más variantes)
    "iphone 11 128gb",
    "iphone 11 pro 256gb",
    "iphone 12 128gb",
    "iphone 12 pro 128gb",
    "iphone 12 pro max 128gb",
    "iphone 13 128gb",
    "iphone 13 pro 128gb",
    "iphone 13 pro max 128gb",
    "iphone 14 128gb",
    "iphone 14 pro 128gb",
    "iphone 14 pro max 128gb",
    "iphone 15 128gb",
    "iphone 15 pro 128gb",
    "iphone 15 pro 256gb",
    "iphone 15 pro max 256gb",
    # 🎮 Consolas
    "ps4 slim",
    "ps4 pro",
    "ps5",
    "ps5 digital",
    "xbox series s",
    "xbox series x",
    "nintendo switch",
    "nintendo switch oled",
    "nintendo switch lite",
    "nintendo ds",
    # 💻 Laptops (muy buenas para arbitraje)
    "macbook air m1",
    "macbook air m2",
    "macbook pro m1",
    "macbook pro m2",
    "macbook pro 14 m1",
    "macbook pro 16 m1",
    # 🖥️ GPUs (mercado volátil = oportunidades)
    "rtx 3060",
    "rtx 3070",
    "rtx 3080",
    "rtx 3090",
    # 🎧 Electrónica rápida
    "airpods pro",
    "airpods pro 2",
    "sony wh-1000xm4",
    "sony wh-1000xm5",
    # ⌚ Wearables
    "apple watch series 7",
    "apple watch series 8",
    "apple watch ultra",
    # 📸 Cámaras (muy buen margen)
    "sony a7 iii",
    "sony a7 iv",
    "canon eos r",
    "canon eos rp",
    # 👟 Sneakers (tu nicho 🔥)
    "nike dunk low",
    "nike air force 1",
    "jordan 1 retro",
    "jordan 4 retro",
    "yeezy 350",
    # 🎴 Cartas (mercado hype)
    "pokemon charizard",
    "pokemon psa",
    "pokemon booster box",
]

TARGET_QUERIES_BY_SOURCE = {
    "ebay": EBAY_TARGET_QUERIES,
    "wallapop": WALLAPOP_TARGET_QUERIES,
}


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderCycleSummary:
    source_name: str
    status: str
    queries: list[str]
    listings_scraped: int
    listings_normalized: int
    persisted_results: int
    inserted: int
    updated: int
    deactivated: int
    discarded_results: int
    discard_reasons: dict[str, int]
    quality_signals: dict[str, int]
    opportunities_count: int
    opportunities_by_type: dict[str, int]
    fresh_data_available: bool
    error_message: str


@dataclass(frozen=True)
class CycleReport:
    run_id: int | None
    status: str
    started_at: datetime
    finished_at: datetime
    duration_seconds: float
    listings_scraped: int
    listings_normalized: int
    opportunities_count: int
    errors_count: int
    error_message: str
    provider_summaries: list[ProviderCycleSummary]


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


def get_target_queries_by_source() -> dict[str, list[str]]:
    return {
        source: list(queries) for source, queries in TARGET_QUERIES_BY_SOURCE.items()
    }


def build_market_providers(
    selected_sources: Iterable[str] | None = None,
) -> list[tuple[str, object, list[str]]]:
    settings = get_settings()
    allowed_sources = set(selected_sources or [])
    providers: list[tuple[str, object, list[str]]] = []

    # Register new providers here, reusing the common fetch_listings/debug_scrape contract.
    if not allowed_sources or "ebay" in allowed_sources:
        providers.append(("ebay", build_ebay_provider(), EBAY_TARGET_QUERIES))
    if settings.enable_wallapop and (
        not allowed_sources or "wallapop" in allowed_sources
    ):
        providers.append(
            ("wallapop", build_wallapop_provider(), WALLAPOP_TARGET_QUERIES)
        )
    return providers


def run_market_cycle(
    *, scraper=None, selected_sources: Iterable[str] | None = None
) -> CycleReport:
    init_db()
    db = SessionLocal()
    provider_entries = (
        [("custom", scraper, EBAY_TARGET_QUERIES)]
        if scraper is not None
        else build_market_providers(selected_sources)
    )
    started_at = datetime.now(UTC)
    started_perf = time.perf_counter()
    listings_scraped = 0
    listings_normalized = 0
    errors_count = 0
    error_messages: list[str] = []
    run_id: int | None = None
    provider_reports: list[dict] = []

    try:
        for source_name, active_provider, queries in provider_entries:
            provider_items: list[dict] = []
            provider_scraped = 0
            provider_normalized = 0
            provider_errors = 0
            provider_error_messages: list[str] = []
            provider_discard_reasons: dict[str, int] = {}
            provider_quality: dict[str, int] = {}
            query_summaries: list[dict] = []

            for query in queries:
                try:
                    if hasattr(active_provider, "debug_scrape"):
                        query_result = active_provider.debug_scrape(query)
                        raw_candidates = int(query_result["raw_candidates"])
                        valid_results = len(query_result["results"])
                        discard_reasons = dict(
                            query_result.get("discard_reasons") or {}
                        )
                        quality_signals = dict(
                            query_result.get("quality_signals") or {}
                        )
                        provider_scraped += raw_candidates
                        provider_normalized += valid_results
                        provider_items.extend(query_result["results"])
                        _merge_int_dict(provider_discard_reasons, discard_reasons)
                        _merge_int_dict(provider_quality, quality_signals)
                        query_summaries.append(
                            {
                                "query": query,
                                "raw_candidates": raw_candidates,
                                "valid_results": valid_results,
                                "discarded": sum(discard_reasons.values()),
                                "discard_reasons": discard_reasons,
                                "quality_signals": quality_signals,
                            }
                        )
                        logger.info(
                            (
                                "cycle source=%s query=%s raw_candidates=%s valid_results=%s "
                                "discarded=%s discard_reasons=%s quality=%s"
                            ),
                            source_name,
                            query,
                            raw_candidates,
                            valid_results,
                            sum(discard_reasons.values()),
                            discard_reasons,
                            quality_signals,
                        )
                    else:
                        results = active_provider.fetch_listings(query)
                        raw_candidates = len(results)
                        valid_results = len(results)
                        provider_scraped += raw_candidates
                        provider_normalized += valid_results
                        provider_items.extend(results)
                        query_summaries.append(
                            {
                                "query": query,
                                "raw_candidates": raw_candidates,
                                "valid_results": valid_results,
                                "discarded": 0,
                                "discard_reasons": {},
                                "quality_signals": {},
                            }
                        )
                        logger.info(
                            "cycle source=%s query=%s raw_candidates=%s valid_results=%s",
                            source_name,
                            query,
                            raw_candidates,
                            valid_results,
                        )
                except Exception as exc:
                    provider_errors += 1
                    provider_error_messages.append(f"{query}: {exc}")
                    logger.exception(
                        "cycle query_failed source=%s query=%s", source_name, query
                    )

            summary = sync_source_listings(
                db,
                source=source_name,
                scraped_items=provider_items,
                seen_at=started_at,
            )
            listings_scraped += provider_scraped
            listings_normalized += provider_normalized
            errors_count += provider_errors
            error_messages.extend(provider_error_messages)

            provider_reports.append(
                {
                    "source_name": source_name,
                    "queries": queries,
                    "scraped": provider_scraped,
                    "normalized": provider_normalized,
                    "summary": summary,
                    "errors_count": provider_errors,
                    "error_messages": provider_error_messages,
                    "discard_reasons": provider_discard_reasons,
                    "quality_signals": provider_quality,
                    "query_summaries": query_summaries,
                    "fresh_data_available": provider_scraped > 0
                    or provider_normalized > 0,
                }
            )

        opportunities = refresh_opportunities(db)
        finished_at = datetime.now(UTC)
        duration_seconds = time.perf_counter() - started_perf
        fresh_data_any = any(
            provider_report["fresh_data_available"]
            for provider_report in provider_reports
        )
        status = "error" if errors_count or not fresh_data_any else "success"
        error_message = "\n".join(error_messages)
        if not fresh_data_any:
            error_message = (
                f"{error_message}\nno_fresh_data_detected"
                if error_message
                else "no_fresh_data_detected"
            )
        opportunities_by_source = _count_opportunities_by_source(opportunities)
        opportunities_by_type = _count_opportunities_by_type(opportunities)
        opportunities_by_source_and_type = _count_opportunities_by_source_and_type(
            opportunities
        )

        for provider_report in provider_reports:
            source_name = provider_report["source_name"]
            summary = provider_report["summary"]
            provider_status = "error" if provider_report["errors_count"] else "success"
            provider_error_message = "\n".join(provider_report["error_messages"])
            if not provider_report["fresh_data_available"]:
                provider_status = "error"
                provider_error_message = (
                    f"{provider_error_message}\nno_fresh_data_detected"
                    if provider_error_message
                    else "no_fresh_data_detected"
                )
            summary_payload = {
                "source": source_name,
                "queries": provider_report["query_summaries"],
                "raw_results": provider_report["scraped"],
                "persisted_results": summary.total_seen,
                "persisted_changes": {
                    "inserted": summary.inserted,
                    "updated": summary.updated,
                    "deactivated": summary.deactivated,
                },
                "valid_results": provider_report["normalized"],
                "discarded_results": sum(provider_report["discard_reasons"].values()),
                "discard_reasons": provider_report["discard_reasons"],
                "quality_signals": provider_report["quality_signals"],
                "fresh_data_available": provider_report["fresh_data_available"],
                "opportunities_generated": opportunities_by_source.get(source_name, 0),
                "opportunities_generated_by_type": opportunities_by_source_and_type.get(
                    source_name, {}
                ),
                "errors": provider_report["error_messages"],
            }

            run = record_scrape_run(
                db,
                source=source_name,
                status=provider_status,
                queries=provider_report["queries"],
                summary=summary,
                listings_normalized=provider_report["normalized"],
                opportunities_generated=opportunities_by_source.get(source_name, 0),
                errors_count=provider_report["errors_count"],
                duration_seconds=duration_seconds,
                summary_json=json.dumps(summary_payload),
                started_at=started_at,
                finished_at=finished_at,
                error_message=provider_error_message,
                notes=provider_error_message,
            )
            run_id = run.id

            logger.info(
                (
                    "cycle provider_completed source=%s run_id=%s status=%s duration=%.2fs "
                    "raw=%s valid=%s persisted=%s inserted=%s updated=%s deactivated=%s "
                    "discarded=%s discard_reasons=%s fresh_data=%s opportunities=%s opportunities_by_type=%s errors=%s"
                ),
                source_name,
                run.id,
                provider_status,
                duration_seconds,
                provider_report["scraped"],
                provider_report["normalized"],
                summary.total_seen,
                summary.inserted,
                summary.updated,
                summary.deactivated,
                sum(provider_report["discard_reasons"].values()),
                provider_report["discard_reasons"],
                provider_report["fresh_data_available"],
                opportunities_by_source.get(source_name, 0),
                opportunities_by_source_and_type.get(source_name, {}),
                provider_report["errors_count"],
            )

        logger.info(
            (
                "cycle completed status=%s duration=%.2fs "
                "listings_scraped=%s listings_valid=%s opportunities=%s opportunities_by_source=%s opportunities_by_type=%s fresh_data=%s errors=%s"
            ),
            status,
            duration_seconds,
            listings_scraped,
            listings_normalized,
            len(opportunities),
            opportunities_by_source,
            opportunities_by_type,
            fresh_data_any,
            errors_count,
        )

        provider_summaries = [
            ProviderCycleSummary(
                source_name=provider_report["source_name"],
                status=(
                    "error"
                    if provider_report["errors_count"]
                    or not provider_report["fresh_data_available"]
                    else "success"
                ),
                queries=list(provider_report["queries"]),
                listings_scraped=provider_report["scraped"],
                listings_normalized=provider_report["normalized"],
                persisted_results=provider_report["summary"].total_seen,
                inserted=provider_report["summary"].inserted,
                updated=provider_report["summary"].updated,
                deactivated=provider_report["summary"].deactivated,
                discarded_results=sum(provider_report["discard_reasons"].values()),
                discard_reasons=dict(provider_report["discard_reasons"]),
                quality_signals=dict(provider_report["quality_signals"]),
                opportunities_count=opportunities_by_source.get(
                    provider_report["source_name"], 0
                ),
                opportunities_by_type=dict(
                    opportunities_by_source_and_type.get(
                        provider_report["source_name"], {}
                    )
                ),
                fresh_data_available=provider_report["fresh_data_available"],
                error_message=(
                    "\n".join(provider_report["error_messages"])
                    if provider_report["fresh_data_available"]
                    else (
                        f"{'\n'.join(provider_report['error_messages'])}\nno_fresh_data_detected"
                        if provider_report["error_messages"]
                        else "no_fresh_data_detected"
                    )
                ),
            )
            for provider_report in provider_reports
        ]

        return CycleReport(
            run_id=run_id,
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=duration_seconds,
            listings_scraped=listings_scraped,
            listings_normalized=listings_normalized,
            opportunities_count=len(opportunities),
            errors_count=errors_count,
            error_message=error_message,
            provider_summaries=provider_summaries,
        )
    finally:
        db.close()


def _merge_int_dict(target: dict[str, int], new_values: dict[str, int]) -> None:
    for key, value in new_values.items():
        target[key] = target.get(key, 0) + int(value)


def _count_opportunities_by_source(opportunities) -> dict[str, int]:
    counts: dict[str, int] = {}
    for opportunity in opportunities:
        counts[opportunity.source] = counts.get(opportunity.source, 0) + 1
    return counts


def _count_opportunities_by_type(opportunities) -> dict[str, int]:
    counts: dict[str, int] = {}
    for opportunity in opportunities:
        opportunity_type = opportunity.opportunity_type or "unknown"
        counts[opportunity_type] = counts.get(opportunity_type, 0) + 1
    return counts


def _count_opportunities_by_source_and_type(opportunities) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for opportunity in opportunities:
        source_counts = counts.setdefault(opportunity.source, {})
        opportunity_type = opportunity.opportunity_type or "unknown"
        source_counts[opportunity_type] = source_counts.get(opportunity_type, 0) + 1
    return counts
