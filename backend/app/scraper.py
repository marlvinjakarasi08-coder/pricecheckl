"""
AMA market-price scraper (class mock).

Primary source: https://ama.co.zw/market-commodity-price-28-09-2021-3/

Scrape fragility (for maintainers):
- AMA reuses an old WordPress slug; body is updated in place.
- Prices are plain <p> paragraphs, not a stable HTML table.
- Chipadze is often missing; maize/soya rarely appear on this flash page.
- On any failure we fall back to sample data so the demo still runs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

import requests
from bs4 import BeautifulSoup

from .sample_data import SAMPLE_PRICES, utc_now_iso

logger = logging.getLogger(__name__)

AMA_PRICE_URL = "https://ama.co.zw/market-commodity-price-28-09-2021-3/"

# Always ensure these exist even when AMA horticulture flash omits them.
ENSURE_COMMODITIES = {"maize", "soya", "tomato", "potato"}

MARKET_NAMES = ("Mbare", "Sakubva", "Chipadze", "Renkini")

# Known friendly ids when AMA heading text matches.
KNOWN_SLUGS = [
    (re.compile(r"^tomatoes?\b", re.I), "tomato", "Tomatoes"),
    (re.compile(r"^sweet\s+potatoes?\b", re.I), "sweet-potato", "Sweet Potatoes"),
    (re.compile(r"^potatoes?\b", re.I), "potato", "Potatoes"),
    (re.compile(r"^maize\b|^corn\b", re.I), "maize", "Maize"),
    (re.compile(r"^soya\b|^soy", re.I), "soya", "Soya Beans"),
    (re.compile(r"^cabbages?\b", re.I), "cabbage-white", "Cabbages (white)"),
    (re.compile(r"^carrots?\b", re.I), "carrot", "Carrots"),
    (re.compile(r"^covo\b", re.I), "covo", "Covo"),
    (re.compile(r"^onions?\s*\(dried\)|^onions?\(dried\)", re.I), "onion-dried", "Onions (dried)"),
    (re.compile(r"^fresh\s+onions?\b", re.I), "onion-fresh", "Fresh onions"),
    (re.compile(r"^okra\b", re.I), "okra", "Okra"),
    (re.compile(r"^watermelon\b", re.I), "watermelon", "Watermelon"),
    (re.compile(r"^broccoli\b", re.I), "broccoli", "Broccoli"),
    (re.compile(r"^butternut\b", re.I), "butternut", "Butternut"),
    (re.compile(r"^lettuce\b", re.I), "lettuce", "Lettuce"),
    (re.compile(r"^ginger\b", re.I), "ginger", "Ginger"),
    (re.compile(r"^garlic\b", re.I), "garlic", "Garlic"),
    (re.compile(r"^mopani\b", re.I), "mopani-worm", "Mopani worm"),
]

HEADING_RE = re.compile(
    r"^(?P<name>.+?)\s*\(?\s*(?P<unit>USD\$?/[^)\s]+|USD/[^)\s]+|ZWL[^)\s]*)",
    re.I,
)

MARKET_LINE_RE = re.compile(
    r"^(?P<market>Mbare|Sakubva|Chipadze|Renkini)\s+"
    r"(?:Min\s*\$?\s*(?P<min>[\d.]+|-|–)?)\s*"
    r"(?:Max\s*\$?\s*(?P<max>[\d.]+|-|–)?)",
    re.I,
)


def slugify(name: str) -> str:
    """Turn an AMA product heading into a URL-ish commodity id."""
    cleaned = name.lower().strip()
    cleaned = re.sub(r"\([^)]*\)", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned).strip("-")
    return cleaned or "unknown"


def resolve_commodity(heading_name: str) -> tuple[str, str]:
    """Return (commodity_id, display_name) for an AMA heading."""
    name = heading_name.strip()
    for pattern, cid, display in KNOWN_SLUGS:
        if pattern.search(name):
            return cid, display
    # Fallback: keep AMA wording as the display label
    return slugify(name), name


def _parse_money(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    token = raw.strip().replace(",", "")
    if not token or token in {"-", "–", "—"}:
        return None
    try:
        return float(token)
    except ValueError:
        return None


def _extract_as_of(text_blocks: list[str]) -> Optional[str]:
    for block in text_blocks:
        m = re.search(r"as at\s+(\d{2}-\d{2}-\d{4})", block, re.I)
        if m:
            return m.group(1)
    return None


def parse_ama_html(html: str) -> list[dict[str, Any]]:
    """Parse AMA flash-price HTML into price rows for EVERY listed product."""
    soup = BeautifulSoup(html, "lxml")
    content = soup.select_one(".entry-content") or soup.select_one("article") or soup
    texts = [
        p.get_text(" ", strip=True).replace("\xa0", " ")
        for p in content.find_all("p")
    ]
    texts = [re.sub(r"\s+", " ", t).strip() for t in texts if t and t.strip()]

    as_of = _extract_as_of(texts)
    updated_at = utc_now_iso()
    if as_of:
        logger.info("AMA flash date: %s", as_of)

    rows: list[dict[str, Any]] = []
    current_id: Optional[str] = None
    current_display: Optional[str] = None
    current_unit = "USD$/kg"

    for text in texts:
        heading = HEADING_RE.match(text)
        starts_market = text.lower().startswith(tuple(m.lower() for m in MARKET_NAMES))
        if heading and not starts_market:
            name = heading.group("name").strip()
            unit = heading.group("unit").strip().rstrip(")")
            current_id, current_display = resolve_commodity(name)
            current_unit = unit or "USD$/kg"
            continue

        market_match = MARKET_LINE_RE.match(text)
        if market_match and current_id:
            market = market_match.group("market").title()
            for known in MARKET_NAMES:
                if known.lower() == market.lower():
                    market = known
                    break
            rows.append(
                {
                    "commodity": current_id,
                    "display_name": current_display or current_id,
                    "market": market,
                    "min_price": _parse_money(market_match.group("min")),
                    "max_price": _parse_money(market_match.group("max")),
                    "unit": current_unit,
                    "currency": "USD" if "USD" in current_unit.upper() else "ZWL",
                    "source": "ama_scrape",
                    "updated_at": updated_at,
                }
            )

    return rows


def fetch_ama_prices(timeout: float = 15.0) -> list[dict[str, Any]]:
    """HTTP-fetch AMA page and parse it. Raises on network/HTTP failure."""
    headers = {
        "User-Agent": (
            "PriceCheckClassMock/1.0 (+educational; contact: student@example.com)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    resp = requests.get(AMA_PRICE_URL, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return parse_ama_html(resp.text)


def merge_with_sample(scraped: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Keep all scraped AMA products; fill sample gaps for maize/soya/etc.
    and missing markets (e.g. Chipadze).
    """
    if not scraped:
        return [dict(s) for s in SAMPLE_PRICES]

    present = {row["commodity"] for row in scraped}
    merged = list(scraped)

    for sample in SAMPLE_PRICES:
        cid = sample["commodity"]
        if cid not in present:
            if cid in ENSURE_COMMODITIES or cid not in present:
                merged.append(dict(sample))
        else:
            markets = {
                r["market"].lower()
                for r in scraped
                if r["commodity"] == cid
            }
            if sample["market"].lower() not in markets:
                # Only gap-fill Chipadze (and similar) for commodities we care to complete
                if cid in ENSURE_COMMODITIES or sample["market"] == "Chipadze":
                    merged.append(dict(sample))

    return merged


def scrape_prices() -> dict[str, Any]:
    """
    Run a scrape with graceful fallback.

    Returns: ok, source, message, rows
    """
    try:
        scraped = fetch_ama_prices()
        rows = merge_with_sample(scraped)
        if scraped:
            products = sorted({r["commodity"] for r in scraped})
            msg = (
                f"Updated {len(rows)} market rows "
                f"({len(products)} products from AMA, plus any sample fill)."
            )
            source = "ama_scrape"
        else:
            msg = "Could not parse AMA products; loaded demo prices."
            source = "sample_fallback"
            rows = [dict(s) for s in SAMPLE_PRICES]
        return {"ok": True, "source": source, "message": msg, "rows": rows}
    except Exception as exc:  # noqa: BLE001
        logger.exception("AMA scrape failed; using sample data")
        rows = [dict(s) for s in SAMPLE_PRICES]
        return {
            "ok": False,
            "source": "sample_fallback",
            "message": f"Could not reach AMA ({exc.__class__.__name__}); showing demo prices.",
            "rows": rows,
        }
