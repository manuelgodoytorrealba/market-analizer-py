from app.scrapers.base import BaseListingProvider


class EbayAPIProvider(BaseListingProvider):
    def fetch_listings(self, query: str) -> list[dict]:
        # Placeholder funcional para permitir el cambio de provider sin tocar el pipeline.
        return []
