from abc import ABC, abstractmethod


class BaseScraper(ABC):
    @abstractmethod
    def scrape(self, query: str) -> list[dict]:
        raise NotImplementedError
