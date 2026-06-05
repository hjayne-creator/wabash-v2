import { FormEvent, useEffect, useState } from "react";
import { api, ResearchEngine, ResearchEngineProvider, ResearchRunResponse } from "../api/client";

const PROVIDER_LABELS: Record<ResearchEngineProvider, string> = {
  perplexity: "Perplexity",
  parallel: "Parallel",
  brave: "Brave",
};

const VISIBLE_PERPLEXITY_MODELS = new Set(["preset:pro-search"]);

function filterVisibleEngines(list: ResearchEngine[]): ResearchEngine[] {
  return list.filter(
    (engine) => engine.provider !== "perplexity" || VISIBLE_PERPLEXITY_MODELS.has(engine.model),
  );
}
import { ResearchResults } from "../components/ResearchResults";

export function ResearchPage() {
  const [manufacturer, setManufacturer] = useState("");
  const [mpn, setMpn] = useState("");
  const [engines, setEngines] = useState<ResearchEngine[]>([]);
  const [engineProvider, setEngineProvider] = useState<ResearchEngineProvider>("perplexity");
  const [engineModel, setEngineModel] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchRunResponse | null>(null);

  useEffect(() => {
    api
      .getResearchEngines()
      .then((list) => {
        const visible = filterVisibleEngines(list);
        setEngines(visible);
        const defaultEngine = visible.find((e) => e.is_default) ?? visible[0];
        if (defaultEngine) {
          setEngineProvider(defaultEngine.provider);
          setEngineModel(defaultEngine.model);
        }
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load engines."));
  }, []);

  const providers = [...new Set(engines.map((e) => e.provider))];
  const modelsForProvider = engines.filter((e) => e.provider === engineProvider);

  useEffect(() => {
    if (modelsForProvider.length === 0) return;
    if (!modelsForProvider.some((e) => e.model === engineModel)) {
      setEngineModel(modelsForProvider[0].model);
    }
  }, [engineProvider, modelsForProvider, engineModel]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const response = await api.runResearch({
        manufacturer_name: manufacturer.trim(),
        manufacturer_product_number: mpn.trim(),
        engine_provider: engineProvider,
        engine_model: engineModel,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research run failed.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h2>Attribute Research</h2>
          <p className="muted">
            Enter manufacturer and product number. A web-research engine finds specifications and maps them to your
            attribute catalog.
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
          <div className="grid-2" style={{ marginTop: 16 }}>
            <div>
              <label htmlFor="engine-provider">Research engine</label>
              <select
                id="engine-provider"
                value={engineProvider}
                onChange={(e) => setEngineProvider(e.target.value as ResearchEngineProvider)}
              >
                {providers.map((provider) => (
                  <option key={provider} value={provider}>
                    {PROVIDER_LABELS[provider]}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="engine-model">Model / preset</label>
              <select
                id="engine-model"
                value={engineModel}
                onChange={(e) => setEngineModel(e.target.value)}
              >
                {modelsForProvider.map((engine) => (
                  <option key={`${engine.provider}-${engine.model}`} value={engine.model}>
                    {engine.display_name}
                  </option>
                ))}
              </select>
              {modelsForProvider.find((e) => e.model === engineModel)?.description ? (
                <p className="muted small" style={{ marginTop: 6 }}>
                  {modelsForProvider.find((e) => e.model === engineModel)?.description}
                </p>
              ) : null}
            </div>
          </div>
        </div>

        {error ? <p className="bad-text">{error}</p> : null}
        {result ? <ResearchResults result={result} onDismiss={() => setResult(null)} /> : null}

        <div className="row right sticky-actions">
          <button type="submit" disabled={running || !engineModel}>
            {running ? "Researching…" : "Run research"}
          </button>
        </div>
      </form>
    </div>
  );
}
