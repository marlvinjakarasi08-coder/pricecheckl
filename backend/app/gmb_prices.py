"""
Grain Marketing Board (GMB) producer price references.

Hardcoded for this class mock — GMB publishes seasonal producer prices for
maize and soya beans separately from AMA retail/wholesale market flashes.
Label these clearly in the UI as "GMB reference", not live market quotes.

Values are illustrative demo figures in USD per metric tonne (typical GMB
unit). Update by hand when your class has a newer official bulletin.
"""

# Latest-known demo GMB producer prices (USD / MT).
GMB_PRODUCER_PRICES = [
    {
        "commodity": "maize",
        "label": "GMB producer price (maize)",
        "price": 390.0,
        "unit": "USD/MT",
        "currency": "USD",
        "source": "gmb_reference",
        "note": "Hardcoded GMB reference for class demo — not a live scrape.",
        "as_of": "2025-04-01",
    },
    {
        "commodity": "soya",
        "label": "GMB producer price (soya beans)",
        "price": 580.0,
        "unit": "USD/MT",
        "currency": "USD",
        "source": "gmb_reference",
        "note": "Hardcoded GMB reference for class demo — not a live scrape.",
        "as_of": "2025-04-01",
    },
]


def get_gmb_prices(commodity: str | None = None) -> list[dict]:
    """Return GMB reference rows, optionally filtered by commodity key."""
    if not commodity:
        return list(GMB_PRODUCER_PRICES)
    key = commodity.strip().lower()
    # Accept friendly aliases from the frontend dropdown
    aliases = {
        "maize": "maize",
        "soya": "soya",
        "soya beans": "soya",
        "soyabeans": "soya",
        "soybean": "soya",
        "soybeans": "soya",
    }
    normalized = aliases.get(key, key)
    return [row for row in GMB_PRODUCER_PRICES if row["commodity"] == normalized]
