"""
LegalAgent — Rule-based legal + regulatory compliance assessment.
Combines ownership/title factor (f_legal) with a regulatory compliance
multiplier (f_regulatory) covering RERA, OC, CC, encumbrance, litigation.
"""
from app.agents.base import BaseAgent
from app.math.formulas import (
    compute_f_legal, compute_s_legal_liquidity, compute_f_regulatory,
)


class LegalAgent(BaseAgent):
    name = "legal"

    async def run(self, ctx: dict) -> dict:
        inp = ctx["input"]
        ownership   = inp.get("ownership")
        title_clear = inp.get("title_clear")
        age_years   = inp.get("age_years", 0)
        area        = inp.get("built_up_area_sqft", 0)

        # New regulatory fields
        rera_registered        = inp.get("rera_registered")
        occupancy_certificate  = inp.get("occupancy_certificate")
        completion_certificate = inp.get("completion_certificate")
        encumbrance_status     = inp.get("encumbrance_status")
        litigation_pending     = inp.get("litigation_pending")
        approved_plan_area     = inp.get("approved_plan_area_sqft")

        # §8 — Base legal factor (ownership + title)
        f_legal = compute_f_legal(ownership, title_clear)
        s_legal = compute_s_legal_liquidity(ownership, title_clear)

        # §24 — Regulatory compliance factor
        f_regulatory = compute_f_regulatory(
            rera_registered, occupancy_certificate, completion_certificate,
            litigation_pending, encumbrance_status, approved_plan_area,
            area, age_years,
        )

        legal_multiplier = round(f_legal * f_regulatory, 4)

        # Title status
        if title_clear is False:
            title_status = "disputed"
        elif title_clear is None:
            title_status = "unknown"
        else:
            title_status = "clear"

        # Plan deviation percentage for reporting
        plan_deviation_pct = None
        if approved_plan_area and approved_plan_area > 0 and area > 0:
            plan_deviation_pct = round(
                abs(area - approved_plan_area) / approved_plan_area * 100, 1
            )

        # Legal risk category (traffic-light)
        if legal_multiplier >= 0.95 and litigation_pending is not True:
            legal_risk_category = "green"
        elif legal_multiplier >= 0.80 and litigation_pending is not True:
            legal_risk_category = "amber"
        else:
            legal_risk_category = "red"

        # Build warnings list
        warnings = []

        # Existing ownership/title warnings
        if ownership == "leasehold":
            warnings.append({"flag": "leasehold_property", "severity": "low",
                             "explanation": "Leasehold properties have reduced marketability"})
        if title_clear is False:
            warnings.append({"flag": "title_disputed", "severity": "high",
                             "explanation": "Disputed title severely impacts value and liquidity"})
        if title_clear is None and ownership is None:
            warnings.append({"flag": "legal_info_missing", "severity": "low",
                             "explanation": "No ownership or title information provided"})

        # Regulatory warnings
        if rera_registered is False and age_years < 3:
            warnings.append({"flag": "rera_not_registered", "severity": "medium",
                             "explanation": "Under-construction property not registered with RERA — buyer protections missing"})
        if occupancy_certificate is False:
            warnings.append({"flag": "occupancy_certificate_missing", "severity": "high",
                             "explanation": "Occupancy Certificate not obtained — affects legal validity and resale"})
        if completion_certificate is False:
            warnings.append({"flag": "completion_certificate_missing", "severity": "medium",
                             "explanation": "Completion Certificate absent — construction regularity unverified"})
        if litigation_pending is True:
            warnings.append({"flag": "litigation_active", "severity": "high",
                             "explanation": "Active litigation pending — significant value and marketability risk under SARFAESI"})
        if encumbrance_status == "existing_mortgage":
            warnings.append({"flag": "existing_mortgage_charge", "severity": "medium",
                             "explanation": "Existing mortgage must be discharged before fresh charge can be created"})
        elif encumbrance_status == "attachment_order":
            warnings.append({"flag": "attachment_order_active", "severity": "high",
                             "explanation": "Court attachment order on property — highly restricted marketability"})
        elif encumbrance_status == "disputed":
            warnings.append({"flag": "encumbrance_disputed", "severity": "high",
                             "explanation": "Disputed encumbrance status — requires resolution before mortgage"})
        if plan_deviation_pct is not None and plan_deviation_pct > 10:
            warnings.append({"flag": "plan_area_deviation", "severity": "medium",
                             "explanation": f"Built-up area deviates {plan_deviation_pct}% from approved plan — possible unauthorised construction"})

        return {
            "f_legal":              f_legal,
            "f_regulatory":         round(f_regulatory, 4),
            "legal_multiplier":     legal_multiplier,
            "s_legal":              s_legal,
            "ownership":            ownership or "unknown",
            "title_status":         title_status,
            "legal_risk_category":  legal_risk_category,
            "rera_registered":      rera_registered,
            "occupancy_certificate": occupancy_certificate,
            "completion_certificate": completion_certificate,
            "encumbrance_status":   encumbrance_status or "unknown",
            "litigation_pending":   litigation_pending,
            "plan_deviation_pct":   plan_deviation_pct,
            "warnings":             warnings,
        }
