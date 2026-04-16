"""Geocoding via Nominatim (OSM). Cached to avoid rate limits."""
import os
import httpx
import asyncio
from functools import lru_cache

USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "collateral-engine-dev")
BASE_URL = "https://nominatim.openstreetmap.org"

_cache: dict[str, dict] = {}


async def geocode(address: str) -> dict:
    """Convert address string to lat/lon."""
    cache_key = address.strip().lower()
    if cache_key in _cache:
        return _cache[cache_key]
    
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/search",
                params={"q": address, "format": "json", "limit": 1, "countrycodes": "in"},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            results = resp.json()
            if results:
                result = {
                    "lat": float(results[0]["lat"]),
                    "lon": float(results[0]["lon"]),
                    "display_name": results[0].get("display_name", address),
                }
                _cache[cache_key] = result
                return result
        except Exception:
            pass
    
    return {"lat": None, "lon": None, "display_name": address, "error": "geocoding_failed"}


async def reverse_geocode(lat: float, lon: float) -> dict:
    """Convert lat/lon to address."""
    cache_key = f"{lat:.6f},{lon:.6f}"
    if cache_key in _cache:
        return _cache[cache_key]
    
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            resp = await client.get(
                f"{BASE_URL}/reverse",
                params={"lat": lat, "lon": lon, "format": "json"},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            data = resp.json()
            addr = data.get("address", {})
            result = {
                "address": data.get("display_name", ""),
                "city": addr.get("city", addr.get("town", addr.get("village", ""))),
                "state": addr.get("state", ""),
                "district": addr.get("county", addr.get("state_district", "")),
                "locality": addr.get("suburb", addr.get("neighbourhood", "")),
            }
            _cache[cache_key] = result
            return result
        except Exception:
            pass
    
    return {"address": "", "city": "", "state": "", "district": "", "locality": "", "error": "reverse_geocode_failed"}
