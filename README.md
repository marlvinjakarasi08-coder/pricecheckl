# PriceCheck — Zimbabwe farmers market prices (class mock)

Simple single-user demo so farmers can **check and compare** current market prices for **maize, tomatoes, potatoes, and soya beans**. Goal: reduce middleman information advantage.

**Not production software.** No real auth, no multi-user accounts, local run only.

## Stack

| Layer    | Tech                                      |
|----------|-------------------------------------------|
| Backend  | Python 3.10+, FastAPI, SQLite             |
| Scraping | `requests` + BeautifulSoup (AMA flash page) |
| Frontend | React 18 + Vite                           |

## Project layout

```
pricecheck/
├── README.md
├── backend/
│   ├── requirements.txt
│   ├── pricecheck.db          # created on first run
│   └── app/
│       ├── main.py            # FastAPI app + CORS
│       ├── database.py        # SQLite helpers
│       ├── scraper.py         # AMA scrape + sample fallback
│       ├── sample_data.py     # offline demo prices
│       └── gmb_prices.py      # GMB producer price references
└── frontend/
    ├── package.json
    ├── vite.config.js         # proxies /api → :8000
    └── src/
        ├── App.jsx
        └── api.js
```

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/commodities?q=onion` | List / search products from the latest scrape |
| `GET`  | `/prices?commodity=tomato` | Market rows for a product id/name |
| `GET`  | `/prices?q=cabbage` | Same via free-text search; GMB refs attached for maize/soya |
| `POST` | `/scrape` | Manual scrape; falls back to sample data on failure |
| `GET`  | `/health` | Smoke check |

## Scrape notes (honest)

- Primary source: [AMA market commodity flash page](https://ama.co.zw/market-commodity-price-28-09-2021-3/) (WordPress slug is old; body is updated in place).
- Prices are **paragraph text**, not a stable HTML table. Spacing, missing values (`Min $-`), and which markets appear (Chipadze often absent) change often.
- Horticulture flashes usually include **tomato / potato**; **maize / soya** are filled from sample data when missing.
- **GMB producer prices** for maize and soya are **hardcoded references** — labeled clearly in the UI; not live scrapes.
- Currency labeling follows the source (typically `USD$/kg`). ZWL may appear if AMA lists it.

If the scrape fails for any reason, the API still returns **sample/cached** rows so the class demo works offline.

## Setup & run

### 1. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs

### 2. Frontend (new terminal)

```bash
cd frontend
# If an empty leftover node_modules/ folder exists, remove it first:
#   rm -rf node_modules
npm install
npm run dev
```

Open http://127.0.0.1:5173 — Vite proxies `/api` to the backend.

### Quick checks

```bash
curl http://127.0.0.1:8000/commodities
curl "http://127.0.0.1:8000/prices?commodity=tomato"
curl -X POST http://127.0.0.1:8000/scrape
```

## UI

1. Optional welcome screen (session-only; no login).
2. **Type or search** any product (suggestions + quick chips).
3. Table: market, min, max, unit, last updated (all AMA products when scraped).
4. GMB producer reference shown as an *extra* for maize / soya only.
5. **Update prices** calls `POST /scrape`.

## License / context

Built as a **class mock** for educational use. Do not treat prices as trading advice. Respect AMA / GMB terms when scraping or citing data.
