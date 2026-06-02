import { FormEvent, useEffect, useState } from "react";
import { api, ProductAttribute } from "../api/client";

const emptyForm = {
  key: "",
  label: "",
  aliases: "",
  hint: "",
  sort_order: 0,
  active: true,
};

export function AttributesPage() {
  const [rows, setRows] = useState<ProductAttribute[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try {
      const data = await api.listAttributes(true);
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load attributes.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function startEdit(row: ProductAttribute) {
    setEditingId(row.id);
    setForm({
      key: row.key,
      label: row.label,
      aliases: row.aliases.join(", "),
      hint: row.hint ?? "",
      sort_order: row.sort_order,
      active: row.active,
    });
  }

  function resetForm() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const aliases = form.aliases
      .split(",")
      .map((a) => a.trim())
      .filter(Boolean);
    try {
      if (editingId) {
        await api.updateAttribute(editingId, {
          label: form.label,
          aliases,
          hint: form.hint || null,
          sort_order: form.sort_order,
          active: form.active,
        });
      } else {
        await api.createAttribute({
          key: form.key,
          label: form.label,
          aliases,
          hint: form.hint || null,
          sort_order: form.sort_order,
          active: form.active,
        });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed.");
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Delete this attribute?")) return;
    try {
      await api.deleteAttribute(id);
      if (editingId === id) resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed.");
    }
  }

  return (
    <div>
      <header className="page-header">
        <div>
          <h2>Attribute catalog</h2>
          <p className="muted">Manage canonical attributes and aliases used for deterministic matching.</p>
        </div>
      </header>

      {error ? <p className="bad-text">{error}</p> : null}

      <div className="card">
        <h3>{editingId ? "Edit attribute" : "Add attribute"}</h3>
        <form onSubmit={onSubmit}>
          <div className="grid-2">
            <div>
              <label htmlFor="attr-key">Key (slug)</label>
              <input
                id="attr-key"
                value={form.key}
                onChange={(e) => setForm({ ...form, key: e.target.value })}
                disabled={Boolean(editingId)}
                required
              />
            </div>
            <div>
              <label htmlFor="attr-label">Label</label>
              <input
                id="attr-label"
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                required
              />
            </div>
          </div>
          <div style={{ marginTop: 12 }}>
            <label htmlFor="attr-aliases">Aliases (comma-separated)</label>
            <input
              id="attr-aliases"
              value={form.aliases}
              onChange={(e) => setForm({ ...form, aliases: e.target.value })}
              placeholder="housing material, construction material"
            />
          </div>
          <div className="grid-2" style={{ marginTop: 12 }}>
            <div>
              <label htmlFor="attr-hint">Hint for LLM</label>
              <input
                id="attr-hint"
                value={form.hint}
                onChange={(e) => setForm({ ...form, hint: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="attr-sort">Sort order</label>
              <input
                id="attr-sort"
                type="number"
                value={form.sort_order}
                onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })}
              />
            </div>
          </div>
          <label className="checkbox-row" style={{ marginTop: 12 }}>
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => setForm({ ...form, active: e.target.checked })}
            />
            Active
          </label>
          <div className="row" style={{ marginTop: 12, gap: 8 }}>
            <button type="submit">{editingId ? "Update" : "Create"}</button>
            {editingId ? (
              <button type="button" className="secondary" onClick={resetForm}>
                Cancel edit
              </button>
            ) : null}
          </div>
        </form>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h3>All attributes</h3>
        {loading ? <p className="muted">Loading…</p> : null}
        <table className="data-table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Key</th>
              <th>Aliases</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.label}</td>
                <td>{row.key}</td>
                <td className="muted small">{row.aliases.join(", ") || "—"}</td>
                <td>{row.active ? "Yes" : "No"}</td>
                <td className="row" style={{ gap: 8 }}>
                  <button type="button" className="secondary" onClick={() => startEdit(row)}>
                    Edit
                  </button>
                  <button type="button" className="secondary" onClick={() => void onDelete(row.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
