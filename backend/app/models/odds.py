from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MarketLine(BaseModel):
    source: str
    event_id: str
    event_name: str
    market: str
    outcome: str
    book: str
    sport: str = ""
    decimal_odds: float = Field(gt=1.0)
    american_odds: int
    event_url: str | None = None
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def american_to_decimal(american_odds: int) -> float:
    if american_odds > 0:
        return round((american_odds / 100.0) + 1.0, 4)
    return round((100.0 / abs(american_odds)) + 1.0, 4)
