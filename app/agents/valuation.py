"""
ValuationAgent — UPGRADED with multi-scenario analysis, NOI-based income approach,
and regulatory compliance factor integration.
Core math remains deterministic (NO LLM).
"""
from app.agents.base import BaseAgent
from app.math.formulas import (
    compute_valuation, compute_driver_contributions,
    compute_uncertainty, compute_mv_range,
    compute_q_data, compute_q_agree, compute_q_density, compute_p_fraud,
    compute_confidence,
    compute_noi, compute_gross_yield, compute_net_yield,
    compute_monthly_emi, compute_dscr, compute_grm, compute_rent_coverage_ratio,
)
from app.config.constants import (
    ASSERTION_BOUNDS, YIELD_EXPECTED, NET_YIELD_EXPECTED,
    VACANCY_DEFAULTS, OPEX_DEFAULTS,
)


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
        f_legal = legal["f_legal"]           # ownership/title only — for assertion
        f_regulatory = legal.get("f_regulatory", 1.0)
        f_floor = prop["f_floor"]

        self._assert_bounds("S_infra",     loc.get("infra_score", 0))
        self._assert_bounds("S_nbhd",      loc.get("neighborhood_quality", 0))
        self._assert_bounds("MCR",         mcr)
        self._assert_bounds("f_loc",       f_loc)
        self._assert_bounds("f_age",       f_age)
        self._assert_bounds("f_cfg",       f_cfg)
        self._assert_bounds("f_legal",     f_legal)
        self._assert_bounds("f_regulatory", f_regulatory)
        self._assert_bounds("f_floor",     f_floor)

        # BASE SCENARIO — apply regulatory on top of standard formula
        v_base_raw = compute_valuation(
            circle_rate, area, mcr, f_loc, f_age, f_cfg, f_legal, f_floor
        )
        v_base = v_base_raw * f_regulatory

        # Apply macro adjustment
        macro_adj = macro.get("macro_adjustment_factor", 1.0)
        v_base_macro = v_base * macro_adj

        v_optimistic  = v_base_macro * 1.08
        v_pessimistic = v_base_macro * 0.90

        drivers = compute_driver_contributions(
            mcr, f_loc, f_age, f_cfg, f_legal, f_floor, f_regulatory
        )

        # Confidence components
        input_fields = {
            "address_or_coords":    True,
            "property_type":        inp.get("property_type"),
            "sub_type":             inp.get("sub_type"),
            "built_up_area_sqft":   inp.get("built_up_area_sqft"),
            "age_years":            inp.get("age_years"),
            "floor":                inp.get("floor"),
            "ownership":            inp.get("ownership"),
            "title_clear":          inp.get("title_clear"),
            "occupancy":            inp.get("occupancy"),
            "monthly_rent":         inp.get("monthly_rent"),
            "exterior_image_url":   inp.get("exterior_image_url"),
            "interior_image_url":   inp.get("interior_image_url"),
            "rera_registered":      inp.get("rera_registered"),
            "occupancy_certificate": inp.get("occupancy_certificate"),
            "encumbrance_status":   inp.get("encumbrance_status"),
            "loan_amount_requested": inp.get("loan_amount_requested"),
        }
        q_data = compute_q_data(input_fields)

        # V1 — circle rate anchored (always available)
        v1 = circle_rate * area * mcr * f_loc

        # V2 — comparable-based (from ComparableAnalysisAgent)
        v2 = comparable.get("v2_comparable_estimate")

        # V3 — income / rental capitalisation using NOI and net cap rate
        v3 = None
        if inp.get("monthly_rent") and inp["monthly_rent"] > 0:
            ptype = "residential" if inp["property_type"] == "residential" else "commercial"
            tier = loc["city_tier"]
            vacancy = (
                inp["vacancy_rate_pct"] / 100
                if inp.get("vacancy_rate_pct") is not None
                else VACANCY_DEFAULTS.get((tier, ptype), 0.07)
            )
            opex = (
                inp["opex_ratio_pct"] / 100
                if inp.get("opex_ratio_pct") is not None
                else OPEX_DEFAULTS.get(inp["property_type"], 0.20)
            )
            noi = compute_noi(inp["monthly_rent"], vacancy, opex)
            net_yr = NET_YIELD_EXPECTED.get((tier, ptype), (0.016, 0.030))
            cap_rate = (net_yr[0] + net_yr[1]) / 2
            if cap_rate > 0 and noi > 0:
                v3 = noi / cap_rate

        values = [v for v in [v1, v2, v3] if v is not None and v > 0]
        q_agree  = compute_q_agree(values)
        q_density = compute_q_density(market.get("active_listings_1km"))
        p_fraud   = compute_p_fraud(fraud_flags)
        confidence = compute_confidence(q_data, q_agree, q_density, p_fraud)

        llm_agents_count = sum(
            1 for k in ["location_intel", "property_char", "market_dynamics",
                        "comparable_analysis", "macro_context"]
            if ctx.get(k, {}).get("is_llm_powered", False)
        )
        confidence = min(1.0, confidence + min(0.05, llm_agents_count * 0.01))

        u = compute_uncertainty(q_data, q_agree, p_fraud)
        self._assert_bounds("u", u)
        self._assert_bounds("C", confidence)

        mv_range = compute_mv_range(v_base_macro, u)
        weighted_v = self._weighted_value(v_base_macro, v2, v3, q_agree)

        # ── Income / Rental Analysis ──────────────────────────────────
        income_analysis = None
        if inp.get("monthly_rent") and inp["monthly_rent"] > 0:
            monthly_rent = inp["monthly_rent"]
            ptype = "residential" if inp["property_type"] == "residential" else "commercial"
            tier = loc["city_tier"]
            vacancy = (
                inp["vacancy_rate_pct"] / 100
                if inp.get("vacancy_rate_pct") is not None
                else VACANCY_DEFAULTS.get((tier, ptype), 0.07)
            )
            opex = (
                inp["opex_ratio_pct"] / 100
                if inp.get("opex_ratio_pct") is not None
                else OPEX_DEFAULTS.get(inp["property_type"], 0.20)
            )
            noi = compute_noi(monthly_rent, vacancy, opex)
            ref_value = max(v_base_macro, 1)
            gross_yield = compute_gross_yield(monthly_rent, ref_value)
            net_yield   = compute_net_yield(noi, ref_value)
            grm         = compute_grm(ref_value, monthly_rent)
            loan        = inp.get("loan_amount_requested")
            dscr        = compute_dscr(noi, loan) if loan else None
            rcr         = compute_rent_coverage_ratio(monthly_rent, loan) if loan else None
            monthly_emi = compute_monthly_emi(loan) if loan else None

            income_analysis = {
                "monthly_rent":           round(monthly_rent),
                "gross_annual_rent":      round(monthly_rent * 12),
                "vacancy_rate_pct":       round(vacancy * 100, 1),
                "opex_ratio_pct":         round(opex * 100, 1),
                "noi":                    round(noi),
                "gross_rental_yield_pct": round(gross_yield * 100, 2),
                "net_rental_yield_pct":   round(net_yield * 100, 2),
                "grm":                    round(grm, 1) if grm else None,
                "dscr":                   round(dscr, 2) if dscr else None,
                "rcr":                    round(rcr, 2) if rcr else None,
                "monthly_emi":            round(monthly_emi) if monthly_emi else None,
                "loan_amount_requested":  loan,
            }

        return {
            "point_estimate":       round(v_base_macro),
            "weighted_estimate":    round(weighted_v),
            "mv_range":             mv_range,
            "uncertainty":          round(u, 4),
            "driver_contributions": drivers,
            "confidence_score":     round(confidence, 4),
            "confidence_components": {
                "q_data":        round(q_data, 4),
                "q_agree":       round(q_agree, 4),
                "q_density":     round(q_density, 4),
                "p_fraud":       round(p_fraud, 4),
                "llm_boost":     round(min(0.05, llm_agents_count * 0.01), 4),
            },
            "independent_estimates": {
                "v1_circle_rate":      round(v1) if v1 else None,
                "v2_comparables":      round(v2) if v2 else None,
                "v3_income_approach":  round(v3) if v3 else None,
            },
            "scenarios": {
                "optimistic":  {"value": round(v_optimistic),  "range": compute_mv_range(v_optimistic, u * 0.8)},
                "base":        {"value": round(v_base_macro),  "range": mv_range},
                "pessimistic": {"value": round(v_pessimistic), "range": compute_mv_range(v_pessimistic, u * 1.2)},
            },
            "macro_adjustment_applied": round(macro_adj, 4),
            "f_regulatory_applied":     round(f_regulatory, 4),
            "income_analysis":          income_analysis,
        }

    def _weighted_value(self, v1: float, v2: float | None, v3: float | None,
                        q_agree: float) -> float:
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
