import type { BookStatusResponse, OpportunityResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const API_KEY = import.meta.env.VITE_API_KEY ?? "";

function authHeaders(): HeadersInit {
  return API_KEY ? { "X-API-Key": API_KEY } : {};
}

export async function fetchOpportunities(totalStake: number): Promise<OpportunityResponse> {
  const url = `${API_BASE}/opportunities?total_stake=${encodeURIComponent(totalStake)}`;
  const response = await fetch(url, { method: "GET", headers: authHeaders() });

  if (!response.ok) {
    throw new Error(`Failed to fetch opportunities: ${response.status}`);
  }

  return (await response.json()) as OpportunityResponse;
}

export async function fetchBookStatus(): Promise<BookStatusResponse> {
  const url = `${API_BASE}/books/status`;
  const response = await fetch(url, { method: "GET", headers: authHeaders() });

  if (!response.ok) {
    throw new Error(`Failed to fetch book status: ${response.status}`);
  }

  return (await response.json()) as BookStatusResponse;
}

export async function triggerBookRefresh(book: string): Promise<void> {
  const url = `${API_BASE}/books/${encodeURIComponent(book)}/refresh`;
  await fetch(url, { method: "POST", headers: authHeaders() });
}
