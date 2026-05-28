import { FormEvent, useEffect, useState } from "react";
import { api } from "./api/client";
import { MatchPage } from "./pages/Match";

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
        <h1 className="brand">Wabash</h1>
        <p className="muted small">Product Match POC</p>
        <p className="muted small">{username ? `Signed in as ${username}` : "Internal tool"}</p>
        <details className="sidebar-about">
          <summary>How this works</summary>
          <div className="sidebar-about-body text-light-med">
            <p className="sidebar-about-label">The flow</p>
            <ol>
              <li>Enter the manufacturer name and product number, then run a search.</li>
              <li>We look across the web for pages that look like a single product—not catalogs or search results.</li>
              <li>Promising pages are opened and read so we can see titles, descriptions, and specifications.</li>
              <li>Each page gets a similarity score showing how closely it matches what you entered.</li>
            </ol>
            <p className="sidebar-about-label">How matching works</p>
            <p>
              We favor official manufacturer sites, datasheets, known distributors, and Wabash’s own catalog when
              ranking results. Category pages, shop-all listings, and generic search results are set aside.
            </p>
            <p>
              A strong match usually means the same part number appears on the page and the brand name lines up with
              yours. Pages that read like a real product detail—with specs, part numbers, or a datasheet—score higher
              than vague or unrelated pages.
            </p>
            <p>
              The overall percentage is a quick read: higher means the page is more likely the same product you’re
              looking for. Open a result to see how it scored on manufacturer, part number, title, and other details.
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
        <MatchPage />
      </main>
    </div>
  );
}
