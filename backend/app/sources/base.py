from abc import ABC, abstractmethod

from app.models.odds import MarketLine


class OddsSourceAdapter(ABC):
    source_name: str

    @abstractmethod
    async def fetch_lines(self) -> list[MarketLine]:
        raise NotImplementedError
