"""
ComparableAnalysisAgent — LLM-powered comparable property analysis.
Finds, adjusts, and reasons about comparable properties to produce
an independent value estimate (V2) that's far better than synthetic priors.
"""
from app.agents.base import BaseAgent
from app.tools.llm import analyze_comparables
from app.tools.listings import get_synthetic_listings


class ComparableAnalysisAgent(BaseAgent):
    name = "comparable_analysis"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]

        city = loc.get("city", "")
        locality = loc.get("locality", "")
        sub_type = inp["sub_type"]
        area = inp["built_up_area_sqft"]
        age = inp["age_years"]
        circle_rate = loc["circle_rate_per_sqft"]
        city_tier = loc["city_tier"]
        mcr = loc["mcr"]

        base_value = circle_rate * area * mcr
        listing_data = get_synthetic_listings(city_tier, sub_type, base_value, area)

        llm_analysis = await analyze_comparables(
            city=city,
            locality=locality,
            sub_type=sub_type,
            area_sqft=area,
            age_years=age,
            circle_rate=circle_rate,
            listing_data={
                "city_tier": city_tier,
                "locality": locality,
                "active_listings_1km": listing_data["active_listings_1km"],
                "median_comparable_price": listing_data["median_comparable_price"],
                "comparable_prices": listing_data["comparable_prices"][:5],
                "circle_rate_base_value": round(base_value),
            },
        )

        is_llm_powered = "fallback" not in llm_analysis
        llm_value = llm_analysis.get("market_value_estimate")
        llm_confidence = llm_analysis.get("confidence", 0.5)

        if llm_value and isinstance(llm_value, (int, float)) and llm_value > 0:
            v2_estimate = llm_value
        else:
            v2_estimate = listing_data.get("median_comparable_price", base_value)

        adjustments = llm_analysis.get("comparable_adjustments", [])

        return {
            "v2_comparable_estimate": round(v2_estimate),
            "v2_range": [
                round(llm_analysis.get("value_range_low", v2_estimate * 0.90)),
                round(llm_analysis.get("value_range_high", v2_estimate * 1.10)),
            ],
            "comparable_adjustments": adjustments,
            "reasoning": llm_analysis.get("value_reasoning", "Based on synthetic comparable data"),
            "num_comparables_used": listing_data["active_listings_1km"],
            "confidence": round(llm_confidence, 3),
            "is_llm_powered": is_llm_powered,
            "source_prices": listing_data["comparable_prices"][:5],
        }
