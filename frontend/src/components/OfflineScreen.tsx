export default function OfflineScreen() {
  return (
    <main className="offline-page">
      <div className="offline-card">
        <div className="offline-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18.36 6.64A9 9 0 0 1 20.77 15" />
            <path d="M6.16 6.16a9 9 0 1 0 12.68 12.68" />
            <path d="M12 2v4" />
            <line x1="2" y1="2" x2="22" y2="22" />
          </svg>
        </div>
        <h1>Scanner Offline</h1>
        <p className="offline-sub">
          The backend is not currently running.<br />
          Check back when the scanner is active.
        </p>
        <div className="offline-meta">
          <span className="offline-dot" />
          <span>Retrying automatically…</span>
        </div>
      </div>
    </main>
  );
}
