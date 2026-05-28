const API_BASE = import.meta.env.VITE_API_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (res.status === 401) {
    window.dispatchEvent(new Event("auth:unauthorized"));
    throw new Error("Authentication required.");
  }
  if (!res.ok) {
    let detail = await res.text();
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      /* keep raw text */
    }
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export type CostLine = {
  phase: string;
  service?: string | null;
  model?: string | null;
  total_cost_usd?: number;
};

export type RuntimeLine = { phase: string; duration_ms: number };

export type CandidateRecord = {
  rank: number;
  url: string;
  title: string;
  snippet: string;
  domain: string;
  tier: string;
  serp_score: number;
};

export type MatchCriterion = {
  name: string;
  score_pct: number;
  rationale: string;
};

export type ScoredSource = {
  url: string;
  title: string;
  snippet: string;
  domain: string;
  tier: string;
  scrape_ok: boolean;
  scrape_error?: string | null;
  markdown_excerpt: string;
  rule_mpn_found: boolean;
  rule_manufacturer_match: boolean;
  overall_similarity_pct: number | null;
  criteria: MatchCriterion[];
  score_error?: string | null;
};

export type MatchRunResponse = {
  status: "complete" | "partial" | "no_candidates";
  message?: string | null;
  manufacturer_name: string;
  manufacturer_product_number: string;
  candidates: CandidateRecord[];
  sources: ScoredSource[];
  cost_lines: CostLine[];
  total_cost_usd: number;
  runtime_lines: RuntimeLine[];
  total_runtime_ms: number;
};

export const api = {
  getSession: () =>
    request<{ enabled: boolean; authenticated: boolean; username: string | null }>("/auth/session"),
  login: (body: { username: string; password: string }) =>
    request<{ ok: boolean; username: string }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  runMatch: (body: { manufacturer_name: string; manufacturer_product_number: string }) =>
    request<MatchRunResponse>("/match/run", { method: "POST", body: JSON.stringify(body) }),
};
