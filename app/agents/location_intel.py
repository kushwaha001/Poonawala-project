"""
LocationIntelAgent — UPGRADED with LLM-powered micro-market analysis.
Combines deterministic OSM data with intelligent market reasoning.
The math stays rule-based; the LLM enhances data interpretation.
"""
import asyncio
from functools import lru_cache
from app.agents.base import BaseAgent
from app.tools.circle_rate import lookup as cr_lookup
from app.tools.overpass import query_nearest_poi, query_poi_counts
from app.tools.llm import analyze_micro_market, estimate_dynamic_mcr
from app.math.formulas import compute_s_infra, compute_s_nbhd, compute_mcr, compute_f_loc, get_micro_bucket
from app.config.constants import POI_CONFIG, MCR_TABLE
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


@lru_cache(maxsize=256)
def _load_city_tier(city: str) -> int:
    try:
        df = pd.read_csv(DATA_DIR / "city_tiers.csv")
        match = df[df["city"].str.lower() == city.strip().lower()]
        if not match.empty:
            return int(match.iloc[0]["tier"])
    except Exception:
        pass
    return 3


def _extract_city_from_address(address: str) -> str:
    known_cities = ["mumbai", "delhi", "bangalore", "bengaluru", "pune", "chennai",
                    "hyderabad", "kolkata", "jaipur", "lucknow", "nagpur", "indore",
                    "kochi", "coimbatore", "chandigarh", "gorakhpur", "varanasi"]
    addr_lower = address.lower()
    for c in known_cities:
        if c in addr_lower:
            return c.title()
    return ""


def _extract_locality(address: str) -> str:
    parts = [p.strip() for p in address.split(",")]
    return parts[0] if parts else ""


def _extract_state_district(address: str, city: str) -> tuple[str, str]:
    city_state_map = {
        "mumbai": ("Maharashtra", "Mumbai"), "delhi": ("Delhi", "Delhi"),
        "bangalore": ("Karnataka", "Bangalore"), "bengaluru": ("Karnataka", "Bangalore"),
        "pune": ("Maharashtra", "Pune"), "nagpur": ("Maharashtra", "Nagpur"),
        "jaipur": ("Rajasthan", "Jaipur"), "lucknow": ("Uttar Pradesh", "Lucknow"),
        "gorakhpur": ("Uttar Pradesh", "Gorakhpur"), "chennai": ("Tamil Nadu", "Chennai"),
        "hyderabad": ("Telangana", "Hyderabad"), "kolkata": ("West Bengal", "Kolkata"),
    }
    return city_state_map.get(city.lower(), ("", city))


class LocationIntelAgent(BaseAgent):
    name = "location_intel"

    async def run(self, ctx: dict) -> dict:
        norm = ctx["input_normalizer"]
        inp = ctx["input"]
        lat, lon = norm["lat"], norm["lon"]
        address = norm["address"]

        city = _extract_city_from_address(address)
        locality = _extract_locality(address)
        state, district = _extract_state_district(address, city)
        city_tier = _load_city_tier(city)

        cr_result = cr_lookup(state, district, locality)
        circle_rate = cr_result["rate_per_sqft"]

        poi_distances = {}
        poi_breakdown = {}
        poi_counts = {"n_residential": 10, "n_commercial": 5, "n_industrial": 1}
        if lat and lon:
            # Fire all 5 POI distance queries + the counts query concurrently (was sequential)
            poi_tasks = [
                query_nearest_poi(lat, lon, cat, int(cfg["search_radius"] * 1000))
                for cat, cfg in POI_CONFIG.items()
            ]
            poi_results, poi_counts = await asyncio.gather(
                asyncio.gather(*poi_tasks),
                query_poi_counts(lat, lon),
            )
            for (cat, _), poi in zip(POI_CONFIG.items(), poi_results):
                dist = poi["distance_km"]
                poi_distances[cat] = dist
                poi_breakdown[f"{cat}_dist_km"] = round(dist, 2)
                poi_breakdown[f"{cat}_found"] = poi.get("found", False)

        s_infra = compute_s_infra(poi_distances)
        s_nbhd = compute_s_nbhd(poi_counts["n_residential"], poi_counts["n_commercial"], poi_counts["n_industrial"])

        # Rule-based MCR as baseline
        rule_mcr = compute_mcr(city_tier, s_infra)
        bucket = get_micro_bucket(s_infra)

        # Fire both LLM calls concurrently (was sequential — second waited for first)
        llm_mcr_result, micro_market = await asyncio.gather(
            estimate_dynamic_mcr(city, locality, city_tier, s_infra, inp["sub_type"], rule_mcr, circle_rate),
            analyze_micro_market(city, locality, inp["property_type"], inp["sub_type"],
                                 city_tier, poi_breakdown, inp["built_up_area_sqft"]),
        )

        llm_mcr = llm_mcr_result.get("estimated_mcr")
        llm_mcr_confidence = llm_mcr_result.get("confidence", 0.0)

        if llm_mcr and isinstance(llm_mcr, (int, float)) and 1.0 <= llm_mcr <= 3.0 and llm_mcr_confidence > 0.4:
            tier_bounds = MCR_TABLE.get(city_tier, MCR_TABLE[3])
            mcr_floor = tier_bounds["peripheral"] * 0.9
            mcr_ceil = tier_bounds["prime"] * 1.15
            llm_mcr_clamped = max(mcr_floor, min(mcr_ceil, llm_mcr))
            blend_weight = min(llm_mcr_confidence, 0.6)
            mcr = round(rule_mcr * (1 - blend_weight) + llm_mcr_clamped * blend_weight, 3)
            mcr_source = "blended_rule_llm"
        else:
            mcr = rule_mcr
            mcr_source = "rule_based"

        mcr = max(1.05, min(2.20, mcr))
        f_loc = compute_f_loc(s_infra, s_nbhd)

        return {
            "circle_rate_per_sqft": circle_rate,
            "circle_rate_match": cr_result.get("match_type", "unknown"),
            "infra_score": round(s_infra, 4),
            "neighborhood_quality": round(s_nbhd, 4),
            "city_tier": city_tier,
            "city": city,
            "locality": locality,
            "state": state,
            "district": district,
            "mcr": mcr,
            "mcr_source": mcr_source,
            "rule_based_mcr": rule_mcr,
            "llm_mcr": llm_mcr_result,
            "micro_bucket": bucket,
            "f_loc": round(f_loc, 4),
            "poi_breakdown": poi_breakdown,
            "poi_counts": poi_counts,
            "micro_market_intelligence": micro_market,
        }
