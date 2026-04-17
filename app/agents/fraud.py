"""
FraudAgent — UPGRADED with LLM-powered anomaly detection.
Combines rule-based checks (5 deterministic) with intelligent pattern detection.
"""
from app.agents.base import BaseAgent
from app.config.constants import MIN_CONFIG_AREAS, MCR_TABLE, BUILDER_REPUTATION, BUILDER_REPUTATION_PENALTY
from app.tools.llm import detect_anomalies
import math
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_locality_stats(city: str, locality: str, sub_type: str) -> dict | None:
    try:
        df = pd.read_csv(DATA_DIR / "locality_norms.csv")
        match = df[
            (df["city"].str.lower() == city.strip().lower()) &
            (df["locality"].str.lower() == locality.strip().lower()) &
            (df["sub_type"].str.lower() == sub_type.strip().lower())
        ]
        if not match.empty:
            return {"mean": float(match.iloc[0]["mean_area_sqft"]),
                    "std": float(match.iloc[0]["std_area_sqft"])}
    except Exception:
        pass
    return None


async def _verify_image_gps(image_url: str, input_lat: float, input_lon: float) -> dict:
    """Download image, extract EXIF GPS, cross-check against declared lat/lon."""
    try:
        import httpx
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        import io

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(image_url, follow_redirects=True)
            resp.raise_for_status()
            img = Image.open(io.BytesIO(resp.content))

        exif_data = img._getexif()
        if not exif_data:
            return {"has_gps": False}

        gps_info = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for gps_tag_id, gps_value in value.items():
                    gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                    gps_info[gps_tag] = gps_value

        if not gps_info.get("GPSLatitude") or not gps_info.get("GPSLongitude"):
            return {"has_gps": False}

        def dms_to_decimal(dms, ref):
            d, m, s = [float(x) for x in dms]
            decimal = d + m / 60 + s / 3600
            if ref in ("S", "W"):
                decimal = -decimal
            return decimal

        exif_lat = dms_to_decimal(gps_info["GPSLatitude"], gps_info.get("GPSLatitudeRef", "N"))
        exif_lon = dms_to_decimal(gps_info["GPSLongitude"], gps_info.get("GPSLongitudeRef", "E"))

        # Haversine distance in km
        R = 6371
        dlat = math.radians(exif_lat - input_lat)
        dlon = math.radians(exif_lon - input_lon)
        a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(input_lat)) * math.cos(math.radians(exif_lat)) * math.sin(dlon / 2) ** 2
        distance_km = R * 2 * math.asin(math.sqrt(a))

        return {
            "has_gps": True,
            "exif_lat": round(exif_lat, 5),
            "exif_lon": round(exif_lon, 5),
            "distance_km": round(distance_km, 2),
            "mismatch": distance_km > 2.0,
        }
    except Exception:
        return {"has_gps": False}


def _check_circle_rate_staleness(last_updated_str: str) -> bool:
    try:
        return (datetime.now() - datetime.strptime(last_updated_str, "%Y-%m-%d")) > timedelta(days=3 * 365)
    except Exception:
        return True


class FraudAgent(BaseAgent):
    name = "fraud"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]
        flags = []

        area = inp["built_up_area_sqft"]
        sub_type = inp["sub_type"]
        city = loc.get("city", "")
        locality = loc.get("locality", "")

        # §21.1 — Size vs locality sanity
        stats = _load_locality_stats(city, locality, sub_type)
        if stats and stats["std"] > 0:
            z = (area - stats["mean"]) / stats["std"]
            if abs(z) > 3.0:
                flags.append({"flag": "size_outlier_locality", "severity": "high",
                             "explanation": f"Area {area} sqft is {abs(z):.1f}σ from locality mean {stats['mean']} sqft"})
            elif abs(z) > 2.0:
                flags.append({"flag": "size_outlier_locality", "severity": "medium",
                             "explanation": f"Area {area} sqft is {abs(z):.1f}σ from locality mean {stats['mean']} sqft"})

        # §21.2 — Location-type mismatch
        poi_counts = loc.get("poi_counts", {})
        n_r = poi_counts.get("n_residential", 0)
        n_c = poi_counts.get("n_commercial", 0)
        n_i = poi_counts.get("n_industrial", 0)
        total = n_r + n_c + n_i
        if total > 0:
            rho_r, rho_i = n_r / total, n_i / total
            if sub_type in ("warehouse",) and rho_r > 0.70:
                flags.append({"flag": "industrial_in_residential_zone", "severity": "medium",
                             "explanation": f"Warehouse in area with {rho_r:.0%} residential POIs"})
            if sub_type in ("apartment", "villa") and rho_i > 0.40:
                flags.append({"flag": "residential_in_industrial_zone", "severity": "high",
                             "explanation": f"Residential property in area with {rho_i:.0%} industrial POIs"})

        # §21.3 — Configuration plausibility
        config = inp.get("configuration")
        if config and config.upper() in MIN_CONFIG_AREAS:
            min_area = MIN_CONFIG_AREAS[config.upper()] * 0.80
            if area < min_area:
                flags.append({"flag": "config_area_mismatch", "severity": "high",
                             "explanation": f"{config} needs at least {min_area:.0f} sqft, got {area} sqft"})

        # §21.4 — Self-declared value outlier
        circle_rate = loc["circle_rate_per_sqft"]
        tier = loc["city_tier"]
        mcr_max = MCR_TABLE.get(tier, {}).get("prime", 2.20)
        declared_value = inp.get("declared_value")
        if declared_value and declared_value > 2 * circle_rate * area * mcr_max:
            flags.append({"flag": "declared_value_above_market", "severity": "medium",
                         "explanation": f"Declared ₹{declared_value:,} exceeds 2× market ceiling"})

        # §21.5 — Circle rate staleness
        cr_last_updated = loc.get("circle_rate_last_updated", "2024-04-01")
        if _check_circle_rate_staleness(cr_last_updated):
            flags.append({"flag": "circle_rate_may_be_stale", "severity": "low",
                         "explanation": f"Circle rate last updated {cr_last_updated}"})

        # NEW — Rent vs value yield anomaly check
        if inp.get("monthly_rent") and inp.get("monthly_rent") > 0:
            v_approx = circle_rate * area * loc.get("mcr", 1.5)
            annual_yield = (inp["monthly_rent"] * 12) / v_approx if v_approx > 0 else 0
            if annual_yield > 0.12:
                flags.append({"flag": "abnormally_high_rental_yield", "severity": "medium",
                             "explanation": f"Yield {annual_yield:.1%} is abnormally high, possible rent inflation"})
            elif annual_yield < 0.005 and annual_yield > 0:
                flags.append({"flag": "abnormally_low_rental_yield", "severity": "low",
                             "explanation": f"Yield {annual_yield:.1%} is unusually low for a rented property"})

        # §21.6 — Photo-location EXIF GPS verification
        exterior_url = inp.get("exterior_image_url")
        input_lat = inp.get("latitude")
        input_lon = inp.get("longitude")
        if exterior_url and input_lat is not None and input_lon is not None:
            gps_result = await _verify_image_gps(exterior_url, input_lat, input_lon)
            if gps_result.get("has_gps") and gps_result.get("mismatch"):
                dist = gps_result.get("distance_km", 0)
                sev = "high" if dist > 10 else "medium"
                flags.append({"flag": "photo_location_mismatch", "severity": sev,
                             "explanation": f"Photo GPS coordinates are {dist} km from declared property location"})
            elif gps_result.get("has_gps"):
                pass  # GPS verified, no flag
            # no flag if image has no EXIF (common for web-hosted images)

        # §21.7 — Builder reputation check
        builder_raw = inp.get("builder_name") or ""
        builder_key = builder_raw.strip().lower()
        if builder_key:
            rep_score = None
            for known, score in BUILDER_REPUTATION.items():
                if known in builder_key or builder_key in known:
                    rep_score = score
                    break
            if rep_score is None:
                flags.append({"flag": "unknown_builder", "severity": "low",
                             "explanation": f"Builder '{builder_raw}' not found in reputation database — perform additional due diligence"})
            elif rep_score < 0.80:
                flags.append({"flag": "low_reputation_builder", "severity": "medium",
                             "explanation": f"Builder '{builder_raw}' has a below-average reputation score ({rep_score:.2f})"})

        # LLM-POWERED ANOMALY DETECTION — catches subtle patterns
        llm_anomalies = await detect_anomalies(inp, ctx)
        is_llm_powered = "fallback" not in llm_anomalies

        llm_flags = []
        if is_llm_powered:
            for anomaly in llm_anomalies.get("anomalies_detected", []):
                if isinstance(anomaly, dict) and anomaly.get("severity") in ("medium", "high"):
                    llm_flags.append({
                        "flag": f"llm_detected_{anomaly.get('anomaly', 'unknown')[:50].replace(' ', '_').lower()}",
                        "severity": anomaly["severity"],
                        "explanation": anomaly.get("reasoning", "LLM-detected anomaly"),
                    })

        all_flags = flags + llm_flags
        severity_weights = {"low": 0.1, "medium": 0.25, "high": 0.5}

        return {
            "flags": all_flags,
            "rule_based_flags": flags,
            "llm_detected_flags": llm_flags,
            "fraud_score": sum(severity_weights.get(f["severity"], 0) for f in all_flags),
            "overall_risk": llm_anomalies.get("overall_risk_level", "low") if is_llm_powered else ("high" if any(f["severity"] == "high" for f in flags) else "low"),
            "llm_recommendation": llm_anomalies.get("recommendation", "proceed"),
            "checks_performed": [
                "size_sanity", "location_type_mismatch", "config_plausibility",
                "declared_value_outlier", "circle_rate_staleness", "yield_anomaly",
                "photo_gps_verification", "builder_reputation",
                "llm_anomaly_detection",
            ],
            "is_llm_powered": is_llm_powered,
        }
