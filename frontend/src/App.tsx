import { FormEvent, useCallback, useEffect, useState } from "react";
import { fetchBookStatus, fetchOpportunities } from "./api";
import BookStatusPanel from "./components/BookStatusPanel";
import OfflineScreen from "./components/OfflineScreen";
import OpportunityCard from "./components/OpportunityCard";
import SportTabs from "./components/SportTabs";
import type { ArbitrageOpportunity, BookStatus } from "./types";

export default function App() {
  const [totalStake, setTotalStake] = useState(100);
  const [inputValue, setInputValue] = useState("100");
  const [data, setData] = useState<ArbitrageOpportunity[]>([]);
  const [bookStatus, setBookStatus] = useState<Record<string, BookStatus>>({});
  const [sport, setSport] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);

  const loadOpportunities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetchOpportunities(totalStake);
      setOffline(false);
      setData(response.opportunities);
    } catch (err) {
      if (err instanceof TypeError) {
        setOffline(true);
      } else {
        setError(err instanceof Error ? err.message : "Unknown error");
      }
    } finally {
      setLoading(false);
    }
  }, [totalStake]);

  const loadBookStatus = useCallback(async () => {
    try {
      const response = await fetchBookStatus();
      setBookStatus(response.books);
    } catch {
      // non-fatal; book status panel simply stays empty
    }
  }, []);

  useEffect(() => {
    void loadOpportunities();
    void loadBookStatus();

    const oppTimer = setInterval(() => void loadOpportunities(), 10_000);
    const statusTimer = setInterval(() => void loadBookStatus(), 10_000);

    return () => {
      clearInterval(oppTimer);
      clearInterval(statusTimer);
    };
  }, [loadOpportunities, loadBookStatus]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const parsed = Number(inputValue);
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError("Enter a valid positive stake.");
      return;
    }
    setTotalStake(parsed);
  }

  const filtered = sport ? data.filter((opp) => opp.sport === sport) : data;

  if (offline) return <OfflineScreen />;

  return (
    <main className="page">
      <header>
        <h1>Arb Scanner</h1>
        <p>Live moneyline arbitrage across DraftKings · FanDuel · BetRivers · betPARX</p>
      </header>

      <BookStatusPanel books={bookStatus} />

      <form className="controls" onSubmit={onSubmit}>
        <label htmlFor="stake">Total Stake (USD)</label>
        <input
          id="stake"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          inputMode="decimal"
        />
        <button type="submit">Apply</button>
        <button type="button" onClick={() => void loadOpportunities()}>
          Refresh
        </button>
      </form>

      <section className="status">
        <span>Active stake: ${totalStake.toFixed(2)}</span>
        <span>{loading ? "Updating..." : `Loaded ${data.length} opportunities`}</span>
      </section>

      {error ? <p className="error">{error}</p> : null}

      <SportTabs selected={sport} onChange={setSport} />

      <div className="opp-list">
        {filtered.length === 0 && !loading ? (
          <p className="no-results">No arbitrage opportunities found for this filter.</p>
        ) : (
          filtered.map((opp) => (
            <OpportunityCard
              key={`${opp.event_id}-${opp.market}`}
              opportunity={opp}
            />
          ))
        )}
      </div>
    </main>
  );
}
