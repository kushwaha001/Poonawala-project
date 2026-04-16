"""
LLM Reasoning Engine — Ollama/Gemma4 (local) with data-grounded prompts.

DESIGN PRINCIPLES:
  1. LLM NEVER generates facts. It reasons about data WE provide.
  2. Every prompt includes the real data (from CSVs, OSM, agent outputs).
  3. Every response must follow a strict JSON schema.
  4. Math stays deterministic — LLM only adjusts within bounded ranges.
  5. Fallback to rule-based defaults if LLM is unavailable.
"""
import os
import json
import httpx

OLLAMA_BASE = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60"))


async def _call_ollama(system: str, user: str, temperature: float = 0.2) -> str:
    """Raw Ollama call via its OpenAI-compatible endpoint."""
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(
                f"{OLLAMA_BASE}/v1/chat/completions",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": temperature,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception:
        return ""


def _parse_json(raw: str) -> dict | None:
    """Extract JSON from LLM response, handling markdown fences."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines) - 1
        for i, line in enumerate(lines[1:], 1):
            if line.strip().startswith("```"):
                end = i
                break
        text = "\n".join(lines[start:end])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


async def call_llm(system: str, user: str, temperature: float = 0.2) -> str:
    """Call local Gemma4 for text reasoning. Returns raw string."""
    result = await _call_ollama(system, user, temperature)
    return result if result else ""


async def call_llm_json(system: str, user: str, schema: dict,
                         temperature: float = 0.1) -> dict:
    """
    Call Gemma4 with strict JSON schema enforcement.
    The schema is embedded in the prompt so the model knows exactly
    what fields to produce. Falls back to defaults if parsing fails.
    """
    schema_str = json.dumps(schema, indent=2)
    enforced_system = f"""{system}

STRICT OUTPUT RULES:
- You MUST respond with ONLY valid JSON. No markdown, no explanation outside JSON.
- Your response MUST exactly follow this JSON schema:
{schema_str}
- Every field is required. Use the types shown.
- Do NOT add extra fields. Do NOT omit any field.
- Base your response ONLY on the data provided. Do NOT invent facts."""

    raw = await _call_ollama(enforced_system, user, temperature)
    parsed = _parse_json(raw)
    if parsed and _validate_schema(parsed, schema):
        return parsed
    return None


def _validate_schema(data: dict, schema: dict) -> bool:
    """Basic check that all required keys from schema are present."""
    for key in schema:
        if key not in data:
            return False
    return True


# ─── SCHEMAS: Strict JSON contracts for each reasoning task ─────────

SCHEMA_MICRO_MARKET = {
    "market_premium_estimate": 1.5,
    "market_premium_reasoning": "string",
    "demand_profile": "string",
    "price_trend": "string",
    "micro_market_risks": ["string"],
    "micro_market_strengths": ["string"],
    "liquidity_assessment": "string",
    "confidence_in_analysis": 0.5,
}

SCHEMA_DYNAMIC_MCR = {
    "estimated_mcr": 1.5,
    "mcr_reasoning": "string",
    "confidence": 0.5,
    "market_maturity": "string",
}

SCHEMA_CONDITION = {
    "condition_score": 0.75,
    "condition_grade": "string",
    "likely_issues": ["string"],
    "structural_risk": "string",
    "maintenance_estimate_pct": 0.0,
    "expected_remaining_life_years": 30,
}

SCHEMA_MARKET_TRENDS = {
    "price_momentum": "string",
    "absorption_rate_assessment": "string",
    "buyer_profile": "string",
    "supply_pipeline_risk": "string",
    "fungibility_score": 0.5,
    "negotiation_discount_pct": 5.0,
}

SCHEMA_COMPARABLES = {
    "estimated_value_per_sqft": 10000,
    "value_reasoning": "string",
    "market_value_estimate": 1000000,
    "confidence": 0.5,
    "value_range_low": 900000,
    "value_range_high": 1100000,
}

SCHEMA_ANOMALIES = {
    "anomalies_detected": [{"anomaly": "string", "severity": "string", "reasoning": "string"}],
    "overall_risk_level": "string",
    "recommendation": "string",
}

SCHEMA_SYNTHESIS = {
    "explanation": "string",
    "agent_agreement_assessment": "string",
    "collateral_recommendation": "string",
    "recommended_ltv_pct": 70,
    "ltv_reasoning": "string",
    "additional_diligence_needed": ["string"],
    "scenario_assessment": {
        "optimistic": "string",
        "pessimistic": "string",
        "most_likely": "string",
    },
}


# ─── DATA-GROUNDED REASONING FUNCTIONS ──────────────────────────────
# Every function below injects REAL DATA into the prompt.
# The LLM reasons about our data — it never generates facts.

async def analyze_micro_market(city: str, locality: str, property_type: str,
                                sub_type: str, city_tier: int,
                                poi_data: dict, area_sqft: float) -> dict:
    system = """You are a real estate analyst. You will be given ACTUAL DATA about a
property location — POI distances, city tier, and property details.
Based ONLY on this data, reason about the micro-market quality.
Do NOT invent any facts. Only interpret the numbers given."""

    user = f"""Here is the ACTUAL DATA for this property location:

LOCATION: {locality}, {city} (Tier {city_tier})
PROPERTY: {property_type} / {sub_type}, {area_sqft} sqft

MEASURED POI DISTANCES (from OpenStreetMap):
{json.dumps(poi_data, indent=2)}

REASONING TASK:
Based on these measured distances, assess:
- market_premium_estimate: float between 1.0-2.5 (how much market exceeds circle rate)
  Tier 1 prime locations with close POIs → 1.8-2.5
  Tier 1 standard → 1.4-1.8
  Tier 2 → 1.1-1.6
  Tier 3 → 1.0-1.3
- demand_profile: one of "high_demand", "moderate_demand", "low_demand", "niche"
- price_trend: one of "appreciating", "stable", "correcting"
- micro_market_risks: list of risks based on the data
- micro_market_strengths: list of strengths based on the data
- liquidity_assessment: one of "high", "moderate", "low"
- confidence_in_analysis: float 0-1 (how confident based on data completeness)"""

    result = await call_llm_json(system, user, SCHEMA_MICRO_MARKET)
    if result and "market_premium_estimate" in result:
        return result
    return _default_micro_market(city_tier)


async def estimate_dynamic_mcr(city: str, locality: str, city_tier: int,
                                infra_score: float, sub_type: str,
                                rule_mcr: float, circle_rate: float) -> dict:
    system = """You are estimating the Market-to-Circle Ratio (MCR) for an Indian property.
MCR = actual market price / government circle rate.
You are given the ACTUAL circle rate, infrastructure score, and rule-based MCR.
Adjust the MCR based on the data. Stay within the bounded range."""

    user = f"""ACTUAL DATA:
- City: {city}, Locality: {locality} (Tier {city_tier})
- Circle rate: ₹{circle_rate:,}/sqft (government published)
- Infrastructure score: {infra_score:.3f} (0-1, computed from OSM POI distances)
- Rule-based MCR: {rule_mcr} (from our lookup table)
- Property type: {sub_type}

MCR BOUNDS (you MUST stay within these):
- Tier 1: 1.30 to 2.20
- Tier 2: 1.10 to 1.60
- Tier 3: 1.05 to 1.20

TASK: Given infra_score {infra_score:.3f} and tier {city_tier}, estimate MCR.
Higher infra_score → higher MCR. The rule_mcr is {rule_mcr} — you can adjust ±15%.
- estimated_mcr: float (within bounds above)
- mcr_reasoning: why this MCR based on the data
- confidence: float 0-1
- market_maturity: one of "mature", "developing", "emerging", "nascent" """

    result = await call_llm_json(system, user, SCHEMA_DYNAMIC_MCR)
    if result and "estimated_mcr" in result:
        mcr = result["estimated_mcr"]
        bounds = {1: (1.30, 2.20), 2: (1.10, 1.60), 3: (1.05, 1.20)}
        lo, hi = bounds.get(city_tier, (1.05, 2.20))
        result["estimated_mcr"] = max(lo, min(hi, mcr))
        return result
    return {"estimated_mcr": rule_mcr, "mcr_reasoning": "rule-based fallback",
            "confidence": 0.0, "market_maturity": "unknown", "fallback": True}


async def assess_property_condition(age_years: int, sub_type: str,
                                     config: str = None, area_sqft: float = 0) -> dict:
    system = """You are assessing the physical condition of an Indian property.
You are given the ACTUAL age and type. Based on typical Indian construction
quality and maintenance patterns for this property type/age, estimate condition.
Do NOT invent specific defects. Only reason about what is TYPICAL for this age/type."""

    user = f"""ACTUAL PROPERTY DATA:
- Type: {sub_type}
- Age: {age_years} years
- Configuration: {config or 'not specified'}
- Area: {area_sqft} sqft

TYPICAL INDIAN CONSTRUCTION PATTERNS:
- New (<3yr): Excellent condition, no issues
- 3-10yr: Good, minor wear
- 10-20yr: Fair, waterproofing/plumbing issues common
- 20-30yr: Needs maintenance, structural checks recommended
- 30-50yr: Major repairs likely, reinforcement may be needed
- 50+yr: Redevelopment candidate in many cases

TASK: Based on the age ({age_years} years) and type ({sub_type}), estimate:
- condition_score: float 0-1 (1=excellent)
- condition_grade: one of "excellent", "good", "fair", "poor", "dilapidated"
- likely_issues: list of typical issues for this age (from patterns above, not invented)
- structural_risk: one of "low", "medium", "high"
- maintenance_estimate_pct: float (% of value needed for repairs)
- expected_remaining_life_years: int"""

    result = await call_llm_json(system, user, SCHEMA_CONDITION)
    if result and "condition_score" in result:
        score = result["condition_score"]
        if not isinstance(score, (int, float)):
            score = 0.75
        result["condition_score"] = max(0.0, min(1.0, float(score)))
        return result
    return _default_condition(age_years, sub_type)


async def analyze_market_trends(city: str, locality: str, city_tier: int,
                                 sub_type: str, listings_1km: int,
                                 supply_demand_score: float,
                                 base_value: float) -> dict:
    system = """You are analyzing real estate market dynamics.
You are given ACTUAL measured data: listing counts, supply-demand score, and base value.
Reason about market trends based ONLY on these numbers."""

    user = f"""ACTUAL MARKET DATA:
- Location: {locality}, {city} (Tier {city_tier})
- Property type: {sub_type}
- Active listings within 1km: {listings_1km}
- Supply-demand score: {supply_demand_score:.3f} (1.0=instant sale, 0.0=illiquid)
- Base value estimate: ₹{base_value:,.0f}

INTERPRETATION GUIDE:
- S_ds > 0.7: Sellers' market (low inventory)
- S_ds 0.4-0.7: Balanced market
- S_ds < 0.4: Buyers' market (oversupply)
- Listings > 30 in Tier 1: Normal supply
- Listings < 10: Thin market (less price discovery)

TASK: Based on this measured data:
- price_momentum: one of "appreciating", "stable", "correcting", "declining"
- absorption_rate_assessment: one of "fast", "normal", "slow", "stagnant"
- buyer_profile: one of "end_users", "investors", "mixed"
- supply_pipeline_risk: one of "low", "moderate", "high"
- fungibility_score: float 0-1 (standard apt in Tier 1 → 0.7-0.9, niche warehouse → 0.2-0.4)
- negotiation_discount_pct: float (typical % below asking price, 3-15%)"""

    result = await call_llm_json(system, user, SCHEMA_MARKET_TRENDS)
    if result and "price_momentum" in result:
        return result
    return _default_market_trends(city_tier, sub_type)


async def analyze_comparables(city: str, locality: str, sub_type: str,
                               area_sqft: float, age_years: int,
                               circle_rate: float, listing_data: dict) -> dict:
    system = """You are conducting comparable property analysis.
You are given ACTUAL circle rate data and listing data from our database.
Estimate fair value based ONLY on these numbers. Do NOT invent comparable prices."""

    user = f"""ACTUAL DATA:
- Location: {locality}, {city}
- Type: {sub_type}, {area_sqft} sqft, {age_years} years old
- Government circle rate: ₹{circle_rate:,}/sqft
- City tier: {listing_data.get('city_tier', 2)}

LISTING DATA FROM OUR DATABASE:
- Active listings within 1km: {listing_data.get('active_listings_1km', 0)}
- Comparable prices (from our data): {listing_data.get('comparable_prices', [])}
- Median comparable: ₹{listing_data.get('median_comparable_price', 0):,}
- Circle rate base value: ₹{listing_data.get('circle_rate_base_value', 0):,}

TASK: Using ONLY the data above, estimate:
- estimated_value_per_sqft: int (must be between circle_rate and circle_rate × 2.5)
- value_reasoning: explain using the actual numbers above
- market_value_estimate: int (= estimated_value_per_sqft × {area_sqft})
- confidence: float 0-1 (higher if more comparables available)
- value_range_low: int (estimate × 0.90)
- value_range_high: int (estimate × 1.10)"""

    result = await call_llm_json(system, user, SCHEMA_COMPARABLES)
    if result and "market_value_estimate" in result:
        return result
    return {"fallback": True, "confidence": 0.0}


async def detect_anomalies(property_data: dict, agent_outputs: dict) -> dict:
    system = """You are a fraud detection specialist reviewing a property loan application.
You are given the ACTUAL property data and all agent analysis results.
Look for INCONSISTENCIES between the numbers — not external facts."""

    loc = agent_outputs.get("location_intel", {})
    prop = agent_outputs.get("property_char", {})
    legal = agent_outputs.get("legal", {})
    market = agent_outputs.get("market_dynamics", {})

    user = f"""ACTUAL APPLICATION DATA:
Property input:
  - Address: {property_data.get('address', 'N/A')}
  - Type: {property_data.get('property_type')} / {property_data.get('sub_type')}
  - Area: {property_data.get('built_up_area_sqft')} sqft
  - Age: {property_data.get('age_years')} years
  - Configuration: {property_data.get('configuration', 'N/A')}
  - Ownership: {property_data.get('ownership', 'N/A')}
  - Title clear: {property_data.get('title_clear', 'N/A')}
  - Monthly rent: ₹{property_data.get('monthly_rent', 0) or 0:,}

COMPUTED AGENT DATA:
  - Circle rate: ₹{loc.get('circle_rate_per_sqft', 0):,}/sqft
  - MCR: {loc.get('mcr', 0)}
  - City tier: {loc.get('city_tier', 0)}
  - Infra score: {loc.get('infra_score', 0)}
  - f_age: {prop.get('f_age', 0)}
  - f_cfg: {prop.get('f_cfg', 0)}
  - f_legal: {legal.get('f_legal', 0)}
  - Active listings: {market.get('active_listings_1km', 0)}

CHECK FOR THESE INCONSISTENCIES:
1. Rent vs value: If rent is given, yield should be 2-8%. Outside → suspicious.
2. Area vs config: 4BHK in <500sqft is impossible.
3. Age vs claimed condition: 50yr building claimed as "new" is suspicious.
4. Type vs location: Warehouse in purely residential area.
5. Any numbers that don't add up.

TASK: List anomalies found (only real inconsistencies in the data above):
- anomalies_detected: list of {{anomaly, severity (low/medium/high), reasoning}}
- overall_risk_level: one of "low", "medium", "high"
- recommendation: one of "proceed", "proceed_with_caution", "flag_for_review" """

    result = await call_llm_json(system, user, SCHEMA_ANOMALIES)
    if result and "anomalies_detected" in result:
        return result
    return {"anomalies_detected": [], "overall_risk_level": "low",
            "recommendation": "proceed", "fallback": True}


async def synthesize_valuation(all_outputs: dict, property_input: dict) -> dict:
    system = """You are a senior credit analyst writing a valuation summary.
You are given ALL computed data from 11 agents. Summarize the findings.
Reference ONLY the actual numbers provided. Do NOT invent any data."""

    val = all_outputs.get("valuation_summary", {})
    liq = all_outputs.get("liquidity_summary", {})
    fraud = all_outputs.get("fraud_summary", {})
    loc = all_outputs.get("location_intel", {})

    user = f"""COMPLETE VALUATION DATA (from 11 agents):

Property: {property_input.get('address', 'N/A')}, {property_input.get('sub_type')}, {property_input.get('built_up_area_sqft')} sqft, {property_input.get('age_years')} years

VALUATION RESULTS:
- Market value range: ₹{val.get('mv_range', [0,0])[0]:,} to ₹{val.get('mv_range', [0,0])[1]:,}
- Point estimate: ₹{val.get('point_estimate', 0):,}
- Confidence: {val.get('confidence', 0)}
- Circle rate: ₹{loc.get('circle_rate_per_sqft', 0):,}/sqft
- MCR: {loc.get('mcr', 0)} ({loc.get('micro_bucket', '')})

LIQUIDITY:
- RPI: {liq.get('rpi', 0)}/100
- Time to sell: {liq.get('ttl', [0,0])} days
- Distress range: ₹{liq.get('distress_range', [0,0])[0]:,} to ₹{liq.get('distress_range', [0,0])[1]:,}

FRAUD: {fraud.get('flags', 'none')} | Risk: {fraud.get('overall_risk', 'low')}

TASK: Write a concise summary referencing ONLY these numbers:
- explanation: 3-4 sentences about valuation + liquidity
- agent_agreement_assessment: one of "strong", "moderate", "weak"
- collateral_recommendation: one of "strong_accept", "accept", "conditional_accept", "review_needed", "reject"
- recommended_ltv_pct: int 50-80 (higher confidence+RPI → higher LTV)
- ltv_reasoning: one sentence justification
- additional_diligence_needed: list of items if any
- scenario_assessment: {{optimistic, pessimistic, most_likely}} — one sentence each"""

    result = await call_llm_json(system, user, SCHEMA_SYNTHESIS)
    if result and "explanation" in result:
        return result
    return {"fallback": True}


# ─── FALLBACK DEFAULTS (when LLM is unavailable) ───────────────────

def _default_micro_market(city_tier: int) -> dict:
    defaults = {
        1: {"market_premium_estimate": 1.70, "market_premium_reasoning": "rule-based Tier 1 default",
            "demand_profile": "moderate_demand", "price_trend": "stable",
            "micro_market_risks": ["market_cycle_risk"], "micro_market_strengths": ["metro_connectivity"],
            "liquidity_assessment": "moderate", "confidence_in_analysis": 0.3, "fallback": True},
        2: {"market_premium_estimate": 1.30, "market_premium_reasoning": "rule-based Tier 2 default",
            "demand_profile": "moderate_demand", "price_trend": "stable",
            "micro_market_risks": ["limited_demand_pool"], "micro_market_strengths": ["affordability"],
            "liquidity_assessment": "moderate", "confidence_in_analysis": 0.2, "fallback": True},
        3: {"market_premium_estimate": 1.10, "market_premium_reasoning": "rule-based Tier 3 default",
            "demand_profile": "low_demand", "price_trend": "stable",
            "micro_market_risks": ["thin_market"], "micro_market_strengths": ["low_competition"],
            "liquidity_assessment": "low", "confidence_in_analysis": 0.15, "fallback": True},
    }
    return defaults.get(city_tier, defaults[3])


def _default_condition(age: int, sub_type: str) -> dict:
    if age <= 3: score, grade, risk = 0.90, "excellent", "low"
    elif age <= 10: score, grade, risk = 0.75, "good", "low"
    elif age <= 20: score, grade, risk = 0.60, "fair", "medium"
    elif age <= 35: score, grade, risk = 0.45, "poor", "medium"
    else: score, grade, risk = 0.30, "dilapidated", "high"

    return {"condition_score": score, "condition_grade": grade,
            "likely_issues": ["age-related wear"], "structural_risk": risk,
            "maintenance_estimate_pct": min(15, age * 0.3),
            "expected_remaining_life_years": max(5, 60 - age), "fallback": True}


def _default_market_trends(city_tier: int, sub_type: str) -> dict:
    fung = {"apartment": 0.7, "villa": 0.5, "plot": 0.45, "shop": 0.55,
            "warehouse": 0.3, "office": 0.5}.get(sub_type, 0.5)
    tier_adj = {1: 1.0, 2: 0.85, 3: 0.70}.get(city_tier, 0.7)
    return {"price_momentum": "stable", "absorption_rate_assessment": "normal",
            "buyer_profile": "mixed", "supply_pipeline_risk": "moderate",
            "fungibility_score": round(fung * tier_adj, 2),
            "negotiation_discount_pct": 5.0, "fallback": True}


# ─── LEGACY COMPATIBILITY (agents call these names) ─────────────────

async def call_claude(system: str, user: str, images: list = None,
                      temperature: float = 0.3, max_tokens: int = 2048) -> str:
    return await call_llm(system, user, temperature)


async def call_claude_json(system: str, user: str, temperature: float = 0.2) -> dict:
    result = await call_llm_json(system, user, {}, temperature)
    return result if result else {"fallback": True}
