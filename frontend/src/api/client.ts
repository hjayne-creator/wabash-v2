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
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json() as Promise<T>;
}

export type CostLine = {
  phase: string;
  service?: string | null;
  model?: string | null;
  total_cost_usd?: number;
  units?: number | null;
  unit_cost_usd?: number | null;
};

export type RuntimeLine = { phase: string; duration_ms: number };

export type ResearchEngineProvider = "perplexity" | "parallel" | "brave" | "openai" | "firecrawl";

export type ResearchEngine = {
  provider: ResearchEngineProvider;
  model: string;
  display_name: string;
  description: string;
  is_default: boolean;
};

export type MappedAttribute = {
  key: string;
  label: string;
  value: string;
  confidence: "exact" | "alias" | "fuzzy";
  source_key: string;
};

export type ResearchRunResponse = {
  id: number;
  status: "complete" | "partial" | "no_product" | "error";
  message?: string | null;
  manufacturer_name: string;
  manufacturer_product_number: string;
  engine_provider: string;
  engine_model: string;
  research_query?: string | null;
  research_prompt?: string | null;
  product_found: boolean;
  raw_output: Record<string, unknown>;
  mapped: Record<string, MappedAttribute>;
  unmapped_from_llm: Record<string, string>;
  missing: string[];
  fill_pct: number;
  attributes_filled: number;
  attributes_total: number;
  sources: { url: string; title: string }[];
  cost_lines: CostLine[];
  total_cost_usd: number;
  runtime_lines: RuntimeLine[];
  total_runtime_ms: number;
  error_message?: string | null;
};

export type ResearchRunSummary = {
  id: number;
  created_at: string;
  manufacturer_name: string;
  manufacturer_product_number: string;
  engine_provider: string;
  engine_model: string;
  status: string;
  fill_pct: number;
  attributes_filled: number;
  attributes_total: number;
  total_cost_usd: number;
  runtime_ms: number;
  message?: string | null;
  error_message?: string | null;
};

export type ProductAttribute = {
  id: number;
  key: string;
  label: string;
  aliases: string[];
  hint?: string | null;
  sort_order: number;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export const api = {
  getSession: () =>
    request<{ enabled: boolean; authenticated: boolean; username: string | null }>("/auth/session"),
  login: (body: { username: string; password: string }) =>
    request<{ ok: boolean; username: string }>("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<{ ok: boolean }>("/auth/logout", { method: "POST" }),
  getResearchEngines: () => request<ResearchEngine[]>("/research/engines"),
  runResearch: (body: {
    manufacturer_name: string;
    manufacturer_product_number: string;
    engine_provider: ResearchEngineProvider;
    engine_model: string;
  }) => request<ResearchRunResponse>("/research/run", { method: "POST", body: JSON.stringify(body) }),
  listResearchRuns: (limit = 50) => request<ResearchRunSummary[]>(`/research/runs?limit=${limit}`),
  getResearchRun: (id: number) => request<ResearchRunResponse>(`/research/runs/${id}`),
  listAttributes: (includeInactive = true) =>
    request<ProductAttribute[]>(`/admin/attributes?include_inactive=${includeInactive}`),
  createAttribute: (body: {
    key: string;
    label: string;
    aliases?: string[];
    hint?: string | null;
    sort_order?: number;
    active?: boolean;
  }) => request<ProductAttribute>("/admin/attributes", { method: "POST", body: JSON.stringify(body) }),
  updateAttribute: (
    id: number,
    body: Partial<{ label: string; aliases: string[]; hint: string | null; sort_order: number; active: boolean }>
  ) => request<ProductAttribute>(`/admin/attributes/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteAttribute: (id: number) => request<void>(`/admin/attributes/${id}`, { method: "DELETE" }),
};
