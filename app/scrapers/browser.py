from playwright.sync_api import sync_playwright


def fetch_rendered_html(url: str) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, timeout=30000)

        # esperar a que carguen los productos
        page.wait_for_timeout(3000)

        html = page.content()

        browser.close()
        return html
