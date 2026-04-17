"""
ValuationAgent — UPGRADED with multi-scenario analysis.
Core math remains deterministic (NO LLM). But now produces three scenarios
(optimistic/base/pessimistic) and incorporates comparable + macro context.
"""
from app.agents.base import BaseAgent
from app.math.formulas import (
    compute_valuation, compute_driver_contributions, compute_f_regulatory,
    compute_uncertainty, compute_mv_range,
    compute_q_data, compute_q_agree, compute_q_density, compute_p_fraud,
    compute_confidence,
)
from app.config.constants import ASSERTION_BOUNDS, YIELD_EXPECTED


class ValuationAgent(BaseAgent):
    name = "valuation"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]
        prop = ctx["property_char"]
        market = ctx["market_dynamics"]
        legal = ctx["legal"]
        fraud_flags = ctx.get("fraud", {}).get("flags", [])
        comparable = ctx.get("comparable_analysis", {})
        macro = ctx.get("macro_context", {})

        circle_rate = loc["circle_rate_per_sqft"]
        area = inp["built_up_area_sqft"]
        mcr = loc["mcr"]
        f_loc = loc["f_loc"]
        f_age = prop["f_age"]
        f_cfg = prop["f_cfg"]
        f_legal = legal["f_legal"]
        f_floor = prop["f_floor"]
        f_regulatory = compute_f_regulatory(inp.get("rera_registered"))

        self._assert_bounds("S_infra", loc.get("infra_score", 0))
        self._assert_bounds("S_nbhd", loc.get("neighborhood_quality", 0))
        self._assert_bounds("MCR", mcr)
        self._assert_bounds("f_loc", f_loc)
        self._assert_bounds("f_age", f_age)
        self._assert_bounds("f_cfg", f_cfg)
        self._assert_bounds("f_legal", f_legal)
        self._assert_bounds("f_floor", f_floor)
        self._assert_bounds("f_regulatory", f_regulatory)

        # BASE SCENARIO — standard valuation
        v_base = compute_valuation(circle_rate, area, mcr, f_loc, f_age, f_cfg, f_legal, f_floor, f_regulatory)

        # Apply macro adjustment if available
        macro_adj = macro.get("macro_adjustment_factor", 1.0)
        v_base_macro = v_base * macro_adj

        # OPTIMISTIC SCENARIO — favorable factors at upper bound
        v_optimistic = v_base_macro * 1.08

        # PESSIMISTIC SCENARIO — adverse conditions
        v_pessimistic = v_base_macro * 0.90

        drivers = compute_driver_contributions(mcr, f_loc, f_age, f_cfg, f_legal, f_floor, f_regulatory)

        # Confidence components
        input_fields = {
            "address_or_coords": True,
            "property_type": inp.get("property_type"),
            "sub_type": inp.get("sub_type"),
            "built_up_area_sqft": inp.get("built_up_area_sqft"),
            "age_years": inp.get("age_years"),
            "floor": inp.get("floor"),
            "ownership": inp.get("ownership"),
            "title_clear": inp.get("title_clear"),
            "occupancy": inp.get("occupancy"),
            "monthly_rent": inp.get("monthly_rent"),
            "exterior_image_url": inp.get("exterior_image_url"),
            "interior_image_url": inp.get("interior_image_url"),
        }
        q_data = compute_q_data(input_fields)

        # V1 — circle rate anchored (always available)
        v1 = circle_rate * area * mcr * f_loc

        # V2 — comparable-based (from ComparableAnalysisAgent)
        v2 = comparable.get("v2_comparable_estimate")

        # V3 — rental yield capitalization (if rent provided)
        v3 = None
        if inp.get("monthly_rent"):
            ptype = "residential" if inp["property_type"] == "residential" else "commercial"
            yr = YIELD_EXPECTED.get((loc["city_tier"], ptype), (0.025, 0.045))
            yield_mid = (yr[0] + yr[1]) / 2
            if yield_mid > 0:
                v3 = (inp["monthly_rent"] * 12) / yield_mid

        values = [v for v in [v1, v2, v3] if v is not None and v > 0]
        q_agree = compute_q_agree(values)
        q_density = compute_q_density(market.get("active_listings_1km"))
        p_fraud = compute_p_fraud(fraud_flags)
        confidence = compute_confidence(q_data, q_agree, q_density, p_fraud)

        # Boost confidence if LLM-powered agents contributed
        llm_agents_count = sum(1 for k in ["location_intel", "property_char", "market_dynamics", "comparable_analysis", "macro_context"]
                                if ctx.get(k, {}).get("is_llm_powered", False))
        confidence_boost = min(0.05, llm_agents_count * 0.01)
        confidence = min(1.0, confidence + confidence_boost)

        u = compute_uncertainty(q_data, q_agree, p_fraud)
        self._assert_bounds("u", u)
        self._assert_bounds("C", confidence)

        mv_range = compute_mv_range(v_base_macro, u)

        # Weighted value estimate using multiple sources
        weighted_v = self._weighted_value(v_base_macro, v2, v3, q_agree)

        return {
            "point_estimate": round(v_base_macro),
            "weighted_estimate": round(weighted_v),
            "mv_range": mv_range,
            "uncertainty": round(u, 4),
            "driver_contributions": drivers,
            "confidence_score": round(confidence, 4),
            "confidence_components": {
                "q_data": round(q_data, 4),
                "q_agree": round(q_agree, 4),
                "q_density": round(q_density, 4),
                "p_fraud": round(p_fraud, 4),
                "llm_boost": round(confidence_boost, 4),
            },
            "independent_estimates": {
                "v1_circle_rate": round(v1) if v1 else None,
                "v2_comparables": round(v2) if v2 else None,
                "v3_rental_yield": round(v3) if v3 else None,
            },
            "scenarios": {
                "optimistic": {"value": round(v_optimistic), "range": compute_mv_range(v_optimistic, u * 0.8)},
                "base": {"value": round(v_base_macro), "range": mv_range},
                "pessimistic": {"value": round(v_pessimistic), "range": compute_mv_range(v_pessimistic, u * 1.2)},
            },
            "macro_adjustment_applied": round(macro_adj, 4),
            "f_regulatory": round(f_regulatory, 4),
            "rera_registered": inp.get("rera_registered"),
        }

    def _weighted_value(self, v1: float, v2: float | None, v3: float | None, q_agree: float) -> float:
        """Weighted average of available value estimates."""
        estimates = [(v1, 0.50)]
        if v2 and isinstance(v2, (int, float)) and v2 > 0:
            estimates.append((v2, 0.30))
        if v3 and isinstance(v3, (int, float)) and v3 > 0:
            estimates.append((v3, 0.20))

        total_weight = sum(w for _, w in estimates)
        return sum(v * (w / total_weight) for v, w in estimates)

    @staticmethod
    def _assert_bounds(name: str, value: float):
        lo, hi = ASSERTION_BOUNDS.get(name, (float("-inf"), float("inf")))
        if not (lo <= value <= hi):
            raise ValueError(f"Assertion failed: {name}={value} not in [{lo}, {hi}]")
