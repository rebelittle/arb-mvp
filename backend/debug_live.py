"""
Re-fetch live pages and diagnose why parsers return 0 lines.
Run: .venv\Scripts\python.exe debug_live.py
"""
import pathlib, sys, re
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8")

from scrapling.fetchers import DynamicFetcher

OUT = pathlib.Path("debug_html2")
OUT.mkdir(exist_ok=True)

BOOKS = {
    "fanduel":  "https://sportsbook.fanduel.com/navigation/nba",
    "betmgm":   "https://sports.betmgm.com/en/sports/basketball-7/nba-6004",
    "caesars":  "https://sportsbook.caesars.com/us/nba/betting",
}

for name, url in BOOKS.items():
    print(f"\n{'='*60}")
    print(f"Fetching {name}: {url}")
    try:
        page = DynamicFetcher().fetch(url, headless=True, network_idle=True)
        final_url = page.url
        print(f"  Final URL: {final_url}")

        html = str(page.html)
        (OUT / f"{name}_nba.html").write_text(html, encoding="utf-8")
        print(f"  HTML saved ({len(html)} chars)")

        # ---- FanDuel diagnostics ----
        if name == "fanduel":
            ml = page.css('[aria-label^="Moneyline"]')
            print(f"  [aria-label^=Moneyline]: {len(ml)}")
            # Check all aria-label containing 'moneyline'
            all_aria = page.css('[aria-label]')
            ml_any = [e.attrib.get('aria-label','') for e in all_aria
                      if 'moneyline' in e.attrib.get('aria-label','').lower()]
            print(f"  aria-label containing 'moneyline' (any case): {len(ml_any)}")
            for l in ml_any[:5]:
                print(f"    {repr(l)}")
            # Check for price spans (alternative selector)
            prices = page.css('span[class*="price"]')
            print(f"  span[class*=price]: {len(prices)}")
            for p in prices[:4]:
                print(f"    {repr(p.text.strip())}")

        # ---- BetMGM diagnostics ----
        if name == "betmgm":
            games = page.css("ms-six-pack-event")
            print(f"  ms-six-pack-event: {len(games)}")
            if games:
                g = games[0]
                teams = g.css(".participant")
                odds = g.css('span[class*="custom-odds-value"]')
                print(f"    teams: {[t.text.strip() for t in teams[:2]]}")
                print(f"    odds ({len(odds)}): {[o.text.strip() for o in odds[:7]]}")
            else:
                # Try alternative containers
                alts = [
                    "ms-event",
                    "[class*='event-card']",
                    "[class*='EventCard']",
                    "ms-grid",
                    ".KambiBC-event-item",
                    "[data-testid*='event']",
                ]
                for sel in alts:
                    els = page.css(sel)
                    if els:
                        print(f"  FOUND alternative: {sel} -> {len(els)}")
                        # Show first element's text snippet
                        txt = els[0].text.strip()[:100]
                        print(f"    preview: {repr(txt)}")
                # Show any odds-like spans
                odds_spans = page.css('span[class*="odds"]')
                print(f"  span[class*=odds]: {len(odds_spans)}")
                # Show body class snippet
                body = page.css("body")
                if body:
                    body_html = str(body[0])[:500]
                    print(f"  body snippet: {body_html[:200]}")

        # ---- Caesars diagnostics ----
        if name == "caesars":
            # Check if redirected to homepage
            if "caesars.com" in final_url and "/us/nba" not in final_url:
                print(f"  REDIRECTED away from NBA page!")
            # Try testid patterns
            for sel in ['[data-testid*="event"]', '[class*="EventRow"]', '[class*="event-row"]',
                        '[class*="eventRow"]', '[class*="EventCard"]', '[class*="CouponCard"]',
                        '[class*="couponCard"]', 'button[data-testid*="moneyline"]',
                        '[class*="Coupon"]', '[class*="coupon"]']:
                els = page.css(sel)
                if els:
                    print(f"  FOUND: {sel} -> {len(els)}")
                    print(f"    preview: {repr(els[0].text.strip()[:100])}")
            # Find any money-like text (+/- numbers)
            import re as re_
            all_text = page.text or ""
            money = re_.findall(r'[+-]\d{3,4}', all_text)
            print(f"  Money-like text (+/-NNN): {money[:20]}")

    except Exception as exc:
        print(f"  ERROR: {exc}")

print("\nDone. Check debug_html2/ for fresh HTML files.")
