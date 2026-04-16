"""OSM Overpass API client for POI queries. Results cached by (lat, lon, query_type)."""
import os
import math
import httpx

OVERPASS_URL = os.getenv("OVERPASS_URL", "https://overpass-api.de/api/interpreter")

_cache: dict[str, list] = {}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


QUERIES = {
    "metro": '''[out:json];(node["railway"="station"](around:{radius},{lat},{lon});node["station"="subway"](around:{radius},{lat},{lon}););out body;''',
    "highway": '''[out:json];(way["highway"="trunk"](around:{radius},{lat},{lon});way["highway"="motorway"](around:{radius},{lat},{lon});way["highway"="primary"](around:{radius},{lat},{lon}););out body;''',
    "school": '''[out:json];(node["amenity"="school"](around:{radius},{lat},{lon});way["amenity"="school"](around:{radius},{lat},{lon}););out body;''',
    "hospital": '''[out:json];(node["amenity"="hospital"](around:{radius},{lat},{lon});way["amenity"="hospital"](around:{radius},{lat},{lon}););out body;''',
    "commercial": '''[out:json];(node["shop"="mall"](around:{radius},{lat},{lon});node["shop"="supermarket"](around:{radius},{lat},{lon});way["shop"="mall"](around:{radius},{lat},{lon});node["amenity"="marketplace"](around:{radius},{lat},{lon}););out body;''',
    "it_park": '''[out:json];(node["office"="it"](around:{radius},{lat},{lon});way["office"="it"](around:{radius},{lat},{lon});node["landuse"="commercial"](around:{radius},{lat},{lon});way["office"](around:{radius},{lat},{lon}););out body;''',
}

POI_COUNT_QUERY = '''[out:json];(
  node["building"="residential"](around:500,{lat},{lon});
  node["building"="apartments"](around:500,{lat},{lon});
  node["building"="house"](around:500,{lat},{lon});
  node["building"="commercial"](around:500,{lat},{lon});
  node["shop"](around:500,{lat},{lon});
  node["office"](around:500,{lat},{lon});
  node["building"="industrial"](around:500,{lat},{lon});
  node["landuse"="industrial"](around:500,{lat},{lon});
);out body;'''


async def query_nearest_poi(lat: float, lon: float, poi_type: str, radius_m: int = 3000) -> dict:
    cache_key = f"{lat:.4f},{lon:.4f},{poi_type},{radius_m}"
    if cache_key in _cache:
        return _cache[cache_key]

    query_template = QUERIES.get(poi_type)
    if not query_template:
        return {"distance_km": radius_m / 1000, "found": False}

    query = query_template.format(lat=lat, lon=lon, radius=radius_m)

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])

            if not elements:
                result = {"distance_km": radius_m / 1000, "found": False}
                _cache[cache_key] = result
                return result

            min_dist = float("inf")
            for el in elements:
                el_lat = el.get("lat")
                el_lon = el.get("lon")
                if el_lat and el_lon:
                    d = haversine(lat, lon, el_lat, el_lon)
                    min_dist = min(min_dist, d)
                elif "center" in el:
                    d = haversine(lat, lon, el["center"]["lat"], el["center"]["lon"])
                    min_dist = min(min_dist, d)

            if min_dist == float("inf"):
                min_dist = radius_m / 1000

            result = {"distance_km": round(min_dist, 3), "found": True, "count": len(elements)}
            _cache[cache_key] = result
            return result
    except Exception:
        return {"distance_km": radius_m / 1000, "found": False, "error": "overpass_query_failed"}


async def query_poi_counts(lat: float, lon: float) -> dict:
    """Count residential/commercial/industrial POIs in 500m radius."""
    cache_key = f"counts_{lat:.4f},{lon:.4f}"
    if cache_key in _cache:
        return _cache[cache_key]

    query = POI_COUNT_QUERY.format(lat=lat, lon=lon)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            data = resp.json()
            elements = data.get("elements", [])

            n_r, n_c, n_i = 0, 0, 0
            for el in elements:
                tags = el.get("tags", {})
                building = tags.get("building", "")
                if building in ("residential", "apartments", "house"):
                    n_r += 1
                elif building in ("commercial",) or "shop" in tags or "office" in tags:
                    n_c += 1
                elif building == "industrial" or tags.get("landuse") == "industrial":
                    n_i += 1

            result = {"n_residential": max(n_r, 1), "n_commercial": max(n_c, 1), "n_industrial": n_i}
            _cache[cache_key] = result
            return result
    except Exception:
        return {"n_residential": 10, "n_commercial": 5, "n_industrial": 1, "error": "poi_count_failed"}
