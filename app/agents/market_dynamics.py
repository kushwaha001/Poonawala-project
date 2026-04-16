"""
MarketDynamicsAgent — UPGRADED with LLM-powered trend analysis.
Combines listing data with intelligent market assessment.
"""
from app.agents.base import BaseAgent
from app.tools.listings import get_listings
from app.tools.llm import call_claude_json
from app.math.formulas import compute_s_ds


class MarketDynamicsAgent(BaseAgent):
    name = "market_dynamics"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]

        city_tier = loc["city_tier"]
        city = loc.get("city", "")
        locality = loc.get("locality", "")
        sub_type = inp["sub_type"]
        area = inp["built_up_area_sqft"]
        circle_rate = loc["circle_rate_per_sqft"]
        mcr = loc["mcr"]
        base_value = circle_rate * area * mcr

        listing_data = await get_listings(city_tier, sub_type, base_value, area, locality)

        active_listings = listing_data.get("active_listings_1km", 0)
        s_ds = compute_s_ds(active_listings, city_tier, sub_type)
        comparable_prices = listing_data.get("comparable_prices", [])
        median_comp = listing_data.get("median_comparable_price")

        # LLM-powered market trend analysis
        trend_analysis = await self._analyze_market_trends(
            city, locality, city_tier, sub_type, active_listings, s_ds, base_value,
        )

        is_llm_powered = "fallback" not in trend_analysis
        price_momentum = trend_analysis.get("price_momentum", "stable")
        absorption_assessment = trend_analysis.get("absorption_rate_assessment", "normal")
        buyer_profile = trend_analysis.get("buyer_profile", "mixed")
        supply_risk = trend_analysis.get("supply_pipeline_risk", "moderate")

        # Dynamic fungibility from LLM or rule-based
        fungibility = trend_analysis.get("fungibility_score", None)
        if not fungibility or not isinstance(fungibility, (int, float)):
            fungibility = self._rule_fungibility(sub_type, city_tier)
        fungibility = max(0.0, min(1.0, fungibility))

        return {
            "active_listings_1km": active_listings,
            "supply_density": round(s_ds, 4),
            "asset_fungibility": round(fungibility, 3),
            "price_momentum": price_momentum,
            "median_comparable_price": median_comp,
            "comparable_prices": comparable_prices,
            "source": listing_data.get("source", "synthetic"),
            "absorption_assessment": absorption_assessment,
            "buyer_profile": buyer_profile,
            "supply_pipeline_risk": supply_risk,
            "market_trend_analysis": trend_analysis,
            "is_llm_powered": is_llm_powered,
        }

    async def _analyze_market_trends(self, city: str, locality: str,
                                      city_tier: int, sub_type: str,
                                      listings: int, s_ds: float,
                                      base_value: float) -> dict:
        system = """You are an Indian real estate market analyst. Analyze the supply-demand
dynamics for a specific locality. Provide insights on market trends, buyer profiles,
and liquidity outlook. Respond with JSON only."""

        user = f"""Analyze market dynamics for:
City: {city} (Tier {city_tier}), Locality: {locality}
Property type: {sub_type}
Active listings within 1km: {listings}
Supply-demand score: {s_ds:.3f} (1=instant sale, 0=illiquid)
Base value estimate: ₹{base_value:,.0f}

Provide JSON:
{{
  "price_momentum": "<strongly_appreciating|appreciating|stable|correcting|declining>",
  "absorption_rate_assessment": "<fast|normal|slow|stagnant>",
  "buyer_profile": "<end_users|investors|mixed|institutional>",
  "supply_pipeline_risk": "<low|moderate|high>",
  "fungibility_score": <float 0-1, how easily this type sells here>,
  "market_liquidity_window": "<strong_sellers|balanced|weak_buyers|distressed>",
  "key_demand_drivers": ["<driver1>", "<driver2>"],
  "key_supply_concerns": ["<concern1>", "<concern2>"],
  "expected_days_to_first_offer": <int>,
  "negotiation_discount_pct": <float, typical % below asking>
}}"""

        return await call_claude_json(system, user)

    @staticmethod
    def _rule_fungibility(sub_type: str, city_tier: int) -> float:
        base = {"apartment": 0.80, "villa": 0.55, "plot": 0.50,
                "shop": 0.65, "warehouse": 0.35, "office": 0.55, "other": 0.40}
        tier_adj = {1: 1.0, 2: 0.85, 3: 0.70}
        return base.get(sub_type, 0.50) * tier_adj.get(city_tier, 0.70)
