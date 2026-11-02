/**
 * Tiny API helper. Uses the Vite proxy (/api → FastAPI :8000) in development.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join(", ")
      : detail || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return res.json();
}

export function fetchCommodities(q = "") {
  const query = q ? `?q=${encodeURIComponent(q)}` : "";
  return request(`/commodities${query}`);
}

export function fetchPrices(commodity) {
  const q = commodity ? `?commodity=${encodeURIComponent(commodity)}` : "";
  return request(`/prices${q}`);
}

export function searchPrices(text) {
  const q = text ? `?q=${encodeURIComponent(text)}` : "";
  return request(`/prices${q}`);
}

export function triggerScrape() {
  return request("/scrape", { method: "POST" });
}
