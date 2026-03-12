import type { ArbitrageOpportunity } from "../types";

type Props = {
  opportunity: ArbitrageOpportunity;
};

const SPORT_LABELS: Record<string, string> = {
  nfl: "NFL",
  nba: "NBA",
  ncaam: "NCAAM",
  mlb: "MLB",
  nhl: "NHL",
  soccer: "Soccer",
};

function formatAmerican(odds: number): string {
  return odds > 0 ? `+${odds}` : `${odds}`;
}

export default function OpportunityCard({ opportunity: opp }: Props) {
  const sportLabel = SPORT_LABELS[opp.sport] ?? opp.sport;
  const marketLabel = opp.market.charAt(0).toUpperCase() + opp.market.slice(1);

  return (
    <div className={`opp-card ${opp.verified ? "opp-verified" : "opp-unverified"}`}>
      <div className="opp-card-header">
        <div className="opp-card-event">
          {sportLabel && <span className={`sport-badge sport-${opp.sport}`}>{sportLabel}</span>}
          <span className="opp-card-name">{opp.event_name}</span>
          <span className="opp-card-market">{marketLabel}</span>
          {opp.verified && <span className="verified-badge">✓ Verified</span>}
        </div>
        <div className="opp-card-metrics">
          <span className="opp-roi">{opp.roi_percent.toFixed(3)}% ROI</span>
          <span className="opp-profit">+${opp.guaranteed_profit.toFixed(2)} profit</span>
        </div>
      </div>

      <div className="opp-instructions">
        <div className="instructions-label">What to bet:</div>
        {opp.legs.map((leg, i) => (
          <div key={`${leg.book}-${leg.outcome}`} className="opp-instruction-row">
            <span className="instruction-num">{i + 1}.</span>
            <span className="instruction-text">
              Bet <strong>{leg.outcome}</strong> on{" "}
              <strong>{leg.book}</strong> at{" "}
              <strong>{formatAmerican(leg.american_odds)}</strong> —{" "}
              stake <strong>${leg.stake.toFixed(2)}</strong>
            </span>
            <span className="instruction-payout">→ ${leg.expected_payout.toFixed(2)}</span>
            {leg.bet_url && (
              <a href={leg.bet_url} target="_blank" rel="noopener noreferrer" className="bet-link-btn">
                Bet →
              </a>
            )}
          </div>
        ))}
      </div>

      <div className="opp-card-footer">
        <span>Total stake: <strong>${opp.total_stake.toFixed(2)}</strong></span>
        <span>Guaranteed payout: <strong>${opp.guaranteed_payout.toFixed(2)}</strong></span>
        <span className="opp-implied">Implied: {(opp.implied_probability_sum * 100).toFixed(2)}%</span>
      </div>
    </div>
  );
}
