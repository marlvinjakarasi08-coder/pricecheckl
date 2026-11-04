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

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from . import database as db
from .gmb_prices import get_gmb_prices
from .scraper import scrape_prices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pricecheck")


def _ensure_seed_data() -> None:
    if db.count_prices() == 0:
        logger.info("Empty DB — seeding via scrape/fallback")
        result = scrape_prices()
        n = db.clear_and_insert_prices(result["rows"])
        logger.info("Seeded %s rows (%s)", n, result["source"])


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    _ensure_seed_data()
    yield


app = FastAPI(
    title="PriceCheck",
    description="Class-mock farmers market price transparency for Zimbabwe",
    version="0.2.0",
    lifespan=lifespan,
)

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


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rows": db.count_prices(),
        "products": len(db.list_commodities()),
    }


@app.get("/commodities")
def list_commodities(
    q: Optional[str] = Query(None, description="Type-ahead search text"),
):
    """Return products available in the latest scrape (filterable by search)."""
    items = db.list_commodities(q)
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
    prices = db.get_prices(commodity=commodity, q=q)
    resolved = db.resolve_commodity(query) if query else None

    gmb = []
    if resolved in {"maize", "soya"}:
        gmb = get_gmb_prices(resolved)
    elif not query:
        # Listing everything — include both GMB refs as optional extras
        gmb = get_gmb_prices()

    display = None
    if prices:
        display = prices[0].get("display_name") or resolved

    return {
        "commodity": resolved,
        "display_name": display,
        "query": query,
        "count": len(prices),
        "prices": prices,
        "gmb_reference": gmb,
        "suggestions": db.list_commodities(query)[:8] if query and not prices else [],
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
