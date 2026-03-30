import json
from statistics import median
from typing import Iterable

from app.models import Listing, Opportunity
from app.services.normalizer import build_family_key, build_normalized_name


def analyze_opportunities(listings: Iterable[Listing]) -> list[Opportunity]:
    grouped: dict[str, list[Listing]] = {}
    family_groups: dict[str, list[Listing]] = {}

    for item in listings:
        normalized_name = build_normalized_name(
            title=item.title,
            fallback_query=item.normalized_name,
        )
        if not normalized_name:
            continue

        grouped.setdefault(normalized_name, []).append(item)
        family_key = build_family_key(item.title, fallback_query=item.normalized_name)
        if family_key:
            family_groups.setdefault(family_key, []).append(item)

    found_opportunities: list[Opportunity] = []

    for normalized_name, items in grouped.items():
        if len(items) < 3:
            continue

        prices = sorted(float(item.price) for item in items if item.price is not None)

        if len(prices) < 3:
            continue

        market_median = float(median(prices))
        family_key = build_family_key(items[0].title, fallback_query=normalized_name)
        family_items = family_groups.get(family_key, items)
        discarded_items = [
            family_item
            for family_item in family_items
            if build_normalized_name(
                title=family_item.title,
                fallback_query=family_item.normalized_name,
            )
            != normalized_name
        ]

        for item in items:
            item_price = float(item.price)
            expected_profit = market_median - item_price

            if item_price <= market_median * 0.88 and expected_profit >= 20:
                discount_pct = round((1 - (item_price / market_median)) * 100, 2)
                score = round(discount_pct + (expected_profit / 10), 2)
                confidence = _build_confidence(
                    comparable_count=len(items),
                    discount_pct=discount_pct,
                    source_count=len({comparable.source for comparable in items}),
                )
                evidence = {
                    "metric": "median",
                    "normalized_name": normalized_name,
                    "family_key": family_key,
                    "comparable_count": len(items),
                    "comparable_prices": prices,
                    "comparables": [
                        {
                            "id": comparable.id,
                            "title": comparable.title,
                            "price": comparable.price,
                            "source": comparable.source,
                            "url": comparable.url,
                            "search_query": comparable.search_query,
                            "last_seen_at": (
                                comparable.last_seen_at.isoformat()
                                if comparable.last_seen_at is not None
                                else None
                            ),
                        }
                        for comparable in sorted(items, key=lambda current: current.price)
                    ],
                    "discarded_count": len(discarded_items),
                    "discarded": [
                        {
                            "id": discarded.id,
                            "title": discarded.title,
                            "price": discarded.price,
                            "source": discarded.source,
                            "reason": "variant mismatch",
                        }
                        for discarded in sorted(discarded_items, key=lambda current: current.price)[
                            :12
                        ]
                    ],
                    "data_sources": sorted({comparable.source for comparable in items}),
                    "search_queries": sorted(
                        {comparable.search_query for comparable in items if comparable.search_query}
                    ),
                    "latest_seen_at": max(
                        (
                            comparable.last_seen_at
                            for comparable in items
                            if comparable.last_seen_at is not None
                        ),
                        default=None,
                    ).isoformat()
                    if any(comparable.last_seen_at is not None for comparable in items)
                    else None,
                    "dataset_scope": "active listings history",
                }
                reasoning_summary = (
                    f"Precio detectado {item_price:.2f} EUR frente a mediana {market_median:.2f} EUR, "
                    f"descuento estimado {discount_pct:.2f}% con {len(items)} comparables."
                )

                found_opportunities.append(
                    Opportunity(
                        title=item.title,
                        source=item.source,
                        listing_id=item.id,
                        normalized_name=normalized_name,
                        search_query=item.search_query,
                        buy_it_now=item.buy_it_now,
                        buy_price=item_price,
                        estimated_sale_price=market_median,
                        expected_profit=expected_profit,
                        discount_pct=discount_pct,
                        comparable_count=len(items),
                        confidence=confidence,
                        metric_name="median",
                        reasoning_summary=reasoning_summary,
                        evidence_json=json.dumps(evidence),
                        score=score,
                        url=item.url,
                    )
                )

    found_opportunities.sort(key=lambda x: x.score, reverse=True)
    return found_opportunities


def _build_confidence(comparable_count: int, discount_pct: float, source_count: int) -> str:
    if comparable_count >= 6 and discount_pct >= 18 and source_count >= 1:
        return "high"
    if comparable_count >= 4 and discount_pct >= 12:
        return "medium"
    return "low"
