export type ArbitrageLeg = {
  outcome: string;
  book: string;
  source: string;
  decimal_odds: number;
  american_odds: number;
  stake: number;
  expected_payout: number;
  bet_url: string | null;
};

export type ArbitrageOpportunity = {
  event_id: string;
  event_name: string;
  market: string;
  sport: string;
  implied_probability_sum: number;
  total_stake: number;
  guaranteed_payout: number;
  guaranteed_profit: number;
  roi_percent: number;
  legs: ArbitrageLeg[];
  verified: boolean;
};

export type OpportunityResponse = {
  count: number;
  opportunities: ArbitrageOpportunity[];
};

export type BookStatus = {
  book: string;
  display_name: string;
  logged_in: boolean;
  last_scraped_at: string | null;
  last_error: string | null;
  line_count: number;
  sport_counts: Record<string, number>;
};

export type BookStatusResponse = {
  books: Record<string, BookStatus>;
};
