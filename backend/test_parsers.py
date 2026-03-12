"""
Test parsers against saved HTML files (no network needed).
Run: .venv\Scripts\python.exe test_parsers.py
"""
import pathlib, sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scrapling.parser import Adaptor

from app.scrapers.draftkings import DraftKingsScraper
from app.scrapers.fanduel import FanDuelScraper
from app.scrapers.betmgm import BetMGMScraper
from app.scrapers.caesars import CaesarsScraper

HTML_DIR = pathlib.Path("debug_html")

TESTS = [
    ("draftkings", DraftKingsScraper, "nba"),
    ("fanduel",    FanDuelScraper,    "nba"),
    ("betmgm",     BetMGMScraper,     "nba"),
    ("caesars",    CaesarsScraper,    "nba"),
]

for name, Cls, sport in TESTS:
    html_file = HTML_DIR / f"{name}_nba.html"
    if not html_file.exists():
        print(f"{name}: HTML file not found")
        continue

    html = html_file.read_text(encoding="utf-8", errors="ignore")
    page = Adaptor(html, url=f"https://{name}.com")

    scraper = Cls("", "")
    lines = scraper.parse_lines(page, sport)

    print(f"\n=== {name} ({len(lines)} lines) ===")
    for line in lines[:6]:
        print(f"  {line.event_name} | {line.outcome} | {line.american_odds:+d} | event_id={line.event_id}")
    if len(lines) > 6:
        print(f"  ... and {len(lines)-6} more")

# BetRivers uses Kambi API directly — no HTML file needed, test live
print("\n=== betrivers (Kambi API — live) ===")
try:
    from app.scrapers.betrivers import BetRiversScraper
    s = BetRiversScraper("", "")
    lines = s.scrape_all_sports()
    from collections import Counter
    by_sport = Counter(l.sport for l in lines)
    print(f"  Total: {len(lines)} lines — {dict(by_sport)}")
    for l in lines[:4]:
        print(f"  {l.event_name} | {l.outcome} | {l.american_odds:+d} | event_id={l.event_id}")
    if len(lines) > 4:
        print(f"  ... and {len(lines)-4} more")
except Exception as e:
    print(f"  ERROR: {e}")
