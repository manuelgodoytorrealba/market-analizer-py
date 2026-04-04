from abc import ABC, abstractmethod


class BaseListingProvider(ABC):
    @abstractmethod
    def fetch_listings(self, query: str) -> list[dict]:
        raise NotImplementedError


class BaseScraper(BaseListingProvider):
    def scrape(self, query: str) -> list[dict]:
        return self.fetch_listings(query)
