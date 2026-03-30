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
    request_timeout_seconds: float
    retry_attempts: int
    backoff_base_seconds: float
    user_agent: str
    ebay_search_max_items: int
    ebay_buy_it_now_only: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("MARKET_ANALYZER_DB_URL", "sqlite:///./data/app.db"),
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
    )
