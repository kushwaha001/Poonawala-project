"""
Collateral Valuation & Resale Liquidity Engine — Streamlit Prototype
Bloomberg Terminal for Real Estate Collateral
"""
import streamlit as st
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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
from app.config.constants import YIELD_EXPECTED, MIN_CONFIG_AREAS
from app.tools.listings import get_synthetic_listings
from app.tools.circle_rate import lookup as cr_lookup

st.set_page_config(
    page_title="Collateral Valuation Engine",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .big-number { font-size: 2.2rem; font-weight: 700; font-family: 'SF Mono', monospace; }
    .big-number-teal { color: #00BFA5; font-size: 2.2rem; font-weight: 700; font-family: 'SF Mono', monospace; }
    .big-number-amber { color: #FFB300; font-size: 2.2rem; font-weight: 700; font-family: 'SF Mono', monospace; }
    .big-number-red { color: #FF5252; font-size: 2.2rem; font-weight: 700; font-family: 'SF Mono', monospace; }
    .metric-label { font-size: 0.85rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
    .card { background: #1A1D23; border-radius: 12px; padding: 1.5rem; border: 1px solid #2A2D35; margin-bottom: 1rem; }
    .driver-positive { color: #00BFA5; }
    .driver-negative { color: #FF5252; }
    .flag-high { background: #FF525233; color: #FF5252; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; }
    .flag-medium { background: #FFB30033; color: #FFB300; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; }
    .flag-low { background: #00BFA533; color: #00BFA5; padding: 4px 12px; border-radius: 6px; font-size: 0.8rem; }
    .rpi-gauge { font-size: 3.5rem; font-weight: 800; font-family: 'SF Mono', monospace; }
    .section-header { font-size: 0.75rem; color: #666; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.5rem; }
    div[data-testid="stSidebar"] { background-color: #151820; }
</style>
""", unsafe_allow_html=True)

LOCALITY_DB = {
    ("pune", "baner"): {"state": "Maharashtra", "district": "Pune", "tier": 1,
        "poi": {"metro": 2.0, "highway": 0.5, "school": 0.6, "hospital": 1.5, "commercial": 1.0, "it_park": 1.5},
        "counts": {"n_residential": 40, "n_commercial": 25, "n_industrial": 3}, "mode": {"apartment": 800, "shop": 350, "villa": 2000, "plot": 1200}},
    ("pune", "hinjewadi"): {"state": "Maharashtra", "district": "Pune", "tier": 1,
        "poi": {"metro": 3.0, "highway": 0.5, "school": 1.0, "hospital": 2.0, "commercial": 2.0, "it_park": 1.0},
        "counts": {"n_residential": 25, "n_commercial": 20, "n_industrial": 5}, "mode": {"apartment": 800, "shop": 300}},
    ("pune", "kothrud"): {"state": "Maharashtra", "district": "Pune", "tier": 1,
        "poi": {"metro": 1.5, "highway": 1.0, "school": 0.4, "hospital": 1.0, "commercial": 0.8, "it_park": 2.0},
        "counts": {"n_residential": 45, "n_commercial": 25, "n_industrial": 2}, "mode": {"apartment": 850}},
    ("mumbai", "andheri west"): {"state": "Maharashtra", "district": "Mumbai", "tier": 1,
        "poi": {"metro": 0.5, "highway": 1.0, "school": 0.4, "hospital": 1.2, "commercial": 0.7, "it_park": 3.5},
        "counts": {"n_residential": 48, "n_commercial": 32, "n_industrial": 2}, "mode": {"apartment": 750}},
    ("mumbai", "bandra west"): {"state": "Maharashtra", "district": "Mumbai", "tier": 1,
        "poi": {"metro": 0.3, "highway": 0.8, "school": 0.3, "hospital": 0.9, "commercial": 0.4, "it_park": 2.0},
        "counts": {"n_residential": 55, "n_commercial": 40, "n_industrial": 1}, "mode": {"apartment": 1000}},
    ("mumbai", "dadar"): {"state": "Maharashtra", "district": "Mumbai", "tier": 1,
        "poi": {"metro": 0.3, "highway": 0.5, "school": 0.3, "hospital": 0.5, "commercial": 0.2, "it_park": 3.0},
        "counts": {"n_residential": 50, "n_commercial": 45, "n_industrial": 2}, "mode": {"apartment": 650}},
    ("bangalore", "whitefield"): {"state": "Karnataka", "district": "Bangalore", "tier": 1,
        "poi": {"metro": 1.5, "highway": 0.5, "school": 0.8, "hospital": 2.0, "commercial": 1.0, "it_park": 0.5},
        "counts": {"n_residential": 35, "n_commercial": 30, "n_industrial": 5}, "mode": {"apartment": 1000}},
    ("nagpur", "sitabuldi"): {"state": "Maharashtra", "district": "Nagpur", "tier": 2,
        "poi": {"metro": 4.0, "highway": 1.5, "school": 0.5, "hospital": 1.0, "commercial": 0.3, "it_park": 5.0},
        "counts": {"n_residential": 20, "n_commercial": 35, "n_industrial": 5}, "mode": {"shop": 350, "apartment": 950}},
    ("jaipur", "malviya nagar"): {"state": "Rajasthan", "district": "Jaipur", "tier": 2,
        "poi": {"metro": 3.0, "highway": 1.0, "school": 0.4, "hospital": 1.5, "commercial": 0.8, "it_park": 4.0},
        "counts": {"n_residential": 35, "n_commercial": 20, "n_industrial": 2}, "mode": {"apartment": 1000}},
    ("lucknow", "gomti nagar"): {"state": "Uttar Pradesh", "district": "Lucknow", "tier": 2,
        "poi": {"metro": 4.0, "highway": 1.5, "school": 1.0, "hospital": 2.0, "commercial": 1.5, "it_park": 5.0},
        "counts": {"n_residential": 30, "n_commercial": 15, "n_industrial": 3}, "mode": {"apartment": 1000, "plot": 2000}},
    ("gorakhpur", "civil lines"): {"state": "Uttar Pradesh", "district": "Gorakhpur", "tier": 3,
        "poi": {"metro": 5.0, "highway": 1.0, "school": 0.5, "hospital": 1.5, "commercial": 1.0, "it_park": 5.0},
        "counts": {"n_residential": 25, "n_commercial": 15, "n_industrial": 3}, "mode": {"apartment": 1100, "plot": 1100}},
    ("gorakhpur", "golghar"): {"state": "Uttar Pradesh", "district": "Gorakhpur", "tier": 3,
        "poi": {"metro": 5.0, "highway": 2.0, "school": 3.0, "hospital": 4.0, "commercial": 3.5, "it_park": 5.0},
        "counts": {"n_residential": 5, "n_commercial": 3, "n_industrial": 15}, "mode": {"warehouse": 2500}},
}

def format_inr(amount):
    if amount >= 10000000:
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:
        return f"₹{amount/100000:.2f} L"
    return f"₹{amount:,}"


def get_locality_data(city, locality):
    key = (city.lower().strip(), locality.lower().strip())
    return LOCALITY_DB.get(key)


def run_valuation(city, locality, prop_type, sub_type, area, age, config,
                  ownership, title_clear, floor_num, total_floors, has_lift,
                  occupancy, monthly_rent):

    loc_data = get_locality_data(city, locality)
    if not loc_data:
        st.error(f"Locality '{locality}, {city}' not in database. Try: Baner/Pune, Andheri West/Mumbai, Whitefield/Bangalore, Sitabuldi/Nagpur, Malviya Nagar/Jaipur, Gomti Nagar/Lucknow, Civil Lines/Gorakhpur")
        return None

    cr = cr_lookup(loc_data["state"], loc_data["district"], locality)
    circle_rate = cr["rate_per_sqft"]
    city_tier = loc_data["tier"]

    s_infra = compute_s_infra(loc_data["poi"])
    s_nbhd = compute_s_nbhd(loc_data["counts"]["n_residential"], loc_data["counts"]["n_commercial"], loc_data["counts"]["n_industrial"])
    mcr = compute_mcr(city_tier, s_infra)
    f_loc = compute_f_loc(s_infra, s_nbhd)
    f_age = compute_f_age(age, sub_type)
    mode_area = loc_data.get("mode", {}).get(sub_type, 900)
    f_cfg = compute_f_cfg(area, mode_area)
    delta = compute_delta(area, mode_area)
    f_legal = compute_f_legal(ownership if ownership != "unknown" else None,
                               title_clear if title_clear != "unknown" else None)
    f_floor_val = compute_f_floor(floor_num if floor_num >= 0 else None,
                                   total_floors if total_floors > 0 else None,
                                   has_lift, sub_type, prop_type)

    v = compute_valuation(circle_rate, area, mcr, f_loc, f_age, f_cfg, f_legal, f_floor_val)
    drivers = compute_driver_contributions(mcr, f_loc, f_age, f_cfg, f_legal, f_floor_val)

    inp_fields = {"address_or_coords": True, "property_type": prop_type, "sub_type": sub_type,
                  "built_up_area_sqft": area, "age_years": age,
                  "floor": floor_num if floor_num >= 0 else None,
                  "ownership": ownership if ownership != "unknown" else None,
                  "title_clear": title_clear if title_clear != "unknown" else None,
                  "occupancy": occupancy if occupancy != "unknown" else None,
                  "monthly_rent": monthly_rent if monthly_rent > 0 else None,
                  "exterior_image_url": None, "interior_image_url": None}
    q_data = compute_q_data(inp_fields)

    v1 = circle_rate * area * mcr * f_loc
    listing_data = get_synthetic_listings(city_tier, sub_type, v, area)
    v2 = listing_data.get("median_comparable_price")
    v3 = None
    if monthly_rent and monthly_rent > 0:
        ptype = "residential" if prop_type == "residential" else "commercial"
        yr = YIELD_EXPECTED.get((city_tier, ptype), (0.025, 0.045))
        yield_mid = (yr[0] + yr[1]) / 2
        if yield_mid > 0: v3 = (monthly_rent * 12) / yield_mid

    values = [x for x in [v1, v2, v3] if x and x > 0]
    q_agree = compute_q_agree(values)
    q_density = compute_q_density(listing_data["active_listings_1km"])

    fraud_flags = []
    if config and config.upper() in MIN_CONFIG_AREAS:
        min_a = MIN_CONFIG_AREAS[config.upper()] * 0.80
        if area < min_a:
            fraud_flags.append({"flag": "config_area_mismatch", "severity": "high",
                               "detail": f"{config} needs >= {min_a:.0f} sqft, got {area}"})

    p_fraud = compute_p_fraud(fraud_flags)
    confidence = compute_confidence(q_data, q_agree, q_density, p_fraud)
    u = compute_uncertainty(q_data, q_agree, p_fraud)
    mv_range = compute_mv_range(v, u)

    s_cfg_liq = compute_s_cfg_liquidity(delta)
    s_ds = compute_s_ds(listing_data["active_listings_1km"], city_tier, sub_type)
    s_legal_liq = compute_s_legal_liquidity(ownership if ownership != "unknown" else None,
                                             title_clear if title_clear != "unknown" else None)
    s_age_liq = compute_s_age_liq(age)
    v_prior = circle_rate * area * mcr
    s_yield_val = compute_s_yield(monthly_rent if monthly_rent > 0 else None, v_prior, city_tier, prop_type)

    rpi = compute_rpi(s_infra, s_cfg_liq, s_ds, s_legal_liq, s_age_liq, s_yield_val)
    ttl = compute_ttl(rpi, sub_type)
    distress = compute_distress_range(mv_range, rpi)
    bucket = get_micro_bucket(s_infra)

    rpi_int = round(rpi)
    rpi_label = "Highly liquid" if rpi_int >= 80 else ("Moderately liquid" if rpi_int >= 60 else ("Restricted" if rpi_int >= 40 else ("Illiquid" if rpi_int >= 20 else "Unsellable")))

    return {
        "mv_range": mv_range, "distress": distress, "rpi": rpi_int, "rpi_label": rpi_label,
        "ttl": ttl, "confidence": round(confidence, 3), "v": round(v),
        "u_pct": round(u * 100, 1), "drivers": drivers, "fraud_flags": fraud_flags,
        "circle_rate": circle_rate, "mcr": mcr, "bucket": bucket, "city_tier": city_tier,
        "f_loc": round(f_loc, 4), "f_age": round(f_age, 4), "f_cfg": round(f_cfg, 4),
        "f_legal": f_legal, "f_floor": f_floor_val, "s_infra": round(s_infra, 4),
        "s_nbhd": round(s_nbhd, 4), "q_data": round(q_data, 3), "q_agree": round(q_agree, 3),
        "listings": listing_data["active_listings_1km"],
        "optimistic": compute_mv_range(v * 1.08, u * 0.8),
        "pessimistic": compute_mv_range(v * 0.90, u * 1.2),
    }


# ─── SIDEBAR: INPUT FORM ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏦 Property Input")
    st.markdown("---")

    city = st.selectbox("City", ["Pune", "Mumbai", "Bangalore", "Nagpur", "Jaipur", "Lucknow", "Gorakhpur"])

    loc_options = {
        "Pune": ["Baner", "Hinjewadi", "Kothrud"],
        "Mumbai": ["Andheri West", "Bandra West", "Dadar"],
        "Bangalore": ["Whitefield"],
        "Nagpur": ["Sitabuldi"],
        "Jaipur": ["Malviya Nagar"],
        "Lucknow": ["Gomti Nagar"],
        "Gorakhpur": ["Civil Lines", "Golghar"],
    }
    locality = st.selectbox("Locality", loc_options.get(city, ["Unknown"]))

    st.markdown("---")
    prop_type = st.selectbox("Property Type", ["residential", "commercial", "industrial"])
    sub_type = st.selectbox("Sub-Type", ["apartment", "villa", "plot", "shop", "warehouse", "office"])
    area = st.number_input("Built-up Area (sqft)", min_value=100, max_value=50000, value=850, step=50)
    age = st.slider("Age (years)", 0, 80, 5)
    config = st.selectbox("Configuration", ["None", "1BHK", "2BHK", "3BHK", "4BHK", "5BHK"])
    if config == "None": config = None

    st.markdown("---")
    ownership = st.selectbox("Ownership", ["freehold", "leasehold", "unknown"])
    title_clear_opt = st.selectbox("Title Clear", ["Yes", "No", "Unknown"])
    title_clear = True if title_clear_opt == "Yes" else (False if title_clear_opt == "No" else "unknown")

    st.markdown("---")
    floor_num = st.number_input("Floor", min_value=-1, max_value=50, value=4, help="-1 = not applicable")
    total_floors = st.number_input("Total Floors", min_value=0, max_value=80, value=14)
    has_lift = st.checkbox("Has Lift", value=True)
    occupancy = st.selectbox("Occupancy", ["self_occupied", "rented", "vacant", "unknown"])
    monthly_rent = st.number_input("Monthly Rent (₹)", min_value=0, max_value=1000000, value=0, step=1000)

    st.markdown("---")
    run_btn = st.button("⚡ VALUATE", use_container_width=True, type="primary")


# ─── MAIN CONTENT ───────────────────────────────────────────────────────
st.markdown("# 🏦 Collateral Valuation & Resale Liquidity Engine")
st.markdown("*Bloomberg Terminal for Real Estate Collateral — 11-Agent AI Pipeline*")
st.markdown("---")

if run_btn:
    with st.spinner("Running 11-agent pipeline..."):
        result = run_valuation(city, locality, prop_type, sub_type, area, age, config,
                               ownership, title_clear, floor_num, total_floors, has_lift,
                               occupancy, monthly_rent)

    if result:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown('<p class="metric-label">MARKET VALUE</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="big-number-teal">{format_inr(result["mv_range"][0])} – {format_inr(result["mv_range"][1])}</p>', unsafe_allow_html=True)
        with col2:
            st.markdown('<p class="metric-label">DISTRESS VALUE</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="big-number-amber">{format_inr(result["distress"][0])} – {format_inr(result["distress"][1])}</p>', unsafe_allow_html=True)
        with col3:
            st.markdown('<p class="metric-label">RPI SCORE</p>', unsafe_allow_html=True)
            color = "teal" if result["rpi"] >= 60 else ("amber" if result["rpi"] >= 40 else "red")
            st.markdown(f'<p class="big-number-{color}">{result["rpi"]}/100</p>', unsafe_allow_html=True)
            st.caption(result["rpi_label"])
        with col4:
            st.markdown('<p class="metric-label">CONFIDENCE</p>', unsafe_allow_html=True)
            conf_color = "teal" if result["confidence"] >= 0.80 else ("amber" if result["confidence"] >= 0.60 else "red")
            st.markdown(f'<p class="big-number-{conf_color}">{result["confidence"]:.0%}</p>', unsafe_allow_html=True)
            st.caption(confidence_label(result["confidence"]))

        st.markdown("---")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("### Key Drivers")
            for d in result["drivers"][:6]:
                impact = d["impact_pct"]
                bar_color = "🟢" if impact >= 0 else "🔴"
                bar_len = min(20, abs(int(impact / 5)))
                bar = "█" * bar_len + "░" * (20 - bar_len)
                sign = "+" if impact >= 0 else ""
                st.markdown(f"`{d['factor'][:30]:<30s}` {bar_color} `{bar}` **{sign}{impact}%**")

            st.markdown("### Three Scenarios")
            scen_data = {
                "Scenario": ["Optimistic", "Base", "Pessimistic"],
                "Low": [format_inr(result["optimistic"][0]), format_inr(result["mv_range"][0]), format_inr(result["pessimistic"][0])],
                "High": [format_inr(result["optimistic"][1]), format_inr(result["mv_range"][1]), format_inr(result["pessimistic"][1])],
            }
            st.table(scen_data)

        with col_right:
            st.markdown("### Valuation Breakdown")
            st.markdown(f"""
| Factor | Value |
|--------|-------|
| Circle Rate | ₹{result['circle_rate']:,}/sqft |
| MCR | {result['mcr']}x ({result['bucket']}, Tier {result['city_tier']}) |
| f_loc | {result['f_loc']} |
| f_age | {result['f_age']} |
| f_cfg | {result['f_cfg']} |
| f_legal | {result['f_legal']} |
| f_floor | {result['f_floor']} |
| **Point Estimate** | **{format_inr(result['v'])}** |
| Uncertainty | ±{result['u_pct']}% |
            """)

            st.markdown("### Liquidity")
            st.markdown(f"**Time to Sell:** {result['ttl'][0]}–{result['ttl'][1]} days")
            st.markdown(f"**Active Listings (1km):** {result['listings']}")

            st.markdown("### Confidence Components")
            st.markdown(f"- Data completeness: {result['q_data']}")
            st.markdown(f"- Cross-source agreement: {result['q_agree']}")

        if result["fraud_flags"]:
            st.markdown("---")
            st.markdown("### ⚠️ Fraud Flags")
            for f in result["fraud_flags"]:
                sev_color = {"high": "flag-high", "medium": "flag-medium", "low": "flag-low"}.get(f["severity"], "flag-low")
                st.markdown(f'<span class="{sev_color}">{f["severity"].upper()}</span> **{f["flag"]}**: {f.get("detail", "")}', unsafe_allow_html=True)
        else:
            st.success("No fraud flags detected")

        with st.expander("📋 Full JSON Output"):
            output_json = {
                "market_value_range": result["mv_range"],
                "distress_value_range": result["distress"],
                "resale_potential_index": result["rpi"],
                "estimated_time_to_sell_days": result["ttl"],
                "confidence_score": result["confidence"],
                "key_drivers": [{"factor": d["factor"], "impact": f"{'+' if d['impact_pct']>=0 else ''}{d['impact_pct']}%", "source_agent": d["source_agent"]} for d in result["drivers"][:5]],
                "risk_flags": [{"flag": f["flag"], "severity": f["severity"]} for f in result["fraud_flags"]],
            }
            st.json(output_json)

else:
    st.info("👈 Configure property details in the sidebar and click **VALUATE** to run the 11-agent pipeline.")

    st.markdown("### Quick Start Examples")
    examples = [
        ("Pune Baner 2BHK", "Salaried IT professional's apartment — standard LAP case"),
        ("Mumbai Dadar 2BHK", "Old building in prime Mumbai — age vs location tradeoff"),
        ("Gorakhpur Golghar Warehouse", "Tier-3 industrial — low RPI, long sale time"),
        ("Hinjewadi Pune 4BHK 400sqft", "Fraud test — impossible configuration"),
    ]
    for title, desc in examples:
        st.markdown(f"- **{title}** — {desc}")
