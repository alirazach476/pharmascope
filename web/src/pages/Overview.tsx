import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { api, CHART_COLORS, fmt, type DashboardBundle } from "../api";

export default function Overview() {
  const navigate = useNavigate();
  const [dash, setDash] = useState<DashboardBundle | null>(null);
  const [aeTrends, setAeTrends] = useState<Array<{ year_month: string; report_count: number }>>([]);
  const [topDrugs, setTopDrugs] = useState<
    Array<{ medicinalproduct: string; report_count: number }>
  >([]);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [nameQuery, setNameQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const status = await api.catalogStatus();
        if (cancelled) return;
        setReady(!!status.ready);
        setMessage(status.message ?? null);
        if (status.ready) {
          const bundle = await api.catalogDashboard();
          if (!cancelled) setDash(bundle);
        }
        try {
          const [t, p] = await Promise.all([api.aeTrends(), api.topReported()]);
          if (!cancelled) {
            setAeTrends(t.data ?? []);
            setTopDrugs(p.data ?? []);
          }
        } catch {
          /* optional warehouse */
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const radarData = useMemo(() => {
    if (!dash) return [];
    return dash.by_class.slice(0, 8).map((r) => ({
      class: String(r.therapeutic_class).slice(0, 12),
      n: Number(r.n),
    }));
  }, [dash]);

  const scatterData = useMemo(() => {
    if (!dash) return [];
    return dash.form_route.slice(0, 40).map((r) => ({
      x: String(r.dosage_form),
      y: String(r.route),
      z: Number(r.n),
      label: `${r.dosage_form} / ${r.route}`,
    }));
  }, [dash]);

  const topRoutes = useMemo(() => {
    return [...(dash?.by_route ?? [])]
      .sort((a, b) => Number(b.n) - Number(a.n))
      .slice(0, 10);
  }, [dash]);

  const stats = dash?.stats;

  function onSearchName(e: FormEvent) {
    e.preventDefault();
    const q = nameQuery.trim();
    navigate(q ? `/medicines?q=${encodeURIComponent(q)}` : "/medicines");
  }

  return (
    <>
      <div className="hero">
        <div className="badge">50M-scale intelligence</div>
        <h1>Pharmaceutical command center</h1>
        <p>
          Dense visualization suite over a 50-million-row catalog (authentic OpenFDA NDC seed +
          labeled synthetic fill) plus authentic FAERS/recall warehouse extracts.
        </p>
      </div>

      <form className="toolbar" onSubmit={onSearchName}>
        <input
          value={nameQuery}
          onChange={(e) => setNameQuery(e.target.value)}
          placeholder="Search medicine by name…"
          aria-label="Search medicine by name"
          style={{ flex: 1, minWidth: 240 }}
        />
        <button type="submit">Search medicines</button>
      </form>

      {error && <div className="error">{error}</div>}
      {!ready && !error && (
        <div className="banner">{message ?? "Building 50M catalog… refresh in a minute."}</div>
      )}

      <div className="kpi-grid kpi-grid-6">
        {[
          ["Total medicines", stats?.total_medicines, "Catalog rows"],
          ["Synthetic fill", stats?.synthetic_count, "Scale demo"],
          ["Authentic NDC", stats?.authentic_count, "OpenFDA seed"],
          ["Manufacturers", stats?.manufacturers, "Distinct"],
          ["Ingredients", stats?.ingredients, "Distinct actives"],
          ["Regions", stats?.regions, "Synthetic markets"],
        ].map(([label, value, hint]) => (
          <div className="kpi" key={String(label)}>
            <div className="label">{label}</div>
            <div className="value">{fmt(value as number)}</div>
            <div className="hint">{hint}</div>
          </div>
        ))}
      </div>

      <div className="grid-3">
        <div className="panel">
          <h3>Authenticity mix</h3>
          <div className="sub">Seed vs synthetic fill</div>
          <div className="chart-box">
            <ResponsiveContainer>
              <PieChart>
                <Pie
                  data={dash?.authenticity ?? []}
                  dataKey="n"
                  nameKey="origin"
                  innerRadius={55}
                  outerRadius={90}
                >
                  {(dash?.authenticity ?? []).map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Dosage forms</h3>
          <div className="sub">Top forms in catalog</div>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={(dash?.by_form ?? []).slice(0, 8)}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="dosage_form" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#1aa6a0" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Routes</h3>
          <div className="sub">Top administration routes</div>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={topRoutes} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="route"
                  width={108}
                  tick={{ fill: "#93a0b8", fontSize: 10 }}
                />
                <Tooltip />
                <Bar dataKey="n" fill="#8b7cf6" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Therapeutic class radar</h3>
          <div className="sub">Relative class volumes</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#243049" />
                <PolarAngleAxis dataKey="class" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <PolarRadiusAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Radar dataKey="n" stroke="#3d8bfd" fill="#3d8bfd" fillOpacity={0.35} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Market regions</h3>
          <div className="sub">Synthetic regional allocation</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={dash?.by_region ?? []} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="market_region"
                  width={110}
                  tick={{ fill: "#93a0b8", fontSize: 10 }}
                />
                <Tooltip />
                <Bar dataKey="n" fill="#e6a23c" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Synthetic launch-year timeline</h3>
          <div className="sub">Assigned demo years (not real marketing dates)</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <AreaChart data={dash?.by_year ?? []}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="launch_year" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="n" stroke="#1aa6a0" fill="#1aa6a033" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Strength buckets</h3>
          <div className="sub">Synthetic strength_mg distribution</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={dash?.by_strength ?? []}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="strength_bucket" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#8b7cf6" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Top ingredients</h3>
          <div className="sub">Catalog-wide active ingredient counts</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={(dash?.by_ingredient ?? []).slice(0, 12)} layout="vertical" margin={{ left: 10 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="active_ingredient"
                  width={120}
                  tick={{ fill: "#93a0b8", fontSize: 10 }}
                />
                <Tooltip />
                <Bar dataKey="n" fill="#5ad1e6" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Top manufacturers</h3>
          <div className="sub">Includes synthetic labelers</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart
                data={(dash?.top_manufacturers ?? []).slice(0, 12)}
                layout="vertical"
                margin={{ left: 10 }}
              >
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="manufacturer_name"
                  width={130}
                  tick={{ fill: "#93a0b8", fontSize: 9 }}
                />
                <Tooltip />
                <Bar dataKey="n" fill="#3d8bfd" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Form × route concentration</h3>
        <div className="sub">Bubble size = medicine count</div>
        <div className="chart-box tall">
          <ResponsiveContainer>
            <ScatterChart margin={{ left: 10, bottom: 10 }}>
              <CartesianGrid stroke="#243049" />
              <XAxis
                type="category"
                dataKey="x"
                name="Form"
                allowDuplicatedCategory={false}
                tick={{ fill: "#93a0b8", fontSize: 9 }}
              />
              <YAxis
                type="category"
                dataKey="y"
                name="Route"
                allowDuplicatedCategory={false}
                width={100}
                tick={{ fill: "#93a0b8", fontSize: 9 }}
              />
              <ZAxis type="number" dataKey="z" range={[40, 400]} />
              <Tooltip cursor={{ strokeDasharray: "3 3" }} />
              <Scatter data={scatterData} fill="#1aa6a0" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Authentic AE trend</h3>
          <div className="sub">Warehouse FAERS sample — reported cases</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <LineChart data={aeTrends}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Line type="monotone" dataKey="report_count" stroke="#e35d6a" strokeWidth={2.4} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Top reported products (FAERS)</h3>
          <div className="sub">Authentic warehouse extract</div>
          <div className="chart-box tall">
            <ResponsiveContainer>
              <BarChart data={topDrugs} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="medicinalproduct"
                  width={130}
                  tick={{ fill: "#93a0b8", fontSize: 9 }}
                />
                <Tooltip />
                <Bar dataKey="report_count" fill="#e35d6a" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}
