"""Computes RPI, time-to-liquidate, and distress value."""
from app.agents.base import BaseAgent
from app.math.formulas import (
    compute_s_cfg_liquidity, compute_s_age_liq, compute_s_yield,
    compute_rpi, compute_ttl, compute_distress_range,
)


class LiquidityAgent(BaseAgent):
    name = "liquidity"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]
        prop = ctx["property_char"]
        market = ctx["market_dynamics"]
        legal = ctx["legal"]
        val = ctx["valuation"]

        s_infra = loc["infra_score"]
        delta = prop["delta"]
        s_cfg = compute_s_cfg_liquidity(delta)
        s_ds = market["supply_density"]
        s_legal = legal["s_legal"]
        s_age_liq = compute_s_age_liq(inp["age_years"])

        v_prior = loc["circle_rate_per_sqft"] * inp["built_up_area_sqft"] * loc["mcr"]
        s_yield = compute_s_yield(inp.get("monthly_rent"), v_prior, loc["city_tier"], inp["property_type"])

        rpi = compute_rpi(s_infra, s_cfg, s_ds, s_legal, s_age_liq, s_yield)
        ttl = compute_ttl(rpi, inp["sub_type"])

        mv_range = val["mv_range"]
        distress_range = compute_distress_range(mv_range, rpi)

        rpi_int = round(rpi)
        if rpi_int >= 80:
            label = "Highly liquid"
        elif rpi_int >= 60:
            label = "Moderately liquid"
        elif rpi_int >= 40:
            label = "Restricted liquidity"
        elif rpi_int >= 20:
            label = "Illiquid"
        else:
            label = "Unsellable without deep discount"

        return {
            "rpi": rpi_int,
            "rpi_label": label,
            "estimated_time_to_sell_days": ttl,
            "distress_value_range": distress_range,
            "rpi_components": {
                "s_infra": round(s_infra, 4),
                "s_cfg": round(s_cfg, 4),
                "s_ds": round(s_ds, 4),
                "s_legal": round(s_legal, 4),
                "s_age_liq": round(s_age_liq, 4),
                "s_yield": round(s_yield, 4),
            },
        }
