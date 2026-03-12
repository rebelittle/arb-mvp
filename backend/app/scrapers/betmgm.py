"""BetMGM scraper — ms-six-pack-event structure, 7 odds per game [spread×2, total_pts, over, under, ML1, ML2]."""

from __future__ import annotations

import logging
import re

from app.models.odds import MarketLine, american_to_decimal
from app.scrapers.base import BookScraper

logger = logging.getLogger(__name__)

_AMERICAN_RE = re.compile(r"[+\-]\d+")


def _parse_american(text: str) -> int | None:
    m = _AMERICAN_RE.search(text.strip())
    if not m:
        return None
    try:
        return int(m.group())
    except ValueError:
        return None


def _normalize_team(name: str) -> str:
    return name.strip().split()[-1].lower()


def _event_id(sport: str, t1: str, t2: str) -> str:
    names = sorted([_normalize_team(t1), _normalize_team(t2)])
    return f"ml-{sport}-{names[0]}-{names[1]}"


class BetMGMScraper(BookScraper):
    book_name = "betmgm"
    display_name = "BetMGM"

    BASE = "https://sports.betmgm.com/en/sports"

    SPORT_URLS = {
        "ncaam": BASE + "/basketball-7/ncaa-basketball-36",
    }

    def login(self, page_action_fn) -> None:
        raise NotImplementedError("Login requires credentials")

    def is_login_redirect(self, url: str) -> bool:
        return "login" in url.lower()

    def parse_lines(self, page: object, sport: str) -> list[MarketLine]:
        lines: list[MarketLine] = []

        # BetMGM 6-pack grid: ms-six-pack-event contains one game.
        # custom-odds-value-style order per game:
        #   [0] team1 spread, [1] team2 spread, [2] total pts,
        #   [3] over odds, [4] under odds, [5] team1 ML, [6] team2 ML
        try:
            games = page.css("ms-six-pack-event")
        except Exception:
            return lines

        seen_events: set[str] = set()

        for game in games:
            try:
                team_els = game.css(".participant")
                odds_els = game.css('span[class*="custom-odds-value"]')

                if len(team_els) < 2 or len(odds_els) < 7:
                    continue

                team1 = team_els[0].text.strip()
                team2 = team_els[1].text.strip()

                if not team1 or not team2:
                    continue

                ml1 = _parse_american(odds_els[5].text.strip())
                ml2 = _parse_american(odds_els[6].text.strip())

                if ml1 is None or ml2 is None:
                    continue

                event_id = _event_id(sport, team1, team2)
                if event_id in seen_events:
                    continue  # skip duplicate rendering
                seen_events.add(event_id)

                event_name = f"{team1} vs {team2}"

                for team, american_odds in [(team1, ml1), (team2, ml2)]:
                    try:
                        lines.append(
                            MarketLine(
                                source="scrapling",
                                event_id=event_id,
                                event_name=event_name,
                                market="moneyline",
                                outcome=_normalize_team(team).title(),
                                book=self.display_name,
                                sport=sport,
                                decimal_odds=american_to_decimal(american_odds),
                                american_odds=american_odds,
                            )
                        )
                    except Exception as exc:
                        logger.debug("[betmgm] Skipping line: %s", exc)
            except Exception as exc:
                logger.debug("[betmgm] Game parse error: %s", exc)

        return lines
