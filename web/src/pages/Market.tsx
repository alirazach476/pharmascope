import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Tooltip,
  XAxis,
  YAxis,
  Treemap,
} from "recharts";
import { ChartFrame } from "../components/ChartFrame";
import { api, fmt, type DashboardBundle } from "../api";

export default function Market() {
  const [dash, setDash] = useState<DashboardBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .catalogDashboard()
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const tree = (dash?.top_manufacturers ?? []).slice(0, 16).map((r) => ({
    name: String(r.manufacturer_name).slice(0, 22),
    size: Number(r.n),
  }));

  return (
    <>
      <div className="hero">
        <div className="badge">Market landscape</div>
        <h1>Product & market analytics</h1>
        <p>
          Region, manufacturer, class, and timeline visuals from the 50M catalog aggregates. Price and
          CMS utilization remain unavailable until official sources are configured.
        </p>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="kpi-grid">
        <div className="kpi">
          <div className="label">Catalog</div>
          <div className="value">{fmt(dash?.stats.total_medicines)}</div>
          <div className="hint">Medicines</div>
        </div>
        <div className="kpi">
          <div className="label">Manufacturers</div>
          <div className="value">{fmt(dash?.stats.manufacturers)}</div>
          <div className="hint">Distinct</div>
        </div>
        <div className="kpi">
          <div className="label">Regions</div>
          <div className="value">{fmt(dash?.stats.regions)}</div>
          <div className="hint">Market regions</div>
        </div>
        <div className="kpi">
          <div className="label">Classes</div>
          <div className="value">{fmt(dash?.stats.therapeutic_classes)}</div>
          <div className="hint">Therapeutic</div>
        </div>
        <div className="kpi">
          <div className="label">Routes</div>
          <div className="value">{fmt(dash?.stats.routes)}</div>
          <div className="hint">Admin routes</div>
        </div>
      </div>

      <div className="grid-3">
        <div className="panel">
          <h3>Region share</h3>
          <div className="chart-box">
            <ChartFrame empty={!dash?.by_region?.length}>
              <BarChart data={dash?.by_region ?? []} layout="vertical" margin={{ left: 8 }}>
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
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Therapeutic classes</h3>
          <div className="chart-box">
            <ChartFrame empty={!dash?.by_class?.length}>
              <BarChart data={dash?.by_class ?? []}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="therapeutic_class" hide />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#3d8bfd" />
              </BarChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Strength profile</h3>
          <div className="chart-box">
            <ChartFrame empty={!dash?.by_strength?.length}>
              <BarChart data={dash?.by_strength ?? []}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="strength_bucket" tick={{ fill: "#93a0b8", fontSize: 9 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#8b7cf6" />
              </BarChart>
            </ChartFrame>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Launch-year volume</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!dash?.by_year?.length}>
              <AreaChart data={dash?.by_year ?? []}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="launch_year" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="n" stroke="#e6a23c" fill="#e6a23c33" />
              </AreaChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Manufacturer treemap</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!tree.length}>
              <Treemap data={tree} dataKey="size" nameKey="name" stroke="#0b1220" fill="#1aa6a0" />
            </ChartFrame>
          </div>
        </div>
      </div>
    </>
  );
}
