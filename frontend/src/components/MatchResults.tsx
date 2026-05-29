import { MatchRunResponse } from "../api/client";

type MatchResultsProps = {
  result: MatchRunResponse;
  onDismiss: () => void;
};

export function MatchResults({ result, onDismiss }: MatchResultsProps) {
  const statusClass =
    result.status === "complete" ? "good" : result.status === "no_candidates" ? "bad" : "warn";

  return (
    <div className="card match-results">
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h3>Match results</h3>
          <span className={`status-pill ${statusClass}`}>{result.status.replace("_", " ")}</span>
        </div>
        <button type="button" className="secondary" onClick={onDismiss}>
          Dismiss
        </button>
      </div>

      {result.message ? <p className="bad-text">{result.message}</p> : null}

      <p className="small muted">
        Normalized: <strong>{result.manufacturer_name}</strong> / <strong>{result.manufacturer_product_number}</strong>
      </p>

      <h4>Step 1 — Candidates from search</h4>
      {result.candidates.length === 0 ? (
        <p className="muted small">No candidates returned.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Tier</th>
              <th>Title</th>
              <th>Snippet</th>
              <th>SERP rank</th>
            </tr>
          </thead>
          <tbody>
            {result.candidates.map((c) => (
              <tr key={c.url}>
                <td>{c.rank}</td>
                <td>{c.tier}</td>
                <td>
                  <a href={c.url} target="_blank" rel="noreferrer">
                    {c.title || c.url}
                  </a>
                </td>
                <td className="snippet-cell">{c.snippet}</td>
                <td>{c.serp_score.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Step 2 — Scrape &amp; prefilter</h4>
      {result.sources.length === 0 ? (
        <p className="muted small">Nothing scraped.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>URL</th>
              <th>Scraped</th>
              <th>Product page</th>
              <th>Page score</th>
              <th>Match score</th>
              <th>Rule MPN</th>
              <th>Rule mfg</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {result.sources.map((s) => (
              <tr key={s.url}>
                <td>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title || s.url}
                  </a>
                </td>
                <td>{s.scrape_ok ? "yes" : "no"}</td>
                <td>
                  {s.is_product_page == null ? "—" : s.is_product_page ? "yes" : "no"}
                </td>
                <td>{s.product_page_score ?? "—"}</td>
                <td>{s.product_match_score ?? "—"}</td>
                <td>{s.rule_mpn_found ? "yes" : "no"}</td>
                <td>{s.rule_manufacturer_match ? "yes" : "no"}</td>
                <td>{s.scrape_error || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <h4>Step 3 — Match scores (LLM)</h4>
      {result.sources.every((s) => s.overall_similarity_pct == null) ? (
        <p className="muted small">No scores available (scrapes or scoring failed).</p>
      ) : (
        <div className="score-cards">
          {result.sources.map((s) => (
            <details key={s.url} className="score-card" open={!!s.overall_similarity_pct}>
              <summary>
                <span className="score-summary-title">{s.title || s.url}</span>
                {s.overall_similarity_pct != null ? (
                  <span className="score-pill">{s.overall_similarity_pct}% overall</span>
                ) : (
                  <span className="score-pill bad">unscored</span>
                )}
              </summary>
              {s.score_error ? <p className="bad-text small">{s.score_error}</p> : null}
              {s.criteria.length > 0 ? (
                <table className="data-table criteria-table">
                  <thead>
                    <tr>
                      <th>Criterion</th>
                      <th>Score</th>
                      <th>Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {s.criteria.map((c) => (
                      <tr key={c.name}>
                        <td>{c.name}</td>
                        <td>{c.score_pct}%</td>
                        <td>{c.rationale}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : null}
              {s.markdown_excerpt ? (
                <details className="step-output-details">
                  <summary>Scraped excerpt</summary>
                  <pre className="output-text step-output-pre">{s.markdown_excerpt}</pre>
                </details>
              ) : null}
            </details>
          ))}
        </div>
      )}

      <p className="small muted" style={{ marginTop: 16 }}>
        Runtime: {result.total_runtime_ms} ms · Est. cost: ${result.total_cost_usd.toFixed(4)}
      </p>
    </div>
  );
}
