"""
MacroContextAgent — Provides macroeconomic and market-cycle context.
Adjusts valuation based on interest rate environment, market cycle position,
regulatory changes, and seasonal patterns. Uses LLM reasoning when available,
falls back to rule-based priors.
"""
import math
from datetime import datetime
from app.agents.base import BaseAgent
from app.tools.llm import call_claude_json


MARKET_CYCLE_PRIORS = {
    1: {"cycle_position": "mid", "yoy_appreciation": 0.05, "sentiment": "cautiously_optimistic"},
    2: {"cycle_position": "mid", "yoy_appreciation": 0.04, "sentiment": "stable"},
    3: {"cycle_position": "early", "yoy_appreciation": 0.03, "sentiment": "neutral"},
}

SEASONAL_FACTORS = {
    1: 0.97, 2: 0.98, 3: 1.02, 4: 1.03,
    5: 0.98, 6: 0.96, 7: 0.95, 8: 0.96,
    9: 0.98, 10: 1.04, 11: 1.05, 12: 1.02,
}

REPO_RATE_IMPACT = {
    "low": 1.03,
    "moderate": 1.00,
    "high": 0.97,
    "very_high": 0.94,
}


class MacroContextAgent(BaseAgent):
    name = "macro_context"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]

        city = loc.get("city", "")
        city_tier = loc["city_tier"]
        sub_type = inp["sub_type"]
        property_type = inp["property_type"]

        current_month = datetime.now().month
        seasonal_factor = SEASONAL_FACTORS.get(current_month, 1.0)

        llm_macro = await self._get_llm_macro_context(city, city_tier, sub_type, property_type)

        if llm_macro and "fallback" not in llm_macro:
            repo_rate_env = llm_macro.get("interest_rate_environment", "moderate")
            cycle_position = llm_macro.get("market_cycle_position", "mid")
            yoy_estimate = llm_macro.get("yoy_price_change_pct", 4) / 100
            market_sentiment = llm_macro.get("market_sentiment", "stable")
            regulatory_impact = llm_macro.get("regulatory_impact_score", 0.0)
            macro_risks = llm_macro.get("macro_risks", [])
            macro_tailwinds = llm_macro.get("macro_tailwinds", [])
            is_llm_powered = True
        else:
            prior = MARKET_CYCLE_PRIORS.get(city_tier, MARKET_CYCLE_PRIORS[3])
            repo_rate_env = "moderate"
            cycle_position = prior["cycle_position"]
            yoy_estimate = prior["yoy_appreciation"]
            market_sentiment = prior["sentiment"]
            regulatory_impact = 0.0
            macro_risks = ["general_market_uncertainty"]
            macro_tailwinds = ["urbanization_trend"]
            is_llm_powered = False

        repo_impact = REPO_RATE_IMPACT.get(repo_rate_env, 1.0)

        cycle_adj = {"boom": 1.05, "mid": 1.00, "correction": 0.95, "trough": 0.92, "early": 1.02}
        cycle_factor = cycle_adj.get(cycle_position, 1.0)

        macro_adjustment = seasonal_factor * repo_impact * cycle_factor
        macro_adjustment = max(0.85, min(1.15, macro_adjustment))

        return {
            "macro_adjustment_factor": round(macro_adjustment, 4),
            "seasonal_factor": seasonal_factor,
            "interest_rate_environment": repo_rate_env,
            "repo_rate_impact": repo_impact,
            "market_cycle_position": cycle_position,
            "cycle_factor": cycle_factor,
            "yoy_price_trend_pct": round(yoy_estimate * 100, 1),
            "market_sentiment": market_sentiment,
            "regulatory_impact": regulatory_impact,
            "macro_risks": macro_risks,
            "macro_tailwinds": macro_tailwinds,
            "current_month": current_month,
            "is_llm_powered": is_llm_powered,
        }

    async def _get_llm_macro_context(self, city: str, city_tier: int,
                                      sub_type: str, property_type: str) -> dict:
        system = """You are an Indian macroeconomic analyst specializing in real estate markets.
Provide current market context for property valuation. Use your knowledge of
RBI policies, interest rates, RERA regulations, and market cycles.
Respond with JSON only."""

        user = f"""Provide macroeconomic context for property valuation:

City: {city} (Tier {city_tier})
Property type: {property_type}, sub-type: {sub_type}
Current date: {datetime.now().strftime('%B %Y')}

Provide JSON:
{{
  "interest_rate_environment": "<low|moderate|high|very_high>",
  "market_cycle_position": "<boom|mid|correction|trough|early>",
  "yoy_price_change_pct": <float, year-over-year change>,
  "market_sentiment": "<bullish|cautiously_optimistic|stable|bearish|uncertain>",
  "regulatory_impact_score": <float -0.1 to 0.1, RERA/policy impact>,
  "macro_risks": ["<risk1>", "<risk2>"],
  "macro_tailwinds": ["<tailwind1>", "<tailwind2>"],
  "liquidity_environment": "<tight|normal|abundant>",
  "infrastructure_pipeline": "<description of upcoming infra projects>"
}}"""

        return await call_claude_json(system, user)
