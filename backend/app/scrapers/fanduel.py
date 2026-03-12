"""FanDuel scraper — aria-label="Moneyline, {Team}, {odds} Odds" pattern.

Uses StealthyFetcher with a persistent browser profile to bypass Akamai WAF.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from app.models.odds import MarketLine, american_to_decimal
from app.scrapers.base import BookScraper, SessionExpiredError

logger = logging.getLogger(__name__)

_ML_RE = re.compile(r"^Moneyline, (.+), ([+\-]\d+) Odds$")


def _normalize_team(name: str) -> str:
    return name.strip().split()[-1].lower()


def _event_id(sport: str, t1: str, t2: str) -> str:
    names = sorted([_normalize_team(t1), _normalize_team(t2)])
    return f"ml-{sport}-{names[0]}-{names[1]}"


class FanDuelScraper(BookScraper):
    book_name = "fanduel"
    display_name = "FanDuel"

    BASE = "https://sportsbook.fanduel.com"

    SPORT_URLS = {
        "ncaam": BASE + "/navigation/ncaab",
    }

    def login(self, page_action_fn) -> None:
        raise NotImplementedError("Login requires credentials")

    def is_login_redirect(self, url: str) -> bool:
        return "/login" in url.lower() or "sign-in" in url.lower()

    def scrape_all_sports(self) -> list[MarketLine]:
        """Override to use StealthyFetcher with persistent browser profile."""
        try:
            from scrapling.fetchers import StealthyFetcher  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"scrapling import failed: {exc}") from exc

        profile_path = Path(self._browser_profile)
        profile_path.mkdir(parents=True, exist_ok=True)
        for lock_name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
            try:
                (profile_path / lock_name).unlink(missing_ok=True)
            except Exception:
                pass
        cookies = self._load_cookies() or []

        all_lines: list[MarketLine] = []
        for sport, url in self.SPORT_URLS.items():
            try:
                page = StealthyFetcher().fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    user_data_dir=self._browser_profile,
                    cookies=cookies,
                )
                if page.status in (403, 429, 503):
                    raise RuntimeError(f"HTTP {page.status} — blocked by anti-bot on {sport}")
                if self.is_login_redirect(page.url):
                    raise SessionExpiredError(f"[fanduel] Redirected to login on {sport}")
                lines = self.parse_lines(page, sport)
                all_lines.extend(lines)
                logger.info("[fanduel] %s: %d lines", sport, len(lines))
            except SessionExpiredError:
                raise
            except Exception as exc:
                logger.error("[fanduel] Error scraping %s: %s", sport, exc)

        return all_lines

    def parse_lines(self, page: object, sport: str) -> list[MarketLine]:
        lines: list[MarketLine] = []

        # Collect all ML outcomes: aria-label="Moneyline, {Team}, {odds} Odds"
        try:
            ml_els = page.css('[aria-label^="Moneyline"]')
        except Exception:
            return lines

        def _event_url_from_el(el: object) -> str | None:
            """Walk up 3 ancestors from a ML button to find the game container's <a> href."""
            try:
                node = el
                for _ in range(3):
                    node = node.parent
                link = node.css_first("a[href]")
                href = link.attrib.get("href", "") if link else ""
                return self.BASE + href if href else None
            except Exception:
                return None

        outcomes: list[tuple[str, int, str | None]] = []
        for el in ml_els:
            label = el.attrib.get("aria-label", "")
            m = _ML_RE.match(label)
            if not m:
                continue
            team = m.group(1).strip()
            try:
                american_odds = int(m.group(2))
                outcomes.append((team, american_odds, _event_url_from_el(el)))
            except ValueError:
                continue

        # Pair consecutive outcomes (away, home) per game
        for i in range(0, len(outcomes) - 1, 2):
            team1, odds1, url1 = outcomes[i]
            team2, odds2, _    = outcomes[i + 1]
            event_url = url1  # both legs point to the same event page

            event_id = _event_id(sport, team1, team2)
            event_name = f"{team1} vs {team2}"

            for team, american_odds in [(team1, odds1), (team2, odds2)]:
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
                    logger.debug("[fanduel] Skipping line: %s", exc)

        return lines
