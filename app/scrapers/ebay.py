import json
import logging
from pathlib import Path
import re
import time
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from app.config import get_settings
from app.scrapers.base import BaseScraper
from app.services.normalizer import build_normalized_name


logger = logging.getLogger(__name__)


class EbayScraper(BaseScraper):
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

    def scrape(self, query: str) -> list[dict]:
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
        auction_filtered = 0
        invalid_filtered = 0

        for candidate in candidates[: self.settings.ebay_search_max_items]:
            try:
                url = str(candidate["url"])
                if not self._is_valid_item(url):
                    invalid_filtered += 1
                    continue

                title = str(candidate.get("title") or "").strip()
                price = candidate.get("price")
                if not title or price is None:
                    detail = self._fetch_item_detail(url)
                    if not detail:
                        invalid_filtered += 1
                        continue
                    if detail["is_auction"] and not relax_filters:
                        auction_filtered += 1
                        continue
                    title = str(detail["title"])
                    price = detail["price"]

                if self._is_auction_listing(
                    title,
                    str(candidate.get("raw_text") or candidate.get("subtitle") or ""),
                ) and not relax_filters:
                    auction_filtered += 1
                    continue

                if not self._is_valid_listing(title, float(price)):
                    invalid_filtered += 1
                    continue

                results.append(
                    {
                        "source": "ebay",
                        "external_id": url,
                        "title": title,
                        "normalized_name": build_normalized_name(title, fallback_query=query),
                        "search_query": query,
                        "buy_it_now": bool(candidate.get("buy_it_now", self.settings.ebay_buy_it_now_only)),
                        "price": float(price),
                        "url": url,
                        "location": str(candidate.get("location") or "Unknown"),
                    }
                )
            except Exception as exc:
                logger.warning("ebay detail error query=%s error=%s", query, exc)
                continue

        logger.info(
            "ebay search filtered_candidates query=%s auction_filtered=%s invalid_filtered=%s",
            query,
            auction_filtered,
            invalid_filtered,
        )
        logger.info("ebay search valid_results query=%s valid_results=%s", query, len(results))
        return {
            "query": query,
            "saved_path": str(saved_path),
            "page_title": title,
            "used_mobile_fallback": used_mobile_fallback,
            "strategy_counts": strategy_counts,
            "raw_candidates": len(candidates),
            "auction_filtered": auction_filtered,
            "invalid_filtered": invalid_filtered,
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
        is_auction = self._is_auction_listing(title or "", response.text)

        if not title or price is None:
            return None

        return {
            "title": title,
            "price": price,
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
