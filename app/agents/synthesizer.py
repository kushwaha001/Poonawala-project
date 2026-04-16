"""
SynthesizerAgent — UPGRADED to a true reasoning agent.
Resolves conflicts between agents, identifies most reliable signals,
and produces an intelligent, defensible collateral assessment.
"""
from app.agents.base import BaseAgent
from app.tools.llm import synthesize_valuation
from app.math.formulas import (
    confidence_label,
    compute_forced_sale_value, compute_realizable_value, compute_reconstruction_value,
)


class SynthesizerAgent(BaseAgent):
    name = "synthesizer"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        loc = ctx["location_intel"]
        prop = ctx["property_char"]
        market = ctx["market_dynamics"]
        legal = ctx["legal"]
        val = ctx["valuation"]
        liq = ctx["liquidity"]
        fraud = ctx["fraud"]
        comparable = ctx.get("comparable_analysis", {})
        macro = ctx.get("macro_context", {})

        mv_range = val["mv_range"]
        distress_range = liq["distress_value_range"]
        mv_mid = (mv_range[0] + mv_range[1]) / 2
        forced_sale_value    = compute_forced_sale_value(mv_mid)
        realizable_value     = compute_realizable_value(mv_mid)
        reconstruction_value = compute_reconstruction_value(
            inp["built_up_area_sqft"], inp["age_years"], loc["city_tier"], inp["sub_type"]
        )
        rpi = liq["rpi"]
        ttl = liq["estimated_time_to_sell_days"]
        confidence = val["confidence_score"]
        scenarios = val.get("scenarios", {})

        # Key drivers from valuation decomposition
        drivers_raw = val["driver_contributions"]
        key_drivers = []
        for d in drivers_raw[:5]:
            impact_str = f"+{d['impact_pct']}%" if d['impact_pct'] >= 0 else f"{d['impact_pct']}%"
            key_drivers.append({"factor": d["factor"], "impact": impact_str, "source_agent": d["source_agent"]})

        # Add macro context as a driver if significant
        macro_adj = val.get("macro_adjustment_applied", 1.0)
        if abs(macro_adj - 1.0) > 0.01:
            impact_pct = round((macro_adj - 1.0) * 100, 1)
            impact_str = f"+{impact_pct}%" if impact_pct >= 0 else f"{impact_pct}%"
            key_drivers.append({"factor": "macro_economic_adjustment", "impact": impact_str, "source_agent": "macro_context"})

        # Risk flags from all sources
        risk_flags = []
        for f in fraud.get("flags", []):
            risk_flags.append({"flag": f["flag"], "severity": f["severity"],
                             "source_agent": "fraud", "explanation": f.get("explanation", "")})
        for w in legal.get("warnings", []):
            risk_flags.append({"flag": w["flag"], "severity": w["severity"],
                             "source_agent": "legal", "explanation": w.get("explanation", "")})
        if market.get("supply_density", 1) < 0.35:
            risk_flags.append({"flag": "high_micro_market_competition", "severity": "medium",
                             "source_agent": "market_dynamics", "explanation": "High months of inventory"})

        # Micro-market risks from LLM analysis
        mm_intel = loc.get("micro_market_intelligence", {})
        for risk in mm_intel.get("micro_market_risks", []):
            if isinstance(risk, str) and risk:
                risk_flags.append({"flag": f"micro_market_{risk.replace(' ', '_').lower()[:40]}",
                                 "severity": "low", "source_agent": "location_intel",
                                 "explanation": risk})

        # Macro risks
        for risk in macro.get("macro_risks", []):
            if isinstance(risk, str) and risk:
                risk_flags.append({"flag": f"macro_{risk.replace(' ', '_').lower()[:40]}",
                                 "severity": "low", "source_agent": "macro_context",
                                 "explanation": risk})

        # LLM-POWERED SYNTHESIS — true reasoning about the valuation
        all_outputs = {
            "location_intel": {k: v for k, v in loc.items() if k != "micro_market_intelligence"},
            "property_char": prop,
            "market_dynamics": {k: v for k, v in market.items() if k != "market_trend_analysis"},
            "legal": legal,
            "valuation_summary": {
                "point_estimate": val["point_estimate"],
                "mv_range": mv_range,
                "confidence": confidence,
                "scenarios": scenarios,
                "independent_estimates": val.get("independent_estimates", {}),
            },
            "liquidity_summary": {
                "rpi": rpi, "ttl": ttl, "distress_range": distress_range,
            },
            "fraud_summary": {
                "flags": [f["flag"] for f in fraud.get("flags", [])],
                "overall_risk": fraud.get("overall_risk", "low"),
            },
            "comparable_summary": {
                "v2_estimate": comparable.get("v2_comparable_estimate"),
                "confidence": comparable.get("confidence", 0),
            },
            "macro_summary": {
                "adjustment": macro_adj,
                "cycle": macro.get("market_cycle_position"),
                "sentiment": macro.get("market_sentiment"),
            },
        }

        llm_synthesis = await synthesize_valuation(all_outputs, inp)
        is_llm_powered = "fallback" not in llm_synthesis

        if is_llm_powered:
            explanation = llm_synthesis.get("explanation", "")
            collateral_recommendation = llm_synthesis.get("collateral_recommendation", "review_needed")
            recommended_ltv = llm_synthesis.get("recommended_ltv_pct", 70)
            ltv_reasoning = llm_synthesis.get("ltv_reasoning", "")
            additional_diligence = llm_synthesis.get("additional_diligence_needed", [])
            scenario_narrative = llm_synthesis.get("scenario_assessment", {})
        else:
            explanation = self._build_template_explanation(inp, loc, prop, val, liq, macro)
            collateral_recommendation = self._rule_based_recommendation(confidence, rpi, fraud)
            recommended_ltv = self._rule_based_ltv(confidence, rpi)
            ltv_reasoning = f"Based on confidence {confidence:.2f} and RPI {rpi}"
            additional_diligence = []
            scenario_narrative = {}

        if not explanation or len(explanation) < 20:
            explanation = self._build_template_explanation(inp, loc, prop, val, liq, macro)

        # Agent trace — full audit trail
        agent_trace = {
            "input_normalizer": ctx["input_normalizer"],
            "location_intel": loc,
            "property_char": prop,
            "market_dynamics": market,
            "legal": legal,
            "valuation": val,
            "liquidity": liq,
            "fraud": fraud,
            "comparable_analysis": comparable,
            "macro_context": macro,
        }

        # Count how many agents used LLM reasoning
        llm_powered_agents = [k for k in ["location_intel", "property_char", "market_dynamics",
                                           "fraud", "comparable_analysis", "macro_context"]
                               if ctx.get(k, {}).get("is_llm_powered", False)]

        # Build rich insight panels for the frontend
        insights = self._build_insights(inp, loc, prop, market, legal, val, liq, fraud, comparable, macro)

        return {
            "market_value_range": mv_range,
            "distress_value_range": distress_range,
            "forced_sale_value": forced_sale_value,
            "realizable_value": realizable_value,
            "reconstruction_value": reconstruction_value,
            "resale_potential_index": rpi,
            "estimated_time_to_sell_days": ttl,
            "confidence_score": round(confidence, 2),
            "key_drivers": key_drivers,
            "risk_flags": risk_flags,
            "explanation": explanation,
            "scenarios": scenarios,
            "collateral_recommendation": collateral_recommendation,
            "recommended_ltv_pct": recommended_ltv,
            "ltv_reasoning": ltv_reasoning,
            "additional_diligence": additional_diligence,
            "scenario_narrative": scenario_narrative,
            "insights": insights,
            "agent_trace": agent_trace,
            "intelligence_summary": {
                "total_agents": 11,
                "llm_powered_agents": llm_powered_agents,
                "llm_agent_count": len(llm_powered_agents),
                "is_llm_synthesis": is_llm_powered,
            },
        }

    @staticmethod
    def _build_template_explanation(inp, loc, prop, val, liq, macro):
        macro_adj = macro.get("macro_adjustment_factor", 1.0) if macro else 1.0
        macro_note = ""
        if abs(macro_adj - 1.0) > 0.01:
            direction = "upward" if macro_adj > 1.0 else "downward"
            macro_note = f" A {direction} macro adjustment of {macro_adj:.1%} reflects current market conditions."

        return (
            f"This {inp['sub_type']} in {loc.get('city', 'the area')} ({loc.get('locality', '')}) is valued at "
            f"₹{val['mv_range'][0]:,}–₹{val['mv_range'][1]:,} based on circle rate ₹{loc['circle_rate_per_sqft']:,}/sqft "
            f"with MCR {loc['mcr']}x (Tier-{loc['city_tier']} {loc['micro_bucket']} market). "
            f"The {prop['vintage_bracket']} building ({inp['age_years']} years) applies a {prop['f_age']:.1%} age factor. "
            f"Resale potential index of {liq['rpi']} ({liq['rpi_label']}) suggests a "
            f"{liq['estimated_time_to_sell_days'][0]}–{liq['estimated_time_to_sell_days'][1]} day sale window. "
            f"Confidence: {confidence_label(val['confidence_score'])} ({val['confidence_score']:.0%}).{macro_note}"
        )

    @staticmethod
    def _rule_based_recommendation(confidence, rpi, fraud):
        if fraud.get("overall_risk") == "high" or any(f["severity"] == "high" for f in fraud.get("flags", [])):
            return "review_needed"
        if confidence >= 0.80 and rpi >= 60:
            return "strong_accept"
        if confidence >= 0.65 and rpi >= 40:
            return "accept"
        if confidence >= 0.50:
            return "conditional_accept"
        return "review_needed"

    @staticmethod
    def _rule_based_ltv(confidence, rpi):
        if rpi >= 80 and confidence >= 0.85:
            return 80
        if rpi >= 60 and confidence >= 0.70:
            return 70
        if rpi >= 40 and confidence >= 0.50:
            return 60
        return 50

    @staticmethod
    def _build_insights(inp, loc, prop, market, legal, val, liq, fraud, comparable, macro):
        """Build rich insight panels from all agent data."""
        mm = loc.get("micro_market_intelligence", {})
        cond = prop

        # Location insight
        poi = loc.get("poi_breakdown", {})
        strengths = mm.get("micro_market_strengths", [])
        risks = mm.get("micro_market_risks", [])
        location_insight = {
            "title": "Location Intelligence",
            "city": loc.get("city", ""), "locality": loc.get("locality", ""),
            "tier": loc.get("city_tier", 3), "bucket": loc.get("micro_bucket", ""),
            "infra_score": loc.get("infra_score", 0),
            "neighborhood_quality": loc.get("neighborhood_quality", 0),
            "poi_summary": {k.replace("_dist_km", ""): v for k, v in poi.items() if "_dist_km" in k},
            "strengths": strengths[:3] if isinstance(strengths, list) else [],
            "risks": risks[:3] if isinstance(risks, list) else [],
            "demand_profile": mm.get("demand_profile", "moderate_demand"),
            "price_trend": mm.get("price_trend", "stable"),
        }

        # Property insight
        property_insight = {
            "title": "Property Assessment",
            "vintage": cond.get("vintage_bracket", ""),
            "condition_grade": cond.get("condition_grade", "fair"),
            "condition_score": cond.get("visual_condition", 0.75),
            "structural_risk": cond.get("structural_risk", "low"),
            "likely_issues": cond.get("likely_issues", [])[:3] if isinstance(cond.get("likely_issues"), list) else [],
            "maintenance_pct": cond.get("maintenance_estimate_pct", 0),
            "remaining_life_years": cond.get("expected_remaining_life_years", 40),
            "age_impact_pct": round((cond.get("f_age", 1) - 1) * 100, 1),
            "config_impact_pct": round((cond.get("f_cfg", 1) - 1) * 100, 1),
        }

        # Market insight
        mkt_trends = market.get("market_trend_analysis", {})
        market_insight = {
            "title": "Market Dynamics",
            "listings_nearby": market.get("active_listings_1km", 0),
            "supply_demand_score": market.get("supply_density", 0.5),
            "fungibility": market.get("asset_fungibility", 0.5),
            "price_momentum": mkt_trends.get("price_momentum", market.get("price_momentum", "stable")),
            "buyer_profile": mkt_trends.get("buyer_profile", "mixed"),
            "absorption": mkt_trends.get("absorption_rate_assessment", "normal"),
            "supply_risk": mkt_trends.get("supply_pipeline_risk", "moderate"),
            "negotiation_discount": mkt_trends.get("negotiation_discount_pct", 5),
        }

        # Fraud insight
        all_flags = fraud.get("flags", [])
        rule_flags = fraud.get("rule_based_flags", all_flags)
        llm_flags = fraud.get("llm_detected_flags", [])
        fraud_insight = {
            "title": "Fraud & Risk Analysis",
            "total_flags": len(all_flags),
            "rule_based_count": len(rule_flags),
            "llm_detected_count": len(llm_flags),
            "overall_risk": fraud.get("overall_risk", "low"),
            "fraud_score": fraud.get("fraud_score", 0),
            "checks_performed": fraud.get("checks_performed", []),
            "recommendation": fraud.get("llm_recommendation", "proceed"),
            "flags_detail": [{"flag": f.get("flag",""), "severity": f.get("severity","low"),
                             "explanation": f.get("explanation",""), "source": "rule-based"}
                            for f in rule_flags] +
                           [{"flag": f.get("flag",""), "severity": f.get("severity","low"),
                             "explanation": f.get("explanation",""), "source": "AI-detected"}
                            for f in llm_flags],
        }

        # Investment insight
        rpi_val = liq.get("rpi", 50)
        conf_val = val.get("confidence_score", 0.5)
        if rpi_val >= 70 and conf_val >= 0.80:
            investment_outlook = "Strong collateral — liquid asset with high confidence"
        elif rpi_val >= 50 and conf_val >= 0.60:
            investment_outlook = "Acceptable collateral — moderate liquidity, reasonable confidence"
        elif rpi_val >= 30:
            investment_outlook = "Marginal collateral — restricted liquidity, requires higher margin"
        else:
            investment_outlook = "Weak collateral — illiquid asset, high risk of value erosion"

        valuation_insight = {
            "title": "Valuation & Investment Outlook",
            "point_estimate": val.get("point_estimate", 0),
            "weighted_estimate": val.get("weighted_estimate", val.get("point_estimate", 0)),
            "uncertainty_pct": round((val.get("uncertainty", 0.1)) * 100, 1),
            "independent_estimates": val.get("independent_estimates", {}),
            "investment_outlook": investment_outlook,
            "macro_adjustment": macro.get("macro_adjustment_factor", 1.0) if macro else 1.0,
            "market_cycle": macro.get("market_cycle_position", "mid") if macro else "mid",
            "market_sentiment": macro.get("market_sentiment", "stable") if macro else "stable",
            "seasonal_factor": macro.get("seasonal_factor", 1.0) if macro else 1.0,
        }

        # Income analysis insight (from valuation agent)
        income_insight = val.get("income_analysis")  # None when not rented

        # Legal compliance insight
        legal_insight = {
            "title": "Legal & Compliance",
            "legal_risk_category":  legal.get("legal_risk_category", "amber"),
            "f_legal":              legal.get("f_legal", 0.95),
            "f_regulatory":         legal.get("f_regulatory", 1.0),
            "legal_multiplier":     legal.get("legal_multiplier", 0.95),
            "ownership":            legal.get("ownership", "unknown"),
            "title_status":         legal.get("title_status", "unknown"),
            "encumbrance_status":   legal.get("encumbrance_status", "unknown"),
            "rera_registered":      legal.get("rera_registered"),
            "occupancy_certificate": legal.get("occupancy_certificate"),
            "completion_certificate": legal.get("completion_certificate"),
            "litigation_pending":   legal.get("litigation_pending"),
            "plan_deviation_pct":   legal.get("plan_deviation_pct"),
            "warnings":             legal.get("warnings", []),
        }

        return {
            "location":         location_insight,
            "property":         property_insight,
            "market":           market_insight,
            "fraud":            fraud_insight,
            "valuation":        valuation_insight,
            "income":           income_insight,
            "legal_compliance": legal_insight,
        }
