from pydantic import BaseModel


class ArbitrageLeg(BaseModel):
    outcome: str
    book: str
    source: str
    decimal_odds: float
    american_odds: int
    stake: float
    expected_payout: float
    bet_url: str | None = None


class ArbitrageOpportunity(BaseModel):
    event_id: str
    event_name: str
    market: str
    sport: str = ""
    implied_probability_sum: float
    total_stake: float
    guaranteed_payout: float
    guaranteed_profit: float
    roi_percent: float
    legs: list[ArbitrageLeg]
    verified: bool = False
