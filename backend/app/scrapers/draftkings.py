"""DraftKings scraper — component builder (Spread|Total|Moneyline column order)."""

from __future__ import annotations

import logging
import re

from app.models.odds import MarketLine, american_to_decimal
from app.scrapers.base import BookScraper

logger = logging.getLogger(__name__)

# Unicode minus sign used by DraftKings on odds display
_UNICODE_MINUS = "\u2212"


def _parse_american(text: str) -> int | None:
    cleaned = text.strip().replace(_UNICODE_MINUS, "-")
    m = re.search(r"[+\-]\d+", cleaned)
    if not m:
        return None
    try:
        return int(m.group())
    except ValueError:
        return None


def _normalize_team(name: str) -> str:
    """'MEM Grizzlies' → 'grizzlies', 'PHI 76ers' → '76ers'"""
    return name.strip().split()[-1].lower()


def _event_id(sport: str, t1: str, t2: str) -> str:
    names = sorted([_normalize_team(t1), _normalize_team(t2)])
    return f"ml-{sport}-{names[0]}-{names[1]}"


class DraftKingsScraper(BookScraper):
    book_name = "draftkings"
    display_name = "DraftKings"

    BASE = "https://sportsbook.draftkings.com"

    SPORT_URLS = {
        "ncaam": BASE + "/leagues/basketball/ncaab",
    }

    def login(self, page_action_fn) -> None:
        raise NotImplementedError("Login requires credentials")

    def is_login_redirect(self, url: str) -> bool:
        return "/login" in url.lower()

    def parse_lines(self, page: object, sport: str) -> list[MarketLine]:
        lines: list[MarketLine] = []

        # Each game lives in a cb-static-parlay__content--inner block.
        # Column order per team row: [Spread, Total, Moneyline]
        # → odds indices 0,1,2 = team1; 3,4,5 = team2
        try:
            event_wrappers = page.css("div.cb-static-parlay__event-wrapper")
        except Exception:
            return lines

        for wrapper in event_wrappers:
            try:
                game = wrapper.css_first("div.cb-static-parlay__content--inner")
                if not game:
                    continue

                team_els = game.css("span.cb-market__label-inner--parlay")
                odds_els = game.css('span[data-testid="button-odds-market-board"]')

                if len(team_els) < 2 or len(odds_els) < 6:
                    continue

                team1 = team_els[0].text.strip()
                team2 = team_els[1].text.strip()

                ml1_raw = odds_els[2].text.strip()
                ml2_raw = odds_els[5].text.strip()

                ml1 = _parse_american(ml1_raw)
                ml2 = _parse_american(ml2_raw)

                if ml1 is None or ml2 is None:
                    continue

                event_id = _event_id(sport, team1, team2)
                event_name = f"{team1} vs {team2}"

                # Nav links are siblings of content--inner inside the event-wrapper
                event_url: str | None = None
                try:
                    for lnk in wrapper.css('a[data-testid="lp-nav-link"]'):
                        href = lnk.attrib.get("href", "")
                        if href and "sgpmode" not in href:
                            event_url = self.BASE + href
                            break
                except Exception:
                    pass

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
                                event_url=event_url,
                            )
                        )
                    except Exception as exc:
                        logger.debug("[draftkings] Skipping line: %s", exc)
            except Exception as exc:
                logger.debug("[draftkings] Game parse error: %s", exc)

        return lines
