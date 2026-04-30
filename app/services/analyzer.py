import json
from statistics import median
from typing import Iterable

from app.config import get_settings
from app.models import Listing, Opportunity
from app.services.normalizer import build_comparable_key
from app.services.filters import is_valid_listing

SHIPPING_ESTIMATE_EUR = 10.0
WALLAPOP_MARKET_OPPORTUNITY_TYPE = "wallapop_market_gap"


# -----------------------------
# 🔥 OUTLIERS (IQR REAL)
# -----------------------------


def remove_outliers(prices: list[float]) -> list[float]:
    if len(prices) < 4:
        return prices

    prices = sorted(prices)

    q1_index = int(len(prices) * 0.25)
    q3_index = int(len(prices) * 0.75)

    q1 = prices[q1_index]
    q3 = prices[q3_index]

    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return [p for p in prices if lower <= p <= upper]


# -----------------------------
# 🔥 URGENCY (MEJORADO)
# -----------------------------


def urgency_score(title: str) -> float:
    title = title.lower()

    score = 0

    keywords_strong = ["urge", "hoy", "ya", "urgente"]
    keywords_medium = ["negociable", "escucho ofertas", "rebajado"]

    for word in keywords_strong:
        if word in title:
            score += 2

    for word in keywords_medium:
        if word in title:
            score += 1

    return score


# -----------------------------
# 🔥 QUALITY SCORE
# -----------------------------


def quality_score(item: Listing) -> float:
    score = 0

    if item.image_url:
        score += 1

    if item.location:
        score += 1

    if item.condition:
        score += 1

    # penalizar títulos sospechosos
    bad_patterns = ["solo", "caja", "pantalla", "repuesto"]

    for p in bad_patterns:
        if p in item.title.lower():
            score -= 2

    return score


# -----------------------------
# 🔥 MAIN
# -----------------------------


def analyze_opportunities(listings: Iterable[Listing]) -> list[Opportunity]:
    grouped: dict[str, list[Listing]] = {}

    # 🔥 FILTRO DE CALIDAD
    for item in listings:
        if not is_valid_listing(item):
            continue

        comparable_key = build_comparable_key(
            item.title,
            fallback_query=item.normalized_name,
        )

        if not comparable_key:
            continue

        grouped.setdefault(comparable_key, []).append(item)

    opportunities: list[Opportunity] = []

    for comparable_key, items in grouped.items():
        if len(items) < 3:
            continue

        prices = [float(item.price) for item in items if item.price is not None]

        prices = remove_outliers(prices)

        if len(prices) < 3:
            continue

        reference_price = float(median(prices))

        for item in items:
            opportunity = _build_opportunity(
                item=item,
                comparable_key=comparable_key,
                reference_price=reference_price,
                comparables=items,
            )

            if opportunity:
                opportunities.append(opportunity)

    opportunities.sort(key=lambda x: x.score, reverse=True)
    return opportunities


# -----------------------------
# 🔥 BUILDER
# -----------------------------


def _build_opportunity(
    *,
    item: Listing,
    comparable_key: str,
    reference_price: float,
    comparables: list[Listing],
) -> Opportunity | None:

    settings = get_settings()

    item_price = float(item.price)

    shipping_estimate = (
        float(item.shipping_cost)
        if item.shipping_cost is not None
        else SHIPPING_ESTIMATE_EUR
    )

    profit_estimate = round(
        reference_price - item_price - shipping_estimate,
        2,
    )

    # ❌ filtro base
    if profit_estimate <= settings.arbitrage_profit_threshold:
        return None

    discount_pct = round((1 - (item_price / reference_price)) * 100, 2)

    # 🔥 SCORES
    urgency = urgency_score(item.title)
    quality = quality_score(item)
    liquidity = len(comparables)

    # 🔥 SCORE PRO (balanceado)
    score = round(
        (profit_estimate * 2.0)
        + (discount_pct * 0.5)
        + (liquidity * 1.5)
        + (urgency * 4)
        + (quality * 2),
        2,
    )

    evidence = {
        "comparable_key": comparable_key,
        "reference_price": reference_price,
        "profit_estimate": profit_estimate,
        "urgency": urgency,
        "quality": quality,
        "liquidity": liquidity,
        "prices_sample": sorted([float(c.price) for c in comparables])[:10],
    }

    return Opportunity(
        title=item.title,
        source=item.source,
        listing_id=item.id,
        source_listing_id=item.id,
        normalized_name=item.normalized_name,
        search_query=item.search_query,
        opportunity_type=WALLAPOP_MARKET_OPPORTUNITY_TYPE,
        buy_it_now=item.buy_it_now,
        buy_price=item_price,
        estimated_resale_price=reference_price,
        profit_estimate=profit_estimate,
        fees_estimate=0,
        shipping_estimate=shipping_estimate,
        liquidity_count=liquidity,
        estimated_sale_price=reference_price,
        expected_profit=profit_estimate,
        discount_pct=discount_pct,
        comparable_count=liquidity,
        confidence=_build_confidence(liquidity, profit_estimate),
        metric_name="smart_wallapop_gap_v2",
        reasoning_summary=(
            f"{item_price}€ vs {reference_price}€ → profit {profit_estimate}€ | "
            f"urgency {urgency} | liquidity {liquidity}"
        ),
        evidence_json=json.dumps(evidence),
        score=score,
        url=item.url,
    )


# -----------------------------
# 🔥 CONFIDENCE
# -----------------------------


def _build_confidence(comparable_count: int, profit: float) -> str:
    if comparable_count >= 6 and profit >= 50:
        return "high"
    if comparable_count >= 4 and profit >= 30:
        return "medium"
    return "low"
