import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Line,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
  Scatter,
  ScatterChart,
  ZAxis,
} from "recharts";
import { ChartFrame } from "../components/ChartFrame";
import { api } from "../api";

export default function Safety() {
  const [trends, setTrends] = useState<Array<{ year_month: string; report_count: number }>>([]);
  const [top, setTop] = useState<Array<{ medicinalproduct: string; report_count: number }>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [t, p] = await Promise.all([api.aeTrends(), api.topReported()]);
        setTrends(t.data ?? []);
        setTop(p.data ?? []);
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      }
    })();
  }, []);

  const rolling = useMemo(() => {
    const out = [];
    for (let i = 0; i < trends.length; i++) {
      const window = trends.slice(Math.max(0, i - 2), i + 1);
      const avg = window.reduce((s, r) => s + r.report_count, 0) / Math.max(window.length, 1);
      out.push({ ...trends[i], rolling_3: Number(avg.toFixed(2)) });
    }
    return out;
  }, [trends]);

  const scatter = useMemo(
    () =>
      top.map((r, i) => ({
        rank: i + 1,
        reports: r.report_count,
        name: r.medicinalproduct,
      })),
    [top],
  );

  const cumulative = useMemo(() => {
    let run = 0;
    return trends.map((r) => {
      run += r.report_count;
      return { ...r, cumulative: run };
    });
  }, [trends]);

  return (
    <>
      <div className="hero">
        <div className="badge">Authentic FAERS sample</div>
        <h1>Drug safety analytics</h1>
        <p>
          Multiple views of reported adverse-event volumes from the warehouse. These are reported
          cases — not incidence, risk, or proven causation.
        </p>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="grid-2">
        <div className="panel">
          <h3>Monthly reports + 3-period rolling mean</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!rolling.length}>
              <ComposedChart data={rolling}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="report_count" fill="#1aa6a0" name="Reports" />
                <Line type="monotone" dataKey="rolling_3" stroke="#e6a23c" strokeWidth={2.5} name="Rolling mean" />
              </ComposedChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Cumulative reported cases</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!cumulative.length}>
              <AreaChart data={cumulative}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Area type="monotone" dataKey="cumulative" stroke="#3d8bfd" fill="#3d8bfd33" />
              </AreaChart>
            </ChartFrame>
          </div>
        </div>
      </div>

      <div className="grid-2">
        <div className="panel">
          <h3>Top reported products</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!top.length}>
              <BarChart data={top} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis type="category" dataKey="medicinalproduct" width={140} tick={{ fill: "#93a0b8", fontSize: 9 }} />
                <Tooltip />
                <Bar dataKey="report_count" fill="#e35d6a" />
              </BarChart>
            </ChartFrame>
          </div>
        </div>
        <div className="panel">
          <h3>Rank vs report volume</h3>
          <div className="chart-box tall">
            <ChartFrame empty={!scatter.length}>
              <ScatterChart>
                <CartesianGrid stroke="#243049" />
                <XAxis type="number" dataKey="rank" name="Rank" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis type="number" dataKey="reports" name="Reports" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <ZAxis range={[60, 200]} />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} />
                <Scatter data={scatter} fill="#8b7cf6" />
              </ScatterChart>
            </ChartFrame>
          </div>
        </div>
      </div>
    </>
  );
}
