import argparse
import sys
import time
from typing import cast

import uvicorn

from app.core.config import get_settings
from app.db.session import SessionLocal, init_db
from app.models.entities import Listing, Opportunity
from app.scrapers.wallapop import WallapopScraper
from app.services.runtime import (
    CycleReport,
    configure_logging,
    get_target_queries_by_source,
    run_market_cycle,
)


VALID_SOURCES = ("ebay", "wallapop")


def _parse_sources(value: str) -> list[str] | None:
    normalized = (value or "all").strip().lower()
    if normalized == "all":
        return None
    sources = [source.strip() for source in normalized.split(",") if source.strip()]
    invalid = [source for source in sources if source not in VALID_SOURCES]
    if invalid:
        raise argparse.ArgumentTypeError(
            f"Fuentes no soportadas: {', '.join(invalid)}. Usa: all, ebay, wallapop o una lista separada por comas."
        )
    return sources


def _add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--source",
        type=_parse_sources,
        default=None,
        help="Fuente a ejecutar: all, ebay, wallapop o varias separadas por comas",
    )


def _print_header(title: str) -> None:
    line = "=" * 78
    print(line)
    print(title)
    print(line)


def _print_cycle_report(report: CycleReport) -> None:
    _print_header("Market Analyzer Runtime Summary")
    print(f"status:        {report.status}")
    print(f"duration:      {report.duration_seconds:.2f}s")
    print(f"scraped:       {report.listings_scraped}")
    print(f"normalized:    {report.listings_normalized}")
    print(f"opportunities: {report.opportunities_count}")
    print(f"errors:        {report.errors_count}")
    if report.error_message:
        print(f"error_message: {report.error_message}")
    print()
    print("Per source")
    print("-" * 78)
    for summary in report.provider_summaries:
        print(
            (
                f"{summary.source_name:<10} status={summary.status:<7} raw={summary.listings_scraped:<3} "
                f"valid={summary.listings_normalized:<3} persisted={summary.persisted_results:<3} "
                f"inserted={summary.inserted:<3} updated={summary.updated:<3} "
                f"opp={summary.opportunities_count:<3} fresh={str(summary.fresh_data_available).lower()}"
            )
        )
        if summary.discard_reasons:
            print(f"  discard_reasons: {summary.discard_reasons}")
        if summary.quality_signals:
            print(f"  quality:         {summary.quality_signals}")
        if summary.opportunities_by_type:
            print(f"  opportunities:   {summary.opportunities_by_type}")
        if summary.error_message:
            print(f"  notes:           {summary.error_message}")
    print("-" * 78)


def _run_once(args: argparse.Namespace) -> int:
    configure_logging()
    report = run_market_cycle(selected_sources=args.source)
    _print_cycle_report(report)
    return 0 if report.status == "success" else 1


def _run_runtime(args: argparse.Namespace) -> int:
    configure_logging()
    interval_seconds = max(args.interval, 1)
    cycle_number = 0
    _print_header("Market Analyzer Runtime Loop")
    print(f"interval_seconds: {interval_seconds}")
    print(f"sources:          {', '.join(args.source) if args.source else 'all'}")
    print()
    try:
        while True:
            cycle_number += 1
            print(f"[cycle {cycle_number}] starting")
            report = run_market_cycle(selected_sources=args.source)
            _print_cycle_report(report)
            print(f"[cycle {cycle_number}] sleeping {interval_seconds}s")
            print()
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("runtime stopped_by_user")
        return 0


def _run_init_db(_: argparse.Namespace) -> int:
    init_db()
    _print_header("Database Ready")
    print("SQLite schema initialized.")
    return 0


def _run_serve(args: argparse.Namespace) -> int:
    _print_header("Dashboard Server")
    print(f"url:    http://{args.host}:{args.port}")
    print(f"reload: {str(args.reload).lower()}")
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


def _run_queries(_: argparse.Namespace) -> int:
    _print_header("Configured Queries")
    for source, queries in get_target_queries_by_source().items():
        print(f"{source}:")
        for query in queries:
            print(f"  - {query}")
        print()
    print("Add or edit queries in: app/services/runtime.py")
    return 0


def _run_repair_wallapop_urls(_: argparse.Namespace) -> int:
    scraper = WallapopScraper()
    db = SessionLocal()
    updated_listings = 0
    updated_opportunities = 0
    try:
        listings = db.query(Listing).filter(Listing.source == "wallapop").all()
        listing_url_by_id: dict[int, str] = {}
        for listing in listings:
            candidate = {
                "id": cast(str, listing.external_id),
                "title": cast(str, listing.title),
            }
            expected_url = scraper._build_url(candidate)
            listing_id = cast(int, listing.id)
            current_url = cast(str, listing.url)
            if expected_url:
                listing_url_by_id[listing_id] = expected_url
            if expected_url and current_url != expected_url:
                setattr(listing, "url", expected_url)
                updated_listings += 1

        opportunities = db.query(Opportunity).filter(Opportunity.source == "wallapop").all()
        for opportunity in opportunities:
            listing_id = cast(int, opportunity.listing_id)
            current_url = cast(str, opportunity.url)
            expected_url = listing_url_by_id.get(listing_id)
            if expected_url and current_url != expected_url:
                setattr(opportunity, "url", expected_url)
                updated_opportunities += 1
        db.commit()
    finally:
        db.close()

    _print_header("Wallapop URL Repair")
    print(f"updated_listings:      {updated_listings}")
    print(f"updated_opportunities: {updated_opportunities}")
    print("Wallapop public URLs recalculated in listings and opportunities.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    settings = get_settings()
    parser = argparse.ArgumentParser(
        description="CLI operativo para Market Analyzer",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_db_parser = subparsers.add_parser("init-db", help="Inicializa la base de datos")
    init_db_parser.set_defaults(handler=_run_init_db)

    once_parser = subparsers.add_parser("once", help="Ejecuta un solo ciclo de scraping/análisis")
    _add_source_argument(once_parser)
    once_parser.set_defaults(handler=_run_once)

    runtime_parser = subparsers.add_parser("runtime", help="Ejecuta el runtime continuo")
    _add_source_argument(runtime_parser)
    runtime_parser.add_argument(
        "--interval",
        type=int,
        default=settings.runtime_interval_seconds,
        help="Segundos entre ciclos",
    )
    runtime_parser.set_defaults(handler=_run_runtime)

    serve_parser = subparsers.add_parser("serve", help="Levanta el dashboard FastAPI")
    serve_parser.add_argument("--host", default="127.0.0.1", help="Host del servidor")
    serve_parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor")
    serve_parser.add_argument("--reload", action="store_true", help="Activa autoreload")
    serve_parser.set_defaults(handler=_run_serve)

    queries_parser = subparsers.add_parser("queries", help="Muestra las queries configuradas")
    queries_parser.set_defaults(handler=_run_queries)

    repair_urls_parser = subparsers.add_parser(
        "repair-wallapop-urls",
        help="Recalcula URLs públicas de listings Wallapop ya persistidos",
    )
    repair_urls_parser.set_defaults(handler=_run_repair_wallapop_urls)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
