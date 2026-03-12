import asyncio

from app.arb.engine import find_arbitrage_opportunities
from app.models.odds import MarketLine
from app.models.opportunity import ArbitrageOpportunity
from app.sources.base import OddsSourceAdapter


class OpportunityService:
    def __init__(self, sources: list[OddsSourceAdapter]) -> None:
        self.sources = sources

    async def collect_lines(self) -> list[MarketLine]:
        if not self.sources:
            return []

        tasks = [source.fetch_lines() for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        lines: list[MarketLine] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            lines.extend(result)

        return lines

    async def find_opportunities(self, total_stake: float) -> list[ArbitrageOpportunity]:
        lines = await self.collect_lines()
        return find_arbitrage_opportunities(lines, total_stake)
