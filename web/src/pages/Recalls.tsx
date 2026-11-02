import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ChartFrame } from "../components/ChartFrame";
import { api, CHART_COLORS } from "../api";

export default function Recalls() {
  const [raw, setRaw] = useState<
    Array<{ year_month: string; classification: string; recall_count: number }>
  >([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .recallTrends()
      .then((r) => setRaw(r.data ?? []))
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const series = useMemo(() => {
    const map = new Map<string, Record<string, string | number>>();
    for (const row of raw) {
      const cur = map.get(row.year_month) ?? { year_month: row.year_month, total: 0 };
      const key = row.classification || "Unknown";
      cur[key] = Number(cur[key] ?? 0) + row.recall_count;
      cur.total = Number(cur.total) + row.recall_count;
      map.set(row.year_month, cur);
    }
    return [...map.values()].sort((a, b) =>
      String(a.year_month).localeCompare(String(b.year_month)),
    );
  }, [raw]);

  const classes = useMemo(
    () => [...new Set(raw.map((r) => r.classification || "Unknown"))],
    [raw],
  );

  const classTotals = useMemo(() => {
    const map = new Map<string, number>();
    for (const row of raw) {
      const key = row.classification || "Unknown";
      map.set(key, (map.get(key) ?? 0) + row.recall_count);
    }
    return [...map.entries()].map(([classification, recall_count]) => ({
      classification,
      recall_count,
    }));
  }, [raw]);

  const topMonths = useMemo(
    () => [...series].sort((a, b) => Number(b.total) - Number(a.total)).slice(0, 12),
    [series],
  );

  return (
    <>
      <div className="hero">
        <div className="badge">OpenFDA enforcement</div>
        <h1>Recall intelligence</h1>
        <p>
          Multi-chart recall analytics from authentic warehouse extracts. Verify status fields before
          inferring current recall state.
        </p>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="grid-3">
        <div className="panel">
          <h3>Classification mix</h3>
          <div className="chart-box">
            <ChartFrame empty={!classTotals.length}>
              <PieChart>
                <Pie data={classTotals} dataKey="recall_count" nameKey="classification" outerRadius={90}>
                  {classTotals.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Busiest months</h3>
          <div className="chart-box">
            <ChartFrame empty={!topMonths.length}>
              <BarChart data={topMonths}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" tick={{ fill: "#93a0b8", fontSize: 8 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="total" fill="#e35d6a" />
              </BarChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Total trend</h3>
          <div className="chart-box">
            <ChartFrame empty={!series.length}>
              <AreaChart data={series}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" hide />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="total" stroke="#e6a23c" fill="#e6a23c33" />
              </AreaChart>
            </ChartFrame>
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Recalls by classification over time</h3>
        <div className="chart-box tall">
          <ChartFrame empty={!series.length}>
            <LineChart data={series}>
              <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
              <XAxis dataKey="year_month" tick={{ fill: "#93a0b8", fontSize: 10 }} />
              <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
              <Tooltip />
              <Legend />
              {classes.map((c, i) => (
                <Line
                  key={c}
                  type="monotone"
                  dataKey={c}
                  stroke={CHART_COLORS[i % CHART_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ChartFrame>
        </div>
      </div>
    </>
  );
}
