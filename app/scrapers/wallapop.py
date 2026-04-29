import json
import logging
from pathlib import Path
import re
import unicodedata
from urllib.parse import quote
from collections import Counter
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from app.config import get_settings
from app.scrapers.base import BaseListingProvider
from app.services.normalizer import extract_iphone_specs, infer_condition


logger = logging.getLogger(__name__)


WALLAPOP_SHIPPING_BY_REGION = {
    "local": 5.0,
    "national": 7.0,
    "unknown": 7.0,
}


class WallapopScraper(BaseListingProvider):
    def __init__(
        self,
        *,
        debug: bool = False,
        debug_dir: str = "data/raw",
    ) -> None:
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

    def fetch_listings(self, query: str) -> list[dict]:
        result = self.debug_scrape(query)
        return result["results"]

    def debug_scrape(self, query: str) -> dict:
        api_result = self._fetch_api_candidates(query)
        if api_result is not None and api_result["raw_candidates"] > 0:
            return api_result

        search_attempts = [
            ("seo", self._build_search_url(query)),
            ("app", self._build_app_search_url(query)),
        ]

        html = ""
        page_title = "unknown"
        saved_path: str | None = None
        extraction = {"candidates": [], "next_data_found": False, "dom_candidates": 0}
        selected_attempt = "seo"

        for attempt_name, search_url in search_attempts:
            try:
                response = self.session.get(
                    search_url,
                    headers=self.headers,
                    timeout=self.settings.request_timeout_seconds,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning(
                    "wallapop search attempt_failed query=%s strategy=%s url=%s error=%s",
                    query,
                    attempt_name,
                    search_url,
                    exc,
                )
                continue

            html = response.text
            page_title = self._extract_page_title(html)
            extraction = self._extract_candidates_from_search(html)
            selected_attempt = attempt_name
            if extraction["candidates"]:
                break

        if self.debug:
            saved_path = str(self._save_debug_html(query, html))

        candidates = extraction["candidates"]
        logger.info(
            "wallapop search query=%s strategy=%s raw_candidates=%s page_title=%s next_data=%s dom_links=%s",
            query,
            selected_attempt,
            len(candidates),
            page_title,
            extraction["next_data_found"],
            extraction["dom_candidates"],
        )

        results: list[dict] = []
        discard_reasons: Counter[str] = Counter()
        quality_signals = {
            "location_present": 0,
            "shipping_region_unknown": 0,
            "missing_price_usable": 0,
            "normalization_failed": 0,
        }
        for candidate in candidates[: self.settings.ebay_search_max_items]:
            listing, discard_reason, candidate_quality = self._normalize_candidate_with_reason(
                candidate,
                query,
            )
            for key, value in candidate_quality.items():
                quality_signals[key] += value
            if listing is None:
                if discard_reason:
                    discard_reasons[discard_reason] += 1
                continue
            results.append(listing)

        logger.info(
            (
                "wallapop search query=%s valid_results=%s invalid_filtered=%s "
                "discard_reasons=%s quality=%s"
            ),
            query,
            len(results),
            sum(discard_reasons.values()),
            dict(discard_reasons),
            quality_signals,
        )
        if not candidates and saved_path is None:
            saved_path = str(self._save_debug_html(query, html))
            logger.warning(
                "wallapop search empty_results_debug_saved query=%s path=%s page_title=%s next_data=%s dom_links=%s",
                query,
                saved_path,
                page_title,
                extraction["next_data_found"],
                extraction["dom_candidates"],
            )
        return {
            "query": query,
            "saved_path": saved_path or "",
            "page_title": page_title,
            "strategy": selected_attempt,
            "raw_candidates": len(candidates),
            "invalid_filtered": sum(discard_reasons.values()),
            "discard_reasons": dict(discard_reasons),
            "quality_signals": quality_signals,
            "results": results,
        }

    def _build_search_url(self, query: str) -> str:
        return f"https://es.wallapop.com/moviles-telefonos/{self._build_query_slug(query)}"

    def _build_app_search_url(self, query: str) -> str:
        return f"https://es.wallapop.com/app/search?keywords={quote(query)}"

    def _build_api_search_url(self, query: str) -> str:
        params = {
            "keywords": query,
            "filters_source": "search_box",
            "latitude": self.settings.wallapop_search_latitude,
            "longitude": self.settings.wallapop_search_longitude,
            "items_count": self.settings.ebay_search_max_items,
            "order_by": self.settings.wallapop_search_order_by,
            "language": "es_ES",
        }
        return f"https://api.wallapop.com/api/v3/general/search?{urlencode(params)}"

    def _fetch_api_candidates(self, query: str) -> dict | None:
        search_url = self._build_api_search_url(query)
        try:
            response = self.session.get(
                search_url,
                headers={
                    **self.headers,
                    "Accept": "application/json, text/plain, */*",
                    "Origin": "https://es.wallapop.com",
                    "Referer": "https://es.wallapop.com/",
                },
                timeout=self.settings.request_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, json.JSONDecodeError) as exc:
            logger.warning("wallapop api search failed query=%s error=%s", query, exc)
            return None

        candidates = self._extract_candidates_from_api_payload(payload)
        saved_path = ""
        if self.debug and not candidates:
            saved_path = str(self._save_debug_payload(query, payload))
            logger.warning(
                "wallapop api search empty_results_debug_saved query=%s path=%s",
                query,
                saved_path,
            )
        logger.info(
            "wallapop api search query=%s raw_candidates=%s",
            query,
            len(candidates),
        )

        results: list[dict] = []
        discard_reasons: Counter[str] = Counter()
        quality_signals = {
            "location_present": 0,
            "shipping_region_unknown": 0,
            "missing_price_usable": 0,
            "normalization_failed": 0,
        }

        for candidate in candidates[: self.settings.ebay_search_max_items]:
            listing, discard_reason, candidate_quality = self._normalize_candidate_with_reason(
                candidate,
                query,
            )
            for key, value in candidate_quality.items():
                quality_signals[key] += value
            if listing is None:
                if discard_reason:
                    discard_reasons[discard_reason] += 1
                continue
            results.append(listing)

        logger.info(
            (
                "wallapop api search query=%s valid_results=%s invalid_filtered=%s "
                "discard_reasons=%s quality=%s"
            ),
            query,
            len(results),
            sum(discard_reasons.values()),
            dict(discard_reasons),
            quality_signals,
        )
        return {
            "query": query,
            "saved_path": saved_path,
            "page_title": "api_v3_general_search",
            "strategy": "api",
            "raw_candidates": len(candidates),
            "invalid_filtered": sum(discard_reasons.values()),
            "discard_reasons": dict(discard_reasons),
            "quality_signals": quality_signals,
            "results": results,
        }

    def _extract_candidates_from_search(self, html: str) -> dict:
        next_data = self._extract_next_data(html)
        if next_data is not None:
            candidates = self._collect_items_from_json(next_data)
            if candidates:
                return {
                    "candidates": candidates,
                    "next_data_found": True,
                    "dom_candidates": 0,
                }

        dom_candidates = self._extract_candidates_from_dom(html)
        return {
            "candidates": dom_candidates,
            "next_data_found": next_data is not None,
            "dom_candidates": len(dom_candidates),
        }

    def _extract_candidates_from_api_payload(self, payload: object) -> list[dict]:
        if not isinstance(payload, dict):
            return []

        for key in ("search_objects", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]

        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("search_objects", "items", "results"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]

        return []

    def _extract_next_data(self, html: str) -> dict | None:
        soup = BeautifulSoup(html, "lxml")
        script = soup.find("script", id="__NEXT_DATA__")
        if script is None or not script.string:
            return None
        try:
            return json.loads(script.string)
        except json.JSONDecodeError:
            return None

    def _collect_items_from_json(self, payload: object) -> list[dict]:
        items: list[dict] = []
        seen_ids: set[str] = set()

        def walk(node: object) -> None:
            if isinstance(node, dict):
                candidate_id = node.get("id") or node.get("item_id")
                title = node.get("title") or node.get("name")
                if candidate_id is not None and isinstance(title, str):
                    external_id = str(candidate_id)
                    if external_id not in seen_ids:
                        seen_ids.add(external_id)
                        items.append(node)
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload)
        return items

    def _extract_candidates_from_dom(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        items: list[dict] = []
        seen_ids: set[str] = set()

        for link in soup.select("a[href*='/item/']"):
            href = str(link.get("href") or "")
            external_id = self._build_external_id(href)
            if not external_id or external_id in seen_ids:
                continue

            text = link.get_text(" ", strip=True)
            price = self._extract_price_from_text(text)
            title = text
            if not title or price is None:
                continue

            seen_ids.add(external_id)
            items.append(
                {
                    "id": external_id,
                    "title": title,
                    "price": price,
                    "url": href,
                }
            )

        return items

    def _normalize_candidate(self, candidate: dict, query: str) -> dict | None:
        listing, _, _ = self._normalize_candidate_with_reason(candidate, query)
        return listing

    def _normalize_candidate_with_reason(
        self,
        candidate: dict,
        query: str,
    ) -> tuple[dict | None, str | None, dict[str, int]]:
        quality_signals = {
            "location_present": 0,
            "shipping_region_unknown": 0,
            "missing_price_usable": 0,
            "normalization_failed": 0,
        }
        title = str(candidate.get("title") or candidate.get("name") or "").strip()
        if not title:
            return None, "missing_title", quality_signals
        title_lower = title.lower()
        if any(keyword in title_lower for keyword in self.bad_title_keywords):
            logger.info("wallapop discard reason=bad_title title=%s", title)
            return None, "bad_title", quality_signals

        price = self._extract_price(candidate)
        if price is None or price < 20:
            logger.info("wallapop discard reason=invalid_price title=%s", title)
            quality_signals["missing_price_usable"] = 1
            return None, "invalid_price", quality_signals

        seller_location = self._extract_location(candidate)
        if seller_location:
            quality_signals["location_present"] = 1
        shipping_region = self._classify_shipping_region(seller_location)
        if shipping_region == "unknown":
            quality_signals["shipping_region_unknown"] = 1
        shipping_cost = self._estimate_shipping_cost(candidate, shipping_region)
        url = self._build_url(candidate)
        external_id = self._extract_external_id(candidate, url)
        if not external_id or not url:
            logger.info("wallapop discard reason=missing_identity title=%s", title)
            return None, "missing_identity", quality_signals

        iphone_specs = extract_iphone_specs(title, fallback_query=query)
        if iphone_specs is None:
            quality_signals["normalization_failed"] = 1
            logger.info("wallapop discard reason=unsupported_model title=%s", title)
            return None, "unsupported_model", quality_signals

        return {
            "source": "wallapop",
            "external_id": external_id,
            "title": title,
            "normalized_name": iphone_specs["normalized_name"],
            "price": price,
            "currency": "EUR",
            "url": url,
            "image_url": self._extract_image_url(candidate),
            "location": seller_location,
            "seller_location": seller_location,
            "shipping_region": shipping_region,
            "shipping_cost": shipping_cost,
            "search_query": query,
            "condition": self._extract_condition(candidate, title) or iphone_specs["condition"],
            "buy_it_now": True,
        }, None, quality_signals

    def _extract_price(self, candidate: dict) -> float | None:
        for key in ("price", "sale_price", "final_price"):
            value = candidate.get(key)
            parsed = self._parse_price_value(value)
            if parsed is not None:
                return parsed
        return self._extract_price_from_text(json.dumps(candidate, ensure_ascii=False))

    def _parse_price_value(self, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, dict):
            for key in ("amount", "cents", "eur"):
                nested = value.get(key)
                if isinstance(nested, (int, float)):
                    if key == "cents":
                        return round(float(nested) / 100, 2)
                    return float(nested)
        if isinstance(value, str):
            return self._extract_price_from_text(value)
        return None

    def _extract_price_from_text(self, text: str) -> float | None:
        match = re.search(r"([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|€)", text.lower())
        if not match:
            return None
        raw = match.group(1).replace(".", "").replace(",", ".")
        try:
            return float(raw)
        except ValueError:
            return None

    def _extract_location(self, candidate: dict) -> str:
        for key in ("location", "seller_location", "user", "seller"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                city = value.get("city") or value.get("city_name")
                region = value.get("region") or value.get("region_name") or value.get("admin_area")
                country = value.get("country") or value.get("country_code")
                parts = [part for part in (city, region, country) if isinstance(part, str) and part.strip()]
                if parts:
                    return ", ".join(parts)
        return ""

    def _classify_shipping_region(self, seller_location: str) -> str:
        if not seller_location:
            return "unknown"
        return "national"

    def _estimate_shipping_cost(self, candidate: dict, shipping_region: str) -> float | None:
        shipping_info = candidate.get("shipping")
        if isinstance(shipping_info, dict):
            for key in ("price", "cost"):
                value = shipping_info.get(key)
                parsed = self._parse_price_value(value)
                if parsed is not None:
                    return parsed
        return WALLAPOP_SHIPPING_BY_REGION[shipping_region]

    def _extract_condition(self, candidate: dict, title: str) -> str:
        for key in ("condition", "item_condition"):
            value = candidate.get(key)
            if isinstance(value, str) and value.strip():
                lowered = value.strip().lower()
                if "nuevo" in lowered or "new" in lowered:
                    return "new"
                if "reacond" in lowered or "refurb" in lowered:
                    return "refurb"
                if "usad" in lowered or "used" in lowered:
                    return "used"
        return infer_condition(title) or ""

    def _extract_image_url(self, candidate: dict) -> str:
        images = candidate.get("images")
        if isinstance(images, list) and images:
            first = images[0]
            if isinstance(first, str):
                return first
            if isinstance(first, dict):
                for key in ("original", "big", "medium", "small", "url", "urls"):
                    value = first.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
                    if isinstance(value, dict):
                        for nested_key in ("big", "medium", "small", "original"):
                            nested_value = value.get(nested_key)
                            if isinstance(nested_value, str) and nested_value.strip():
                                return nested_value.strip()
        image_info = candidate.get("image") or candidate.get("picture")
        if isinstance(image_info, dict):
            for key in ("original", "big", "medium", "small", "url"):
                value = image_info.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    def _build_url(self, candidate: dict) -> str:
        raw_url = candidate.get("url") or candidate.get("item_url")
        if isinstance(raw_url, str) and raw_url.strip():
            if raw_url.startswith("http"):
                return raw_url.strip()
            return f"https://es.wallapop.com{raw_url.strip()}"

        web_slug = candidate.get("web_slug") or candidate.get("slug")
        item_id = candidate.get("id") or candidate.get("item_id")
        if isinstance(web_slug, str) and web_slug.strip():
            slug = web_slug.strip().strip("/")
            if slug.startswith("item/"):
                return f"https://es.wallapop.com/{slug}"
            return f"https://es.wallapop.com/item/{slug}"
        if item_id is not None:
            title = str(candidate.get("title") or candidate.get("name") or "").strip()
            title_slug = self._slugify_title(title)
            if title_slug:
                return f"https://es.wallapop.com/item/{title_slug}-{item_id}"
            return f"https://es.wallapop.com/item/{item_id}"
        return ""

    def _extract_external_id(self, candidate: dict, url: str) -> str:
        item_id = candidate.get("id") or candidate.get("item_id")
        if item_id is not None:
            return str(item_id)
        return self._build_external_id(url)

    def _build_external_id(self, url: str) -> str:
        match = re.search(r"/item/(?:[^/]*-)?([0-9]+)(?:\?.*)?$", url)
        if match:
            return match.group(1)
        match = re.search(r"/item/([^/?#]+)", url)
        if match:
            return match.group(1)
        return ""

    def _save_debug_html(self, query: str, html: str) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
        path = self.debug_dir / f"wallapop_debug_{slug}.html"
        path.write_text(html, encoding="utf-8")
        return path

    def _save_debug_payload(self, query: str, payload: object) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
        path = self.debug_dir / f"wallapop_debug_{slug}.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def _extract_page_title(self, html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return "unknown"
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _build_query_slug(self, query: str) -> str:
        slug = self._slugify_text(query)
        slug = slug.replace("128gb", "128-gb").replace("256gb", "256-gb")
        return slug

    def _slugify_title(self, title: str) -> str:
        return self._slugify_text(title)

    def _slugify_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKD", (text or "").lower())
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
        slug = re.sub(r"-{2,}", "-", slug)
        return slug


def build_wallapop_provider() -> WallapopScraper:
    return WallapopScraper()
