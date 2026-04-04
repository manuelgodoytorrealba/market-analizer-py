import json
from statistics import median
from typing import Iterable

from app.config import get_settings
from app.models import Listing, Opportunity
from app.services.normalizer import build_comparable_key, extract_iphone_specs


SHIPPING_ESTIMATE_EUR = 10.0
GENERIC_OPPORTUNITY_TYPE = "generic_market_gap"
ARBITRAGE_OPPORTUNITY_TYPE = "wallapop_to_ebay_arbitrage"


def analyze_opportunities(listings: Iterable[Listing]) -> list[Opportunity]:
    grouped: dict[str, list[Listing]] = {}
    group_specs: dict[str, dict[str, str]] = {}

    for item in listings:
        specs = extract_iphone_specs(item.title, fallback_query=item.normalized_name)
        if specs is None:
            continue

        comparable_key = build_comparable_key(item.title, fallback_query=item.normalized_name)
        grouped.setdefault(comparable_key, []).append(item)
        group_specs[comparable_key] = specs

    found_opportunities: list[Opportunity] = []
    found_opportunities.extend(_analyze_generic_opportunities(grouped, group_specs))
    found_opportunities.extend(_analyze_wallapop_to_ebay_arbitrage(grouped, group_specs))
    found_opportunities.sort(key=lambda x: x.score, reverse=True)
    return found_opportunities


def _analyze_generic_opportunities(
    grouped: dict[str, list[Listing]],
    group_specs: dict[str, dict[str, str]],
) -> list[Opportunity]:
    settings = get_settings()
    opportunities: list[Opportunity] = []

    for comparable_key, items in grouped.items():
        generic_items = [item for item in items if item.source != "wallapop"]
        if len(generic_items) < settings.arbitrage_min_comparables:
            continue

        prices = sorted(float(item.price) for item in generic_items if item.price is not None)
        if len(prices) < settings.arbitrage_min_comparables:
            continue

        estimated_resale_price = float(median(prices))
        specs = group_specs[comparable_key]

        for item in generic_items:
            opportunity = _build_opportunity(
                item=item,
                comparable_key=comparable_key,
                specs=specs,
                reference_price=estimated_resale_price,
                comparables=generic_items,
                fee_rate=settings.arbitrage_fee_rate,
                min_profit=settings.arbitrage_profit_threshold,
                opportunity_type=GENERIC_OPPORTUNITY_TYPE,
                metric_name="median_profit",
                reference_source="mixed_market",
                liquidity_count=len(generic_items),
            )
            if opportunity is not None:
                opportunities.append(opportunity)

    return opportunities


def _analyze_wallapop_to_ebay_arbitrage(
    grouped: dict[str, list[Listing]],
    group_specs: dict[str, dict[str, str]],
) -> list[Opportunity]:
    settings = get_settings()
    opportunities: list[Opportunity] = []

    for comparable_key, items in grouped.items():
        wallapop_items = [item for item in items if item.source == "wallapop"]
        ebay_items = [item for item in items if item.source == "ebay"]
        if not wallapop_items or len(ebay_items) < settings.arbitrage_min_comparables:
            continue

        ebay_prices = sorted(float(item.price) for item in ebay_items if item.price is not None)
        if len(ebay_prices) < settings.arbitrage_min_comparables:
            continue

        ebay_reference_price = float(median(ebay_prices))
        specs = group_specs[comparable_key]

        for item in wallapop_items:
            opportunity = _build_opportunity(
                item=item,
                comparable_key=comparable_key,
                specs=specs,
                reference_price=ebay_reference_price,
                comparables=ebay_items,
                fee_rate=settings.arbitrage_fee_rate,
                min_profit=settings.arbitrage_profit_threshold,
                opportunity_type=ARBITRAGE_OPPORTUNITY_TYPE,
                metric_name="wallapop_to_ebay_arbitrage",
                reference_source="ebay",
                liquidity_count=len(ebay_items),
            )
            if opportunity is not None:
                opportunities.append(opportunity)

    return opportunities


def _build_opportunity(
    *,
    item: Listing,
    comparable_key: str,
    specs: dict[str, str],
    reference_price: float,
    comparables: list[Listing],
    fee_rate: float,
    min_profit: float,
    opportunity_type: str,
    metric_name: str,
    reference_source: str,
    liquidity_count: int,
) -> Opportunity | None:
    item_price = float(item.price)
    fees_estimate = round(reference_price * fee_rate, 2)
    shipping_estimate = round(
        float(item.shipping_cost) if item.shipping_cost is not None else SHIPPING_ESTIMATE_EUR,
        2,
    )
    profit_estimate = round(
        reference_price - item_price - fees_estimate - shipping_estimate,
        2,
    )

    if profit_estimate <= min_profit:
        return None

    discount_pct = round((1 - (item_price / reference_price)) * 100, 2)
    score = round((profit_estimate * 1.5) + (discount_pct * 0.25), 2)
    confidence = _build_confidence(
        comparable_count=len(comparables),
        profit_estimate=profit_estimate,
        source_count=len({comparable.source for comparable in comparables}),
    )

    evidence = {
        "metric": metric_name,
        "opportunity_type": opportunity_type,
        "normalized_name": specs["normalized_name"],
        "model": specs["model"],
        "capacity": specs["capacity"],
        "comparable_key": comparable_key,
        "source_listing_id": item.id,
        "reference_source": reference_source,
        "comparable_count": len(comparables),
        "liquidity_signal": {
            "type": "active_market_comparables",
            "count": liquidity_count,
            "sold_count": None,
            "status": "proxy",
        },
        "comparable_prices": sorted(float(comparable.price) for comparable in comparables),
        "ebay_reference_price": reference_price if reference_source == "ebay" else None,
        "estimated_resale_price": reference_price,
        "fees_estimate": fees_estimate,
        "shipping_estimate": shipping_estimate,
        "profit_estimate": profit_estimate,
        "comparables": [
            {
                "id": comparable.id,
                "title": comparable.title,
                "price": comparable.price,
                "source": comparable.source,
                "url": comparable.url,
                "search_query": comparable.search_query,
                "condition": comparable.condition,
                "shipping_cost": comparable.shipping_cost,
                "last_seen_at": (
                    comparable.last_seen_at.isoformat()
                    if comparable.last_seen_at is not None
                    else None
                ),
            }
            for comparable in sorted(comparables, key=lambda current: current.price)
        ],
        "data_sources": sorted({comparable.source for comparable in comparables}),
        "conditions": sorted(
            {
                comparable.condition
                for comparable in comparables
                if comparable.condition
            }
        ),
        "shipping_regions": sorted(
            {
                comparable.shipping_region
                for comparable in comparables
                if comparable.shipping_region
            }
        ),
        "seller_locations": sorted(
            {
                comparable.seller_location
                for comparable in comparables
                if comparable.seller_location
            }
        )[:12],
        "search_queries": sorted(
            {comparable.search_query for comparable in comparables if comparable.search_query}
        ),
        "latest_seen_at": max(
            (
                comparable.last_seen_at
                for comparable in comparables
                if comparable.last_seen_at is not None
            ),
            default=None,
        ).isoformat()
        if any(comparable.last_seen_at is not None for comparable in comparables)
        else None,
        "dataset_scope": "active listings same model and capacity",
    }
    reasoning_summary = (
        f"Compra {item_price:.2f} EUR desde {item.source}, reventa estimada {reference_price:.2f} EUR "
        f"en {reference_source}, fees {fees_estimate:.2f} EUR, envío {shipping_estimate:.2f} EUR, "
        f"profit estimado {profit_estimate:.2f} EUR con {len(comparables)} comparables."
    )

    return Opportunity(
        title=item.title,
        source=item.source,
        listing_id=item.id,
        source_listing_id=item.id,
        normalized_name=specs["normalized_name"],
        search_query=item.search_query,
        opportunity_type=opportunity_type,
        buy_it_now=item.buy_it_now,
        buy_price=item_price,
        estimated_resale_price=reference_price,
        profit_estimate=profit_estimate,
        fees_estimate=fees_estimate,
        shipping_estimate=shipping_estimate,
        liquidity_count=liquidity_count,
        estimated_sale_price=reference_price,
        expected_profit=profit_estimate,
        discount_pct=discount_pct,
        comparable_count=len(comparables),
        confidence=confidence,
        metric_name=metric_name,
        reasoning_summary=reasoning_summary,
        evidence_json=json.dumps(evidence),
        score=score,
        url=item.url,
    )


def _build_confidence(comparable_count: int, profit_estimate: float, source_count: int) -> str:
    if comparable_count >= 6 and profit_estimate >= 45 and source_count >= 1:
        return "high"
    if comparable_count >= 4 and profit_estimate >= 30:
        return "medium"
    return "low"
