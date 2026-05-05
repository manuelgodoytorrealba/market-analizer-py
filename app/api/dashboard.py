import json
from collections import Counter
from typing import Any

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import Listing, ListingFeedback, Opportunity, ScrapeRun
from app.services.feedback import FEEDBACK_LABELS, get_listing_feedback, save_listing_feedback

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

NAV_ITEMS = [
    {"key": "overview", "label": "Overview", "href": "/"},
    {
        "key": "decision_engine",
        "label": "Decision Engine",
        "href": "/decision-engine-view",
    },
    {"key": "opportunities", "label": "Opportunities", "href": "/opportunities"},
    {"key": "listings", "label": "Listings", "href": "/listings"},
    {"key": "analysis", "label": "Pricing Evidence", "href": "/analysis"},
    {"key": "runs", "label": "Runs", "href": "/runs"},
    {"key": "settings", "label": "Settings", "href": "/settings"},
]


# =========================
# ROUTES
# =========================


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
                "source_breakdown": Counter(
                    item.source for item in listings
                ).most_common(),
                "confidence_breakdown": Counter(
                    opportunity.confidence or "unknown" for opportunity in opportunities
                ).most_common(),
                "recent_listings": listings[:8],
            }
        )

        return templates.TemplateResponse(
            request=request,
            name="overview.html",
            context=context,
        )
    finally:
        db.close()


@router.get("/decision-engine-view")
def decision_engine_view(request: Request):
    context = _base_context(request, active_page="decision_engine")

    return templates.TemplateResponse(
        request=request,
        name="decision_engine.html",
        context=context,
    )


@router.get("/opportunities")
def opportunities_view(request: Request):
    db: Session = SessionLocal()
    try:
        opportunities = _query_opportunities(db)

        opportunities = _apply_opportunity_filters(opportunities, request)
        opportunities = _apply_category_filter(opportunities, request)

        selected = _pick_selected(request, opportunities, "opportunity_id")

        context = _base_context(request, active_page="opportunities")
        context.update(
            {
                "opportunities": opportunities,
                "selected_opportunity": selected,
                "selected_evidence": _load_evidence(selected),
                "filters": _opportunity_filters_snapshot(request),
            }
        )

        return templates.TemplateResponse(
            request=request,
            name="opportunities.html",
            context=context,
        )
    finally:
        db.close()


@router.get("/listings")
def listings_view(request: Request):
    db: Session = SessionLocal()
    try:
        listings = _query_listings(db, include_inactive=True)

        listings = _apply_listing_filters(listings, request)
        listings = _apply_category_filter(listings, request)

        selected = _pick_selected(request, listings, "listing_id")

        related_opportunities = []
        if selected:
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
                "selected_feedback": (
                    get_listing_feedback(db, listing_id=int(selected.id))
                    if selected is not None
                    else None
                ),
                "feedback_labels": FEEDBACK_LABELS,
                "related_opportunities": related_opportunities,
                "filters": _listing_filters_snapshot(request),
            }
        )

        return templates.TemplateResponse(
            request=request,
            name="listings.html",
            context=context,
        )
    finally:
        db.close()


@router.post("/listings/{listing_id}/feedback")
def update_listing_feedback(
    listing_id: int,
    request: Request,
    feedback_label: str = Form(...),
    feedback_notes: str = Form(""),
):
    db: Session = SessionLocal()
    try:
        listing = db.query(Listing).filter(Listing.id == listing_id).first()
        if listing is None:
            raise HTTPException(status_code=404, detail="Listing not found")

        try:
            save_listing_feedback(
                db,
                listing=listing,
                feedback_label=feedback_label,
                feedback_notes=feedback_notes,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        db.close()

    redirect_target = request.headers.get("referer") or f"/listings?listing_id={listing_id}"
    return RedirectResponse(url=redirect_target, status_code=303)


@router.post("/opportunities/{opportunity_id}/decision")
def update_opportunity_decision(opportunity_id: int, request: Request, decision: str):
    if decision not in {"accepted", "rejected"}:
        raise HTTPException(status_code=400, detail="Invalid decision")

    db: Session = SessionLocal()
    try:
        opportunity = (
            db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
        )
        if opportunity is None:
            raise HTTPException(status_code=404, detail="Opportunity not found")

        opportunity.manual_decision = decision
        db.commit()
    finally:
        db.close()

    redirect_target = (
        request.headers.get("referer")
        or f"/opportunities?opportunity_id={opportunity_id}"
    )
    return RedirectResponse(url=redirect_target, status_code=303)


# =========================
# CATEGORY FILTER
# =========================


def _apply_category_filter(items, request):
    category = request.query_params.get("category", "").lower()

    if not category:
        return items

    def match(item):
        text = f"{getattr(item, 'title', '')} {getattr(item, 'normalized_name', '')}".lower()

        if category == "iphone":
            return "iphone" in text

        if category == "macbook":
            return any(x in text for x in ["macbook", "macbook air", "macbook pro"])

        if category == "gpu":
            return any(x in text for x in ["rtx", "gtx", "gpu", "nvidia"])

        return True

    return [item for item in items if match(item)]


# =========================
# HELPERS
# =========================


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
    return query.order_by(Listing.last_seen_at.desc()).limit(400).all()


def _query_runs(db: Session) -> list[ScrapeRun]:
    return db.query(ScrapeRun).limit(50).all()


def _build_stats(listings, opportunities, latest_run):
    return [
        {"label": "Listings", "value": len(listings)},
        {"label": "Opportunities", "value": len(opportunities)},
        {"label": "Last run", "value": latest_run.status if latest_run else "none"},
    ]


def _apply_opportunity_filters(opportunities, request):
    source = request.query_params.get("source", "").lower()
    confidence = request.query_params.get("confidence", "").lower()
    q = request.query_params.get("q", "").lower()

    if source:
        opportunities = [o for o in opportunities if o.source.lower() == source]

    if confidence:
        opportunities = [
            o for o in opportunities if (o.confidence or "").lower() == confidence
        ]

    if q:
        opportunities = [
            o
            for o in opportunities
            if q in o.title.lower() or q in (o.normalized_name or "").lower()
        ]

    return opportunities


def _apply_listing_filters(listings, request):
    source = request.query_params.get("source", "").lower()
    q = request.query_params.get("q", "").lower()

    if source:
        listings = [l for l in listings if l.source.lower() == source]

    if q:
        listings = [
            l
            for l in listings
            if q in l.title.lower()
            or q in (l.normalized_name or "").lower()
            or q in (l.search_query or "").lower()
        ]

    return listings


def _pick_selected(request: Request, items, key):
    selected_id = request.query_params.get(key)
    if selected_id:
        for item in items:
            if str(item.id) == selected_id:
                return item
    return items[0] if items else None


def _load_evidence(op):
    if not op or not op.evidence_json:
        return None
    try:
        return json.loads(op.evidence_json)
    except:
        return None


def _opportunity_filters_snapshot(request: Request):
    return {
        "q": request.query_params.get("q", ""),
        "source": request.query_params.get("source", ""),
        "confidence": request.query_params.get("confidence", ""),
        "category": request.query_params.get("category", ""),
    }


def _listing_filters_snapshot(request: Request):
    return {
        "q": request.query_params.get("q", ""),
        "source": request.query_params.get("source", ""),
        "category": request.query_params.get("category", ""),
    }
