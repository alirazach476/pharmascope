const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const USE_STATIC =
  import.meta.env.VITE_USE_STATIC === "true" || import.meta.env.PROD;

type MedicineSearchResult = {
  total: number;
  limit: number;
  offset: number;
  data: MedicineRow[];
  total_capped?: boolean;
};

let medicinesCache: MedicineRow[] | null = null;

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function getStatic<T>(path: string): Promise<T> {
  const res = await fetch(`/static-api${path}`);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

async function getSmart<T>(livePath: string, staticPath: string): Promise<T> {
  if (USE_STATIC && !API_BASE) {
    return getStatic<T>(staticPath);
  }
  try {
    return await getJson<T>(livePath);
  } catch (err) {
    if (!USE_STATIC && !API_BASE) throw err;
    return getStatic<T>(staticPath);
  }
}

export type CatalogStats = {
  total_medicines: number;
  synthetic_count: number;
  authentic_count: number;
  manufacturers: number;
  dosage_forms: number;
  therapeutic_classes: number;
  ingredients: number;
  regions?: number;
  routes?: number;
  disclaimer?: string;
};

export type MedicineRow = {
  medicine_id: string;
  brand_name: string;
  generic_name: string;
  manufacturer_name: string;
  dosage_form: string;
  route: string;
  active_ingredient: string;
  therapeutic_class: string | null;
  product_type: string;
  strength_mg?: number | null;
  market_region?: string | null;
  launch_year?: number | null;
  synthetic: boolean;
  data_class: string;
  source_system: string;
  uses?: string;
  indication?: string | null;
  pack_size?: string | null;
  sale_price?: number | null;
  mrp?: number | null;
  source_url?: string | null;
};

export type DashboardBundle = {
  stats: CatalogStats;
  disclaimer?: string;
  by_form: Array<Record<string, string | number>>;
  by_class: Array<Record<string, string | number>>;
  by_route: Array<Record<string, string | number>>;
  by_region: Array<Record<string, string | number>>;
  by_year: Array<Record<string, string | number>>;
  by_strength: Array<Record<string, string | number>>;
  by_ingredient: Array<Record<string, string | number>>;
  top_manufacturers: Array<Record<string, string | number>>;
  authenticity: Array<Record<string, string | number>>;
  form_route: Array<Record<string, string | number>>;
  class_form: Array<Record<string, string | number>>;
  by_source?: Array<Record<string, string | number>>;
};

async function loadMedicinesIndex(): Promise<MedicineRow[]> {
  if (medicinesCache) return medicinesCache;
  medicinesCache = await getStatic<MedicineRow[]>("/medicines.json");
  return medicinesCache;
}

function searchStatic(params: URLSearchParams): Promise<MedicineSearchResult> {
  return loadMedicinesIndex().then((all) => {
    const q = (params.get("q") ?? "").trim().toLowerCase();
    const form = params.get("dosage_form") ?? "";
    const source = params.get("source") ?? "";
    const synthetic = params.get("synthetic");
    const limit = Math.min(Number(params.get("limit") ?? 50), 200);
    const offset = Math.max(Number(params.get("offset") ?? 0), 0);

    let rows = all;
    if (source) rows = rows.filter((r) => r.source_system === source);
    if (form) rows = rows.filter((r) => r.dosage_form === form);
    if (synthetic === "true") rows = rows.filter((r) => r.synthetic);
    if (synthetic === "false") rows = rows.filter((r) => !r.synthetic);
    if (q) {
      const aliases =
        q.includes("panadol") || q.includes("paracetamol") || q.includes("acetaminophen")
          ? ["panadol", "paracetamol", "acetaminophen", "calpol"]
          : [q];
      rows = rows.filter((r) => {
        const hay = [
          r.brand_name,
          r.generic_name,
          r.active_ingredient,
          r.manufacturer_name,
          r.therapeutic_class,
          r.indication,
          r.uses,
          r.medicine_id,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        return aliases.some((a) => hay.includes(a));
      });
    }
    return {
      total: rows.length,
      limit,
      offset,
      data: rows.slice(offset, offset + limit),
    };
  });
}

export const api = {
  health: () => getSmart<{ status: string; version: string }>("/health", "/health.json"),
  catalogStatus: () =>
    getSmart<{ ready: boolean; stats?: CatalogStats; message?: string }>(
      "/api/v1/catalog/status",
      "/status.json",
    ),
  catalogStats: () => getSmart<CatalogStats>("/api/v1/catalog/stats", "/stats.json"),
  catalogDashboard: () =>
    getSmart<DashboardBundle>("/api/v1/catalog/dashboard", "/dashboard.json"),
  breakdown: (kind: string) =>
    getSmart<{ kind: string; data: Array<Record<string, string | number>> }>(
      `/api/v1/catalog/breakdown/${kind}`,
      `/breakdown/${kind}.json`,
    ),
  medicines: async (params: URLSearchParams) => {
    if (USE_STATIC && !API_BASE) return searchStatic(params);
    try {
      return await getJson<MedicineSearchResult>(
        `/api/v1/catalog/medicines?${params.toString()}`,
      );
    } catch {
      return searchStatic(params);
    }
  },
  aeTrends: () =>
    getSmart<{ data: Array<{ year_month: string; report_count: number }> }>(
      "/api/v1/analytics/adverse-events/trends",
      "/ae_trends.json",
    ),
  topReported: () =>
    getSmart<{ data: Array<{ medicinalproduct: string; report_count: number }> }>(
      "/api/v1/analytics/adverse-events/top-reported?limit=15",
      "/top_reported.json",
    ),
  recallTrends: () =>
    getSmart<{
      data: Array<{ year_month: string; classification: string; recall_count: number }>;
    }>("/api/v1/analytics/recalls/trends", "/recall_trends.json"),
  sources: () =>
    getSmart<{ sources: Array<Record<string, unknown>> }>("/api/v1/sources", "/sources.json"),
  dqSummary: () =>
    getSmart<{ reports: Array<Record<string, unknown>>; count: number }>(
      "/api/v1/data-quality/summary",
      "/dq_summary.json",
    ),
  pipelineRuns: () =>
    getSmart<{ runs: Array<Record<string, unknown>>; count: number }>(
      "/api/v1/pipeline/runs",
      "/pipeline_runs.json",
    ),
};

export function fmt(n?: number | null) {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US").format(n);
}

export const CHART_COLORS = [
  "#1aa6a0",
  "#3d8bfd",
  "#e6a23c",
  "#e35d6a",
  "#5ad1e6",
  "#8b7cf6",
  "#3dbf8a",
  "#f0c14a",
];
