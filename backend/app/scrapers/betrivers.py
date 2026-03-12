"""BetRivers scraper — Kambi platform JSON API (no browser needed).

Uses the undocumented Kambi offering API backed by customer ID ``rsiusoh``
(Rush Street Interactive Ohio). Returns all upcoming events directly as JSON,
bypassing Playwright entirely and running ~100x faster than a page scrape.

API base: https://eu-offering-api.kambicdn.com/offering/v2018/rsiusoh
"""

from __future__ import annotations

import logging

import httpx

from app.models.odds import MarketLine, american_to_decimal
from app.scrapers.base import BookScraper

logger = logging.getLogger(__name__)

_KAMBI_BASE = "https://eu-offering-api.kambicdn.com/offering/v2018/{cid}"
_KAMBI_PARAMS = "lang=en_US&market=US&client_id=2&channel_id=1&ncid=1&useCombined=true"

# Customer ID → state mapping.  Default is Ohio (rsiusoh).
_STATE_CID: dict[str, str] = {
    "oh": "rsiusoh",
    "il": "rsiuil",
    "pa": "rsiupa",
    "mi": "rsiumi",
    "nj": "rsianj",
    "va": "rsiuva",
    "co": "rsiuco",
    "az": "rsiuaz",
    "ia": "rsiuia",
    "in": "rsiuin",
    "la": "rsiula",
    "md": "rsiumd",
    "ny": "rsiuny",
    "tn": "rsiutn",
    "wv": "rsiuwv",
}

# Kambi path fragments per sport
_SPORT_PATHS: dict[str, str] = {
    "kbo":    "baseball/korea",
    "nba":    "basketball/nba",
    "mlb":    "baseball/mlb",
    "nhl":    "ice_hockey/nhl",
    "soccer": "football/england/premier_league",
    "ncaam":  "basketball/ncaa",
}

# Kambi bet-offer type names for head-to-head moneyline
_ML_OFFER_TYPES = {"Match", "Head to Head", "Money Line", "Moneyline", "Winner (3-way)"}


def _normalize_team(name: str) -> str:
    """Last word of team name, lowercased. Handles city-only names gracefully."""
    return name.strip().split()[-1].lower()


def _event_id(sport: str, t1: str, t2: str) -> str:
    names = sorted([_normalize_team(t1), _normalize_team(t2)])
    return f"ml-{sport}-{names[0]}-{names[1]}"


def _parse_american(raw: str) -> int | None:
    """Parse Kambi's oddsAmerican field ('188', '-250', '' → None)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        val = int(raw)
        # Kambi omits the '+' for positive odds; normalise to signed int
        return val
    except ValueError:
        return None


class BetRiversScraper(BookScraper):
    book_name = "betrivers"
    display_name = "BetRivers"
    scrape_type = "api"

    # Kept for base-class compatibility; not used in API mode.
    SPORT_URLS: dict[str, str] = {}

    def __init__(self, email: str, password: str, state: str = "oh") -> None:
        super().__init__(email, password)
        self._state = state
        cid = _STATE_CID.get(state, f"rsiu{state}")
        self._api_base = _KAMBI_BASE.format(cid=cid)

    def login(self, page_action_fn) -> None:
        raise NotImplementedError("BetRivers public odds require no login")

    # parse_lines is not used in API mode but required by the ABC
    def parse_lines(self, page: object, sport: str) -> list[MarketLine]:
        return []

    # ------------------------------------------------------------------ #
    # Main entry point — overrides base to use Kambi JSON API             #
    # ------------------------------------------------------------------ #

    def scrape_all_sports(self) -> list[MarketLine]:
        all_lines: list[MarketLine] = []

        with httpx.Client(timeout=20, headers={"Accept": "application/json"}) as client:
            for sport, path in _SPORT_PATHS.items():
                url = f"{self._api_base}/listView/{path}.json?{_KAMBI_PARAMS}"
                try:
                    resp = client.get(url)
                    if resp.status_code == 404:
                        logger.debug("[betrivers] %s not available (404)", sport)
                        continue
                    resp.raise_for_status()
                    events = resp.json().get("events", [])
                    lines = self._parse_events(events, sport)
                    all_lines.extend(lines)
                    logger.info("[betrivers] %s: %d lines", sport, len(lines))
                except Exception as exc:
                    logger.error("[betrivers] Error fetching %s: %s", sport, exc)

        return all_lines

    def _parse_events(self, events: list[dict], sport: str) -> list[MarketLine]:
        lines: list[MarketLine] = []

        for ev_data in events:
            try:
                ev = ev_data.get("event", {})
                event_name = ev.get("englishName", "")
                if not event_name or " - " not in event_name:
                    continue  # skip futures/non-matchup events

                # Kambi uses "Team A - Team B" format
                parts = event_name.split(" - ", 1)
                team1, team2 = parts[0].strip(), parts[1].strip()

                # Find the moneyline offer
                ml_offer = next(
                    (o for o in ev_data.get("betOffers", [])
                     if o.get("betOfferType", {}).get("englishName") in _ML_OFFER_TYPES),
                    None,
                )
                if ml_offer is None:
                    continue

                outcomes = ml_offer.get("outcomes", [])
                if len(outcomes) < 2:
                    continue

                event_id = _event_id(sport, team1, team2)
                display_name = f"{team1} vs {team2}"
                kambi_id = ev.get("id")
                event_url = f"https://{self._state}.betrivers.com/?page=sportsbook#event/{kambi_id}" if kambi_id else None

                for outcome in outcomes:
                    team = outcome.get("englishLabel", "").strip()
                    if not team:
                        continue
                    american_odds = _parse_american(outcome.get("oddsAmerican", ""))
                    if american_odds is None:
                        continue
                    try:
                        lines.append(
                            MarketLine(
                                source="kambi_api",
                                event_id=event_id,
                                event_name=display_name,
                                market="moneyline",
                                outcome=_normalize_team(team).title(),
                                book=self.display_name,
                                sport=sport,
                                decimal_odds=american_to_decimal(american_odds),
                                american_odds=american_odds,
                                event_url=event_url,
                            )
                        )
                    except Exception as exc:
                        logger.debug("[betrivers] Skipping outcome: %s", exc)

            except Exception as exc:
                logger.debug("[betrivers] Event parse error: %s", exc)

        return lines
