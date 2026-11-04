"""
Fallback / cached sample prices used when the AMA scrape fails or a
commodity is missing (e.g. maize, soya rarely appear on horticulture flash).

DEMO-ONLY numbers so the class mock still works offline.
"""

from datetime import datetime, timezone

SAMPLE_UPDATED_AT = "2025-11-08T08:00:00+00:00"

MARKETS = ("Mbare", "Sakubva", "Chipadze", "Renkini")


def _rows(commodity: str, display_name: str, unit: str, prices: dict) -> list[dict]:
    """Build four market rows from {market: (min, max)}."""
    out = []
    for market, (lo, hi) in prices.items():
        out.append(
            {
                "commodity": commodity,
                "display_name": display_name,
                "market": market,
                "min_price": lo,
                "max_price": hi,
                "unit": unit,
                "currency": "USD" if "USD" in unit.upper() else "ZWL",
                "source": "sample",
                "updated_at": SAMPLE_UPDATED_AT,
            }
        )
    return out


# Core crops + common AMA horticulture items for offline demo / gap fill.
SAMPLE_PRICES: list[dict] = []
SAMPLE_PRICES += _rows(
    "tomato",
    "Tomatoes",
    "USD$/kg",
    {
        "Mbare": (0.63, 0.80),
        "Sakubva": (None, 0.50),
        "Chipadze": (0.55, 0.75),
        "Renkini": (0.90, 1.10),
    },
)
SAMPLE_PRICES += _rows(
    "potato",
    "Potatoes",
    "USD$/kg",
    {
        "Mbare": (0.45, 0.55),
        "Sakubva": (0.95, 1.20),
        "Chipadze": (0.50, 0.70),
        "Renkini": (0.50, 0.60),
    },
)
SAMPLE_PRICES += _rows(
    "maize",
    "Maize",
    "USD$/20kg",
    {
        "Mbare": (6.50, 8.00),
        "Sakubva": (6.00, 7.50),
        "Chipadze": (5.80, 7.20),
        "Renkini": (6.20, 7.80),
    },
)
SAMPLE_PRICES += _rows(
    "soya",
    "Soya Beans",
    "USD$/20kg",
    {
        "Mbare": (12.00, 14.50),
        "Sakubva": (11.50, 13.80),
        "Chipadze": (11.00, 13.50),
        "Renkini": (11.80, 14.00),
    },
)
SAMPLE_PRICES += _rows(
    "onion-dried",
    "Onions (dried)",
    "USD$/kg",
    {
        "Mbare": (0.40, 0.90),
        "Sakubva": (None, 0.85),
        "Chipadze": (0.55, 0.80),
        "Renkini": (0.80, 1.00),
    },
)
SAMPLE_PRICES += _rows(
    "cabbage-white",
    "Cabbages (white)",
    "USD$/head",
    {
        "Mbare": (0.50, 0.50),
        "Sakubva": (0.40, 0.75),
        "Chipadze": (0.45, 0.70),
        "Renkini": (0.50, 1.00),
    },
)
SAMPLE_PRICES += _rows(
    "carrot",
    "Carrots",
    "USD$/Bunch",
    {
        "Mbare": (None, 0.70),
        "Sakubva": (0.50, 0.75),
        "Chipadze": (0.40, 0.65),
        "Renkini": (None, 1.00),
    },
)
SAMPLE_PRICES += _rows(
    "covo",
    "Covo",
    "USD$/Large Bundle",
    {
        "Mbare": (3.00, 4.00),
        "Sakubva": (None, 1.40),
        "Chipadze": (2.00, 2.80),
        "Renkini": (2.50, 3.00),
    },
)
SAMPLE_PRICES += _rows(
    "sweet-potato",
    "Sweet Potatoes",
    "USD$/kg",
    {
        "Mbare": (0.55, 0.70),
        "Sakubva": (None, 0.45),
        "Chipadze": (0.40, 0.60),
        "Renkini": (None, 0.85),
    },
)


def utc_now_iso() -> str:
    """Return current UTC time in ISO-8601 form."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
