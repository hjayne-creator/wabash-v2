import { FormEvent, useState } from "react";
import { api, MatchRunResponse } from "../api/client";
import { MatchResults } from "../components/MatchResults";

export function MatchPage() {
  const [manufacturer, setManufacturer] = useState("");
  const [mpn, setMpn] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MatchRunResponse | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.runMatch({
        manufacturer_name: manufacturer.trim(),
        manufacturer_product_number: mpn.trim(),
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Match run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h2>Product Match Finder</h2>
          <p className="muted">
            Enter manufacturer name and product number. We search Google (US/en), scrape candidate PDPs, and score
            similarity with an LLM.
          </p>
        </div>
      </header>

      <form onSubmit={onSubmit}>
        <div className="card">
          <h3>Product inputs</h3>
          <div className="grid-2">
            <div>
              <label htmlFor="manufacturer">Manufacturer name</label>
              <input
                id="manufacturer"
                value={manufacturer}
                onChange={(e) => setManufacturer(e.target.value)}
                placeholder="WHITING DOOR"
                required
              />
            </div>
            <div>
              <label htmlFor="mpn">Manufacturer product number</label>
              <input
                id="mpn"
                value={mpn}
                onChange={(e) => setMpn(e.target.value)}
                placeholder="ML5035"
                required
              />
            </div>
          </div>
        </div>

        {error ? <p className="bad-text">{error}</p> : null}

        {result ? <MatchResults result={result} onDismiss={() => setResult(null)} /> : null}

        <div className="row right sticky-actions">
          <button type="submit" disabled={running}>
            {running ? "Finding matches…" : "Find matches"}
          </button>
        </div>
      </form>
    </div>
  );
}
