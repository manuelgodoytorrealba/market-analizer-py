import json
import logging
from pathlib import Path
import re
import unicodedata
from urllib import response
from urllib.parse import quote, urlencode
from collections import Counter

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from app.scrapers.base import BaseListingProvider
from app.services.normalizer import (
    build_normalized_name,
    build_comparable_key,
    infer_condition,
)

logger = logging.getLogger(__name__)

WALLAPOP_SHIPPING_BY_REGION = {
    "local": 5.0,
    "national": 7.0,
    "unknown": 7.0,
}


class WallapopScraper(BaseListingProvider):
    def __init__(self, *, debug: bool = False, debug_dir: str = "data/raw") -> None:
        settings = get_settings()
        self.settings = settings
        self.session = requests.Session()
        self.debug = debug
        self.debug_dir = Path(debug_dir)

        self.headers = {
            "User-Agent": settings.user_agent,
            "Accept-Language": "es-ES,es;q=0.9",
        }

        self.bad_title_keywords = {
            "for parts",
            "broken",
            "defective",
            "icloud locked",
            "repuesto",
            "para piezas",
            "bloqueado",
        }

    # =============================
    # ENTRY POINT
    # =============================

    def fetch_listings(self, query: str) -> list[dict]:
        result = self.debug_scrape(query)
        return result["results"]

    # =============================
    # MAIN SCRAPE
    # =============================

    def debug_scrape(self, query: str) -> dict:
        # 1. Intento API primero (rápido)
        api_result = self._fetch_api_candidates(query)
        if api_result and api_result["raw_candidates"] > 0:
            return api_result

        search_url = self._build_search_url(query)

        try:
            from app.scrapers.browser import fetch_rendered_html

            html = fetch_rendered_html(search_url)

        except Exception as exc:
            logger.error("wallapop browser fetch failed query=%s error=%s", query, exc)
            return self._empty_result(query)

        # 2. Extraer candidatos
        extraction = self._extract_candidates_from_search(html)

        if self.debug:
            self._save_debug_html(query, html)

        candidates = extraction.get("candidates", [])

        results = []
        discard_reasons = Counter()

        # 3. Normalizar
        for candidate in candidates[: self.settings.ebay_search_max_items]:
            listing, reason, _ = self._normalize_candidate_with_reason(candidate, query)

            if listing is None:
                if reason:
                    discard_reasons[reason] += 1
                continue

            results.append(listing)

        # 4. Logs
        logger.info(
            "wallapop query=%s raw=%s valid=%s discarded=%s",
            query,
            len(candidates),
            len(results),
            dict(discard_reasons),
        )

        # 5. Resultado final
        return {
            "query": query,
            "raw_candidates": len(candidates),
            "invalid_filtered": sum(discard_reasons.values()),
            "discard_reasons": dict(discard_reasons),
            "results": results,
        }

    def _empty_result(self, query: str):
        return {
            "query": query,
            "raw_candidates": 0,
            "invalid_filtered": 0,
            "discard_reasons": {},
            "results": [],
        }

    # =============================
    # URLS
    # =============================

    def _build_search_url(self, query: str) -> str:
        return f"https://es.wallapop.com/app/search?keywords={quote(query)}"

    def _build_api_search_url(self, query: str) -> str:
        params = {
            "keywords": query,
            "latitude": self.settings.wallapop_search_latitude,
            "longitude": self.settings.wallapop_search_longitude,
            "items_count": self.settings.ebay_search_max_items,
            "order_by": self.settings.wallapop_search_order_by,
        }
        return f"https://api.wallapop.com/api/v3/general/search?{urlencode(params)}"

    # =============================
    # API
    # =============================

    def _fetch_api_candidates(self, query: str) -> dict | None:
        try:
            response = self.session.get(
                self._build_api_search_url(query),
                headers={
                    "User-Agent": self.settings.user_agent,
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "es-ES,es;q=0.9",
                    "Origin": "https://es.wallapop.com",
                    "Referer": f"https://es.wallapop.com/app/search?keywords={query}",
                    "Connection": "keep-alive",
                },
                timeout=10,
            )

            print("STATUS:", response.status_code)

            payload = response.json()

        except Exception as e:
            print("API ERROR:", e)
            return None

        candidates = payload.get("search_objects", [])

        print("API RESULTS:", len(candidates))

        results = []

        for item in candidates:
            listing, _, _ = self._normalize_candidate_with_reason(item, query)
            if listing:
                results.append(listing)

        return {
            "query": query,
            "raw_candidates": len(candidates),
            "invalid_filtered": len(candidates) - len(results),
            "discard_reasons": {},
            "results": results,
        }

    def _extract_candidates_from_api_payload(self, payload):
        if not isinstance(payload, dict):
            return []

        for key in ("search_objects", "items", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]

        return []

    # =============================
    # EXTRACTION
    # =============================

    def _extract_candidates_from_search(self, html: str):
        next_data = self._extract_next_data(html)

        if next_data:
            items = self._collect_items_from_json(next_data)
            if items:
                return {"candidates": items}

        return {"candidates": self._extract_candidates_from_dom(html)}

    def _extract_next_data(self, html: str):
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")

        if not script or not script.string:
            return None

        try:
            return json.loads(script.string)
        except Exception:
            return None

    def _collect_items_from_json(self, payload):
        items = []
        seen = set()

        def walk(node):
            if isinstance(node, dict):
                item_id = node.get("id")
                title = node.get("title")

                if item_id and title and item_id not in seen:
                    seen.add(item_id)
                    items.append(node)

                for v in node.values():
                    walk(v)

            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(payload)
        return items

    def _extract_candidates_from_dom(self, html: str):
        soup = BeautifulSoup(html, "lxml")
        items = []

        for link in soup.select("a[href*='/item/']"):
            text = link.get_text(" ", strip=True)
            price = self._extract_price_from_text(text)

            if not price:
                continue

            items.append(
                {
                    "title": text,
                    "price": price,
                    "url": link.get("href"),
                }
            )

        return items

    # =============================
    # NORMALIZATION
    # =============================

    def _normalize_candidate_with_reason(self, candidate, query):
        title = self._clean_title(str(candidate.get("title", "")).strip())

        if not title:
            return None, "no_title", {}

        if any(bad in title.lower() for bad in self.bad_title_keywords):
            return None, "bad_title", {}

        price = self._extract_price(candidate)

        if not price or price < 20:
            return None, "invalid_price", {}

        normalized_name = build_normalized_name(title, query)
        comparable_key = build_comparable_key(title, query)

        if not normalized_name:
            return None, "normalization_failed", {}

        return (
            {
                "source": "wallapop",
                "external_id": str(candidate.get("id") or hash(title)),
                "title": title,
                "normalized_name": normalized_name,
                "price": price,
                "currency": "EUR",
                "url": self._build_url(candidate),
                "image_url": self._extract_image_url(candidate),
                "location": self._extract_location(candidate),
                "seller_location": self._extract_seller_location(candidate),
                "shipping_region": "national",
                "shipping_cost": 7.0,
                "search_query": query,
                "condition": infer_condition(title, query) or "",
                "description": self._extract_description(candidate),
                "snippet": self._extract_snippet(candidate),
                "buy_it_now": True,
            },
            None,
            {},
        )

    # =============================
    # HELPERS
    # =============================

    def _extract_price(self, candidate):
        if isinstance(candidate.get("price"), (int, float)):
            return float(candidate["price"])

        return self._extract_price_from_text(json.dumps(candidate))

    def _extract_price_from_text(self, text: str):
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(€|eur)", text.lower())
        if not match:
            return None

        raw = match.group(1).replace(",", ".")
        return float(raw)

    def _clean_title(self, title: str) -> str:
        cleaned = re.sub(
            r"^\s*\d+\s*/\s*\d+\s+[0-9]+(?:[.,][0-9]+)?\s*(?:€|eur)\s*",
            "",
            title,
            flags=re.IGNORECASE,
        )
        return re.sub(r"\s+", " ", cleaned).strip()

    def _build_url(self, candidate):
        url = candidate.get("url")

        if isinstance(url, str) and url.startswith("http"):
            return url

        if isinstance(url, str):
            return f"https://es.wallapop.com{url}"

        return ""

    def _extract_description(self, candidate) -> str:
        for key in ("description", "body", "details"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _extract_snippet(self, candidate) -> str:
        for key in ("snippet", "subtitle", "storytelling"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def _extract_image_url(self, candidate) -> str:
        for key in ("image_url", "web_slug"):
            value = candidate.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value

        images = candidate.get("images") or candidate.get("photos")
        if isinstance(images, list):
            for image in images:
                if isinstance(image, str) and image.startswith("http"):
                    return image
                if isinstance(image, dict):
                    for key in ("url", "small", "medium", "large"):
                        value = image.get(key)
                        if isinstance(value, str) and value.startswith("http"):
                            return value
        return ""

    def _extract_location(self, candidate) -> str:
        location = candidate.get("location")
        if isinstance(location, str):
            return location
        if isinstance(location, dict):
            for key in ("city", "name"):
                value = location.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    def _extract_seller_location(self, candidate) -> str:
        user = candidate.get("user") or candidate.get("seller")
        if isinstance(user, dict):
            location = user.get("location")
            if isinstance(location, str):
                return location
            if isinstance(location, dict):
                city = location.get("city") or location.get("name")
                if isinstance(city, str):
                    return city
        return ""

    def _save_debug_html(self, query: str, html: str):
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        path = self.debug_dir / f"{query}.html"
        path.write_text(html)

    def _slugify_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
        slug = re.sub(r"-{2,}", "-", slug)
        return slug


def build_wallapop_provider() -> WallapopScraper:
    return WallapopScraper()
