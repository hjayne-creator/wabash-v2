import { useEffect, useState } from "react";
import { api, ResearchRunResponse, ResearchRunSummary } from "../api/client";
import { ResearchResults } from "../components/ResearchResults";

export function ReportsPage() {
  const [runs, setRuns] = useState<ResearchRunSummary[]>([]);
  const [selected, setSelected] = useState<ResearchRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .listResearchRuns(100)
      .then(setRuns)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load reports."))
      .finally(() => setLoading(false));
  }, []);

  async function openRun(id: number) {
    try {
      const detail = await api.getResearchRun(id);
      setSelected(detail);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load run.");
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h2>Research reports</h2>
          <p className="muted">History of attribute research runs with fill rate and cost.</p>
        </div>
      </header>

      {error ? <p className="bad-text">{error}</p> : null}
      {loading ? <p className="muted">Loading reports…</p> : null}

      <div className="card">
        <table className="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>Manufacturer</th>
              <th>MPN</th>
              <th>Engine</th>
              <th>Fill %</th>
              <th>Cost</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>{new Date(run.created_at).toLocaleString()}</td>
                <td>{run.manufacturer_name}</td>
                <td>{run.manufacturer_product_number}</td>
                <td>
                  {run.engine_provider} / {run.engine_model}
                </td>
                <td>{run.fill_pct}%</td>
                <td>${run.total_cost_usd.toFixed(4)}</td>
                <td>{run.status}</td>
                <td>
                  <button type="button" className="secondary" onClick={() => void openRun(run.id)}>
                    View
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && runs.length === 0 ? <p className="muted small">No runs yet.</p> : null}
      </div>

      {selected ? <ResearchResults result={selected} onDismiss={() => setSelected(null)} /> : null}
    </div>
  );
}
