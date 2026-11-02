import { useEffect, useMemo, useRef, useState } from "react";
import {
  fetchCommodities,
  fetchPrices,
  searchPrices,
  triggerScrape,
} from "./api.js";
import "./App.css";

const QUICK_PICKS = [
  { id: "maize", name: "Maize" },
  { id: "tomato", name: "Tomato" },
  { id: "potato", name: "Potato" },
  { id: "soya", name: "Soya Beans" },
  { id: "onion-dried", name: "Onions" },
  { id: "cabbage-white", name: "Cabbage" },
];

function formatPrice(value) {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(2);
}

function formatWhen(iso) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return iso;
  }
}

export default function App() {
  const [welcomed, setWelcomed] = useState(() => {
    try {
      return sessionStorage.getItem("pricecheck_welcome") === "1";
    } catch {
      return false;
    }
  });

  const [allCommodities, setAllCommodities] = useState([]);
  const [commodity, setCommodity] = useState("tomato");
  const [selectedName, setSelectedName] = useState("Tomatoes");
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const [prices, setPrices] = useState([]);
  const [gmb, setGmb] = useState([]);
  const [loading, setLoading] = useState(false);
  const [scraping, setScraping] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const searchRef = useRef(null);
  const blurTimer = useRef(null);

  useEffect(() => {
    fetchCommodities()
      .then((data) => {
        if (data.commodities?.length) setAllCommodities(data.commodities);
      })
      .catch(() => {});
  }, [refreshKey]);

  useEffect(() => {
    if (!welcomed || !commodity) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    fetchPrices(commodity)
      .then((data) => {
        if (cancelled) return;
        setPrices(data.prices || []);
        setGmb(data.gmb_reference || []);
        if (data.display_name) setSelectedName(data.display_name);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err.message || "Could not load prices");
        setPrices([]);
        setGmb([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [commodity, welcomed, refreshKey]);

  // Live suggestions while typing
  useEffect(() => {
    if (!welcomed) return;
    const text = query.trim();
    if (text.length < 1) {
      setSuggestions(allCommodities.slice(0, 8));
      return;
    }
    let cancelled = false;
    const t = setTimeout(() => {
      fetchCommodities(text)
        .then((data) => {
          if (!cancelled) setSuggestions(data.commodities || []);
        })
        .catch(() => {
          if (!cancelled) {
            const needle = text.toLowerCase();
            setSuggestions(
              allCommodities.filter((c) =>
                `${c.id} ${c.name}`.toLowerCase().includes(needle)
              )
            );
          }
        });
    }, 150);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, welcomed, allCommodities]);

  const marketCount = useMemo(() => prices.length, [prices]);

  function enterApp(keepQuery = false) {
    try {
      sessionStorage.setItem("pricecheck_welcome", "1");
    } catch {
      /* ignore */
    }
    setWelcomed(true);
    if (!keepQuery && !query.trim()) setQuery(selectedName);
  }

  async function onWelcomeSearch(e) {
    e.preventDefault();
    const text = query.trim();
    enterApp(Boolean(text));
    if (text) await onSearchSubmit(e);
  }

  function pickProduct(item) {
    setCommodity(item.id);
    setSelectedName(item.name);
    setQuery(item.name);
    setShowSuggest(false);
    setStatus("");
  }

  async function onSearchSubmit(e) {
    e?.preventDefault?.();
    const text = query.trim();
    if (!text) return;
    setShowSuggest(false);
    setLoading(true);
    setError("");
    try {
      const data = await searchPrices(text);
      if (data.commodity && data.prices?.length) {
        setCommodity(data.commodity);
        setSelectedName(data.display_name || data.commodity);
        setPrices(data.prices);
        setGmb(data.gmb_reference || []);
        setQuery(data.display_name || text);
      } else if (data.suggestions?.length) {
        setSuggestions(data.suggestions);
        setShowSuggest(true);
        setError(`No exact match for “${text}”. Pick a product below.`);
        setPrices([]);
        setGmb([]);
      } else {
        setError(`No prices found for “${text}”. Try another product name.`);
        setPrices([]);
        setGmb([]);
      }
    } catch (err) {
      setError(err.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }

  async function onRefresh() {
    setScraping(true);
    setError("");
    setStatus("");
    try {
      const result = await triggerScrape();
      const n = result.products ? `${result.products} products` : "prices";
      setStatus(`Updated — ${n} ready to search.`);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err.message || "Update failed");
    } finally {
      setScraping(false);
    }
  }

  if (!welcomed) {
    return (
      <div className="shell welcome">
        <div className="welcome-stack">
          <div className="welcome-panel">
            <p className="eyebrow">Zimbabwe markets</p>
            <h1>PriceCheck</h1>
            <p className="lead">
              Search any crop and compare prices across Mbare, Sakubva, Chipadze,
              and Renkini — so middlemen cannot exploit you.
            </p>
            <form className="search-form" onSubmit={onWelcomeSearch}>
              <label htmlFor="welcome-search">Search a crop</label>
              <div className="search-row">
                <input
                  id="welcome-search"
                  type="search"
                  autoComplete="off"
                  placeholder="e.g. tomato, maize, onion, cabbage…"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <button type="submit" className="primary search-btn">
                  Search
                </button>
              </div>
            </form>
            <button type="button" className="text-link" onClick={() => enterApp()}>
              Browse prices
            </button>
            <p className="fineprint">No account needed.</p>
          </div>
          <p className="credit">developed by Malvin Jakarasi</p>
        </div>
      </div>
    );
  }

  return (
    <div className="shell">
      <header className="top">
        <div>
          <p className="eyebrow">Zimbabwe · AMA market flash</p>
          <h1>PriceCheck</h1>
          <p className="sub">
            Type a product name, then compare min and max prices by market.
          </p>
        </div>
        <button
          type="button"
          className="secondary"
          onClick={onRefresh}
          disabled={scraping}
        >
          {scraping ? "Updating…" : "Update prices"}
        </button>
      </header>

      <section className="search-block" aria-label="Search products">
        <form className="search-form" onSubmit={onSearchSubmit}>
          <label htmlFor="product-search">Search a crop</label>
          <div className="search-row">
            <input
              ref={searchRef}
              id="product-search"
              type="search"
              autoComplete="off"
              placeholder="e.g. tomato, maize, onion, cabbage…"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setShowSuggest(true);
              }}
              onFocus={() => {
                clearTimeout(blurTimer.current);
                setShowSuggest(true);
              }}
              onBlur={() => {
                blurTimer.current = setTimeout(() => setShowSuggest(false), 180);
              }}
            />
            <button type="submit" className="primary search-btn">
              Search
            </button>
          </div>
          {showSuggest && suggestions.length > 0 && (
            <ul className="suggest" role="listbox">
              {suggestions.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onMouseDown={(e) => e.preventDefault()}
                    onClick={() => pickProduct(item)}
                  >
                    {item.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </form>

        <div className="chips" aria-label="Popular products">
          {QUICK_PICKS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={
                commodity === item.id ? "chip active" : "chip"
              }
              onClick={() => pickProduct(item)}
            >
              {item.name}
            </button>
          ))}
        </div>
      </section>

      {error && <p className="banner error">{error}</p>}
      {status && !error && <p className="banner info">{status}</p>}

      <section className="panel" aria-live="polite">
        <div className="panel-head">
          <h2>{selectedName || "Market prices"}</h2>
          {!loading && marketCount > 0 && (
            <span className="badge">{marketCount} markets</span>
          )}
        </div>

        {loading ? (
          <p className="muted">Loading…</p>
        ) : prices.length === 0 ? (
          <p className="muted">
            No market rows for this product yet. Try another name or Update
            prices.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Market</th>
                  <th>Min</th>
                  <th>Max</th>
                  <th>Unit</th>
                  <th>Last updated</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((row) => (
                  <tr key={`${row.commodity}-${row.market}-${row.unit}`}>
                    <td data-label="Market">{row.market}</td>
                    <td data-label="Min" className="num">
                      {formatPrice(row.min_price)}
                    </td>
                    <td data-label="Max" className="num">
                      {formatPrice(row.max_price)}
                    </td>
                    <td data-label="Unit">{row.unit}</td>
                    <td data-label="Updated">{formatWhen(row.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {gmb.length > 0 && (
        <section className="panel gmb" aria-label="GMB reference prices">
          <h2>Also: GMB producer reference</h2>
          <p className="muted">
            Extra Grain Marketing Board producer price for this crop — not a
            market quote. Compare with the market table above.
          </p>
          <ul className="gmb-list">
            {gmb.map((row) => (
              <li key={row.commodity}>
                <span className="gmb-label">{row.label}</span>
                <span className="gmb-price">
                  {formatPrice(row.price)} {row.unit}
                </span>
                <span className="as-of">as of {row.as_of}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      <footer>
        <p>
          Market figures from AMA flash prices. Class project only — not trading
          advice.
        </p>
        <p className="credit">developed by Malvin Jakarasi</p>
      </footer>
    </div>
  );
}
