"""
FraudAgent — UPGRADED with LLM-powered anomaly detection.
Combines rule-based checks (5 deterministic) with intelligent pattern detection.
"""
from app.agents.base import BaseAgent
from app.config.constants import MIN_CONFIG_AREAS, MCR_TABLE, VACANCY_DEFAULTS, OPEX_DEFAULTS
from app.math.formulas import compute_noi
from app.tools.llm import detect_anomalies
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

DATA_DIR = Path(__file__).parent.parent / "data"

# Reuse the same cached DataFrame loaded by property_char (same CSV file)
# Falls back to its own load if property_char hasn't been imported yet
_locality_stats_cache: dict = {}


def _get_locality_norms_df():
    """Return the locality norms DataFrame, reusing property_char's cache when possible."""
    try:
        from app.agents.property_char import _get_locality_norms
        return _get_locality_norms()
    except Exception:
        pass
    try:
        return pd.read_csv(DATA_DIR / "locality_norms.csv")
    except Exception:
        return pd.DataFrame()


def _load_locality_stats(city: str, locality: str, sub_type: str) -> dict | None:
    key = (city.strip().lower(), locality.strip().lower(), sub_type.strip().lower())
    if key in _locality_stats_cache:
        return _locality_stats_cache[key]
    try:
        df = _get_locality_norms_df()
        match = df[
            (df["city"].str.lower() == key[0]) &
            (df["locality"].str.lower() == key[1]) &
            (df["sub_type"].str.lower() == key[2])
        ]
        if not match.empty:
            result = {"mean": float(match.iloc[0]["mean_area_sqft"]),
                      "std": float(match.iloc[0]["std_area_sqft"])}
            _locality_stats_cache[key] = result
            return result
    except Exception:
        pass
    _locality_stats_cache[key] = None
    return None


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

        # 21.2 — Location-type mismatch
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

        # 21.3 — Configuration plausibility
        config = inp.get("configuration")
        if config and config.upper() in MIN_CONFIG_AREAS:
            min_area = MIN_CONFIG_AREAS[config.upper()] * 0.80
            if area < min_area:
                flags.append({"flag": "config_area_mismatch", "severity": "high",
                             "explanation": f"{config} needs at least {min_area:.0f} sqft, got {area} sqft"})

        # 21.4 — Self-declared value outlier
        circle_rate = loc["circle_rate_per_sqft"]
        tier = loc["city_tier"]
        mcr_max = MCR_TABLE.get(tier, {}).get("prime", 2.20)
        declared_value = inp.get("declared_value")
        if declared_value and declared_value > 2 * circle_rate * area * mcr_max:
            flags.append({"flag": "declared_value_above_market", "severity": "medium",
                         "explanation": f"Declared ₹{declared_value:,} exceeds 2× market ceiling"})

        # 21.5 — Circle rate staleness
        cr_last_updated = loc.get("circle_rate_last_updated", "2024-04-01")
        if _check_circle_rate_staleness(cr_last_updated):
            flags.append({"flag": "circle_rate_may_be_stale", "severity": "low",
                         "explanation": f"Circle rate last updated {cr_last_updated}"})

        # §21.6 — Rental yield anomaly check (gross and net)
        if inp.get("monthly_rent") and inp.get("monthly_rent") > 0:
            v_approx = circle_rate * area * loc.get("mcr", 1.5)
            monthly_rent = inp["monthly_rent"]
            ptype = "residential" if inp.get("property_type") == "residential" else "commercial"
            tier = loc.get("city_tier", 2)
            vacancy = VACANCY_DEFAULTS.get((tier, ptype), 0.07)
            opex    = OPEX_DEFAULTS.get(inp.get("property_type", "residential"), 0.20)
            gross_yield = (monthly_rent * 12) / v_approx if v_approx > 0 else 0
            noi         = compute_noi(monthly_rent, vacancy, opex)
            net_yield   = noi / v_approx if v_approx > 0 else 0
            if gross_yield > 0.14:
                flags.append({"flag": "abnormally_high_rental_yield", "severity": "medium",
                             "explanation": f"Gross yield {gross_yield:.1%} is abnormally high (>14%), possible rent inflation"})
            elif net_yield > 0.08:
                flags.append({"flag": "high_net_yield_after_costs", "severity": "low",
                             "explanation": f"Net yield {net_yield:.1%} after vacancy+opex exceeds typical range for this tier"})
            elif gross_yield < 0.005 and gross_yield > 0:
                flags.append({"flag": "abnormally_low_rental_yield", "severity": "low",
                             "explanation": f"Gross yield {gross_yield:.1%} is unusually low for a rented property"})

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
                "llm_anomaly_detection",
            ],
            "is_llm_powered": is_llm_powered,
        }
