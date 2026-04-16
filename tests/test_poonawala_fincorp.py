"""
Poonawalla Fincorp — Realistic LAP Portfolio Test
===================================================
Tests the engine on 6 scenarios modeled after Poonawalla Fincorp's actual
Loan Against Property business:

  - LAP = 24% of total loan assets (₹25,335 Cr AUM as of FY25)
  - Focus on residential properties (high attachment value + marketability)
  - Average ticket size: ₹10-15L (housing), up to ₹25 Cr (LAP)
  - LTV typically 50-70% for LAP
  - Expanding aggressively in Tier 2/3 cities
  - AI-driven credit underwriting
  - Interest rates from 9.5% p.a.

Each scenario simulates a real borrower walking into Poonawalla Fincorp
and offering their property as collateral for a Loan Against Property.
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.math.formulas import (
    compute_s_infra, compute_s_nbhd, compute_mcr, compute_f_loc,
    compute_f_age, compute_f_cfg, compute_f_floor, compute_f_legal,
    compute_valuation, compute_driver_contributions,
    compute_uncertainty, compute_mv_range, compute_s_ds,
    compute_s_age_liq, compute_s_cfg_liquidity, compute_s_legal_liquidity,
    compute_s_yield, compute_rpi, compute_ttl, compute_distress_range,
    compute_q_data, compute_q_agree, compute_q_density, compute_p_fraud,
    compute_confidence, confidence_label, compute_delta, get_micro_bucket,
)
from app.config.constants import MCR_TABLE, YIELD_EXPECTED, MIN_CONFIG_AREAS
from app.tools.listings import get_synthetic_listings


POONAWALA_SCENARIOS = {
    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 1: Poonawalla's bread-and-butter — salaried IT
    # professional in Pune (their HQ city) with a standard 2BHK.
    # Borrower wants ₹30L LAP for child's education abroad.
    # ─────────────────────────────────────────────────────────────────
    "pune_salaried_2bhk_baner": {
        "borrower": "Salaried IT professional, age 38, CIBIL 780",
        "loan_purpose": "Child's higher education abroad",
        "requested_loan": 3000000,
        "input": {
            "address": "Baner, Pune",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 850,
            "age_years": 5,
            "configuration": "2BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 4,
            "total_floors": 14,
            "has_lift": True,
            "occupancy": "self_occupied",
            "monthly_rent": None,
        },
        "location": {
            "circle_rate_per_sqft": 7000,
            "city_tier": 1,
            "city": "Pune",
            "locality": "Baner",
            "poi_distances": {"metro": 2.0, "highway": 0.5, "school": 0.6,
                              "hospital": 1.5, "commercial": 1.0, "it_park": 1.5},
            "poi_counts": {"n_residential": 40, "n_commercial": 25, "n_industrial": 3},
        },
        "market": {"active_listings_1km": 35},
        "mode_area": 800,
    },

    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 2: Tier-2 MSME borrower — shop owner in Nagpur
    # offering commercial shop as collateral for working capital.
    # This tests Poonawalla's Tier 2 expansion + commercial property.
    # ─────────────────────────────────────────────────────────────────
    "nagpur_msme_shop_sitabuldi": {
        "borrower": "Self-employed shopkeeper, age 45, CIBIL 720",
        "loan_purpose": "Working capital for seasonal inventory",
        "requested_loan": 1500000,
        "input": {
            "address": "Sitabuldi, Nagpur",
            "property_type": "commercial",
            "sub_type": "shop",
            "built_up_area_sqft": 350,
            "age_years": 12,
            "ownership": "freehold",
            "title_clear": True,
            "floor": 0,
            "total_floors": 3,
            "has_lift": False,
            "occupancy": "self_occupied",
            "monthly_rent": None,
        },
        "location": {
            "circle_rate_per_sqft": 6000,
            "city_tier": 2,
            "city": "Nagpur",
            "locality": "Sitabuldi",
            "poi_distances": {"metro": 4.0, "highway": 1.5, "school": 0.5,
                              "hospital": 1.0, "commercial": 0.3, "it_park": 5.0},
            "poi_counts": {"n_residential": 20, "n_commercial": 35, "n_industrial": 5},
        },
        "market": {"active_listings_1km": 12},
        "mode_area": 350,
    },

    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 3: Tier-2 expansion — self-employed in Jaipur
    # offering 3BHK apartment for business expansion loan.
    # Tests Poonawalla's push into Rajasthan markets.
    # ─────────────────────────────────────────────────────────────────
    "jaipur_self_employed_3bhk": {
        "borrower": "Self-employed textile trader, age 42, CIBIL 740",
        "loan_purpose": "Business expansion — new showroom",
        "requested_loan": 5000000,
        "input": {
            "address": "Malviya Nagar, Jaipur",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 1200,
            "age_years": 10,
            "configuration": "3BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 2,
            "total_floors": 7,
            "has_lift": True,
            "occupancy": "rented",
            "monthly_rent": 22000,
        },
        "location": {
            "circle_rate_per_sqft": 5000,
            "city_tier": 2,
            "city": "Jaipur",
            "locality": "Malviya Nagar",
            "poi_distances": {"metro": 3.0, "highway": 1.0, "school": 0.4,
                              "hospital": 1.5, "commercial": 0.8, "it_park": 4.0},
            "poi_counts": {"n_residential": 35, "n_commercial": 20, "n_industrial": 2},
        },
        "market": {"active_listings_1km": 18},
        "mode_area": 1000,
    },

    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 4: High-value Mumbai LAP — property in Dadar
    # This tests the upper end of their LAP book (up to ₹25 Cr).
    # Old building in prime location — classic Mumbai LAP case.
    # ─────────────────────────────────────────────────────────────────
    "mumbai_high_value_dadar": {
        "borrower": "Business owner, age 55, CIBIL 760, existing relationship",
        "loan_purpose": "Business expansion — ₹1.5Cr LAP against Dadar flat",
        "requested_loan": 15000000,
        "input": {
            "address": "Dadar, Mumbai",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 750,
            "age_years": 30,
            "configuration": "2BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 3,
            "total_floors": 4,
            "has_lift": False,
            "occupancy": "self_occupied",
            "monthly_rent": None,
        },
        "location": {
            "circle_rate_per_sqft": 15000,
            "city_tier": 1,
            "city": "Mumbai",
            "locality": "Dadar",
            "poi_distances": {"metro": 0.3, "highway": 0.5, "school": 0.3,
                              "hospital": 0.5, "commercial": 0.2, "it_park": 3.0},
            "poi_counts": {"n_residential": 50, "n_commercial": 45, "n_industrial": 2},
        },
        "market": {"active_listings_1km": 28},
        "mode_area": 650,
    },

    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 5: Tier-3 small ticket — plot in Gorakhpur
    # Tests Poonawalla's Tier 3 penetration. Small borrower offering
    # land as collateral. Higher risk, lower value.
    # ─────────────────────────────────────────────────────────────────
    "gorakhpur_small_ticket_plot": {
        "borrower": "Small business owner, age 35, CIBIL 690",
        "loan_purpose": "Working capital for retail shop",
        "requested_loan": 800000,
        "input": {
            "address": "Civil Lines, Gorakhpur",
            "property_type": "residential",
            "sub_type": "plot",
            "built_up_area_sqft": 1500,
            "age_years": 0,
            "ownership": "freehold",
            "title_clear": True,
            "occupancy": "vacant",
        },
        "location": {
            "circle_rate_per_sqft": 3000,
            "city_tier": 3,
            "city": "Gorakhpur",
            "locality": "Civil Lines",
            "poi_distances": {"metro": 5.0, "highway": 1.0, "school": 0.5,
                              "hospital": 1.5, "commercial": 1.0, "it_park": 5.0},
            "poi_counts": {"n_residential": 25, "n_commercial": 15, "n_industrial": 3},
        },
        "market": {"active_listings_1km": 6},
        "mode_area": 1100,
    },

    # ─────────────────────────────────────────────────────────────────
    # SCENARIO 6: IT hub Bangalore — rented apartment as collateral.
    # Salaried professional with rental income. Tests rental yield
    # capitalization as an independent value estimate.
    # ─────────────────────────────────────────────────────────────────
    "bangalore_it_whitefield_rented": {
        "borrower": "Senior software engineer, age 34, CIBIL 800",
        "loan_purpose": "Startup seed capital",
        "requested_loan": 4000000,
        "input": {
            "address": "Whitefield, Bangalore",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 1100,
            "age_years": 6,
            "configuration": "3BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 8,
            "total_floors": 18,
            "has_lift": True,
            "occupancy": "rented",
            "monthly_rent": 35000,
        },
        "location": {
            "circle_rate_per_sqft": 7500,
            "city_tier": 1,
            "city": "Bangalore",
            "locality": "Whitefield",
            "poi_distances": {"metro": 1.5, "highway": 0.5, "school": 0.8,
                              "hospital": 2.0, "commercial": 1.0, "it_park": 0.5},
            "poi_counts": {"n_residential": 35, "n_commercial": 30, "n_industrial": 5},
        },
        "market": {"active_listings_1km": 45},
        "mode_area": 1000,
    },
}


def run_poonawala_scenario(name: str, scenario: dict) -> dict:
    inp = scenario["input"]
    loc = scenario["location"]
    mkt = scenario["market"]

    s_infra = compute_s_infra(loc["poi_distances"])
    s_nbhd = compute_s_nbhd(loc["poi_counts"]["n_residential"],
                              loc["poi_counts"]["n_commercial"],
                              loc["poi_counts"]["n_industrial"])

    circle_rate = loc["circle_rate_per_sqft"]
    city_tier = loc["city_tier"]
    area = inp["built_up_area_sqft"]
    age = inp["age_years"]
    sub_type = inp["sub_type"]

    mcr = compute_mcr(city_tier, s_infra)
    f_loc = compute_f_loc(s_infra, s_nbhd)
    f_age = compute_f_age(age, sub_type)
    mode_area = scenario["mode_area"]
    f_cfg = compute_f_cfg(area, mode_area)
    delta = compute_delta(area, mode_area)
    f_legal = compute_f_legal(inp.get("ownership"), inp.get("title_clear"))
    f_floor = compute_f_floor(inp.get("floor"), inp.get("total_floors"),
                               inp.get("has_lift"), sub_type, inp["property_type"])

    v = compute_valuation(circle_rate, area, mcr, f_loc, f_age, f_cfg, f_legal, f_floor)
    drivers = compute_driver_contributions(mcr, f_loc, f_age, f_cfg, f_legal, f_floor)

    input_fields = {
        "address_or_coords": True, "property_type": inp.get("property_type"),
        "sub_type": inp.get("sub_type"), "built_up_area_sqft": inp.get("built_up_area_sqft"),
        "age_years": inp.get("age_years"), "floor": inp.get("floor"),
        "ownership": inp.get("ownership"), "title_clear": inp.get("title_clear"),
        "occupancy": inp.get("occupancy"), "monthly_rent": inp.get("monthly_rent"),
        "exterior_image_url": None, "interior_image_url": None,
    }
    q_data = compute_q_data(input_fields)

    v1 = circle_rate * area * mcr * f_loc
    v3 = None
    if inp.get("monthly_rent"):
        ptype = "residential" if inp["property_type"] == "residential" else "commercial"
        yr = YIELD_EXPECTED.get((city_tier, ptype), (0.025, 0.045))
        yield_mid = (yr[0] + yr[1]) / 2
        if yield_mid > 0:
            v3 = (inp["monthly_rent"] * 12) / yield_mid

    listing_data = get_synthetic_listings(city_tier, sub_type, v, area)
    v2 = listing_data.get("median_comparable_price")
    active_listings = mkt["active_listings_1km"]

    values = [val for val in [v1, v2, v3] if val is not None and val > 0]
    q_agree = compute_q_agree(values)
    q_density = compute_q_density(active_listings)

    fraud_flags = []
    config = inp.get("configuration")
    if config and config.upper() in MIN_CONFIG_AREAS:
        min_area = MIN_CONFIG_AREAS[config.upper()] * 0.80
        if area < min_area:
            fraud_flags.append({"flag": "config_area_mismatch", "severity": "high"})

    p_fraud = compute_p_fraud(fraud_flags)
    confidence = compute_confidence(q_data, q_agree, q_density, p_fraud)
    u = compute_uncertainty(q_data, q_agree, p_fraud)
    mv_range = compute_mv_range(v, u)

    s_cfg_liq = compute_s_cfg_liquidity(delta)
    s_ds = compute_s_ds(active_listings, city_tier, sub_type)
    s_legal_liq = compute_s_legal_liquidity(inp.get("ownership"), inp.get("title_clear"))
    s_age_liq = compute_s_age_liq(age)
    v_prior = circle_rate * area * mcr
    s_yield = compute_s_yield(inp.get("monthly_rent"), v_prior, city_tier, inp["property_type"])

    rpi = compute_rpi(s_infra, s_cfg_liq, s_ds, s_legal_liq, s_age_liq, s_yield)
    ttl = compute_ttl(rpi, sub_type)
    distress_range = compute_distress_range(mv_range, rpi)
    bucket = get_micro_bucket(s_infra)

    rpi_int = round(rpi)
    if rpi_int >= 80: rpi_label = "Highly liquid"
    elif rpi_int >= 60: rpi_label = "Moderately liquid"
    elif rpi_int >= 40: rpi_label = "Restricted liquidity"
    elif rpi_int >= 20: rpi_label = "Illiquid"
    else: rpi_label = "Unsellable"

    # Poonawalla Fincorp LAP decision logic
    requested_loan = scenario["requested_loan"]
    max_ltv = 0.70 if rpi_int >= 60 else (0.60 if rpi_int >= 40 else 0.50)
    max_loan_at_ltv = int(mv_range[0] * max_ltv)
    loan_eligible = requested_loan <= max_loan_at_ltv
    recommended_ltv = min(max_ltv, requested_loan / mv_range[0]) if mv_range[0] > 0 else 0

    if confidence >= 0.80 and rpi_int >= 60 and loan_eligible:
        decision = "APPROVE"
    elif confidence >= 0.65 and rpi_int >= 40 and loan_eligible:
        decision = "APPROVE_WITH_CONDITIONS"
    elif confidence >= 0.50 and loan_eligible:
        decision = "REFER_TO_CREDIT_COMMITTEE"
    elif not loan_eligible:
        decision = "REDUCE_LOAN_AMOUNT"
    else:
        decision = "DECLINE"

    key_drivers = []
    for d in drivers[:5]:
        impact_str = f"+{d['impact_pct']}%" if d['impact_pct'] >= 0 else f"{d['impact_pct']}%"
        key_drivers.append({"factor": d["factor"], "impact": impact_str, "source_agent": d["source_agent"]})

    return {
        "market_value_range": mv_range,
        "distress_value_range": distress_range,
        "resale_potential_index": rpi_int,
        "rpi_label": rpi_label,
        "estimated_time_to_sell_days": ttl,
        "confidence_score": round(confidence, 3),
        "key_drivers": key_drivers,
        "fraud_flags": fraud_flags,
        "poonawala_lap_assessment": {
            "borrower": scenario["borrower"],
            "loan_purpose": scenario["loan_purpose"],
            "requested_loan": requested_loan,
            "max_ltv_pct": round(max_ltv * 100),
            "max_eligible_loan": max_loan_at_ltv,
            "actual_ltv_pct": round(recommended_ltv * 100, 1),
            "decision": decision,
            "collateral_adequacy": "ADEQUATE" if loan_eligible else "INSUFFICIENT",
        },
        "valuation_breakdown": {
            "circle_rate": circle_rate,
            "mcr": mcr,
            "bucket": bucket,
            "f_loc": round(f_loc, 4),
            "f_age": round(f_age, 4),
            "f_cfg": round(f_cfg, 4),
            "f_legal": round(f_legal, 2),
            "f_floor": round(f_floor, 2),
            "point_estimate": round(v),
            "uncertainty_pct": round(u * 100, 1),
        },
    }


def format_inr(amount):
    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    return f"₹{amount:,}"


def main():
    print("\n" + "="*90)
    print("  POONAWALLA FINCORP — LAP COLLATERAL VALUATION ENGINE TEST")
    print("  Testing 6 realistic scenarios from their actual portfolio profile")
    print("  (LAP = 24% of ₹25,335 Cr AUM | Residential focus | Tier 1/2/3 cities)")
    print("="*90)

    all_results = {}
    all_pass = True

    for name, scenario in POONAWALA_SCENARIOS.items():
        result = run_poonawala_scenario(name, scenario)
        all_results[name] = result
        lap = result["poonawala_lap_assessment"]
        vb = result["valuation_breakdown"]

        print(f"\n{'─'*90}")
        print(f"  SCENARIO: {name}")
        print(f"  Borrower: {lap['borrower']}")
        print(f"  Purpose:  {lap['loan_purpose']}")
        print(f"{'─'*90}")
        print(f"  COLLATERAL VALUATION:")
        print(f"    Market Value:      {format_inr(result['market_value_range'][0])} – {format_inr(result['market_value_range'][1])}")
        print(f"    Distress Value:    {format_inr(result['distress_value_range'][0])} – {format_inr(result['distress_value_range'][1])}")
        print(f"    Point Estimate:    {format_inr(vb['point_estimate'])} (MCR={vb['mcr']}x, {vb['bucket']})")
        print(f"    Uncertainty:       ±{vb['uncertainty_pct']}%")
        print(f"    RPI:               {result['resale_potential_index']}/100 ({result['rpi_label']})")
        print(f"    Time to Sell:      {result['estimated_time_to_sell_days'][0]}–{result['estimated_time_to_sell_days'][1]} days")
        print(f"    Confidence:        {result['confidence_score']} ({confidence_label(result['confidence_score'])})")

        print(f"\n  POONAWALLA FINCORP LAP DECISION:")
        print(f"    Requested Loan:    {format_inr(lap['requested_loan'])}")
        print(f"    Max LTV:           {lap['max_ltv_pct']}%")
        print(f"    Max Eligible Loan: {format_inr(lap['max_eligible_loan'])}")
        print(f"    Actual LTV:        {lap['actual_ltv_pct']}%")
        print(f"    Collateral:        {lap['collateral_adequacy']}")
        decision_icon = {"APPROVE": "✅", "APPROVE_WITH_CONDITIONS": "⚠️✅",
                        "REFER_TO_CREDIT_COMMITTEE": "📋", "REDUCE_LOAN_AMOUNT": "📉",
                        "DECLINE": "❌"}
        print(f"    DECISION:          {decision_icon.get(lap['decision'], '?')} {lap['decision']}")

        print(f"\n  KEY DRIVERS:")
        for d in result["key_drivers"][:4]:
            print(f"    • {d['factor']:35s} {d['impact']:>8s}  [{d['source_agent']}]")

        if result["fraud_flags"]:
            print(f"\n  ⚠ FRAUD FLAGS: {[f['flag'] for f in result['fraud_flags']]}")

        # Validation checks
        mv_low = result["market_value_range"][0]
        mv_high = result["market_value_range"][1]
        dv_low = result["distress_value_range"][0]
        dv_high = result["distress_value_range"][1]

        checks_ok = True
        if not (mv_low < mv_high):
            print(f"    ❌ MV range not ordered"); checks_ok = False
        if not (dv_low < dv_high):
            print(f"    ❌ DV range not ordered"); checks_ok = False
        if not (dv_high <= mv_high):
            print(f"    ❌ Distress > Market"); checks_ok = False
        if not (0 <= result["resale_potential_index"] <= 100):
            print(f"    ❌ RPI out of bounds"); checks_ok = False
        if not (0 <= result["confidence_score"] <= 1):
            print(f"    ❌ Confidence out of bounds"); checks_ok = False

        if checks_ok:
            print(f"\n  ✅ All assertions passed")
        else:
            all_pass = False
            print(f"\n  ❌ Assertion failures")

    # Summary table
    print(f"\n{'='*90}")
    print(f"  POONAWALLA FINCORP — LAP PORTFOLIO SUMMARY")
    print(f"{'='*90}")
    print(f"  {'Scenario':<35s} {'MV Range':<25s} {'RPI':>4s} {'Conf':>5s} {'Requested':>12s} {'Decision':<25s}")
    print(f"  {'─'*35} {'─'*25} {'─'*4} {'─'*5} {'─'*12} {'─'*25}")

    for name, result in all_results.items():
        lap = result["poonawala_lap_assessment"]
        mv = result["market_value_range"]
        print(f"  {name:<35s} {format_inr(mv[0]):>10s}–{format_inr(mv[1]):<12s} "
              f"{result['resale_potential_index']:>4d} {result['confidence_score']:>5.2f} "
              f"{format_inr(lap['requested_loan']):>12s} {lap['decision']:<25s}")

    # Portfolio-level analytics
    total_requested = sum(r["poonawala_lap_assessment"]["requested_loan"] for r in all_results.values())
    total_eligible = sum(r["poonawala_lap_assessment"]["max_eligible_loan"] for r in all_results.values())
    approved = sum(1 for r in all_results.values() if r["poonawala_lap_assessment"]["decision"].startswith("APPROVE"))
    avg_rpi = sum(r["resale_potential_index"] for r in all_results.values()) / len(all_results)
    avg_conf = sum(r["confidence_score"] for r in all_results.values()) / len(all_results)

    print(f"\n  PORTFOLIO METRICS:")
    print(f"    Total Loan Requested:    {format_inr(total_requested)}")
    print(f"    Total Eligible (at LTV): {format_inr(total_eligible)}")
    print(f"    Coverage Ratio:          {total_eligible/total_requested:.1f}x")
    print(f"    Approval Rate:           {approved}/{len(all_results)} ({approved/len(all_results)*100:.0f}%)")
    print(f"    Avg Portfolio RPI:       {avg_rpi:.0f}/100")
    print(f"    Avg Portfolio Confidence:{avg_conf:.2f}")

    output_path = Path(__file__).parent / "fixtures" / "poonawala_fincorp_output.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  📄 Full output: {output_path}")

    print(f"\n{'='*90}")
    if all_pass:
        print(f"  ✅ ALL 6 POONAWALLA FINCORP SCENARIOS PASSED")
    else:
        print(f"  ❌ SOME SCENARIOS FAILED")
    print(f"{'='*90}\n")

    return all_pass


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
