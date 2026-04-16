"""
PropertyCharAgent — UPGRADED with LLM-powered condition assessment.
Combines deterministic math (age, config, floor factors) with
intelligent property condition reasoning.
"""
from app.agents.base import BaseAgent
from app.math.formulas import compute_f_age, compute_f_cfg, compute_f_floor, compute_delta
from app.tools.llm import assess_property_condition
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Module-level cache — CSV is read once for the lifetime of the process
_locality_norms_df = None
_mode_area_cache: dict = {}


def _get_locality_norms():
    global _locality_norms_df
    if _locality_norms_df is None:
        try:
            _locality_norms_df = pd.read_csv(DATA_DIR / "locality_norms.csv")
        except Exception:
            _locality_norms_df = pd.DataFrame()
    return _locality_norms_df


def _load_mode_area(city: str, locality: str, sub_type: str) -> float:
    key = (city.strip().lower(), locality.strip().lower(), sub_type.strip().lower())
    if key in _mode_area_cache:
        return _mode_area_cache[key]
    try:
        df = _get_locality_norms()
        match = df[
            (df["city"].str.lower() == key[0]) &
            (df["locality"].str.lower() == key[1]) &
            (df["sub_type"].str.lower() == key[2])
        ]
        if not match.empty:
            result = float(match.iloc[0]["mode_area_sqft"])
            _mode_area_cache[key] = result
            return result
    except Exception:
        pass
    defaults = {"apartment": 900, "villa": 2000, "plot": 1500,
                "shop": 400, "warehouse": 3000, "office": 1200, "other": 1000}
    result = defaults.get(sub_type, 1000)
    _mode_area_cache[key] = result
    return result


class PropertyCharAgent(BaseAgent):
    name = "property_char"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]

        age = inp["age_years"]
        sub_type = inp["sub_type"]
        area = inp["built_up_area_sqft"]
        city = loc.get("city", "")
        locality = loc.get("locality", "")

        f_age = compute_f_age(age, sub_type)
        mode_area = _load_mode_area(city, locality, sub_type)
        f_cfg = compute_f_cfg(area, mode_area)
        delta = compute_delta(area, mode_area)
        f_floor = compute_f_floor(
            inp.get("floor"), inp.get("total_floors"),
            inp.get("has_lift"), sub_type, inp["property_type"],
        )

        vintage = "new" if age <= 3 else ("mid_age" if age <= 15 else ("old" if age <= 30 else "very_old"))

        # LLM-powered condition assessment
        condition_result = await assess_property_condition(
            age_years=age, sub_type=sub_type,
            config=inp.get("configuration"),
            image_urls=[u for u in [inp.get("exterior_image_url"), inp.get("interior_image_url")] if u],
        )

        is_llm_powered = "fallback" not in condition_result
        visual_condition = condition_result.get("condition_score", 0.75)
        if not isinstance(visual_condition, (int, float)):
            visual_condition = 0.75
        visual_condition = max(0.0, min(1.0, visual_condition))

        condition_grade = condition_result.get("condition_grade", "fair")
        likely_issues = condition_result.get("likely_issues", [])
        structural_risk = condition_result.get("structural_risk", "low")
        maintenance_pct = condition_result.get("maintenance_estimate_pct", 0)
        remaining_life = condition_result.get("expected_remaining_life_years", max(1, 60 - age))

        # Condition-adjusted age factor: if LLM says condition is better/worse than
        # age implies, we adjust f_age slightly (±5% max)
        condition_deviation = visual_condition - (1.0 - age / 60.0)
        condition_adj = 1.0 + max(-0.05, min(0.05, condition_deviation * 0.1))
        f_age_adjusted = max(0.60, min(1.00, f_age * condition_adj))

        return {
            "f_age": round(f_age_adjusted, 4),
            "f_age_raw": round(f_age, 4),
            "f_age_condition_adjustment": round(condition_adj, 4),
            "f_cfg": round(f_cfg, 4),
            "f_floor": round(f_floor, 4),
            "delta": round(delta, 4),
            "mode_area": mode_area,
            "visual_condition": round(visual_condition, 3),
            "condition_grade": condition_grade,
            "likely_issues": likely_issues,
            "structural_risk": structural_risk,
            "maintenance_estimate_pct": maintenance_pct,
            "expected_remaining_life_years": remaining_life,
            "vintage_bracket": vintage,
            "is_llm_powered": is_llm_powered,
        }
