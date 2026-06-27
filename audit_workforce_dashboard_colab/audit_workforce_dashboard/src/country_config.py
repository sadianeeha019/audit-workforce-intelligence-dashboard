from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class CountryMarketConfig:
    """Country/currency settings used for fair transaction comparison.

    bdt_per_currency means: how many BDT equal 1 unit of the selected currency.
    These demo rates are editable placeholders. In production, connect a live FX API.
    """

    country_name: str
    currency_code: str
    currency_symbol: str
    bdt_per_currency: float
    local_market_multiplier: float = 1.0
    additional_landed_cost_pct: float = 0.0


COUNTRY_MARKETS: Dict[str, CountryMarketConfig] = {
    "Bangladesh": CountryMarketConfig("Bangladesh", "BDT", "৳", 1.0, 1.00, 0.0),
    "India": CountryMarketConfig("India", "INR", "₹", 1.40, 0.95, 2.0),
    "United States": CountryMarketConfig("United States", "USD", "$", 118.0, 1.08, 3.0),
    "United Kingdom": CountryMarketConfig("United Kingdom", "GBP", "£", 150.0, 1.15, 4.0),
    "United Arab Emirates": CountryMarketConfig("United Arab Emirates", "AED", "د.إ", 32.0, 1.04, 2.0),
    "Singapore": CountryMarketConfig("Singapore", "SGD", "S$", 88.0, 1.10, 3.0),
}


def get_country_market(country_name: str) -> CountryMarketConfig:
    return COUNTRY_MARKETS.get(country_name, COUNTRY_MARKETS["Bangladesh"])
