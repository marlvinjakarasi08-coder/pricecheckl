"""
PriceCheck FastAPI app — Zimbabwe farmers market price transparency (class mock).

Endpoints:
  GET  /commodities?q=...   — list / search products in the DB
  GET  /prices?commodity=... — market min/max (+ GMB ref when maize/soya)
  GET  /prices?q=...         — same via free-text search
  POST /scrape               — manual scrape (falls back to sample data)
  GET  /health
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import database as db
from .gmb_prices import get_gmb_prices
from .sample_data import SAMPLE_PRICES
from .scraper import scrape_prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pricecheck")


def _ensure_seed_data() -> None:
    """Always seed demo rows first so the UI works even if AMA/SQLite scrape fails."""
    if db.count_prices() > 0:
        return
    logger.info("Empty DB — loading demo prices, then trying AMA")
    db.clear_and_insert_prices(SAMPLE_PRICES)
    try:
        result = scrape_prices()
        if result.get("rows"):
            n = db.clear_and_insert_prices(result["rows"])
            logger.info("Seeded %s rows (%s)", n, result["source"])
    except Exception:
        logger.exception("AMA scrape skipped; demo prices remain")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        db.init_db()
        _ensure_seed_data()
    except Exception:
        logger.exception("Startup init failed; API will still start")
    yield


app = FastAPI(
    title="PriceCheck",
    description="Class-mock farmers market price transparency for Zimbabwe",
    version="0.2.0",
    lifespan=lifespan,
)

@app.exception_handler(Exception)
async def unhandled_error(_request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://0.0.0.0:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _sample_commodities(q: Optional[str] = None) -> list[dict[str, str]]:
    seen: dict[str, str] = {}
    for row in SAMPLE_PRICES:
        seen[row["commodity"]] = row.get("display_name") or row["commodity"]
    items = [{"id": cid, "name": name} for cid, name in seen.items()]
    items.sort(key=lambda item: item["name"].lower())
    if not q or not q.strip():
        return items
    needle = q.strip().lower()
    return [
        item
        for item in items
        if needle in item["id"].lower() or needle in item["name"].lower()
    ]


def _sample_price_rows(commodity: Optional[str], q: Optional[str]) -> list[dict]:
    key = (commodity or q or "").strip().lower()
    if not key:
        return list(SAMPLE_PRICES)
    return [
        row
        for row in SAMPLE_PRICES
        if key in row["commodity"].lower()
        or key in str(row.get("display_name") or "").lower()
    ]


@app.get("/health")
def health():
    try:
        return {
            "status": "ok",
            "rows": db.count_prices(),
            "products": len(db.list_commodities()),
        }
    except Exception:
        logger.exception("Health check used sample data")
        items = _sample_commodities()
        return {"status": "ok", "rows": len(SAMPLE_PRICES), "products": len(items)}


@app.get("/commodities")
def list_commodities(
    q: Optional[str] = Query(None, description="Type-ahead search text"),
):
    """Return products available in the latest scrape (filterable by search)."""
    try:
        _ensure_seed_data()
        items = db.list_commodities(q)
        if items:
            return {"commodities": items, "count": len(items)}
    except Exception:
        logger.exception("Commodity list failed; using sample products")
    items = _sample_commodities(q)
    return {"commodities": items, "count": len(items)}


@app.get("/prices")
def list_prices(
    commodity: Optional[str] = Query(
        None,
        description="Product id or name (tomato, maize, onion, …)",
    ),
    q: Optional[str] = Query(
        None,
        description="Free-text product search (same as typing in the UI)",
    ),
):
    """
    Market prices for one product (or search). Always returns market rows when
    found; GMB producer references are attached only for maize / soya as extras.
    """
    query = commodity or q
    try:
        _ensure_seed_data()
        prices = db.get_prices(commodity=commodity, q=q)
        resolved = db.resolve_commodity(query) if query else None
    except Exception:
        logger.exception("Price list failed; using sample prices")
        prices = _sample_price_rows(commodity, q)
        resolved = prices[0]["commodity"] if prices else None

    gmb = []
    if resolved in {"maize", "soya"}:
        gmb = get_gmb_prices(resolved)
    elif not query:
        # Listing everything — include both GMB refs as optional extras
        gmb = get_gmb_prices()

    display = None
    if prices:
        display = prices[0].get("display_name") or resolved

    suggestions: list[dict[str, str]] = []
    if query and not prices:
        try:
            suggestions = db.list_commodities(query)[:8]
        except Exception:
            logger.exception("Suggestions failed; using sample products")
            suggestions = _sample_commodities(query)[:8]

    return {
        "commodity": resolved,
        "display_name": display,
        "query": query,
        "count": len(prices),
        "prices": prices,
        "gmb_reference": gmb,
        "suggestions": suggestions,
    }


@app.post("/scrape")
def trigger_scrape():
    """Manual AMA scrape; falls back to sample data on failure."""
    result = scrape_prices()
    n = db.clear_and_insert_prices(result["rows"])
    return {
        "ok": result["ok"],
        "source": result["source"],
        "message": result["message"],
        "inserted": n,
        "products": len(db.list_commodities()),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
