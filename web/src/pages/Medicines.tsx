import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { api, CHART_COLORS, fmt, type MedicineRow } from "../api";

export default function Medicines() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [q, setQ] = useState(searchParams.get("q") ?? "");
  const [form, setForm] = useState("");
  const [synthetic, setSynthetic] = useState("");
  const [source, setSource] = useState(searchParams.get("source") ?? "");
  const [rows, setRows] = useState<MedicineRow[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [forms, setForms] = useState<Array<Record<string, string | number>>>([]);
  const [ingredients, setIngredients] = useState<Array<Record<string, string | number>>>([]);
  const [regions, setRegions] = useState<Array<Record<string, string | number>>>([]);
  const [sources, setSources] = useState<Array<Record<string, string | number>>>([]);
  const [classForm, setClassForm] = useState<Array<Record<string, string | number>>>([]);
  const [error, setError] = useState<string | null>(null);
  const limit = 40;

  async function load(nextOffset = 0, query = q, src = source) {
    setError(null);
    const params = new URLSearchParams({
      limit: String(limit),
      offset: String(nextOffset),
    });
    if (query.trim()) params.set("q", query.trim());
    if (form) params.set("dosage_form", form);
    if (synthetic === "true") params.set("synthetic", "true");
    if (synthetic === "false") params.set("synthetic", "false");
    if (src) params.set("source", src);
    try {
      const res = await api.medicines(params);
      setRows(res.data);
      setTotal(res.total);
      setOffset(nextOffset);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    const initial = searchParams.get("q") ?? "";
    const initialSource = searchParams.get("source") ?? "";
    setQ(initial);
    setSource(initialSource);
    load(0, initial, initialSource);
    Promise.all([
      api.breakdown("form"),
      api.breakdown("ingredient"),
      api.breakdown("region"),
      api.breakdown("source"),
      api.breakdown("class_form"),
    ])
      .then(([f, i, r, s, cf]) => {
        setForms(f.data);
        setIngredients(i.data);
        setRegions(r.data);
        setSources(s.data);
        setClassForm(cf.data);
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stacked = useMemo(() => {
    const map = new Map<string, Record<string, string | number>>();
    for (const row of classForm.slice(0, 60)) {
      const cls = String(row.therapeutic_class);
      const formName = String(row.dosage_form);
      const cur = map.get(cls) ?? { therapeutic_class: cls };
      cur[formName] = Number(row.n);
      map.set(cls, cur);
    }
    return [...map.values()];
  }, [classForm]);

  const formKeys = useMemo(() => {
    return [...new Set(classForm.map((r) => String(r.dosage_form)))].slice(0, 6);
  }, [classForm]);

  const usesSummary = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of rows) {
      const key = r.uses || "General pharmaceutical use";
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return [...map.entries()]
      .map(([uses, n]) => ({ uses: uses.length > 42 ? `${uses.slice(0, 40)}…` : uses, n }))
      .sort((a, b) => b.n - a.n)
      .slice(0, 8);
  }, [rows]);

  function onSearch(e: FormEvent) {
    e.preventDefault();
    const next = q.trim();
    const params: Record<string, string> = {};
    if (next) params.q = next;
    if (source) params.source = source;
    setSearchParams(params);
    load(0, next, source);
  }

  return (
    <>
      <div className="hero">
        <div className="badge">50,000,000-row catalog</div>
        <h1>Medicine explorer</h1>
        <p>
          Includes OpenFDA/synthetic scale catalog plus project CSVs{" "}
          <code>medicine_dataset.csv</code> (50k) and <code>Pakistan_medicines.csv</code> (~19k).
        </p>
      </div>
      {error && <div className="error">{error}</div>}

      <form className="toolbar" onSubmit={onSearch}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search by medicine name (brand / generic)…"
          aria-label="Search by medicine name"
          style={{ flex: 1, minWidth: 260 }}
        />
        <select value={form} onChange={(e) => setForm(e.target.value)}>
          <option value="">All forms</option>
          {forms.map((f) => (
            <option key={String(f.dosage_form)} value={String(f.dosage_form)}>
              {String(f.dosage_form)}
            </option>
          ))}
        </select>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">All sources</option>
          {sources.map((s) => (
            <option key={String(s.source_system)} value={String(s.source_system)}>
              {String(s.source_system)} ({fmt(Number(s.n))})
            </option>
          ))}
        </select>
        <select value={synthetic} onChange={(e) => setSynthetic(e.target.value)}>
          <option value="">All origins</option>
          <option value="false">Authentic only</option>
          <option value="true">Synthetic only</option>
        </select>
        <button type="submit">Search</button>
      </form>

      <div className="grid-3">
        <div className="panel">
          <h3>Forms</h3>
          <div className="chart-box">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={forms.slice(0, 8)} dataKey="n" nameKey="dosage_form" outerRadius={85}>
                  {forms.slice(0, 8).map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Regions</h3>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={regions}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="market_region" tick={{ fill: "#93a0b8", fontSize: 9 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#e6a23c" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Uses in results</h3>
          <div className="sub">From current search page</div>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={usesSummary} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="uses"
                  width={130}
                  tick={{ fill: "#93a0b8", fontSize: 9 }}
                />
                <Tooltip />
                <Bar dataKey="n" fill="#1aa6a0" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Top ingredients</h3>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={ingredients.slice(0, 12)} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis type="category" dataKey="active_ingredient" width={120} tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#1aa6a0" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Class × form stacked</h3>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={stacked.slice(0, 8)}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="therapeutic_class" tick={{ fill: "#93a0b8", fontSize: 9 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Legend />
                {formKeys.map((k, i) => (
                  <Bar key={k} dataKey={k} stackId="a" fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Search results</h3>
        <div className="sub">
          {fmt(total)} matches · rows {offset + 1}-{offset + rows.length}
        </div>
        <div className="table-wrap" style={{ maxHeight: 480 }}>
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Brand</th>
                <th>Manufacturer</th>
                <th>Uses</th>
                <th>Form</th>
                <th>Pack</th>
                <th>MRP</th>
                <th>Region</th>
                <th>Source</th>
                <th>Origin</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.medicine_id}>
                  <td>{r.medicine_id}</td>
                  <td>{r.brand_name}</td>
                  <td>{r.manufacturer_name}</td>
                  <td className="uses-cell">{r.uses ?? "—"}</td>
                  <td>{r.dosage_form ?? "—"}</td>
                  <td>{r.pack_size ?? "—"}</td>
                  <td>{r.mrp != null ? fmt(r.mrp) : "—"}</td>
                  <td>{r.market_region ?? "—"}</td>
                  <td>{r.source_system}</td>
                  <td>
                    <span className={`tag ${r.synthetic ? "syn" : "auth"}`}>
                      {r.synthetic ? "SYNTHETIC" : "AUTHENTIC"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="toolbar" style={{ marginTop: "0.75rem" }}>
          <button
            type="button"
            className="secondary"
            disabled={offset <= 0}
            onClick={() => load(Math.max(0, offset - limit))}
          >
            Previous
          </button>
          <button
            type="button"
            className="secondary"
            disabled={offset + limit >= total}
            onClick={() => load(offset + limit)}
          >
            Next
          </button>
        </div>
      </div>
    </>
  );
}
