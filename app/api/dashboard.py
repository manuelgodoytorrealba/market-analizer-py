import json
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import Listing, Opportunity, ScrapeRun

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"key": "overview", "label": "Overview", "href": "/"},
    {"key": "decision_engine", "label": "Decision Engine", "href": "/decision-engine-view"},
    {"key": "opportunities", "label": "Opportunities", "href": "/opportunities"},
    {"key": "listings", "label": "Listings", "href": "/listings"},
    {"key": "analysis", "label": "Pricing Evidence", "href": "/analysis"},
    {"key": "runs", "label": "Runs", "href": "/runs"},
    {"key": "settings", "label": "Settings", "href": "/settings"},
]


@router.get("/")
def overview(request: Request):
    db: Session = SessionLocal()
    try:
        opportunities = _query_opportunities(db)
        listings = _query_listings(db)
        runs = _query_runs(db)
        latest_run = runs[0] if runs else None
        context = _base_context(request, active_page="overview")
        context.update(
            {
                "stats": _build_stats(listings, opportunities, latest_run),
                "top_opportunities": opportunities[:8],
                "latest_run": latest_run,
                "source_breakdown": Counter(item.source for item in listings).most_common(),
                "confidence_breakdown": Counter(
                    opportunity.confidence or "unknown" for opportunity in opportunities
                ).most_common(),
                "recent_listings": listings[:8],
            }
        )
        return templates.TemplateResponse("overview.html", context)
    finally:
        db.close()


@router.get("/decision-engine-view")
def decision_engine_view(request: Request):
    context = _base_context(request, active_page="decision_engine")
    context.update({"auto_refresh_seconds": None})
    return templates.TemplateResponse("decision_engine.html", context)


@router.get("/opportunities")
def opportunities_view(request: Request):
    db: Session = SessionLocal()
    try:
        opportunities = _apply_opportunity_filters(_query_opportunities(db), request)
        selected = _pick_selected(
            request=request,
            items=opportunities,
            query_name="opportunity_id",
        )
        context = _base_context(request, active_page="opportunities")
        context.update(
            {
                "opportunities": opportunities,
                "selected_opportunity": selected,
                "selected_evidence": _load_evidence(selected),
                "filters": _opportunity_filters_snapshot(request),
            }
        )
        return templates.TemplateResponse("opportunities.html", context)
    finally:
        db.close()


@router.get("/listings")
def listings_view(request: Request):
    db: Session = SessionLocal()
    try:
        listings = _apply_listing_filters(_query_listings(db, include_inactive=True), request)
        selected = _pick_selected(
            request=request,
            items=listings,
            query_name="listing_id",
        )
        related_opportunities = []
        if selected is not None:
            related_opportunities = (
                db.query(Opportunity)
                .filter(Opportunity.listing_id == selected.id)
                .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
                .all()
            )
        context = _base_context(request, active_page="listings")
        context.update(
            {
                "listings": listings,
                "selected_listing": selected,
                "related_opportunities": related_opportunities,
                "filters": _listing_filters_snapshot(request),
            }
        )
        return templates.TemplateResponse("listings.html", context)
    finally:
        db.close()


@router.get("/analysis")
def analysis_view(request: Request):
    db: Session = SessionLocal()
    try:
        opportunities = _query_opportunities(db)
        selected = _pick_selected(
            request=request,
            items=opportunities,
            query_name="opportunity_id",
        )
        selected_evidence = _load_evidence(selected)
        context = _base_context(request, active_page="analysis")
        context.update(
            {
                "opportunities": opportunities[:24],
                "selected_opportunity": selected,
                "selected_evidence": selected_evidence,
            }
        )
        return templates.TemplateResponse("analysis.html", context)
    finally:
        db.close()


@router.get("/runs")
def runs_view(request: Request):
    db: Session = SessionLocal()
    try:
        runs = _query_runs(db)
        selected = _pick_selected(
            request=request,
            items=runs,
            query_name="run_id",
        )
        context = _base_context(request, active_page="runs")
        context.update(
            {
                "runs": runs,
                "selected_run": selected,
                "selected_run_queries": _load_queries(selected),
            }
        )
        return templates.TemplateResponse("runs.html", context)
    finally:
        db.close()


@router.get("/settings")
def settings_view(request: Request):
    settings = get_settings()
    context = _base_context(request, active_page="settings")
    context.update(
        {
            "settings_items": [
                ("Database URL", settings.database_url),
                ("Runtime interval", f"{settings.runtime_interval_seconds} s"),
                ("Dashboard refresh", f"{settings.dashboard_refresh_seconds} s"),
                ("Log level", settings.log_level),
                ("Request timeout", f"{settings.request_timeout_seconds} s"),
                ("Retry attempts", settings.retry_attempts),
                ("Backoff base", f"{settings.backoff_base_seconds} s"),
                ("User agent", settings.user_agent),
                ("Max eBay items", settings.ebay_search_max_items),
                ("Buy it now only", settings.ebay_buy_it_now_only),
            ]
        }
    )
    return templates.TemplateResponse("settings.html", context)


@router.post("/opportunities/{opportunity_id}/decision")
def update_opportunity_decision(opportunity_id: int, request: Request, decision: str):
    if decision not in {"accepted", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid decision")

    db: Session = SessionLocal()
    try:
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity.manual_decision = decision
        db.commit()
    finally:
        db.close()

    redirect_target = request.headers.get("referer") or f"/opportunities?opportunity_id={opportunity_id}"
    return RedirectResponse(url=redirect_target, status_code=303)


def _base_context(request: Request, active_page: str) -> dict[str, Any]:
    settings = get_settings()
    return {
        "request": request,
        "nav_items": NAV_ITEMS,
        "active_page": active_page,
        "runtime_interval_seconds": settings.runtime_interval_seconds,
        "auto_refresh_seconds": settings.dashboard_refresh_seconds,
    }


def _query_opportunities(db: Session) -> list[Opportunity]:
    return (
        db.query(Opportunity)
        .order_by(Opportunity.score.desc(), Opportunity.created_at.desc())
        .limit(250)
        .all()
    )


def _query_listings(db: Session, include_inactive: bool = False) -> list[Listing]:
    query = db.query(Listing)
    if not include_inactive:
        query = query.filter(Listing.is_active.is_(True))
    return query.order_by(Listing.last_seen_at.desc(), Listing.id.desc()).limit(400).all()


def _query_runs(db: Session) -> list[ScrapeRun]:
    return (
        db.query(ScrapeRun)
        .order_by(ScrapeRun.finished_at.desc(), ScrapeRun.id.desc())
        .limit(50)
        .all()
    )


def _build_stats(
    listings: list[Listing],
    opportunities: list[Opportunity],
    latest_run: ScrapeRun | None,
) -> list[dict[str, Any]]:
    active_count = sum(1 for listing in listings if listing.is_active)
    avg_profit = (
        round(
            sum((opportunity.profit_estimate or 0.0) for opportunity in opportunities)
            / len(opportunities),
            2,
        )
        if opportunities
        else 0.0
    )
    return [
        {"label": "Active listings", "value": active_count, "tone": "neutral"},
        {"label": "Live opportunities", "value": len(opportunities), "tone": "accent"},
        {"label": "Average profit", "value": f"{avg_profit} €", "tone": "good"},
        {
            "label": "Last run status",
            "value": latest_run.status.replace("_", " ") if latest_run else "no runs",
            "tone": "warn" if latest_run and latest_run.errors_count else "good",
        },
    ]


def _apply_opportunity_filters(
    opportunities: list[Opportunity], request: Request
) -> list[Opportunity]:
    source = request.query_params.get("source", "").strip().lower()
    confidence = request.query_params.get("confidence", "").strip().lower()
    query_text = request.query_params.get("q", "").strip().lower()
    min_discount = _to_float(request.query_params.get("min_discount"))
    min_price = _to_float(request.query_params.get("min_price"))
    max_price = _to_float(request.query_params.get("max_price"))
    buy_it_now_only = request.query_params.get("buy_it_now", "").strip().lower() == "true"

    filtered = opportunities
    if source:
        filtered = [item for item in filtered if item.source.lower() == source]
    if confidence:
        filtered = [
            item for item in filtered if (item.confidence or "").lower() == confidence
        ]
    if query_text:
        filtered = [
            item
            for item in filtered
            if query_text in item.title.lower()
            or query_text in (item.normalized_name or "").lower()
        ]
    if min_discount is not None:
        filtered = [
            item for item in filtered if (item.discount_pct or 0.0) >= min_discount
        ]
    if min_price is not None:
        filtered = [item for item in filtered if item.buy_price >= min_price]
    if max_price is not None:
        filtered = [item for item in filtered if item.buy_price <= max_price]
    if buy_it_now_only:
        filtered = [item for item in filtered if bool(item.buy_it_now)]
    return filtered


def _apply_listing_filters(listings: list[Listing], request: Request) -> list[Listing]:
    source = request.query_params.get("source", "").strip().lower()
    query_text = request.query_params.get("q", "").strip().lower()
    active = request.query_params.get("active", "").strip().lower()
    min_price = _to_float(request.query_params.get("min_price"))
    max_price = _to_float(request.query_params.get("max_price"))

    filtered = listings
    if source:
        filtered = [item for item in filtered if item.source.lower() == source]
    if query_text:
        filtered = [
            item
            for item in filtered
            if query_text in item.title.lower()
            or query_text in (item.normalized_name or "").lower()
            or query_text in (item.search_query or "").lower()
        ]
    if active in {"true", "false"}:
        expected = active == "true"
        filtered = [item for item in filtered if bool(item.is_active) == expected]
    if min_price is not None:
        filtered = [item for item in filtered if item.price >= min_price]
    if max_price is not None:
        filtered = [item for item in filtered if item.price <= max_price]
    return filtered


def _pick_selected(request: Request, items: list[Any], query_name: str) -> Any | None:
    selected_id = request.query_params.get(query_name)
    if not items:
        return None
    if selected_id and selected_id.isdigit():
        for item in items:
            if getattr(item, "id", None) == int(selected_id):
                return item
    return items[0]


def _load_evidence(opportunity: Opportunity | None) -> dict[str, Any] | None:
    if opportunity is None or not opportunity.evidence_json:
        return None
    try:
        return json.loads(opportunity.evidence_json)
    except json.JSONDecodeError:
        return None


def _load_queries(scrape_run: ScrapeRun | None) -> list[str]:
    if scrape_run is None or not scrape_run.queries_json:
        return []
    try:
        data = json.loads(scrape_run.queries_json)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _to_float(value: str | None) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _opportunity_filters_snapshot(request: Request) -> dict[str, str]:
    return {
        "source": request.query_params.get("source", ""),
        "confidence": request.query_params.get("confidence", ""),
        "q": request.query_params.get("q", ""),
        "min_discount": request.query_params.get("min_discount", ""),
        "min_price": request.query_params.get("min_price", ""),
        "max_price": request.query_params.get("max_price", ""),
        "buy_it_now": request.query_params.get("buy_it_now", ""),
    }


def _listing_filters_snapshot(request: Request) -> dict[str, str]:
    return {
        "source": request.query_params.get("source", ""),
        "active": request.query_params.get("active", ""),
        "q": request.query_params.get("q", ""),
        "min_price": request.query_params.get("min_price", ""),
        "max_price": request.query_params.get("max_price", ""),
    }
