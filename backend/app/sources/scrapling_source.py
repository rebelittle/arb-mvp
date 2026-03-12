from app.models.odds import MarketLine
from app.sources.base import OddsSourceAdapter


class ScraplingSource(OddsSourceAdapter):
    source_name = "scrapling"

    def __init__(self, books: list[str] | None = None) -> None:
        self.books = books or []

    async def fetch_lines(self) -> list[MarketLine]:
        from app.services.scrape_cache import scrape_cache

        lines = await scrape_cache.get_lines()
        if self.books:
            lines = [l for l in lines if l.book.lower().replace(" ", "") in self.books]
        return lines
