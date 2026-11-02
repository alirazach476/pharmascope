import { useEffect, useMemo, useState } from "react";
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
import { api, CHART_COLORS, fmt } from "../api";

export default function Operations() {
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([]);
  const [dq, setDq] = useState<Array<Record<string, unknown>>>([]);
  const [sources, setSources] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.pipelineRuns(), api.dqSummary(), api.sources()])
      .then(([p, d, s]) => {
        setRuns(p.runs ?? []);
        setDq(d.reports ?? []);
        setSources(s.sources ?? []);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  const statusMix = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of runs) {
      const st = String(r.status ?? "unknown");
      map.set(st, (map.get(st) ?? 0) + 1);
    }
    return [...map.entries()].map(([status, count]) => ({ status, count }));
  }, [runs]);

  const bySource = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of runs) {
      const src = String(r.source_name ?? "unknown");
      map.set(src, (map.get(src) ?? 0) + Number(r.raw_record_count ?? 0));
    }
    return [...map.entries()].map(([source, records]) => ({ source, records }));
  }, [runs]);

  const checkRows = useMemo(() => {
    const rows: Array<{ severity: string; passed: boolean }> = [];
    for (const rep of dq.slice(0, 10)) {
      const checks = (rep.checks as Array<Record<string, unknown>>) ?? [];
      for (const c of checks) {
        rows.push({ severity: String(c.severity), passed: Boolean(c.passed) });
      }
    }
    return rows;
  }, [dq]);

  const severityFail = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of checkRows.filter((c) => !c.passed)) {
      map.set(r.severity, (map.get(r.severity) ?? 0) + 1);
    }
    return [...map.entries()].map(([severity, count]) => ({ severity, count }));
  }, [checkRows]);

  return (
    <>
      <div className="hero">
        <div className="badge">Pipeline & quality</div>
        <h1>Operations monitor</h1>
        <p>Extraction manifests, source registry, and data-quality outcomes powering the platform.</p>
      </div>
      {error && <div className="error">{error}</div>}

      <div className="kpi-grid">
        <div className="kpi">
          <div className="label">Pipeline runs</div>
          <div className="value">{fmt(runs.length)}</div>
          <div className="hint">Manifests</div>
        </div>
        <div className="kpi">
          <div className="label">DQ reports</div>
          <div className="value">{fmt(dq.length)}</div>
          <div className="hint">Recent</div>
        </div>
        <div className="kpi">
          <div className="label">Sources</div>
          <div className="value">{fmt(sources.length)}</div>
          <div className="hint">Configured</div>
        </div>
        <div className="kpi">
          <div className="label">Enabled</div>
          <div className="value">{fmt(sources.filter((s) => s.enabled).length)}</div>
          <div className="hint">Active sources</div>
        </div>
        <div className="kpi">
          <div className="label">Failed checks</div>
          <div className="value">{fmt(checkRows.filter((c) => !c.passed).length)}</div>
          <div className="hint">In recent DQ</div>
        </div>
      </div>

      <div className="grid-3">
        <div className="panel">
          <h3>Run status</h3>
          <div className="chart-box">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={statusMix} dataKey="count" nameKey="status" outerRadius={90}>
                  {statusMix.map((_, i) => (
                    <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Records by source</h3>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={bySource}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="source" tick={{ fill: "#93a0b8", fontSize: 9 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="records" fill="#1aa6a0" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        <div className="panel">
          <h3>Failed checks by severity</h3>
          <div className="chart-box">
            <ResponsiveContainer>
              <BarChart data={severityFail}>
                <CartesianGrid stroke="#243049" strokeDasharray="3 3" />
                <XAxis dataKey="severity" tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <YAxis tick={{ fill: "#93a0b8", fontSize: 10 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#e35d6a" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </>
  );
}
