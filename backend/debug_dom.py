"""
Fetch one page from each book and save the HTML for selector inspection.
Run from backend/ with: .venv\Scripts\python.exe debug_dom.py
"""
import pathlib
from scrapling.fetchers import DynamicFetcher, StealthyFetcher

OUT = pathlib.Path("debug_html")
OUT.mkdir(exist_ok=True)

PAGES = [
    ("draftkings_nba", DynamicFetcher, "https://sportsbook.draftkings.com/leagues/basketball/nba"),
    ("fanduel_nba",    DynamicFetcher, "https://sportsbook.fanduel.com/navigation/nba"),
    ("betmgm_nba",     DynamicFetcher, "https://sports.betmgm.com/en/sports/basketball-7/nba-6004"),
    ("caesars_nba",    DynamicFetcher, "https://sportsbook.caesars.com/us/nba/betting"),
    ("bet365_nba",     StealthyFetcher, "https://www.bet365.com/#/AS/B7/"),
]

for name, FetcherClass, url in PAGES:
    print(f"Fetching {name}...")
    try:
        page = FetcherClass().fetch(url, headless=True, network_idle=True)
        out_file = OUT / f"{name}.html"
        out_file.write_text(page.html_content, encoding="utf-8")
        print(f"  Saved {len(page.html_content):,} bytes → {out_file}")

        # Quick probe: print first 5 button aria-labels, any spans with odds-looking text
        buttons = page.css("button[aria-label]")[:5]
        for b in buttons:
            print(f"  button aria-label: {b.attrib.get('aria-label', '')[:80]}")

        # Look for anything with odds-like patterns (+/- numbers)
        import re
        odds_pattern = re.compile(r'[+-]\d{3}')
        text = page.get_all_text()
        matches = odds_pattern.findall(text)[:10]
        print(f"  Odds-like text found: {matches}")

    except Exception as e:
        print(f"  ERROR: {e}")

print("\nDone. Open debug_html/*.html in a browser to inspect DOM.")
