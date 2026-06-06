import { FormEvent, useEffect, useState } from "react";
import { api } from "./api/client";
import { AttributesPage } from "./pages/Attributes";
import { ReportsPage } from "./pages/Reports";
import { ResearchPage } from "./pages/Research";

type Page = "research" | "reports" | "attributes";

function LoginScreen({ onLoggedIn }: { onLoggedIn: (username: string | null) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({ username, password });
      onLoggedIn(res.username);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-screen">
      <div className="card login-card">
        <h2>Sign in</h2>
        <p className="muted small">Use the credentials configured on the backend.</p>
        <form onSubmit={onSubmit}>
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <label htmlFor="login-password">Password</label>
          <input
            id="login-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error ? <p className="small bad-text">{error}</p> : null}
          <div style={{ marginTop: 12 }}>
            <button type="submit" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function App() {
  const [checkingSession, setCheckingSession] = useState(true);
  const [authEnabled, setAuthEnabled] = useState(false);
  const [authenticated, setAuthenticated] = useState(true);
  const [username, setUsername] = useState<string | null>(null);
  const [page, setPage] = useState<Page>("research");

  useEffect(() => {
    let mounted = true;
    async function boot() {
      try {
        const session = await api.getSession();
        if (!mounted) return;
        setAuthEnabled(session.enabled);
        setAuthenticated(session.authenticated);
        setUsername(session.username);
      } catch {
        if (!mounted) return;
        setAuthEnabled(true);
        setAuthenticated(false);
      } finally {
        if (mounted) setCheckingSession(false);
      }
    }
    boot();
    const onUnauthorized = () => {
      setAuthenticated(false);
      setUsername(null);
      setAuthEnabled(true);
    };
    window.addEventListener("auth:unauthorized", onUnauthorized);
    return () => {
      mounted = false;
      window.removeEventListener("auth:unauthorized", onUnauthorized);
    };
  }, []);

  async function handleLogout() {
    try {
      await api.logout();
    } finally {
      setAuthenticated(false);
      setUsername(null);
    }
  }

  if (checkingSession) {
    return (
      <div className="login-screen">
        <div className="card login-card">
          <p className="muted">Checking session…</p>
        </div>
      </div>
    );
  }

  if (authEnabled && !authenticated) {
    return (
      <LoginScreen
        onLoggedIn={(name) => {
          setAuthenticated(true);
          setUsername(name);
        }}
      />
    );
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <h1 className="brand">Wabash V2</h1>
        <p className="muted small">Attribute Research</p>
        <p className="muted small">{username ? `Signed in as ${username}` : "Internal tool"}</p>
        <nav className="sidebar-nav">
          <button
            type="button"
            className={page === "research" ? "nav-active" : "nav-link"}
            onClick={() => setPage("research")}
          >
            Research
          </button>
          <button
            type="button"
            className={page === "reports" ? "nav-active" : "nav-link"}
            onClick={() => setPage("reports")}
          >
            Reports
          </button>
          <button
            type="button"
            className={page === "attributes" ? "nav-active" : "nav-link"}
            onClick={() => setPage("attributes")}
          >
            Attributes
          </button>
        </nav>
        <details className="sidebar-about">
          <summary>How this works</summary>
          <div className="sidebar-about-body text-light-med">
            <p>
              Enter a manufacturer and MPN, pick a web-research engine (Perplexity, Parallel, or Firecrawl), and run a
              single research pass. Results are mapped to your attribute catalog with deterministic matching.
            </p>
          </div>
        </details>
        {authEnabled ? (
          <div className="sidebar-footer">
            <button type="button" className="secondary" onClick={() => void handleLogout()}>
              Log out
            </button>
          </div>
        ) : null}
      </aside>
      <main className="main">
        {page === "research" ? <ResearchPage /> : null}
        {page === "reports" ? <ReportsPage /> : null}
        {page === "attributes" ? <AttributesPage /> : null}
      </main>
    </div>
  );
}
