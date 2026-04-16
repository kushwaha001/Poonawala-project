"""Validates input and resolves geocoding."""
from app.agents.base import BaseAgent
from app.tools.geocode import geocode, reverse_geocode


class InputNormalizerAgent(BaseAgent):
    name = "input_normalizer"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        lat = inp.get("latitude")
        lon = inp.get("longitude")
        address = inp.get("address")
        missing_fields = []

        if address and (lat is None or lon is None):
            geo = await geocode(address)
            if geo.get("lat"):
                lat, lon = geo["lat"], geo["lon"]
            else:
                missing_fields.append("geocoding_failed")

        if lat is not None and lon is not None and not address:
            rev = await reverse_geocode(lat, lon)
            address = rev.get("address", "")
            ctx["_reverse_geo"] = rev

        optional = ["floor", "total_floors", "has_lift", "configuration",
                     "ownership", "title_clear", "occupancy", "monthly_rent",
                     "carpet_area_sqft", "land_parcel_sqft",
                     "exterior_image_url", "interior_image_url"]
        for field in optional:
            if inp.get(field) is None:
                missing_fields.append(field)

        return {
            "lat": lat,
            "lon": lon,
            "address": address or "",
            "missing_fields": missing_fields,
            "status": "ok" if lat and lon else "degraded",
        }
