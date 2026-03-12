import httpx

from app.models.odds import MarketLine, american_to_decimal
from app.sources.base import OddsSourceAdapter


class OddsApiSource(OddsSourceAdapter):
    source_name = "odds_api"

    def __init__(self, api_key: str, sport_key: str = "basketball_nba") -> None:
        self.api_key = api_key
        self.sport_key = sport_key

    async def fetch_lines(self) -> list[MarketLine]:
        if not self.api_key:
            return []

        url = f"https://api.the-odds-api.com/v4/sports/{self.sport_key}/odds/"
        params = {
            "apiKey": self.api_key,
            "regions": "us",
            "markets": "h2h",
            "oddsFormat": "american",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        lines: list[MarketLine] = []

        for event in payload:
            event_id = event.get("id") or "unknown_event"
            event_name = f"{event.get('home_team', 'Home')} vs {event.get('away_team', 'Away')}"

            for bookmaker in event.get("bookmakers", []):
                book_name = bookmaker.get("title") or bookmaker.get("key") or "unknown_book"
                for market in bookmaker.get("markets", []):
                    if market.get("key") != "h2h":
                        continue
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price")
                        if not isinstance(price, (int, float)):
                            continue
                        american = int(price)
                        lines.append(
                            MarketLine(
                                source=self.source_name,
                                event_id=event_id,
                                event_name=event_name,
                                market="h2h",
                                outcome=str(outcome.get("name", "unknown")),
                                book=book_name,
                                american_odds=american,
                                decimal_odds=american_to_decimal(american),
                            )
                        )

        return lines
