from collections import defaultdict
from itertools import product as iproduct
from typing import Iterable

from app.models.odds import MarketLine
from app.models.opportunity import ArbitrageLeg, ArbitrageOpportunity


def find_arb_keys(lines: Iterable[MarketLine]) -> set[tuple[str, str]]:
    """Return (event_id, market) pairs that contain a potential arbitrage.

    Lightweight — no stake computation, just implied-probability check.
    Only considers cross-book combinations.
    """
    # best odds per (event_id, market, outcome, book)
    grouped: dict[tuple[str, str], dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(dict))

    for line in lines:
        key = (line.event_id, line.market)
        existing = grouped[key][line.outcome].get(line.book, 0.0)
        if line.decimal_odds > existing:
            grouped[key][line.outcome][line.book] = line.decimal_odds

    arb_keys: set[tuple[str, str]] = set()
    for key, outcome_map in grouped.items():
        if len(outcome_map) < 2:
            continue
        # Best odds per outcome (any book)
        best_per_outcome = [max(book_odds.values()) for book_odds in outcome_map.values()]
        # Quick check: if all best odds are from the same book, skip
        best_books = [max(book_odds, key=book_odds.get) for book_odds in outcome_map.values()]  # type: ignore[arg-type]
        if len(set(best_books)) == 1:
            continue  # all best lines from same book — not a real arb
        implied_sum = sum(1.0 / odd for odd in best_per_outcome)
        if implied_sum < 1.0:
            arb_keys.add(key)

    return arb_keys


def compute_implied_probability_sum(decimal_odds: list[float]) -> float:
    return sum(1.0 / odd for odd in decimal_odds)


def compute_stakes(decimal_odds: list[float], total_stake: float) -> list[float]:
    implied_sum = compute_implied_probability_sum(decimal_odds)
    if implied_sum <= 0:
        return [0.0 for _ in decimal_odds]
    return [total_stake * ((1.0 / odd) / implied_sum) for odd in decimal_odds]


def find_arbitrage_opportunities(lines: Iterable[MarketLine], total_stake: float) -> list[ArbitrageOpportunity]:
    # Group all lines by (event_id, market, outcome), keeping best odds per book
    grouped: dict[tuple[str, str], dict[str, list[MarketLine]]] = defaultdict(lambda: defaultdict(list))

    for line in lines:
        key = (line.event_id, line.market)
        outcome_lines = grouped[key][line.outcome]
        # Keep only the best line per book for this outcome
        existing = next((l for l in outcome_lines if l.book == line.book), None)
        if existing is None:
            outcome_lines.append(line)
        elif line.decimal_odds > existing.decimal_odds:
            outcome_lines.remove(existing)
            outcome_lines.append(line)

    opportunities: list[ArbitrageOpportunity] = []

    for (event_id, market), outcome_map in grouped.items():
        if len(outcome_map) < 2:
            continue

        # For each outcome, sort candidates by best odds descending
        sorted_outcomes = {
            outcome: sorted(candidates, key=lambda l: l.decimal_odds, reverse=True)
            for outcome, candidates in outcome_map.items()
        }
        outcomes = list(sorted_outcomes.keys())

        # Greedily pick the best cross-book combination:
        # Iterate through all candidates for the first outcome and pair with
        # the best candidate from remaining outcomes that uses a different book.
        best_selection: list[MarketLine] | None = None
        best_implied: float = 1.0

        candidate_lists = [sorted_outcomes[o] for o in outcomes]
        for combo in iproduct(*candidate_lists):
            books_used = [l.book for l in combo]
            if len(set(books_used)) < len(combo):
                continue  # skip — two or more legs from the same book
            implied_sum = compute_implied_probability_sum([l.decimal_odds for l in combo])
            if implied_sum < best_implied:
                best_implied = implied_sum
                best_selection = list(combo)

        if best_selection is None or best_implied >= 1.0:
            continue

        selected_lines = best_selection
        decimal_odds = [line.decimal_odds for line in selected_lines]
        implied_sum = best_implied

        stakes = compute_stakes(decimal_odds, total_stake)
        payouts = [stake * line.decimal_odds for stake, line in zip(stakes, selected_lines)]
        guaranteed_payout = min(payouts)
        guaranteed_profit = guaranteed_payout - total_stake
        roi_percent = (guaranteed_profit / total_stake) * 100.0 if total_stake > 0 else 0.0

        legs = [
            ArbitrageLeg(
                outcome=line.outcome,
                book=line.book,
                source=line.source,
                decimal_odds=line.decimal_odds,
                american_odds=line.american_odds,
                stake=round(stake, 2),
                expected_payout=round(stake * line.decimal_odds, 2),
                bet_url=line.event_url,
            )
            for line, stake in zip(selected_lines, stakes)
        ]

        opportunities.append(
            ArbitrageOpportunity(
                event_id=event_id,
                event_name=selected_lines[0].event_name,
                market=market,
                sport=selected_lines[0].sport,
                implied_probability_sum=round(implied_sum, 6),
                total_stake=round(total_stake, 2),
                guaranteed_payout=round(guaranteed_payout, 2),
                guaranteed_profit=round(guaranteed_profit, 2),
                roi_percent=round(roi_percent, 3),
                legs=legs,
                verified=True,
            )
        )

    opportunities.sort(key=lambda item: item.roi_percent, reverse=True)
    return opportunities
