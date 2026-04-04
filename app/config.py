from dataclasses import dataclass
from functools import lru_cache
import os


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str
    runtime_interval_seconds: int
    dashboard_refresh_seconds: int
    log_level: str
    ebay_provider: str
    enable_wallapop: bool
    request_timeout_seconds: float
    retry_attempts: int
    backoff_base_seconds: float
    user_agent: str
    ebay_search_max_items: int
    ebay_buy_it_now_only: bool
    wallapop_search_latitude: float
    wallapop_search_longitude: float
    wallapop_search_order_by: str
    arbitrage_fee_rate: float
    arbitrage_profit_threshold: float
    arbitrage_min_comparables: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("MARKET_ANALYZER_DB_URL", "sqlite:///./data/app.db"),
        runtime_interval_seconds=_get_int("MARKET_ANALYZER_RUNTIME_INTERVAL", 180),
        dashboard_refresh_seconds=_get_int("MARKET_ANALYZER_DASHBOARD_REFRESH", 12),
        log_level=os.getenv("MARKET_ANALYZER_LOG_LEVEL", "INFO").upper(),
        ebay_provider=os.getenv("MARKET_ANALYZER_EBAY_PROVIDER", "html").strip().lower(),
        enable_wallapop=_get_bool("MARKET_ANALYZER_ENABLE_WALLAPOP", True),
        request_timeout_seconds=_get_float("MARKET_ANALYZER_REQUEST_TIMEOUT", 20.0),
        retry_attempts=_get_int("MARKET_ANALYZER_RETRY_ATTEMPTS", 2),
        backoff_base_seconds=_get_float("MARKET_ANALYZER_BACKOFF_BASE", 1.5),
        user_agent=os.getenv(
            "MARKET_ANALYZER_USER_AGENT",
            (
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        ),
        ebay_search_max_items=_get_int("MARKET_ANALYZER_EBAY_MAX_ITEMS", 20),
        ebay_buy_it_now_only=_get_bool("MARKET_ANALYZER_EBAY_BUY_IT_NOW_ONLY", True),
        wallapop_search_latitude=_get_float("MARKET_ANALYZER_WALLAPOP_LATITUDE", 40.4168),
        wallapop_search_longitude=_get_float("MARKET_ANALYZER_WALLAPOP_LONGITUDE", -3.7038),
        wallapop_search_order_by=os.getenv(
            "MARKET_ANALYZER_WALLAPOP_ORDER_BY",
            "most_relevance",
        ).strip(),
        arbitrage_fee_rate=_get_float("MARKET_ANALYZER_ARBITRAGE_FEE_RATE", 0.13),
        arbitrage_profit_threshold=_get_float("MARKET_ANALYZER_ARBITRAGE_PROFIT_THRESHOLD", 20.0),
        arbitrage_min_comparables=_get_int("MARKET_ANALYZER_ARBITRAGE_MIN_COMPARABLES", 3),
    )
