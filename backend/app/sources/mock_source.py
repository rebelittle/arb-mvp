from app.models.odds import MarketLine, american_to_decimal
from app.sources.base import OddsSourceAdapter


class MockSource(OddsSourceAdapter):
    source_name = "mock"

    async def fetch_lines(self) -> list[MarketLine]:
        rows = [
            {
                "event_id": "nba_lal_bos",
                "event_name": "Lakers vs Celtics",
                "market": "h2h",
                "outcome": "Lakers",
                "book": "DraftKings",
                "american": 120,
            },
            {
                "event_id": "nba_lal_bos",
                "event_name": "Lakers vs Celtics",
                "market": "h2h",
                "outcome": "Celtics",
                "book": "FanDuel",
                "american": 112,
            },
            {
                "event_id": "nba_nyk_mia",
                "event_name": "Knicks vs Heat",
                "market": "h2h",
                "outcome": "Knicks",
                "book": "BetMGM",
                "american": -105,
            },
            {
                "event_id": "nba_nyk_mia",
                "event_name": "Knicks vs Heat",
                "market": "h2h",
                "outcome": "Heat",
                "book": "bet365",
                "american": -105,
            },
        ]

        return [
            MarketLine(
                source=self.source_name,
                event_id=row["event_id"],
                event_name=row["event_name"],
                market=row["market"],
                outcome=row["outcome"],
                book=row["book"],
                american_odds=row["american"],
                decimal_odds=american_to_decimal(row["american"]),
            )
            for row in rows
        ]
