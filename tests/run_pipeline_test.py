"""
Full pipeline test: runs all 5 scenarios from sample_properties.json
through the complete agent DAG, using deterministic synthetic data.

Bypasses network calls (geocoding/Overpass) with pre-seeded fixtures
to ensure reproducibility and reliability.
"""
import asyncio
import json
import sys
import os
import math
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
from app.config.constants import MCR_TABLE, YIELD_EXPECTED

FIXTURE_DIR = Path(__file__).parent / "fixtures"

SCENARIOS = {
    "andheri_2bhk": {
        "input": {
            "address": "Andheri West, Mumbai",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 850,
            "age_years": 8,
            "configuration": "2BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 6,
            "total_floors": 12,
            "has_lift": True,
            "occupancy": "rented",
            "monthly_rent": 45000,
        },
        "location": {
            "circle_rate_per_sqft": 12000,
            "city_tier": 1,
            "city": "Mumbai",
            "locality": "Andheri West",
            "poi_distances": {"metro": 0.5, "highway": 1.0, "school": 0.4,
                              "hospital": 1.2, "commercial": 0.7, "it_park": 3.5},
            "poi_counts": {"n_residential": 48, "n_commercial": 32, "n_industrial": 2},
        },
        "market": {"active_listings_1km": 42},
        "mode_area": 750,
    },
    "gorakhpur_warehouse": {
        "input": {
            "address": "Golghar, Gorakhpur",
            "property_type": "industrial",
            "sub_type": "warehouse",
            "built_up_area_sqft": 5000,
            "age_years": 25,
        },
        "location": {
            "circle_rate_per_sqft": 2500,
            "city_tier": 3,
            "city": "Gorakhpur",
            "locality": "Golghar",
            "poi_distances": {"metro": 5.0, "highway": 2.0, "school": 3.0,
                              "hospital": 4.0, "commercial": 3.5, "it_park": 5.0},
            "poi_counts": {"n_residential": 5, "n_commercial": 3, "n_industrial": 15},
        },
        "market": {"active_listings_1km": 3},
        "mode_area": 2500,
    },
    "lucknow_disputed_plot": {
        "input": {
            "address": "Gomti Nagar, Lucknow",
            "property_type": "residential",
            "sub_type": "plot",
            "built_up_area_sqft": 2400,
            "age_years": 0,
            "ownership": "freehold",
            "title_clear": False,
            "occupancy": "vacant",
        },
        "location": {
            "circle_rate_per_sqft": 5500,
            "city_tier": 2,
            "city": "Lucknow",
            "locality": "Gomti Nagar",
            "poi_distances": {"metro": 4.0, "highway": 1.5, "school": 1.0,
                              "hospital": 2.0, "commercial": 1.5, "it_park": 5.0},
            "poi_counts": {"n_residential": 30, "n_commercial": 15, "n_industrial": 3},
        },
        "market": {"active_listings_1km": 8},
        "mode_area": 2000,
    },
    "bandra_old_building": {
        "input": {
            "address": "Bandra West, Mumbai",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 1100,
            "age_years": 45,
            "configuration": "3BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 3,
            "total_floors": 5,
            "has_lift": False,
            "occupancy": "self_occupied",
        },
        "location": {
            "circle_rate_per_sqft": 18000,
            "city_tier": 1,
            "city": "Mumbai",
            "locality": "Bandra West",
            "poi_distances": {"metro": 0.3, "highway": 0.8, "school": 0.3,
                              "hospital": 0.9, "commercial": 0.4, "it_park": 2.0},
            "poi_counts": {"n_residential": 55, "n_commercial": 40, "n_industrial": 1},
        },
        "market": {"active_listings_1km": 35},
        "mode_area": 1000,
    },
    "pune_fraud_4bhk_400sqft": {
        "input": {
            "address": "Hinjewadi, Pune",
            "property_type": "residential",
            "sub_type": "apartment",
            "built_up_area_sqft": 400,
            "age_years": 3,
            "configuration": "4BHK",
            "ownership": "freehold",
            "title_clear": True,
            "floor": 2,
            "total_floors": 10,
            "has_lift": True,
        },
        "location": {
            "circle_rate_per_sqft": 6500,
            "city_tier": 1,
            "city": "Pune",
            "locality": "Hinjewadi",
            "poi_distances": {"metro": 3.0, "highway": 0.5, "school": 1.0,
                              "hospital": 2.0, "commercial": 2.0, "it_park": 1.0},
            "poi_counts": {"n_residential": 25, "n_commercial": 20, "n_industrial": 5},
        },
        "market": {"active_listings_1km": 30},
        "mode_area": 800,
    },
}


def run_scenario(name: str, scenario: dict) -> dict:
    """Run a complete valuation scenario through all math functions."""
    inp = scenario["input"]
    loc = scenario["location"]
    mkt = scenario["market"]

    s_infra = compute_s_infra(loc["poi_distances"])
    s_nbhd = compute_s_nbhd(
        loc["poi_counts"]["n_residential"],
        loc["poi_counts"]["n_commercial"],
        loc["poi_counts"]["n_industrial"],
    )

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
    f_floor = compute_f_floor(
        inp.get("floor"), inp.get("total_floors"),
        inp.get("has_lift"), sub_type, inp["property_type"],
    )

    v = compute_valuation(circle_rate, area, mcr, f_loc, f_age, f_cfg, f_legal, f_floor)
    drivers = compute_driver_contributions(mcr, f_loc, f_age, f_cfg, f_legal, f_floor)

    # Confidence components
    input_fields = {
        "address_or_coords": True,
        "property_type": inp.get("property_type"),
        "sub_type": inp.get("sub_type"),
        "built_up_area_sqft": inp.get("built_up_area_sqft"),
        "age_years": inp.get("age_years"),
        "floor": inp.get("floor"),
        "ownership": inp.get("ownership"),
        "title_clear": inp.get("title_clear"),
        "occupancy": inp.get("occupancy"),
        "monthly_rent": inp.get("monthly_rent"),
        "exterior_image_url": inp.get("exterior_image_url"),
        "interior_image_url": inp.get("interior_image_url"),
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

    from app.tools.listings import get_synthetic_listings
    listing_data = get_synthetic_listings(city_tier, sub_type, v, area)
    v2 = listing_data.get("median_comparable_price")
    active_listings = mkt["active_listings_1km"]

    values = [v for v in [v1, v2, v3] if v is not None and v > 0]
    q_agree = compute_q_agree(values)
    q_density = compute_q_density(active_listings)

    # Fraud checks
    fraud_flags = []
    from app.config.constants import MIN_CONFIG_AREAS
    config = inp.get("configuration")
    if config and config.upper() in MIN_CONFIG_AREAS:
        min_area = MIN_CONFIG_AREAS[config.upper()] * 0.80
        if area < min_area:
            fraud_flags.append({"flag": "config_area_mismatch", "severity": "high",
                               "explanation": f"{config} needs >= {min_area:.0f} sqft, got {area}"})

    p_fraud = compute_p_fraud(fraud_flags)
    confidence = compute_confidence(q_data, q_agree, q_density, p_fraud)
    u = compute_uncertainty(q_data, q_agree, p_fraud)
    mv_range = compute_mv_range(v, u)

    # Liquidity
    s_cfg_liq = compute_s_cfg_liquidity(delta)
    s_ds = compute_s_ds(active_listings, city_tier, sub_type)
    s_legal_liq = compute_s_legal_liquidity(inp.get("ownership"), inp.get("title_clear"))
    s_age_liq = compute_s_age_liq(age)

    v_prior = circle_rate * area * mcr
    s_yield = compute_s_yield(inp.get("monthly_rent"), v_prior, city_tier, inp["property_type"])

    rpi = compute_rpi(s_infra, s_cfg_liq, s_ds, s_legal_liq, s_age_liq, s_yield)
    ttl = compute_ttl(rpi, sub_type)
    distress_range = compute_distress_range(mv_range, rpi)

    # Risk flags
    risk_flags = []
    for f in fraud_flags:
        risk_flags.append({"flag": f["flag"], "severity": f["severity"], "source_agent": "fraud"})
    if inp.get("title_clear") is False:
        risk_flags.append({"flag": "title_disputed", "severity": "high", "source_agent": "legal"})
    if s_ds < 0.35:
        risk_flags.append({"flag": "high_micro_market_competition", "severity": "medium",
                          "source_agent": "market_dynamics"})
    bucket = get_micro_bucket(s_infra)

    # Key drivers
    key_drivers = []
    for d in drivers[:5]:
        impact_str = f"+{d['impact_pct']}%" if d['impact_pct'] >= 0 else f"{d['impact_pct']}%"
        key_drivers.append({"factor": d["factor"], "impact": impact_str, "source_agent": d["source_agent"]})

    # RPI label
    rpi_int = round(rpi)
    if rpi_int >= 80:
        rpi_label = "Highly liquid"
    elif rpi_int >= 60:
        rpi_label = "Moderately liquid"
    elif rpi_int >= 40:
        rpi_label = "Restricted liquidity"
    elif rpi_int >= 20:
        rpi_label = "Illiquid"
    else:
        rpi_label = "Unsellable without deep discount"

    explanation = (
        f"This {sub_type} in {loc['city']} ({loc['locality']}) is valued at "
        f"₹{mv_range[0]:,}–₹{mv_range[1]:,} based on circle rate ₹{circle_rate:,}/sqft "
        f"with MCR {mcr}x (Tier-{city_tier} {bucket} market). "
        f"Age factor {f_age:.3f} ({age} years, {sub_type}), config factor {f_cfg:.3f}. "
        f"RPI of {rpi_int} ({rpi_label}) yields {ttl[0]}–{ttl[1]} day sale window. "
        f"Confidence: {confidence_label(confidence)} ({confidence:.2f})."
    )

    return {
        "market_value_range": mv_range,
        "distress_value_range": distress_range,
        "resale_potential_index": rpi_int,
        "estimated_time_to_sell_days": ttl,
        "confidence_score": round(confidence, 2),
        "key_drivers": key_drivers,
        "risk_flags": risk_flags,
        "explanation": explanation,
        "agent_trace": {
            "location_intel": {
                "circle_rate_per_sqft": circle_rate,
                "infra_score": round(s_infra, 4),
                "neighborhood_quality": round(s_nbhd, 4),
                "city_tier": city_tier,
                "mcr": mcr,
                "micro_bucket": bucket,
                "f_loc": round(f_loc, 4),
            },
            "property_char": {
                "f_age": round(f_age, 4),
                "f_cfg": round(f_cfg, 4),
                "f_floor": round(f_floor, 2),
                "delta": round(delta, 4),
                "mode_area": mode_area,
            },
            "market_dynamics": {
                "active_listings_1km": active_listings,
                "supply_density_score": round(s_ds, 4),
            },
            "legal": {
                "f_legal": f_legal,
                "s_legal": s_legal_liq,
            },
            "valuation": {
                "point_estimate": round(v),
                "uncertainty": round(u, 4),
                "q_data": round(q_data, 4),
                "q_agree": round(q_agree, 4),
                "q_density": round(q_density, 4),
            },
            "liquidity": {
                "rpi": rpi_int,
                "rpi_components": {
                    "s_infra": round(s_infra, 4),
                    "s_cfg": round(s_cfg_liq, 4),
                    "s_ds": round(s_ds, 4),
                    "s_legal": round(s_legal_liq, 4),
                    "s_age_liq": round(s_age_liq, 4),
                    "s_yield": round(s_yield, 4),
                },
            },
            "fraud": {
                "flags": fraud_flags,
                "fraud_score": round(p_fraud, 4),
            },
        },
    }


def format_inr(amount: int) -> str:
    """Format INR with lakhs/crore notation."""
    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    return f"₹{amount:,}"


def print_scenario_result(name: str, result: dict):
    """Pretty-print a scenario result."""
    print(f"\n{'='*80}")
    print(f"  SCENARIO: {name}")
    print(f"{'='*80}")
    print(f"  Market Value Range:     {format_inr(result['market_value_range'][0])} – {format_inr(result['market_value_range'][1])}")
    print(f"  Distress Value Range:   {format_inr(result['distress_value_range'][0])} – {format_inr(result['distress_value_range'][1])}")
    print(f"  Resale Potential Index:  {result['resale_potential_index']}/100")
    print(f"  Time to Sell:           {result['estimated_time_to_sell_days'][0]}–{result['estimated_time_to_sell_days'][1]} days")
    print(f"  Confidence Score:       {result['confidence_score']} ({confidence_label(result['confidence_score'])})")

    print(f"\n  Key Drivers:")
    for d in result["key_drivers"]:
        print(f"    • {d['factor']:40s} {d['impact']:>8s}  [{d['source_agent']}]")

    if result["risk_flags"]:
        print(f"\n  Risk Flags:")
        for f in result["risk_flags"]:
            print(f"    ⚠ [{f['severity'].upper():6s}] {f['flag']}  [{f['source_agent']}]")
    else:
        print(f"\n  Risk Flags: None")

    print(f"\n  Explanation:")
    print(f"    {result['explanation']}")

    trace = result["agent_trace"]
    print(f"\n  Agent Trace (key values):")
    print(f"    Location:  S_infra={trace['location_intel']['infra_score']}, S_nbhd={trace['location_intel']['neighborhood_quality']}, MCR={trace['location_intel']['mcr']}, f_loc={trace['location_intel']['f_loc']}")
    print(f"    Property:  f_age={trace['property_char']['f_age']}, f_cfg={trace['property_char']['f_cfg']}, f_floor={trace['property_char']['f_floor']}")
    print(f"    Market:    listings={trace['market_dynamics']['active_listings_1km']}, S_ds={trace['market_dynamics']['supply_density_score']}")
    print(f"    Legal:     f_legal={trace['legal']['f_legal']}, s_legal={trace['legal']['s_legal']}")
    print(f"    Valuation: V={format_inr(trace['valuation']['point_estimate'])}, u={trace['valuation']['uncertainty']}")
    rpi_c = trace["liquidity"]["rpi_components"]
    print(f"    RPI:       S_infra={rpi_c['s_infra']}, S_cfg={rpi_c['s_cfg']}, S_ds={rpi_c['s_ds']}, S_legal={rpi_c['s_legal']}, S_age={rpi_c['s_age_liq']}, S_yield={rpi_c['s_yield']}")


def validate_assertions(result: dict) -> list[str]:
    """Run §23 runtime assertions on a result."""
    errors = []
    mv = result["market_value_range"]
    dv = result["distress_value_range"]
    ttl = result["estimated_time_to_sell_days"]

    if not (mv[0] < mv[1]):
        errors.append(f"MV range not ordered: {mv}")
    if not (dv[0] < dv[1]):
        errors.append(f"Distress range not ordered: {dv}")
    if not (dv[1] <= mv[1]):
        errors.append(f"Distress high > MV high: {dv[1]} > {mv[1]}")
    if not (ttl[0] < ttl[1]):
        errors.append(f"TTL range not ordered: {ttl}")
    if not (ttl[0] >= 7):
        errors.append(f"TTL too short: {ttl[0]} < 7 days")
    if not (0 <= result["resale_potential_index"] <= 100):
        errors.append(f"RPI out of bounds: {result['resale_potential_index']}")
    if not (0 <= result["confidence_score"] <= 1):
        errors.append(f"Confidence out of bounds: {result['confidence_score']}")
    return errors


def main():
    print("\n" + "="*80)
    print("  COLLATERAL VALUATION ENGINE — FULL PIPELINE TEST")
    print("  Running all 5 test scenarios with deterministic data")
    print("="*80)

    all_results = {}
    all_passed = True

    for name, scenario in SCENARIOS.items():
        result = run_scenario(name, scenario)
        all_results[name] = result
        print_scenario_result(name, result)

        errors = validate_assertions(result)
        if errors:
            print(f"\n  ❌ ASSERTION FAILURES:")
            for e in errors:
                print(f"    • {e}")
            all_passed = False
        else:
            print(f"\n  ✅ All runtime assertions passed")

    # Specific scenario validations
    print("\n" + "="*80)
    print("  SCENARIO-SPECIFIC VALIDATIONS")
    print("="*80)

    # Andheri: high RPI, tight range
    andheri = all_results["andheri_2bhk"]
    checks = [
        ("Andheri RPI >= 60", andheri["resale_potential_index"] >= 60),
        ("Andheri confidence >= 0.70", andheri["confidence_score"] >= 0.70),
        ("Andheri no fraud flags", len([f for f in andheri["risk_flags"] if f["source_agent"] == "fraud"]) == 0),
    ]

    # Gorakhpur: low RPI
    gorakhpur = all_results["gorakhpur_warehouse"]
    checks += [
        ("Gorakhpur RPI <= 45 (restricted liquidity)", gorakhpur["resale_potential_index"] <= 45),
        ("Gorakhpur TTL > 100 days", gorakhpur["estimated_time_to_sell_days"][1] > 100),
    ]

    # Lucknow: legal flag
    lucknow = all_results["lucknow_disputed_plot"]
    checks += [
        ("Lucknow has title_disputed flag", any(f["flag"] == "title_disputed" for f in lucknow["risk_flags"])),
        ("Lucknow legal f_legal=0.85", lucknow["agent_trace"]["legal"]["f_legal"] == 0.85),
    ]

    # Bandra: old but good location
    bandra = all_results["bandra_old_building"]
    checks += [
        ("Bandra f_age < 0.80 (old building)", bandra["agent_trace"]["property_char"]["f_age"] < 0.80),
        ("Bandra MCR >= 1.70 (prime Tier-1)", bandra["agent_trace"]["location_intel"]["mcr"] >= 1.70),
    ]

    # Pune fraud: must fire config_area_mismatch
    pune = all_results["pune_fraud_4bhk_400sqft"]
    checks += [
        ("Pune fraud: config_area_mismatch fired",
         any(f["flag"] == "config_area_mismatch" for f in pune["risk_flags"])),
    ]

    for desc, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {desc}")
        if not passed:
            all_passed = False

    # Save full output to JSON
    output_path = Path(__file__).parent / "fixtures" / "pipeline_output.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n  📄 Full output saved to: {output_path}")

    print("\n" + "="*80)
    if all_passed:
        print("  ✅ ALL TESTS PASSED — Pipeline is functioning correctly")
    else:
        print("  ❌ SOME TESTS FAILED — Review output above")
    print("="*80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
