import { ResearchRunResponse } from "../api/client";

type Props = {
  result: ResearchRunResponse;
  onDismiss: () => void;
};

function formatRunCost(result: ResearchRunResponse): string {
  const firecrawlLine = result.cost_lines.find((line) => line.service === "firecrawl");
  if (firecrawlLine?.units && firecrawlLine.units > 0) {
    const rate =
      firecrawlLine.unit_cost_usd ??
      (firecrawlLine.total_cost_usd ? firecrawlLine.total_cost_usd / firecrawlLine.units : 0);
    const total = firecrawlLine.total_cost_usd ?? rate * firecrawlLine.units;
    return `${firecrawlLine.units} credits × $${rate.toFixed(4)} = $${total.toFixed(4)}`;
  }
  return `$${result.total_cost_usd.toFixed(4)}`;
}

export function ResearchResults({ result, onDismiss }: Props) {
  const mappedRows = Object.values(result.mapped);

  return (
    <div className="card results-card">
      <div className="row between">
        <div>
          <h3 id="report-results-title">Research results</h3>
          <p className="muted small">
            Run #{result.id} · {result.status} · Fill {result.fill_pct}% ({result.attributes_filled}/
            {result.attributes_total}) · {formatRunCost(result)}
          </p>
        </div>
        <button type="button" className="secondary" onClick={onDismiss}>
          Clear
        </button>
      </div>

      {result.message ? <p className="small">{result.message}</p> : null}
      {result.error_message ? <p className="small bad-text">{result.error_message}</p> : null}

      {result.research_query ? (
        <>
          <h4>Search query</h4>
          <pre className="step-output-pre">{result.research_query}</pre>
        </>
      ) : null}

      {result.research_prompt && result.research_prompt !== result.research_query ? (
        <details className="step-output-details" style={{ marginTop: 12 }}>
          <summary>Full research prompt</summary>
          <pre className="step-output-pre">{result.research_prompt}</pre>
        </details>
      ) : null}

      <h4>Mapped attributes</h4>
      {mappedRows.length === 0 ? (
        <p className="muted small">No mapped attributes.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Attribute</th>
              <th>Value</th>
              <th>Match</th>
            </tr>
          </thead>
          <tbody>
            {mappedRows.map((row) => (
              <tr key={row.key}>
                <td>{row.label}</td>
                <td>{row.value}</td>
                <td className="muted small">{row.confidence}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {result.missing.length > 0 ? (
        <>
          <h4>Missing from catalog</h4>
          <p className="muted small">{result.missing.join(", ")}</p>
        </>
      ) : null}

      {Object.keys(result.unmapped_from_llm).length > 0 ? (
        <>
          <h4>Unmapped LLM keys</h4>
          <table className="data-table">
            <thead>
              <tr>
                <th>Key</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.unmapped_from_llm).map(([key, value]) => (
                <tr key={key}>
                  <td>{key}</td>
                  <td>{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      ) : null}

      {result.sources.length > 0 ? (
        <>
          <h4>Sources</h4>
          <ul className="source-list">
            {result.sources.map((source) => (
              <li key={source.url}>
                <a href={source.url} target="_blank" rel="noreferrer">
                  {source.title || source.url}
                </a>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </div>
  );
}
