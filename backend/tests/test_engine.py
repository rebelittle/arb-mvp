from app.arb.engine import find_arbitrage_opportunities
from app.models.odds import MarketLine


def test_detects_two_way_arb() -> None:
    lines = [
        MarketLine(
            source="test",
            event_id="match_1",
            event_name="A vs B",
            market="h2h",
            outcome="A",
            book="Book1",
            american_odds=120,
            decimal_odds=2.20,
        ),
        MarketLine(
            source="test",
            event_id="match_1",
            event_name="A vs B",
            market="h2h",
            outcome="B",
            book="Book2",
            american_odds=120,
            decimal_odds=2.20,
        ),
    ]

    opportunities = find_arbitrage_opportunities(lines, total_stake=100.0)

    assert len(opportunities) == 1
    assert opportunities[0].guaranteed_profit > 0


def test_ignores_non_arb() -> None:
    lines = [
        MarketLine(
            source="test",
            event_id="match_2",
            event_name="C vs D",
            market="h2h",
            outcome="C",
            book="Book1",
            american_odds=-110,
            decimal_odds=1.9091,
        ),
        MarketLine(
            source="test",
            event_id="match_2",
            event_name="C vs D",
            market="h2h",
            outcome="D",
            book="Book2",
            american_odds=-110,
            decimal_odds=1.9091,
        ),
    ]

    opportunities = find_arbitrage_opportunities(lines, total_stake=100.0)

    assert opportunities == []
