import type { BookStatus } from "../types";
import { triggerBookRefresh } from "../api";

type Props = {
  books: Record<string, BookStatus>;
};

function formatTime(iso: string | null): string {
  if (!iso) return "never";
  const d = new Date(iso);
  return d.toLocaleTimeString();
}

function statusColor(s: BookStatus): string {
  if (s.last_error) return "badge-error";
  if (s.logged_in && s.last_scraped_at) return "badge-ok";
  return "badge-idle";
}

export default function BookStatusPanel({ books }: Props) {
  if (Object.keys(books).length === 0) return null;

  async function handleRefresh(book: string) {
    await triggerBookRefresh(book);
  }

  return (
    <section className="book-status-panel">
      <h2>Book Status</h2>
      <div className="book-badges">
        {Object.values(books).map((s) => (
          <div key={s.book} className={`book-badge ${statusColor(s)}`}>
            <span className="book-badge-name">{s.display_name}</span>
            <span className="book-badge-meta">
              {s.line_count} lines · {formatTime(s.last_scraped_at)}
            </span>
            {s.last_error && (
              <span className="book-badge-error" title={s.last_error}>
                Error
              </span>
            )}
            <button
              type="button"
              className="book-badge-refresh"
              onClick={() => void handleRefresh(s.book)}
              title="Refresh now"
            >
              ↺
            </button>
          </div>
        ))}
      </div>
    </section>
  );
}
