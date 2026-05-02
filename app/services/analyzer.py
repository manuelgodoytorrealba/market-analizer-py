import json
import re
from dataclasses import dataclass
from statistics import median
from typing import Iterable

from app.core.config import get_settings
from app.models.entities import Listing, Opportunity
from app.services.category_filters import (
    CategoryFilterResult,
    evaluate_category_listing,
    is_valid_category_listing,
)
from app.services.filters import is_valid_listing
from app.services.normalizer import (
    build_comparable_key,
    detect_category,
    detect_category_confidence,
    detect_subcategory,
)

SHIPPING_ESTIMATE_EUR = 10.0
GENERIC_OPPORTUNITY_TYPE = "generic_market_gap"
ARBITRAGE_OPPORTUNITY_TYPE = "wallapop_to_ebay_arbitrage"
WALLAPOP_MARKET_OPPORTUNITY_TYPE = "wallapop_market_gap"

CATEGORY_MIN_COMPARABLES = {
    "smartphones": 6,
    "consoles": 4,
    "gpus": 3,
    "laptops": 3,
    "audio": 3,
    "cameras": 3,
    "wearables": 3,
    "sneakers": 3,
    "unknown": 3,
}


@dataclass(frozen=True)
class MarketStats:
    median_price: float
    p25: float
    p75: float
    spread: float
    volatility_ratio: float
    comparable_count: int
    prices: list[float]


@dataclass(frozen=True)
class OpportunitySignals:
    confidence_score: float
    liquidity_score: float
    competition_pressure: float
    competition_density: float
    market_speed_score: float
    speed_category: str
    speed_penalty: float
    roi: float
    capital_efficiency_score: float
    investment_size: str
    capital_risk: str
    capital_penalty: float
    capital_efficiency_details: dict[str, float | str]
    urgency_score: float
    risk_score: float
    listing_quality_score: float
    description_risk_score: float
    volatility_penalty: float
    liquidity_details: dict[str, float]
    market_speed_details: dict[str, float | str]
    listing_quality_details: dict[str, object]
    description_risk_details: dict[str, object]
    category_filter_details: dict[str, object]


def remove_outliers(prices: list[float]) -> list[float]:
    if len(prices) < 4:
        return prices

    sorted_prices = sorted(prices)
    q1 = _percentile(sorted_prices, 25)
    q3 = _percentile(sorted_prices, 75)
    iqr = q3 - q1

    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    return [price for price in sorted_prices if lower <= price <= upper]


def build_market_stats(prices: list[float]) -> MarketStats | None:
    clean_prices = remove_outliers([float(price) for price in prices if price > 0])

    if not clean_prices:
        return None

    sorted_prices = sorted(clean_prices)
    median_price = float(median(sorted_prices))
    p25 = _percentile(sorted_prices, 25)
    p75 = _percentile(sorted_prices, 75)
    spread = p75 - p25
    volatility_ratio = spread / median_price if median_price > 0 else 1.0

    return MarketStats(
        median_price=round(median_price, 2),
        p25=round(p25, 2),
        p75=round(p75, 2),
        spread=round(spread, 2),
        volatility_ratio=round(volatility_ratio, 4),
        comparable_count=len(sorted_prices),
        prices=sorted_prices,
    )


def confidence_score(stats: MarketStats) -> float:
    count_component = min(stats.comparable_count / 8, 1.0) * 6.0
    stability_component = max(0.0, 1.0 - min(stats.volatility_ratio / 0.35, 1.0)) * 4.0
    return round(count_component + stability_component, 2)


def liquidity_score(stats: MarketStats) -> float:
    return compute_liquidity(stats)["score"]


def compute_liquidity(stats: MarketStats) -> dict[str, float]:
    if stats.comparable_count < 3:
        return {
            "score": 0.0,
            "count_component": 0.0,
            "stability_component": 0.0,
            "consistency_component": 0.0,
        }

    count_component = min(stats.comparable_count / 10, 1.0) * 7.0
    stability_component = max(0.0, 1.0 - min(stats.volatility_ratio / 0.45, 1.0)) * 3.0
    consistency_component = _price_consistency_component(stats)
    score = min(count_component + stability_component + consistency_component, 10.0)
    return {
        "score": round(score, 2),
        "count_component": round(count_component, 2),
        "stability_component": round(stability_component, 2),
        "consistency_component": round(consistency_component, 2),
    }


def compute_competition_pressure(
    comparables: list[Listing],
    reference_price: float,
) -> float:
    density = compute_competition_density(comparables, reference_price)
    near_reference_count = _count_prices_in_sale_range(comparables, reference_price)
    saturation_pressure = near_reference_count * 0.9
    density_pressure = density * 8.0
    return round(min(saturation_pressure + density_pressure, 12.0), 2)


def compute_competition_density(
    comparables: list[Listing],
    reference_price: float,
) -> float:
    prices = _listing_prices(comparables)
    if not prices or reference_price <= 0:
        return 0.0
    competing = _count_prices_in_sale_range(comparables, reference_price)
    return round(competing / len(prices), 4)


def compute_market_speed(
    comparables: list[Listing],
    reference_price: float | None = None,
    stats: MarketStats | None = None,
) -> dict[str, float | str]:
    prices = _listing_prices(comparables)
    if not prices:
        return {
            "score": 0.0,
            "speed_category": "slow",
            "competition_density": 0.0,
            "near_reference_count": 0.0,
            "below_reference_ratio": 0.0,
            "count_component": 0.0,
            "consistency_component": 0.0,
            "competition_component": 0.0,
            "price_pressure_component": 0.0,
        }

    reference = reference_price if reference_price is not None else float(median(prices))
    market_stats = stats or build_market_stats(prices)
    volatility_ratio = market_stats.volatility_ratio if market_stats else 1.0
    total = len(prices)
    competition_density_value = compute_competition_density(comparables, reference)
    near_reference_count = _count_prices_in_sale_range(comparables, reference)
    below_reference_ratio = (
        len([price for price in prices if price < reference]) / total
        if reference > 0
        else 1.0
    )

    count_component = _speed_count_component(total)
    consistency_component = max(0.0, 1.0 - min(volatility_ratio / 0.35, 1.0)) * 3.0
    competition_component = max(0.0, 1.0 - min(competition_density_value / 0.65, 1.0)) * 2.0
    price_pressure_component = max(0.0, 1.0 - min(below_reference_ratio / 0.7, 1.0)) * 1.0
    score = _clamp(
        count_component
        + consistency_component
        + competition_component
        + price_pressure_component,
        0.0,
        10.0,
    )

    return {
        "score": round(score, 2),
        "speed_category": _speed_category(score),
        "competition_density": competition_density_value,
        "near_reference_count": float(near_reference_count),
        "below_reference_ratio": round(below_reference_ratio, 4),
        "count_component": round(count_component, 2),
        "consistency_component": round(consistency_component, 2),
        "competition_component": round(competition_component, 2),
        "price_pressure_component": round(price_pressure_component, 2),
    }


def _legacy_competition_pressure(
    comparables: list[Listing],
    reference_price: float,
) -> float:
    lower_bound = reference_price * 0.9
    upper_bound = reference_price * 1.1
    competing = 0

    for comparable in comparables:
        if comparable.price is None:
            continue
        price = float(comparable.price)
        if lower_bound <= price <= upper_bound:
            competing += 1

    return round(min(competing * 1.25, 12.0), 2)


def competition_score(
    item: Listing,
    comparables: list[Listing],
    resale_price: float,
) -> float:
    competitors = [
        comparable
        for comparable in comparables
        if comparable.id != item.id
    ]
    return compute_competition_pressure(competitors, resale_price)


def urgency_score(title: str, price: float | None = None) -> float:
    normalized_title = (title or "").lower()

    score = 0.0
    strong_keywords = ["urge", "urgente", "hoy", "ya", "liquidacion"]
    medium_keywords = ["negociable", "escucho ofertas", "rebajado", "oferta", "fin mes"]

    for keyword in strong_keywords:
        if keyword in normalized_title:
            score += 2.0

    for keyword in medium_keywords:
        if keyword in normalized_title:
            score += 1.0

    if _has_odd_price_signal(normalized_title, price):
        score += 0.75

    if _has_low_quality_title_signal(normalized_title):
        score += 0.5

    return round(min(score, 10.0), 2)


def risk_score(
    item: Listing,
    stats: MarketStats,
    category_filter: CategoryFilterResult | None = None,
) -> float:
    score = 0.0
    item_price = float(item.price)

    if has_extreme_underprice_risk(item_price, stats):
        score += 7.0
    elif item_price < stats.p25 * 0.65:
        score += 4.0
    elif item_price < stats.p25 * 0.8:
        score += 1.5

    score += volatility_penalty(stats)

    if stats.comparable_count < 4:
        score += 2.0
    elif stats.comparable_count < 6:
        score += 1.0

    if not item.image_url:
        score += 1.0
    if not item.location and not item.seller_location:
        score += 0.75
    if not item.condition:
        score += 0.75

    suspicious_terms = [
        "solo",
        "caja",
        "pantalla",
        "repuesto",
        "bloqueado",
        "icloud",
        "piezas",
        "placa base",
    ]
    title = (item.title or "").lower()
    if any(term in title for term in suspicious_terms):
        score += 2.0

    score += analyze_description_risk(_description_text(item))["score"]
    score += max(0.0, 5.0 - listing_quality_score(item)["score"]) * 0.35
    if category_filter:
        score += category_filter.risk_score_boost

    return round(min(score, 10.0), 2)


def listing_quality_score(item: Listing) -> dict[str, object]:
    title = (item.title or "").strip()
    normalized_name = (item.normalized_name or "").strip().lower()
    title_lower = title.lower()
    score = 5.0
    flags: list[str] = []

    word_count = len(title.split())
    if 4 <= word_count <= 12:
        score += 1.5
    elif word_count < 3:
        score -= 1.5
        flags.append("short_title")
    elif word_count > 18:
        score -= 0.75
        flags.append("long_title")

    if item.condition:
        score += 1.0
    else:
        score -= 0.5
        flags.append("missing_condition")

    if item.image_url:
        score += 1.0
    else:
        score -= 0.75
        flags.append("missing_image")

    if item.location or item.seller_location:
        score += 0.5
    else:
        score -= 0.5
        flags.append("missing_location")

    if normalized_name:
        normalized_tokens = [token for token in normalized_name.split() if len(token) > 2]
        if normalized_tokens and all(token in title_lower for token in normalized_tokens[:2]):
            score += 1.0
        else:
            score -= 1.0
            flags.append("weak_name_coherence")

    suspicious_terms = {
        "leer": 1.5,
        "solo hoy": 0.75,
        "urge": 0.5,
        "urgente": 0.5,
        "pantalla": 2.0,
        "no funciona": 4.0,
        "roto": 4.0,
        "averiado": 4.0,
        "piezas": 5.0,
        "placa base": 5.0,
        "repuesto": 5.0,
    }
    for term, penalty in suspicious_terms.items():
        if term in title_lower:
            score -= penalty
            flags.append(term)

    return {
        "score": round(_clamp(score, 0.0, 10.0), 2),
        "flags": flags,
    }


def analyze_description_risk(text: str) -> dict[str, object]:
    normalized = (text or "").lower()
    terms = {
        "no funciona": 5.0,
        "para piezas": 5.0,
        "piezas": 4.0,
        "bloqueado": 4.0,
        "leer bien": 3.0,
        "leer": 1.5,
        "icloud": 5.0,
        "pantalla rota": 4.0,
        "sin probar": 3.0,
        "placa base": 5.0,
        "repuesto": 4.0,
    }
    matched: list[str] = []
    score = 0.0

    for term, value in terms.items():
        if term in normalized:
            matched.append(term)
            score += value

    return {
        "score": round(min(score, 10.0), 2),
        "matched_terms": matched,
        "has_text": bool(normalized.strip()),
    }


def volatility_penalty(stats: MarketStats) -> float:
    if stats.volatility_ratio > 0.4:
        return 8.0
    if stats.volatility_ratio > 0.3:
        return 5.0
    if stats.volatility_ratio > 0.2:
        return 2.0
    return 0.0


def price_position(item_price: float, stats: MarketStats) -> float:
    if stats.p75 == stats.p25:
        return 0.0 if item_price <= stats.p25 else 1.0

    position = (item_price - stats.p25) / (stats.p75 - stats.p25)
    return round(_clamp(position, 0.0, 1.0), 4)


def underpricing_score(item_price: float, stats: MarketStats) -> float:
    if stats.median_price <= 0:
        return 0.0

    return round((stats.median_price - item_price) / stats.median_price, 4)


def roi_score(profit_estimate: float, item_price: float) -> float:
    if item_price <= 0:
        return 0.0
    return round(profit_estimate / item_price, 4)


def compute_capital_efficiency(
    *,
    item_price: float,
    profit_estimate: float,
    market_speed_score: float,
    speed_category: str,
) -> dict[str, float | str]:
    roi = roi_score(profit_estimate, item_price)
    roi_component = min(max(roi, 0.0) / 0.5, 1.0) * 5.0
    price_component = _capital_price_component(item_price)
    speed_component = min(max(market_speed_score, 0.0) / 10.0, 1.0) * 2.0
    raw_score = _clamp(
        roi_component + price_component + speed_component,
        0.0,
        10.0,
    )
    score = raw_score * _capital_speed_multiplier(speed_category)
    investment_size = _investment_size(item_price)
    capital_risk = _capital_risk(item_price, roi, speed_category)

    return {
        "roi": roi,
        "score": round(_clamp(score, 0.0, 10.0), 2),
        "investment_size": investment_size,
        "capital_risk": capital_risk,
        "capital_penalty": _capital_penalty(item_price, roi, speed_category),
        "speed_multiplier": _capital_speed_multiplier(speed_category),
        "roi_component": round(roi_component, 2),
        "price_component": round(price_component, 2),
        "speed_component": round(speed_component, 2),
    }


def has_extreme_underprice_risk(item_price: float, stats: MarketStats) -> bool:
    return item_price < stats.p25 * 0.5


def has_blocking_listing_risk(item: Listing) -> bool:
    text = " ".join(
        [
            item.title or "",
            item.normalized_name or "",
            _description_text(item),
        ]
    ).lower()
    blocking_terms = [
        "no funciona",
        "para piezas",
        "piezas",
        "placa base",
        "pantalla rota",
        "repuesto",
        "bloqueado",
        "icloud",
        "averiado",
        "roto",
    ]
    return any(term in text for term in blocking_terms)


def analyze_opportunities(listings: Iterable[Listing]) -> list[Opportunity]:
    settings = get_settings()
    grouped: dict[str, list[Listing]] = {}

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
        raw_prices = [float(item.price) for item in items if item.price is not None]
        stats = build_market_stats(raw_prices)

        if stats is None:
            continue
        category = _group_category(items)
        if stats.comparable_count < _min_comparables_for_category(category):
            continue
        if stats.volatility_ratio > settings.analyzer_max_volatility_ratio:
            continue

        for item in items:
            if not is_valid_category_listing(item):
                continue
            if has_blocking_listing_risk(item):
                continue
            if has_extreme_underprice_risk(float(item.price), stats):
                continue

            opportunity = _build_opportunity(
                item=item,
                comparable_key=comparable_key,
                stats=stats,
                comparables=items,
            )

            if opportunity:
                opportunities.append(opportunity)

    opportunities.sort(key=lambda opportunity: opportunity.score, reverse=True)
    return opportunities


def _build_opportunity(
    *,
    item: Listing,
    comparable_key: str,
    stats: MarketStats,
    comparables: list[Listing],
) -> Opportunity | None:
    settings = get_settings()
    item_price = float(item.price)
    shipping_estimate = (
        float(item.shipping_cost)
        if item.shipping_cost is not None
        else SHIPPING_ESTIMATE_EUR
    )

    profit_estimate = round(stats.median_price - item_price - shipping_estimate, 2)
    if profit_estimate <= settings.arbitrage_profit_threshold:
        return None

    discount_pct = round((1 - (item_price / stats.median_price)) * 100, 2)
    signals = _build_signals(
        item=item,
        stats=stats,
        comparables=comparables,
        profit_estimate=profit_estimate,
    )
    score = _score_opportunity(profit_estimate=profit_estimate, signals=signals)

    evidence = _build_evidence(
        item=item,
        comparable_key=comparable_key,
        stats=stats,
        profit_estimate=profit_estimate,
        discount_pct=discount_pct,
        signals=signals,
        comparables=comparables,
    )

    confidence_label = _build_confidence_label(
        signals.confidence_score,
        signals.risk_score,
    )

    return Opportunity(
        title=item.title,
        source=item.source,
        listing_id=item.id,
        source_listing_id=item.id,
        normalized_name=item.normalized_name,
        search_query=item.search_query,
        opportunity_type=_opportunity_type(item, comparables),
        buy_it_now=item.buy_it_now,
        buy_price=item_price,
        estimated_resale_price=stats.median_price,
        profit_estimate=profit_estimate,
        fees_estimate=0,
        shipping_estimate=shipping_estimate,
        liquidity_count=stats.comparable_count,
        estimated_sale_price=stats.median_price,
        expected_profit=profit_estimate,
        discount_pct=discount_pct,
        comparable_count=stats.comparable_count,
        confidence=confidence_label,
        metric_name="wallapop_flipping_v5",
        reasoning_summary=(
            f"{item_price}€ vs {stats.median_price}€ median | "
            f"profit {profit_estimate}€ | roi {signals.roi} | "
            f"capital {signals.capital_efficiency_score} | confidence {signals.confidence_score} | "
            f"risk {signals.risk_score} | competition {signals.competition_pressure} | "
            f"speed {signals.market_speed_score} {signals.speed_category}"
        ),
        evidence_json=json.dumps(evidence),
        score=score,
        url=item.url,
    )


def _build_signals(
    *,
    item: Listing,
    stats: MarketStats,
    comparables: list[Listing],
    profit_estimate: float,
) -> OpportunitySignals:
    category_filter = evaluate_category_listing(item)
    market_speed = compute_market_speed(comparables, stats.median_price, stats)
    competition_pressure = competition_score(item, comparables, stats.median_price)
    competition_density = float(market_speed["competition_density"])
    market_speed_score = float(market_speed["score"])
    capital_efficiency = compute_capital_efficiency(
        item_price=float(item.price),
        profit_estimate=profit_estimate,
        market_speed_score=market_speed_score,
        speed_category=str(market_speed["speed_category"]),
    )
    return OpportunitySignals(
        confidence_score=confidence_score(stats),
        liquidity_score=liquidity_score(stats),
        competition_pressure=competition_pressure,
        competition_density=competition_density,
        market_speed_score=market_speed_score,
        speed_category=str(market_speed["speed_category"]),
        speed_penalty=_market_speed_penalty(
            competition_pressure,
            competition_density,
            market_speed_score,
        ),
        roi=float(capital_efficiency["roi"]),
        capital_efficiency_score=float(capital_efficiency["score"]),
        investment_size=str(capital_efficiency["investment_size"]),
        capital_risk=str(capital_efficiency["capital_risk"]),
        capital_penalty=float(capital_efficiency["capital_penalty"]),
        capital_efficiency_details=capital_efficiency,
        urgency_score=urgency_score(item.title, item.price),
        risk_score=risk_score(item, stats, category_filter),
        listing_quality_score=float(listing_quality_score(item)["score"]),
        description_risk_score=float(analyze_description_risk(_description_text(item))["score"]),
        volatility_penalty=volatility_penalty(stats),
        liquidity_details=compute_liquidity(stats),
        market_speed_details=market_speed,
        listing_quality_details=listing_quality_score(item),
        description_risk_details=analyze_description_risk(_description_text(item)),
        category_filter_details={
            "category_filter_reason": category_filter.category_filter_reason,
            "category_risk_flags": category_filter.category_risk_flags,
            "risk_score_boost": category_filter.risk_score_boost,
        },
    )


def _score_opportunity(
    *,
    profit_estimate: float,
    signals: OpportunitySignals,
) -> float:
    settings = get_settings()
    score = (
        (profit_estimate * settings.analyzer_profit_weight)
        + (signals.confidence_score * settings.analyzer_confidence_weight)
        + (signals.liquidity_score * settings.analyzer_liquidity_weight)
        + (signals.urgency_score * settings.analyzer_urgency_weight)
        + (signals.market_speed_score * settings.analyzer_speed_weight)
        + (signals.capital_efficiency_score * settings.analyzer_capital_weight)
        - (signals.risk_score * settings.analyzer_risk_weight)
        - (signals.competition_pressure * settings.analyzer_competition_weight)
        - signals.volatility_penalty
        - signals.speed_penalty
        - signals.capital_penalty
    )
    return round(score, 2)


def _build_evidence(
    *,
    item: Listing,
    comparable_key: str,
    stats: MarketStats,
    profit_estimate: float,
    discount_pct: float,
    signals: OpportunitySignals,
    comparables: list[Listing],
) -> dict:
    item_price = float(item.price)
    category = detect_category(item.title, item.search_query or item.normalized_name)
    category_confidence = detect_category_confidence(
        item.title,
        item.search_query or item.normalized_name,
    )
    subcategory = detect_subcategory(item.title, item.search_query or item.normalized_name)
    return {
        "category": category,
        "category_confidence": category_confidence,
        "subcategory": subcategory,
        "comparable_key": comparable_key,
        "item_price": item_price,
        "reference_price": stats.median_price,
        "median_price": stats.median_price,
        "p25": stats.p25,
        "p75": stats.p75,
        "spread": stats.spread,
        "volatility_ratio": stats.volatility_ratio,
        "price_position": price_position(item_price, stats),
        "underpricing_score": underpricing_score(item_price, stats),
        "comparable_count": stats.comparable_count,
        "confidence_score": signals.confidence_score,
        "risk_score": signals.risk_score,
        "liquidity_score": signals.liquidity_score,
        "liquidity_details": signals.liquidity_details,
        "competition_score": signals.competition_pressure,
        "competition_pressure": signals.competition_pressure,
        "competition_density": signals.competition_density,
        "market_speed_score": signals.market_speed_score,
        "speed_category": signals.speed_category,
        "market_speed_details": signals.market_speed_details,
        "speed_penalty": signals.speed_penalty,
        "roi": signals.roi,
        "capital_efficiency_score": signals.capital_efficiency_score,
        "investment_size": signals.investment_size,
        "capital_risk": signals.capital_risk,
        "capital_penalty": signals.capital_penalty,
        "capital_efficiency_details": signals.capital_efficiency_details,
        "urgency_score": signals.urgency_score,
        "listing_quality_score": signals.listing_quality_score,
        "listing_quality_details": signals.listing_quality_details,
        "description_risk_score": signals.description_risk_score,
        "description_risk_details": signals.description_risk_details,
        "category_filter_reason": signals.category_filter_details["category_filter_reason"],
        "category_risk_flags": signals.category_filter_details["category_risk_flags"],
        "category_risk_score_boost": signals.category_filter_details["risk_score_boost"],
        "volatility_penalty": signals.volatility_penalty,
        "extreme_underprice_risk": has_extreme_underprice_risk(item_price, stats),
        "profit_estimate": profit_estimate,
        "discount_pct": discount_pct,
        "prices_sample": stats.prices[:10],
        "listing_signals": {
            "has_image": bool(item.image_url),
            "has_location": bool(item.location or item.seller_location),
            "has_condition": bool(item.condition),
            "odd_price": _has_odd_price_signal(item.title or "", item.price),
            "low_quality_title": _has_low_quality_title_signal(item.title or ""),
        },
        "comparables": [
            {
                "id": comparable.id,
                "source": comparable.source,
                "title": comparable.title,
                "price": float(comparable.price),
                "url": comparable.url,
                "search_query": comparable.search_query,
                "condition": comparable.condition,
                "shipping_cost": comparable.shipping_cost,
            }
            for comparable in comparables
            if comparable.price is not None
        ][:12],
    }


def _build_confidence_label(confidence: float, risk: float) -> str:
    if confidence >= 7.5 and risk <= 3.5:
        return "high"
    if confidence >= 5.0 and risk <= 6.0:
        return "medium"
    return "low"


def _group_category(items: list[Listing]) -> str:
    counts: dict[str, int] = {}
    for item in items:
        category = detect_category(item.title, item.search_query or item.normalized_name)
        counts[category] = counts.get(category, 0) + 1
    return max(counts, key=counts.get) if counts else "unknown"


def _min_comparables_for_category(category: str) -> int:
    settings = get_settings()
    category_minimum = CATEGORY_MIN_COMPARABLES.get(category, CATEGORY_MIN_COMPARABLES["unknown"])
    return max(settings.arbitrage_min_comparables, category_minimum)


def _opportunity_type(item: Listing, comparables: list[Listing]) -> str:
    sources = {comparable.source for comparable in comparables}
    if item.source == "wallapop" and "ebay" in sources:
        return ARBITRAGE_OPPORTUNITY_TYPE
    if item.source == "wallapop":
        return WALLAPOP_MARKET_OPPORTUNITY_TYPE
    return GENERIC_OPPORTUNITY_TYPE


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    position = (len(sorted_values) - 1) * (percentile / 100)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(sorted_values) - 1)
    fraction = position - lower_index
    value = sorted_values[lower_index] + (
        (sorted_values[upper_index] - sorted_values[lower_index]) * fraction
    )
    return float(value)


def _price_consistency_component(stats: MarketStats) -> float:
    if stats.median_price <= 0:
        return 0.0
    tight_range_ratio = (stats.p75 - stats.p25) / stats.median_price
    return max(0.0, 1.0 - min(tight_range_ratio / 0.2, 1.0)) * 2.0


def _listing_prices(comparables: list[Listing]) -> list[float]:
    return [
        float(comparable.price)
        for comparable in comparables
        if comparable.price is not None and float(comparable.price) > 0
    ]


def _count_prices_in_sale_range(
    comparables: list[Listing],
    reference_price: float,
) -> int:
    lower_bound = reference_price * 0.9
    upper_bound = reference_price * 1.1
    return len(
        [
            price
            for price in _listing_prices(comparables)
            if lower_bound <= price <= upper_bound
        ]
    )


def _speed_count_component(count: int) -> float:
    if count <= 5:
        return 4.0
    if count <= 10:
        return 2.75
    if count <= 15:
        return 1.5
    if count <= 25:
        return 0.75
    return 0.25


def _speed_category(score: float) -> str:
    if score >= 7.0:
        return "fast"
    if score >= 4.5:
        return "medium"
    return "slow"


def _market_speed_penalty(
    competition_pressure: float,
    competition_density: float,
    market_speed_score: float,
) -> float:
    if market_speed_score <= 3.0 and (
        competition_pressure >= 10.0 or competition_density >= 0.65
    ):
        return 90.0
    if market_speed_score <= 4.5 and (
        competition_pressure >= 8.0 or competition_density >= 0.5
    ):
        return 45.0
    return 0.0


def _capital_price_component(item_price: float) -> float:
    if item_price <= 250:
        return 3.0
    if item_price <= 500:
        return 2.25
    if item_price <= 800:
        return 1.25
    if item_price <= 1200:
        return 0.5
    return 0.0


def _investment_size(item_price: float) -> str:
    if item_price <= 250:
        return "low"
    if item_price <= 600:
        return "medium"
    if item_price <= 1200:
        return "high"
    return "very_high"


def _capital_risk(item_price: float, roi: float, speed_category: str) -> str:
    if item_price > 1200 and speed_category != "fast":
        return "very_high"
    if item_price > 800 and speed_category == "slow":
        return "high"
    if item_price > 400 and speed_category == "slow":
        return "high"
    if roi < 0.18 and item_price > 500:
        return "high"
    if roi >= 0.3 and item_price <= 600 and speed_category in {"fast", "medium"}:
        return "low"
    return "medium"


def _capital_penalty(item_price: float, roi: float, speed_category: str) -> float:
    if item_price > 1500 and speed_category != "fast":
        return 650.0
    if item_price > 1000 and speed_category == "slow":
        return 300.0
    if item_price > 800 and speed_category == "slow":
        return 180.0
    if item_price >= 500 and speed_category == "slow":
        return 220.0
    if item_price >= 400 and speed_category == "slow":
        return 140.0
    if item_price > 600 and roi < 0.2:
        return 90.0
    return 0.0


def _capital_speed_multiplier(speed_category: str) -> float:
    if speed_category == "fast":
        return 1.0
    if speed_category == "medium":
        return 0.85
    return 0.5


def _description_text(item: Listing) -> str:
    values = [
        getattr(item, "description", ""),
        getattr(item, "snippet", ""),
        getattr(item, "summary", ""),
    ]
    return " ".join(str(value) for value in values if value)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _has_odd_price_signal(text: str, price: float | None = None) -> bool:
    if price is not None:
        rounded_price = int(round(float(price)))
        if rounded_price % 100 in {9, 49, 90, 95, 99}:
            return True

    prices = re.findall(r"\b\d{2,5}\b", text.lower())
    return any(price.endswith(("9", "99", "95")) for price in prices)


def _has_low_quality_title_signal(text: str) -> bool:
    normalized = (text or "").strip()
    if not normalized:
        return True
    words = normalized.split()
    if len(words) <= 3:
        return True
    alpha_chars = [char for char in normalized if char.isalpha()]
    if not alpha_chars:
        return True
    uppercase_ratio = sum(char.isupper() for char in alpha_chars) / len(alpha_chars)
    return uppercase_ratio > 0.75
