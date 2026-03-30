from app.scrapers.base import BaseScraper


class WallapopScraper(BaseScraper):
    async def scrape(self, query: str) -> list[dict]:
        # Mock inicial para probar el dashboard
        return [
            {
                "source": "wallapop",
                "external_id": "w1",
                "title": "Nintendo Switch OLED blanca",
                "normalized_name": "nintendo switch oled",
                "price": 210.0,
                "url": "https://example.com/1",
                "location": "Madrid",
            },
            {
                "source": "wallapop",
                "external_id": "w2",
                "title": "Nintendo Switch OLED con caja",
                "normalized_name": "nintendo switch oled",
                "price": 260.0,
                "url": "https://example.com/2",
                "location": "Madrid",
            },
            {
                "source": "wallapop",
                "external_id": "w3",
                "title": "Nintendo Switch OLED nueva",
                "normalized_name": "nintendo switch oled",
                "price": 275.0,
                "url": "https://example.com/3",
                "location": "Madrid",
            },
        ]
