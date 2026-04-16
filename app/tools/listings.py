"""Listing data: synthetic mode (default) or live scraping."""
import os
import random
import math

LISTING_MODE = os.getenv("LISTING_MODE", "synthetic")

SYNTHETIC_PRIORS = {
    (1, "apartment"): {"count_range": (25, 60), "price_spread": 0.15},
    (1, "villa"):     {"count_range": (5, 15),  "price_spread": 0.25},
    (1, "plot"):      {"count_range": (3, 10),  "price_spread": 0.30},
    (1, "shop"):      {"count_range": (10, 30), "price_spread": 0.20},
    (1, "warehouse"): {"count_range": (2, 8),   "price_spread": 0.25},
    (1, "office"):    {"count_range": (8, 25),  "price_spread": 0.20},
    (2, "apartment"): {"count_range": (15, 40), "price_spread": 0.18},
    (2, "villa"):     {"count_range": (3, 10),  "price_spread": 0.28},
    (2, "plot"):      {"count_range": (5, 15),  "price_spread": 0.30},
    (2, "shop"):      {"count_range": (5, 20),  "price_spread": 0.22},
    (2, "warehouse"): {"count_range": (2, 6),   "price_spread": 0.28},
    (2, "office"):    {"count_range": (5, 15),  "price_spread": 0.22},
    (3, "apartment"): {"count_range": (5, 20),  "price_spread": 0.22},
    (3, "villa"):     {"count_range": (2, 8),   "price_spread": 0.32},
    (3, "plot"):      {"count_range": (3, 12),  "price_spread": 0.35},
    (3, "shop"):      {"count_range": (3, 12),  "price_spread": 0.25},
    (3, "warehouse"): {"count_range": (1, 4),   "price_spread": 0.30},
    (3, "office"):    {"count_range": (2, 8),   "price_spread": 0.25},
}


def get_synthetic_listings(city_tier: int, sub_type: str, base_value: float,
                           area_sqft: float, seed: int = 42) -> dict:
    """Return synthetic listing data for a locality."""
    random.seed(seed)
    key = (city_tier, sub_type)
    prior = SYNTHETIC_PRIORS.get(key, {"count_range": (5, 20), "price_spread": 0.25})

    count = random.randint(*prior["count_range"])
    spread = prior["price_spread"]

    price_per_sqft = base_value / max(area_sqft, 1)
    comparable_prices = []
    for _ in range(min(count, 10)):
        noise = random.gauss(0, spread * 0.5)
        adj_area = area_sqft * random.uniform(0.8, 1.2)
        comp_price = price_per_sqft * (1 + noise) * adj_area
        comparable_prices.append(round(comp_price))

    median_price = sorted(comparable_prices)[len(comparable_prices) // 2] if comparable_prices else base_value

    return {
        "active_listings_1km": count,
        "comparable_prices": comparable_prices,
        "median_comparable_price": median_price,
        "price_momentum": "stable",
        "source": "synthetic",
    }


async def get_listings(city_tier: int, sub_type: str, base_value: float,
                       area_sqft: float, locality: str = "") -> dict:
    return get_synthetic_listings(city_tier, sub_type, base_value, area_sqft)
