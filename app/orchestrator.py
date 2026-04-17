"""
DAG-based orchestrator — 11 agents with robust error handling.
If any agent fails, downstream agents get safe defaults instead of crashing.
"""
import asyncio
import time
from app.agents.input_normalizer import InputNormalizerAgent
from app.agents.location_intel import LocationIntelAgent
from app.agents.property_char import PropertyCharAgent
from app.agents.market_dynamics import MarketDynamicsAgent
from app.agents.legal import LegalAgent
from app.agents.comparable_analysis import ComparableAnalysisAgent
from app.agents.macro_context import MacroContextAgent
from app.agents.valuation import ValuationAgent
from app.agents.liquidity import LiquidityAgent
from app.agents.fraud import FraudAgent
from app.agents.synthesizer import SynthesizerAgent

SAFE_LOCATION = {
    "circle_rate_per_sqft": 5000, "circle_rate_match": "fallback",
    "infra_score": 0.3, "neighborhood_quality": 0.5, "city_tier": 3,
    "city": "", "locality": "", "state": "", "district": "",
    "mcr": 1.10, "mcr_source": "fallback", "rule_based_mcr": 1.10,
    "llm_mcr": {}, "micro_bucket": "peripheral", "f_loc": 1.0,
    "poi_breakdown": {}, "poi_counts": {"n_residential": 5, "n_commercial": 3, "n_industrial": 1},
    "micro_market_intelligence": {}, "is_llm_powered": False,
}

SAFE_PROPERTY = {
    "f_age": 0.90, "f_age_raw": 0.90, "f_age_condition_adjustment": 1.0,
    "f_cfg": 1.0, "f_floor": 1.0, "delta": 0.0, "mode_area": 900,
    "visual_condition": 0.75, "condition_grade": "fair",
    "likely_issues": [], "structural_risk": "low",
    "maintenance_estimate_pct": 0, "expected_remaining_life_years": 40,
    "vintage_bracket": "mid_age", "is_llm_powered": False,
}

SAFE_MARKET = {
    "active_listings_1km": 10, "supply_density": 0.5,
    "asset_fungibility": 0.5, "price_momentum": "stable",
    "median_comparable_price": None, "comparable_prices": [],
    "source": "fallback", "is_llm_powered": False,
    "absorption_assessment": "normal", "buyer_profile": "mixed",
    "supply_pipeline_risk": "moderate", "market_trend_analysis": {},
}

SAFE_LEGAL = {"f_legal": 0.95, "s_legal": 0.85, "ownership": "unknown",
              "title_status": "unknown", "legal_multiplier": 0.95, "warnings": []}

SAFE_MACRO = {"macro_adjustment_factor": 1.0, "seasonal_factor": 1.0,
              "is_llm_powered": False, "interest_rate_environment": "moderate",
              "market_cycle_position": "mid", "cycle_factor": 1.0,
              "repo_rate_impact": 1.0, "yoy_price_trend_pct": 4.0,
              "market_sentiment": "stable", "macro_risks": [], "macro_tailwinds": []}

SAFE_COMPARABLE = {"v2_comparable_estimate": None, "confidence": 0, "is_llm_powered": False}


def _safe_result(result, default):
    """Return agent result if valid, otherwise return safe default."""
    if isinstance(result, Exception):
        return {**default, "status": "error", "reason": str(result)}
    if isinstance(result, dict) and result.get("status") == "error":
        return {**default, **result}
    return result


async def run_pipeline(input_data: dict) -> dict:
    ctx = {"input": input_data}
    start = time.time()

    # Step 1: Input normalization
    normalizer = InputNormalizerAgent()
    try:
        ctx[normalizer.name] = await normalizer.run(ctx)
    except Exception as e:
        ctx[normalizer.name] = {"lat": None, "lon": None, "address": input_data.get("address", ""),
                                 "missing_fields": ["geocoding_failed"], "status": "degraded"}

    # Step 2: Location + Legal in parallel
    loc_result, legal_result = await asyncio.gather(
        LocationIntelAgent().run(ctx),
        LegalAgent().run(ctx),
        return_exceptions=True,
    )
    ctx["location_intel"] = _safe_result(loc_result, SAFE_LOCATION)
    ctx["legal"] = _safe_result(legal_result, SAFE_LEGAL)

    # Step 3: PropertyChar + MarketDynamics + MacroContext in parallel
    prop_result, market_result, macro_result = await asyncio.gather(
        PropertyCharAgent().run(ctx),
        MarketDynamicsAgent().run(ctx),
        MacroContextAgent().run(ctx),
        return_exceptions=True,
    )
    ctx["property_char"] = _safe_result(prop_result, SAFE_PROPERTY)
    ctx["market_dynamics"] = _safe_result(market_result, SAFE_MARKET)
    ctx["macro_context"] = _safe_result(macro_result, SAFE_MACRO)

    # Step 4: Comparable analysis
    try:
        ctx["comparable_analysis"] = await ComparableAnalysisAgent().run(ctx)
    except Exception as e:
        ctx["comparable_analysis"] = {**SAFE_COMPARABLE, "status": "error", "reason": str(e)}

    # Step 5: Valuation
    try:
        ctx["valuation"] = await ValuationAgent().run(ctx)
    except Exception as e:
        raise ValueError(f"Valuation failed: {e}")

    # Step 6: Liquidity
    try:
        ctx["liquidity"] = await LiquidityAgent().run(ctx)
    except Exception as e:
        raise ValueError(f"Liquidity failed: {e}")

    # Step 7: Fraud detection
    try:
        ctx["fraud"] = await FraudAgent().run(ctx)
    except Exception as e:
        ctx["fraud"] = {"flags": [], "fraud_score": 0, "is_llm_powered": False,
                        "checks_performed": [], "overall_risk": "unknown"}

    # Step 8: Synthesis
    try:
        result = await SynthesizerAgent().run(ctx)
    except Exception as e:
        raise ValueError(f"Synthesis failed: {e}")

    result["_meta"] = {
        "pipeline_time_seconds": round(time.time() - start, 3),
        "agents_executed": 11,
        "dag_version": "v2_robust",
    }
    return result
