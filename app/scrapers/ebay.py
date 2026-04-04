import json
import logging
from pathlib import Path
import re
import time
from urllib.parse import quote
from collections import Counter

import requests
from bs4 import BeautifulSoup

from app.config import get_settings
from app.scrapers.base import BaseScraper
from app.scrapers.ebay_api import EbayAPIProvider
from app.services.normalizer import extract_iphone_specs, infer_condition


logger = logging.getLogger(__name__)


EU_COUNTRY_KEYWORDS = {
    "spain": "ES",
    "espana": "ES",
    "españa": "ES",
    "madrid": "ES",
    "barcelona": "ES",
    "valencia": "ES",
    "sevilla": "ES",
    "france": "EU",
    "francia": "EU",
    "germany": "EU",
    "alemania": "EU",
    "italy": "EU",
    "italia": "EU",
    "portugal": "EU",
    "netherlands": "EU",
    "paises bajos": "EU",
    "belgium": "EU",
    "belgica": "EU",
    "austria": "EU",
    "ireland": "EU",
    "irlanda": "EU",
    "poland": "EU",
    "polonia": "EU",
    "sweden": "EU",
    "suecia": "EU",
    "denmark": "EU",
    "dinamarca": "EU",
    "finland": "EU",
    "finlandia": "EU",
    "czech": "EU",
    "chequia": "EU",
    "romania": "EU",
    "greece": "EU",
    "grecia": "EU",
    "hungary": "EU",
    "hungria": "EU",
    "croatia": "EU",
    "croacia": "EU",
    "slovakia": "EU",
    "slovenia": "EU",
    "luxembourg": "EU",
    "luxemburgo": "EU",
    "lithuania": "EU",
    "latvia": "EU",
    "estonia": "EU",
    "bulgaria": "EU",
}

EXCLUDED_REGION_KEYWORDS = {
    "canada",
    "united states",
    "usa",
    "u.s.",
    "japan",
    "china",
    "hong kong",
    "singapore",
    "korea",
    "india",
    "taiwan",
    "vietnam",
    "thailand",
    "malaysia",
    "philippines",
}

SHIPPING_COST_BY_REGION = {
    "local": 5.0,
    "eu": 12.5,
}


class EbayHTMLScraper(BaseScraper):
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
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        }
        self.mobile_headers = {
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                "Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        self.bad_title_keywords = [
            "broken",
            "defective",
            "icloud locked",
            "pieza",
            "piezas",
            "repuesto",
            "repuestos",
            "repair",
            "for parts",
            "solo consola de repuesto",
            "placa",
            "carcasa",
            "shell",
            "dummy",
            "empty box",
            "caja vacía",
            "caja vacia",
            "box only",
            "manual only",
            "for parts",
        ]
        self.auction_keywords = [
            "subasta",
            "puja",
            "pujas",
            "auction",
            "current bid",
            "current bids",
            "bid ",
            " bids",
        ]
        self.challenge_markers = [
            "disculpa la interrupción",
            "pardon our interruption",
            "comprobación del navegador",
            "checking your browser before you access ebay",
            "challengeget",
        ]

    def fetch_listings(self, query: str) -> list[dict]:
        result = self.debug_scrape(query)
        return result["results"]

    def debug_scrape(self, query: str, *, relax_filters: bool = False) -> dict:
        search_url = self._build_search_url(query)
        response = self._request(search_url, headers=self.headers)
        html = response.text
        title = self._extract_page_title(html)
        logger.info(
            "ebay search request_ok query=%s status=%s host=desktop title=%s",
            query,
            response.status_code,
            title,
        )

        used_mobile_fallback = False
        if self._is_challenge_page(html):
            logger.warning(
                "ebay search challenge_detected query=%s host=desktop title=%s",
                query,
                title,
            )
            mobile_url = self._build_mobile_search_url(query)
            response = self._request(mobile_url, headers=self.mobile_headers)
            html = response.text
            title = self._extract_page_title(html)
            used_mobile_fallback = True
            logger.info(
                "ebay search request_ok query=%s status=%s host=mobile title=%s",
                query,
                response.status_code,
                title,
            )

        if self._is_challenge_page(html):
            saved_path = self._save_debug_html(query, html, "mobile" if used_mobile_fallback else "desktop")
            logger.error(
                "ebay search blocked_by_challenge query=%s host=%s path=%s",
                query,
                "mobile" if used_mobile_fallback else "desktop",
                saved_path,
            )
            return {
                "query": query,
                "saved_path": str(saved_path),
                "page_title": title,
                "used_mobile_fallback": used_mobile_fallback,
                "strategy_counts": {"mobile_cards": 0, "regex_urls": 0},
                "raw_candidates": 0,
                "auction_filtered": 0,
                "invalid_filtered": 1,
                "discard_reasons": {"challenge_blocked": 1},
                "quality_signals": {"challenge_blocked": 1},
                "results": [],
            }

        saved_path = self._save_debug_html(query, html, "mobile" if used_mobile_fallback else "desktop")
        logger.info("ebay search html_saved query=%s path=%s", query, saved_path)

        extraction = self._extract_candidates_from_search(html)
        strategy_counts = extraction["strategy_counts"]
        logger.info(
            "ebay search raw_candidates query=%s dom_cards=%s regex_urls=%s selected=%s",
            query,
            strategy_counts.get("mobile_cards", 0),
            strategy_counts.get("regex_urls", 0),
            len(extraction["candidates"]),
        )

        candidates = extraction["candidates"]

        results: list[dict] = []
        discard_reasons: Counter[str] = Counter()

        for candidate in candidates[: self.settings.ebay_search_max_items]:
            try:
                url = str(candidate["url"])
                if not self._is_valid_item(url):
                    discard_reasons["invalid_item_url"] += 1
                    continue

                title = str(candidate.get("title") or "").strip()
                price = candidate.get("price")
                detail = self._fetch_item_detail(url)
                if not detail:
                    discard_reasons["detail_unavailable"] += 1
                    continue
                seller_location = str(detail.get("seller_location") or candidate.get("location") or "")
                shipping_region = self._classify_shipping_region(seller_location)
                shipping_cost = self._estimate_shipping_cost(
                    seller_location,
                    soup=None,
                    html="",
                    parsed_shipping=detail.get("shipping_cost"),
                )

                if detail["is_auction"] and not relax_filters:
                    discard_reasons["auction_listing"] += 1
                    continue
                if detail["currency"] != "EUR":
                    discard_reasons["non_eur_currency"] += 1
                    continue
                if shipping_region == "international":
                    discard_reasons["outside_target_region"] += 1
                    continue

                title = str(detail["title"] or title)
                price = detail["price"] if detail["price"] is not None else price
                if not title or price is None:
                    discard_reasons["missing_title_or_price"] += 1
                    continue

                if self._is_auction_listing(
                    title,
                    str(candidate.get("raw_text") or candidate.get("subtitle") or ""),
                ) and not relax_filters:
                    discard_reasons["auction_listing"] += 1
                    continue

                if not self._is_valid_listing(title, float(price)):
                    discard_reasons["invalid_listing"] += 1
                    continue

                iphone_specs = extract_iphone_specs(title, fallback_query=query)
                if iphone_specs is None:
                    discard_reasons["unsupported_model"] += 1
                    continue

                results.append(
                    {
                        "source": "ebay",
                        "external_id": self._build_external_id(url),
                        "title": title,
                        "normalized_name": iphone_specs["normalized_name"],
                        "search_query": query,
                        "condition": str(detail.get("condition") or infer_condition(title, fallback_query=query) or ""),
                        "shipping_cost": shipping_cost,
                        "shipping_region": shipping_region,
                        "buy_it_now": bool(candidate.get("buy_it_now", self.settings.ebay_buy_it_now_only)),
                        "price": float(price),
                        "url": url,
                        "location": str(candidate.get("location") or "Unknown"),
                        "seller_location": seller_location,
                    }
                )
            except Exception as exc:
                discard_reasons["detail_error"] += 1
                logger.warning("ebay detail error query=%s error=%s", query, exc)
                continue

        logger.info(
            (
                "ebay search filtered_candidates query=%s discarded=%s "
                "discard_reasons=%s"
            ),
            query,
            sum(discard_reasons.values()),
            dict(discard_reasons),
        )
        logger.info("ebay search valid_results query=%s valid_results=%s", query, len(results))
        return {
            "query": query,
            "saved_path": str(saved_path),
            "page_title": title,
            "used_mobile_fallback": used_mobile_fallback,
            "strategy_counts": strategy_counts,
            "raw_candidates": len(candidates),
            "auction_filtered": discard_reasons.get("auction_listing", 0),
            "invalid_filtered": sum(discard_reasons.values()) - discard_reasons.get("auction_listing", 0),
            "discard_reasons": dict(discard_reasons),
            "quality_signals": {},
            "results": results,
        }

    def _build_search_url(self, query: str) -> str:
        search_url = f"https://www.ebay.es/sch/i.html?_nkw={quote(query)}"
        if self.settings.ebay_buy_it_now_only:
            search_url = f"{search_url}&_LH_BIN=1"
        return search_url

    def _build_mobile_search_url(self, query: str) -> str:
        search_url = f"https://m.ebay.com/sch/i.html?_nkw={quote(query)}"
        if self.settings.ebay_buy_it_now_only:
            search_url = f"{search_url}&_LH_BIN=1"
        return search_url

    def _extract_candidates_from_search(self, html: str) -> dict:
        candidates: list[dict] = []
        seen_urls: set[str] = set()
        strategy_counts = {"mobile_cards": 0, "regex_urls": 0}
        soup = BeautifulSoup(html, "lxml")

        card_nodes = soup.select("li.s-card--horizontal")
        strategy_counts["mobile_cards"] = len(card_nodes)
        for card in card_nodes:
            parsed = self._parse_mobile_card(card)
            if not parsed:
                continue
            url = parsed["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            candidates.append(parsed)

        regex_urls = self._extract_urls_from_html(html)
        strategy_counts["regex_urls"] = len(regex_urls)

        if not candidates:
            logger.info("ebay fallback candidate extractor activated")
            for url in regex_urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                candidates.append({"url": url, "title": "unknown"})

        return {
            "candidates": candidates,
            "strategy_counts": strategy_counts,
        }

    def _is_valid_item(self, url: str) -> bool:
        if "/itm/" not in url:
            return False

        blocked_patterns = [
            "/sch/i.html",
            "ebayadservices",
            "rover.ebay.com",
        ]

        return not any(pattern in url for pattern in blocked_patterns)

    def _fetch_item_detail(self, url: str) -> dict | None:
        response = self._request(url, headers=self.headers)
        if self._is_challenge_page(response.text):
            logger.warning("ebay detail challenge_detected url=%s", url)
            return None

        soup = BeautifulSoup(response.text, "lxml")

        title = self._extract_title(soup)
        price = self._extract_price(soup, response.text)
        currency = self._extract_currency(soup, response.text)
        seller_location = self._extract_seller_location(soup, response.text)
        shipping_region = self._classify_shipping_region(seller_location)
        shipping_cost = self._estimate_shipping_cost(seller_location, soup, response.text)
        condition = self._extract_condition(soup, response.text)
        is_auction = self._is_auction_listing(title or "", response.text)

        if not title or price is None or currency is None or shipping_region == "international":
            return None

        return {
            "title": title,
            "price": price,
            "currency": currency,
            "seller_location": seller_location,
            "shipping_region": shipping_region,
            "shipping_cost": shipping_cost,
            "condition": condition,
            "is_auction": is_auction,
        }

    def _extract_title(self, soup: BeautifulSoup) -> str | None:
        selectors = [
            "h1.x-item-title__mainTitle",
            "h1#itemTitle",
            "h1",
            'meta[property="og:title"]',
        ]

        for selector in selectors:
            el = soup.select_one(selector)
            if not el:
                continue

            if el.name == "meta":
                content = el.get("content")
                if content is not None:
                    return str(content).strip()

            text = el.get_text(" ", strip=True)
            if text:
                return text

        return None

    def _is_auction_listing(self, title: str, html: str) -> bool:
        text = f"{title}\n{html[:6000]}".lower()
        return any(keyword in text for keyword in self.auction_keywords)

    def _extract_price(self, soup: BeautifulSoup, html: str) -> float | None:
        meta_selectors = [
            'meta[property="product:price:amount"]',
            'meta[name="twitter:data1"]',
        ]

        for selector in meta_selectors:
            el = soup.select_one(selector)
            if not el:
                continue

            content = el.get("content")
            parsed = self._parse_price(str(content) if content is not None else "")
            if parsed is not None:
                return parsed

        text_selectors = [
            ".x-price-primary span",
            ".display-price",
            ".notranslate",
            "[itemprop='price']",
        ]

        for selector in text_selectors:
            for el in soup.select(selector):
                text = el.get_text(" ", strip=True)
                parsed = self._parse_price(text)
                if parsed is not None:
                    return parsed

        json_ld_blocks = soup.select('script[type="application/ld+json"]')
        for block in json_ld_blocks:
            try:
                data = json.loads(block.string or "")
                parsed = self._extract_price_from_jsonld(data)
                if parsed is not None:
                    return parsed
            except Exception:
                continue

        regexes = [
            r'"price":"([0-9\.,]+)"',
            r'"value":"([0-9\.,]+)"',
            r'"currentPrice":{"value":"([0-9\.,]+)"',
        ]

        for pattern in regexes:
            match = re.search(pattern, html)
            if match:
                parsed = self._parse_price(match.group(1))
                if parsed is not None:
                    return parsed

        return None

    def _extract_currency(self, soup: BeautifulSoup, html: str) -> str | None:
        currency_meta = soup.select_one('meta[property="product:price:currency"]')
        if currency_meta is not None:
            content = currency_meta.get("content")
            if content:
                return str(content).strip().upper()

        lowered = html.lower()
        if " gbp" in lowered or "£" in html:
            return "GBP"
        if " usd" in lowered or "us $" in lowered:
            return "USD"
        if "approximately" in lowered and "eur" in lowered:
            return "EUR"
        if " eur" in lowered or "€" in html:
            return "EUR"
        return None

    def _extract_shipping_cost(self, soup: BeautifulSoup, html: str) -> float | None:
        text = soup.get_text(" ", strip=True)
        lowered = text.lower()
        if "free shipping" in lowered or "envío gratis" in lowered:
            return 0.0

        patterns = [
            r"(?:env[ií]o|shipping)[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|€)",
            r"([0-9]+(?:[.,][0-9]+)?)\s*(?:eur|€)[^a-z]{0,30}(?:shipping|env[ií]o)",
            r"approx\.\s*([0-9]+(?:[.,][0-9]+)?)\s*eur[^a-z]{0,30}(?:shipping|env[ií]o)",
        ]
        for pattern in patterns:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if not match:
                continue
            parsed = self._parse_price(match.group(1))
            if parsed is not None:
                return parsed
        return None

    def _extract_seller_location(self, soup: BeautifulSoup, html: str) -> str:
        text = soup.get_text(" ", strip=True)
        patterns = [
            r"ubicado en:\s*([^\.|]+)",
            r"located in:\s*([^\.|]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip(" ,-")
        return ""

    def _extract_condition(self, soup: BeautifulSoup, html: str) -> str | None:
        text = soup.get_text(" ", strip=True)
        return infer_condition(text)

    def _classify_shipping_region(self, seller_location: str) -> str:
        lowered = seller_location.lower()
        if not lowered:
            return "international"
        if any(keyword in lowered for keyword in EXCLUDED_REGION_KEYWORDS):
            return "international"
        for keyword, region in EU_COUNTRY_KEYWORDS.items():
            if keyword in lowered:
                return "local" if region == "ES" else "eu"
        return "international"

    def _estimate_shipping_cost(
        self,
        seller_location: str,
        soup: BeautifulSoup | None,
        html: str,
        parsed_shipping: float | None = None,
    ) -> float | None:
        shipping_region = self._classify_shipping_region(seller_location)
        if shipping_region == "international":
            return None
        if parsed_shipping is None and soup is not None:
            parsed_shipping = self._extract_shipping_cost(soup, html)
        if parsed_shipping is not None and parsed_shipping <= 25:
            return parsed_shipping
        return SHIPPING_COST_BY_REGION[shipping_region]

    def _build_external_id(self, url: str) -> str:
        match = re.search(r"/itm/(?:[^/]+/)?(\d+)", url)
        if match:
            return match.group(1)
        return url

    def _extract_price_from_jsonld(self, data: object) -> float | None:
        if isinstance(data, list):
            for item in data:
                parsed = self._extract_price_from_jsonld(item)
                if parsed is not None:
                    return parsed

        if isinstance(data, dict):
            offers = data.get("offers")
            if isinstance(offers, dict):
                price = offers.get("price")
                parsed = self._parse_price(str(price)) if price is not None else None
                if parsed is not None:
                    return parsed

            for value in data.values():
                parsed = self._extract_price_from_jsonld(value)
                if parsed is not None:
                    return parsed

        return None

    def _is_valid_listing(self, title: str, price: float) -> bool:
        title_lower = title.lower()

        if price < 20:
            return False

        if price > 5000:
            return False

        if any(keyword in title_lower for keyword in self.bad_title_keywords):
            return False

        if self._is_auction_listing(title, title_lower):
            return False

        return True

    def _parse_price(self, text: str) -> float | None:
        if not text:
            return None

        cleaned = (
            text.replace("EUR", "")
            .replace("US $", "")
            .replace("USD", "")
            .replace("$", "")
            .replace("€", "")
            .replace("\xa0", " ")
            .strip()
        )

        normalized = cleaned
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                normalized = cleaned.replace(".", "").replace(",", ".")
            else:
                normalized = cleaned.replace(",", "")
        elif "," in cleaned:
            comma_decimals = cleaned.split(",")[-1]
            if len(comma_decimals) == 2:
                normalized = cleaned.replace(",", ".")
            else:
                normalized = cleaned.replace(",", "")
        elif "." in cleaned:
            dot_decimals = cleaned.split(".")[-1]
            if len(dot_decimals) != 2:
                normalized = cleaned.replace(".", "")

        match = re.search(r"([0-9]+(?:\.[0-9]+)?)", normalized)
        if not match:
            return None

        try:
            return float(match.group(1))
        except ValueError:
            return None

    def _request(self, url: str, *, headers: dict[str, str]) -> requests.Response:
        last_error: Exception | None = None

        for attempt in range(self.settings.retry_attempts + 1):
            try:
                response = self.session.get(
                    url,
                    headers=headers,
                    timeout=self.settings.request_timeout_seconds,
                )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt >= self.settings.retry_attempts:
                    break

                sleep_seconds = self.settings.backoff_base_seconds * (2**attempt)
                logger.warning(
                    "ebay request retry=%s url=%s error=%s sleep=%.2f",
                    attempt + 1,
                    url,
                    exc,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)

        raise RuntimeError(f"Could not fetch eBay URL: {url}") from last_error

    def _extract_page_title(self, html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            return "unknown"
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _is_challenge_page(self, html: str) -> bool:
        lowered = html.lower()
        return any(marker in lowered for marker in self.challenge_markers)

    def _save_debug_html(self, query: str, html: str, suffix: str) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
        path = self.debug_dir / f"ebay_debug_{slug}_{suffix}.html"
        path.write_text(html, encoding="utf-8")
        return path

    def _extract_urls_from_html(self, html: str) -> list[str]:
        patterns = [
            r'"href":"(https://[^"]+/itm/[^"]+)"',
            r"https://www\.ebay\.com/itm/[^\s\"<]+",
            r"https://www\.ebay\.es/itm/[^\s\"<]+",
            r"https://ebay\.com/itm/[^\s\"<]+",
        ]
        results: list[str] = []
        seen: set[str] = set()
        for pattern in patterns:
            matches = re.findall(pattern, html)
            if isinstance(matches, str):
                matches = [matches]
            for raw in matches:
                url = raw.replace("\\u0026", "&").replace("\\/", "/")
                if url in seen:
                    continue
                seen.add(url)
                results.append(url)
        return results

    def _parse_mobile_card(self, card) -> dict | None:
        text = card.get_text(" ", strip=True)
        if not text or "Shop on eBay" in text:
            return None

        link = card.select_one("a[href*='/itm/']")
        title_el = card.select_one(".s-card__title")
        price_el = card.select_one(".s-card__price")
        subtitle_el = card.select_one(".s-card__subtitle")
        if link is None or title_el is None or price_el is None:
            return None

        title = title_el.get_text(" ", strip=True)
        price_text = price_el.get_text(" ", strip=True)
        price = self._parse_price(price_text)
        if not title or price is None:
            return None

        location = ""
        location_match = re.search(
            r"Located in ([A-Za-z ,]+)",
            text,
            flags=re.IGNORECASE,
        )
        if location_match:
            location = re.sub(
                r"\b(Last one|Sponsored|Free shipping|Free International Shipping)\b.*$",
                "",
                location_match.group(1),
                flags=re.IGNORECASE,
            ).strip(" ,")

        return {
            "url": link.get("href"),
            "title": title,
            "subtitle": subtitle_el.get_text(" ", strip=True) if subtitle_el else "",
            "raw_text": text,
            "price": price,
            "location": location,
            "buy_it_now": "buy it now" in text.lower() or self.settings.ebay_buy_it_now_only,
        }


EbayScraper = EbayHTMLScraper


def build_ebay_provider():
    settings = get_settings()
    if settings.ebay_provider == "api":
        return EbayAPIProvider()
    return EbayHTMLScraper()
