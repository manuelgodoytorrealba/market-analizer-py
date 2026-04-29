import logging
from dataclasses import dataclass
from typing import Iterable

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.config import get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrowserRenderResult:
    html: str
    final_url: str
    title: str
    browser_name: str
    matched_selector: str
    timed_out: bool
    error: str


def render_page_with_browser_fallback(
    url: str,
    *,
    wait_selectors: Iterable[str],
    no_results_selectors: Iterable[str] = (),
) -> BrowserRenderResult:
    settings = get_settings()
    browsers = _browser_order(settings.browser, settings.browser_fallback)

    last_error = ""

    with sync_playwright() as playwright:
        for browser_name in browsers:
            browser = None
            try:
                browser_type = getattr(playwright, browser_name)
                browser = browser_type.launch(headless=settings.browser_headless)
                context = browser.new_context(
                    locale="es-ES",
                    timezone_id=settings.browser_timezone,
                )
                page = context.new_page()
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.browser_timeout_ms,
                )

                matched_selector = _wait_for_any_selector(
                    page,
                    selectors=list(wait_selectors),
                    no_results_selectors=list(no_results_selectors),
                    timeout_ms=settings.browser_timeout_ms,
                )

                page.wait_for_timeout(settings.browser_render_wait_ms)

                return BrowserRenderResult(
                    html=page.content(),
                    final_url=page.url,
                    title=page.title(),
                    browser_name=browser_name,
                    matched_selector=matched_selector,
                    timed_out=False,
                    error="",
                )
            except PlaywrightTimeoutError as exc:
                last_error = f"{browser_name} timeout: {exc}"
                logger.warning("browser render timeout browser=%s url=%s error=%s", browser_name, url, exc)
            except PlaywrightError as exc:
                last_error = f"{browser_name} playwright_error: {exc}"
                logger.warning("browser render failed browser=%s url=%s error=%s", browser_name, url, exc)
            except Exception as exc:
                last_error = f"{browser_name} unexpected_error: {exc}"
                logger.exception("browser render unexpected error browser=%s url=%s", browser_name, url)
            finally:
                if browser is not None:
                    browser.close()

    return BrowserRenderResult(
        html="",
        final_url=url,
        title="unknown",
        browser_name=",".join(browsers),
        matched_selector="",
        timed_out=True,
        error=last_error or "browser_render_failed",
    )


def _browser_order(primary: str, fallback: str) -> list[str]:
    allowed = {"chromium", "firefox", "webkit"}
    result: list[str] = []

    for browser_name in (primary, fallback):
        normalized = (browser_name or "").strip().lower()
        if normalized not in allowed:
            continue
        if normalized not in result:
            result.append(normalized)

    return result or ["chromium", "firefox"]


def _wait_for_any_selector(
    page,
    *,
    selectors: list[str],
    no_results_selectors: list[str],
    timeout_ms: int,
) -> str:
    deadline_ms = max(timeout_ms, 1000)
    step_ms = 500
    waited_ms = 0

    while waited_ms <= deadline_ms:
        for selector in selectors:
            try:
                if page.locator(selector).count() > 0:
                    return selector
            except PlaywrightError:
                continue

        for selector in no_results_selectors:
            try:
                if page.locator(selector).count() > 0:
                    return selector
            except PlaywrightError:
                continue

        page.wait_for_timeout(step_ms)
        waited_ms += step_ms

    return ""