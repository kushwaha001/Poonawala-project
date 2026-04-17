"""
LocationIntelAgent — UPGRADED with LLM-powered micro-market analysis.
Combines deterministic OSM data with intelligent market reasoning.
The math stays rule-based; the LLM enhances data interpretation.
"""
from app.agents.base import BaseAgent
from app.tools.circle_rate import lookup as cr_lookup
from app.tools.overpass import query_nearest_poi, query_poi_counts
from app.tools.llm import analyze_micro_market, estimate_dynamic_mcr
from app.math.formulas import compute_s_infra, compute_s_nbhd, compute_mcr, compute_f_loc, get_micro_bucket
from app.config.constants import POI_CONFIG, MCR_TABLE, BUILDER_REPUTATION, BUILDER_REPUTATION_PREMIUM, BUILDER_REPUTATION_PENALTY
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def _load_city_tier(city: str) -> int:
    try:
        df = pd.read_csv(DATA_DIR / "city_tiers.csv")
        match = df[df["city"].str.lower() == city.strip().lower()]
        if not match.empty:
            return int(match.iloc[0]["tier"])
    except Exception:
        pass
    return 3


def _extract_city_from_address(address: str) -> str:
    known_cities = [
        "mumbai", "delhi", "bangalore", "bengaluru", "pune", "chennai",
        "hyderabad", "kolkata", "ahmedabad", "surat", "vadodara", "rajkot",
        "gandhinagar", "jaipur", "jodhpur", "udaipur", "kota", "ajmer", "bikaner",
        "lucknow", "kanpur", "agra", "varanasi", "meerut", "ghaziabad", "noida",
        "prayagraj", "allahabad", "gorakhpur", "mathura", "bareilly", "moradabad", "aligarh",
        "nagpur", "nashik", "thane", "navi mumbai", "aurangabad", "solapur",
        "kolhapur", "amravati",
        "indore", "bhopal", "jabalpur", "gwalior", "ujjain",
        "patna", "gaya", "muzaffarpur", "bhagalpur", "darbhanga",
        "ranchi", "dhanbad", "jamshedpur",
        "bhubaneswar", "cuttack", "rourkela", "sambalpur",
        "kochi", "thiruvananthapuram", "kozhikode", "thrissur", "kollam",
        "coimbatore", "madurai", "trichy", "tiruchirappalli", "salem",
        "tirunelveli", "vellore", "erode",
        "visakhapatnam", "vijayawada", "guntur", "tirupati", "nellore", "kakinada",
        "warangal", "karimnagar",
        "mysuru", "mysore", "mangaluru", "mangalore", "hubli", "belgaum", "belagavi",
        "chandigarh", "ludhiana", "amritsar", "jalandhar", "patiala", "mohali",
        "gurugram", "gurgaon", "faridabad", "rohtak", "panipat", "karnal",
        "hisar", "ambala", "sonipat",
        "dehradun", "haridwar", "nainital",
        "shimla", "dharamshala",
        "guwahati", "dibrugarh", "silchar",
        "panaji", "margao",
        "raipur", "bilaspur", "durg",
        "kolkata", "howrah", "siliguri", "durgapur", "asansol",
        "jammu", "srinagar",
        "agartala", "shillong", "imphal", "kohima", "aizawl", "gangtok", "itanagar",
        "puducherry", "pondicherry", "port blair",
    ]
    addr_lower = address.lower()
    # Longer names first to avoid partial matches (e.g. "navi mumbai" before "mumbai")
    for c in sorted(known_cities, key=len, reverse=True):
        if c in addr_lower:
            return c.title()
    return ""


def _extract_locality(address: str) -> str:
    parts = [p.strip() for p in address.split(",")]
    return parts[0] if parts else ""


def _extract_state_district(address: str, city: str) -> tuple[str, str]:
    city_state_map = {
        # Maharashtra
        "mumbai": ("Maharashtra", "Mumbai"),
        "pune": ("Maharashtra", "Pune"),
        "nagpur": ("Maharashtra", "Nagpur"),
        "nashik": ("Maharashtra", "Nashik"),
        "thane": ("Maharashtra", "Thane"),
        "navi mumbai": ("Maharashtra", "Navi Mumbai"),
        "aurangabad": ("Maharashtra", "Aurangabad"),
        "solapur": ("Maharashtra", "Solapur"),
        "kolhapur": ("Maharashtra", "Kolhapur"),
        "amravati": ("Maharashtra", "Amravati"),
        "pcmc": ("Maharashtra", "Pune"),
        "pimpri": ("Maharashtra", "Pune"),
        "chinchwad": ("Maharashtra", "Pune"),
        # Delhi / NCR
        "delhi": ("Delhi", "Delhi"),
        "noida": ("Uttar Pradesh", "Noida"),
        "ghaziabad": ("Uttar Pradesh", "Ghaziabad"),
        "gurugram": ("Haryana", "Gurugram"),
        "gurgaon": ("Haryana", "Gurugram"),
        "faridabad": ("Haryana", "Faridabad"),
        # Karnataka
        "bangalore": ("Karnataka", "Bangalore"),
        "bengaluru": ("Karnataka", "Bangalore"),
        "mysuru": ("Karnataka", "Mysuru"),
        "mysore": ("Karnataka", "Mysuru"),
        "mangaluru": ("Karnataka", "Mangaluru"),
        "mangalore": ("Karnataka", "Mangaluru"),
        "hubli": ("Karnataka", "Hubli"),
        "belgaum": ("Karnataka", "Belagavi"),
        "belagavi": ("Karnataka", "Belagavi"),
        # Tamil Nadu
        "chennai": ("Tamil Nadu", "Chennai"),
        "coimbatore": ("Tamil Nadu", "Coimbatore"),
        "madurai": ("Tamil Nadu", "Madurai"),
        "trichy": ("Tamil Nadu", "Trichy"),
        "tiruchirappalli": ("Tamil Nadu", "Trichy"),
        "salem": ("Tamil Nadu", "Salem"),
        "tirunelveli": ("Tamil Nadu", "Tirunelveli"),
        "vellore": ("Tamil Nadu", "Vellore"),
        "erode": ("Tamil Nadu", "Erode"),
        # Telangana
        "hyderabad": ("Telangana", "Hyderabad"),
        "warangal": ("Telangana", "Warangal"),
        "karimnagar": ("Telangana", "Karimnagar"),
        # Andhra Pradesh
        "visakhapatnam": ("Andhra Pradesh", "Visakhapatnam"),
        "vijayawada": ("Andhra Pradesh", "Vijayawada"),
        "guntur": ("Andhra Pradesh", "Guntur"),
        "tirupati": ("Andhra Pradesh", "Tirupati"),
        "nellore": ("Andhra Pradesh", "Nellore"),
        "kakinada": ("Andhra Pradesh", "Kakinada"),
        # Gujarat
        "ahmedabad": ("Gujarat", "Ahmedabad"),
        "surat": ("Gujarat", "Surat"),
        "vadodara": ("Gujarat", "Vadodara"),
        "rajkot": ("Gujarat", "Rajkot"),
        "gandhinagar": ("Gujarat", "Gandhinagar"),
        "bhavnagar": ("Gujarat", "Bhavnagar"),
        "jamnagar": ("Gujarat", "Jamnagar"),
        "anand": ("Gujarat", "Anand"),
        # Rajasthan
        "jaipur": ("Rajasthan", "Jaipur"),
        "jodhpur": ("Rajasthan", "Jodhpur"),
        "udaipur": ("Rajasthan", "Udaipur"),
        "kota": ("Rajasthan", "Kota"),
        "ajmer": ("Rajasthan", "Ajmer"),
        "bikaner": ("Rajasthan", "Bikaner"),
        # Uttar Pradesh
        "lucknow": ("Uttar Pradesh", "Lucknow"),
        "kanpur": ("Uttar Pradesh", "Kanpur"),
        "agra": ("Uttar Pradesh", "Agra"),
        "varanasi": ("Uttar Pradesh", "Varanasi"),
        "meerut": ("Uttar Pradesh", "Meerut"),
        "prayagraj": ("Uttar Pradesh", "Prayagraj"),
        "allahabad": ("Uttar Pradesh", "Prayagraj"),
        "gorakhpur": ("Uttar Pradesh", "Gorakhpur"),
        "mathura": ("Uttar Pradesh", "Mathura"),
        "bareilly": ("Uttar Pradesh", "Bareilly"),
        "moradabad": ("Uttar Pradesh", "Moradabad"),
        "aligarh": ("Uttar Pradesh", "Aligarh"),
        # Madhya Pradesh
        "indore": ("Madhya Pradesh", "Indore"),
        "bhopal": ("Madhya Pradesh", "Bhopal"),
        "jabalpur": ("Madhya Pradesh", "Jabalpur"),
        "gwalior": ("Madhya Pradesh", "Gwalior"),
        "ujjain": ("Madhya Pradesh", "Ujjain"),
        # Bihar
        "patna": ("Bihar", "Patna"),
        "gaya": ("Bihar", "Gaya"),
        "muzaffarpur": ("Bihar", "Muzaffarpur"),
        "bhagalpur": ("Bihar", "Bhagalpur"),
        "darbhanga": ("Bihar", "Darbhanga"),
        # Jharkhand
        "ranchi": ("Jharkhand", "Ranchi"),
        "dhanbad": ("Jharkhand", "Dhanbad"),
        "jamshedpur": ("Jharkhand", "Jamshedpur"),
        # Odisha
        "bhubaneswar": ("Odisha", "Bhubaneswar"),
        "cuttack": ("Odisha", "Cuttack"),
        "rourkela": ("Odisha", "Rourkela"),
        "sambalpur": ("Odisha", "Sambalpur"),
        # Kerala
        "kochi": ("Kerala", "Kochi"),
        "thiruvananthapuram": ("Kerala", "Thiruvananthapuram"),
        "kozhikode": ("Kerala", "Kozhikode"),
        "thrissur": ("Kerala", "Thrissur"),
        "kollam": ("Kerala", "Kollam"),
        # West Bengal
        "kolkata": ("West Bengal", "Kolkata"),
        "howrah": ("West Bengal", "Howrah"),
        "siliguri": ("West Bengal", "Siliguri"),
        "durgapur": ("West Bengal", "Durgapur"),
        "asansol": ("West Bengal", "Asansol"),
        # Punjab / Haryana / Chandigarh
        "ludhiana": ("Punjab", "Ludhiana"),
        "amritsar": ("Punjab", "Amritsar"),
        "jalandhar": ("Punjab", "Jalandhar"),
        "patiala": ("Punjab", "Patiala"),
        "mohali": ("Punjab", "Mohali"),
        "chandigarh": ("Chandigarh", "Chandigarh"),
        "rohtak": ("Haryana", "Rohtak"),
        "panipat": ("Haryana", "Panipat"),
        "karnal": ("Haryana", "Karnal"),
        "hisar": ("Haryana", "Hisar"),
        "ambala": ("Haryana", "Ambala"),
        "sonipat": ("Haryana", "Sonipat"),
        # Uttarakhand
        "dehradun": ("Uttarakhand", "Dehradun"),
        "haridwar": ("Uttarakhand", "Haridwar"),
        "nainital": ("Uttarakhand", "Nainital"),
        # Himachal Pradesh
        "shimla": ("Himachal Pradesh", "Shimla"),
        "dharamshala": ("Himachal Pradesh", "Kangra"),
        # Assam
        "guwahati": ("Assam", "Kamrup"),
        "dibrugarh": ("Assam", "Dibrugarh"),
        "silchar": ("Assam", "Silchar"),
        # Goa
        "panaji": ("Goa", "North Goa"),
        "margao": ("Goa", "South Goa"),
        # Chhattisgarh
        "raipur": ("Chhattisgarh", "Raipur"),
        "bilaspur": ("Chhattisgarh", "Bilaspur"),
        "durg": ("Chhattisgarh", "Durg"),
        # J&K
        "jammu": ("Jammu and Kashmir", "Jammu"),
        "srinagar": ("Jammu and Kashmir", "Srinagar"),
        # North-East
        "agartala": ("Tripura", "West Tripura"),
        "shillong": ("Meghalaya", "East Khasi Hills"),
        "imphal": ("Manipur", "Imphal West"),
        "kohima": ("Nagaland", "Kohima"),
        "aizawl": ("Mizoram", "Aizawl"),
        "gangtok": ("Sikkim", "East Sikkim"),
        "itanagar": ("Arunachal Pradesh", "Papum Pare"),
        # UT
        "puducherry": ("Puducherry", "Puducherry"),
        "pondicherry": ("Puducherry", "Puducherry"),
        "port blair": ("Andaman and Nicobar", "South Andaman"),
    }
    return city_state_map.get(city.lower(), ("", city))


async def _estimate_circle_rate_llm(city: str, district: str, state: str, sub_type: str) -> float | None:
    """Ask the LLM to estimate a circle rate when CSV has no data for this location."""
    from app.tools.llm import call_llm_json
    system = """You are a real estate data expert for India.
Estimate the government circle rate (ready reckoner rate) for the given location.
Circle rates are set by state governments and used as the minimum property registration value.
Respond ONLY with valid JSON: {"rate_per_sqft": <integer>, "reasoning": "<one sentence>"}
Base your estimate on your knowledge of Indian property markets. Round to the nearest 500."""

    user = f"""Location: {city}, {district}, {state}
Property sub-type: {sub_type}
Estimate the circle rate per sqft in Indian Rupees for a typical mid-range locality in this city."""

    result = await call_llm_json(system, user,
                                  {"rate_per_sqft": 5000, "reasoning": "string"},
                                  temperature=0.1)
    if result and isinstance(result.get("rate_per_sqft"), (int, float)):
        rate = float(result["rate_per_sqft"])
        if 500 <= rate <= 100000:
            return rate
    return None


class LocationIntelAgent(BaseAgent):
    name = "location_intel"

    async def run(self, ctx: dict) -> dict:
        norm = ctx["input_normalizer"]
        inp = ctx["input"]
        lat, lon = norm["lat"], norm["lon"]
        address = norm["address"]

        city = _extract_city_from_address(address)
        locality = _extract_locality(address)
        state, district = _extract_state_district(address, city)
        city_tier = _load_city_tier(city)

        cr_result = cr_lookup(state, district, locality)
        circle_rate = cr_result["rate_per_sqft"]
        cr_match = cr_result.get("match_type", "unknown")

        # LLM fallback: when CSV has no data for this location, ask LLM to estimate
        if cr_match == "national_fallback":
            llm_cr = await _estimate_circle_rate_llm(city, district, state, inp.get("sub_type", "apartment"))
            if llm_cr:
                circle_rate = llm_cr
                cr_match = "llm_estimated"

        poi_distances = {}
        poi_breakdown = {}
        if lat and lon:
            for cat, cfg in POI_CONFIG.items():
                poi = await query_nearest_poi(lat, lon, cat, int(cfg["search_radius"] * 1000))
                dist = poi["distance_km"]
                poi_distances[cat] = dist
                poi_breakdown[f"{cat}_dist_km"] = round(dist, 2)
                poi_breakdown[f"{cat}_found"] = poi.get("found", False)

        s_infra = compute_s_infra(poi_distances)

        poi_counts = {"n_residential": 10, "n_commercial": 5, "n_industrial": 1}
        if lat and lon:
            poi_counts = await query_poi_counts(lat, lon)
        s_nbhd_raw = compute_s_nbhd(poi_counts["n_residential"], poi_counts["n_commercial"], poi_counts["n_industrial"])

        # Builder reputation adjustment to S_nbhd
        builder_raw = (inp.get("builder_name") or "").strip().lower()
        builder_rep_score = None
        builder_rep_adjustment = 0.0
        if builder_raw:
            for known, score in BUILDER_REPUTATION.items():
                if known in builder_raw or builder_raw in known:
                    builder_rep_score = score
                    break
            if builder_rep_score is None:
                builder_rep_adjustment = -BUILDER_REPUTATION_PENALTY
            elif builder_rep_score >= 0.88:
                builder_rep_adjustment = BUILDER_REPUTATION_PREMIUM

        s_nbhd = max(0.0, min(1.0, s_nbhd_raw + builder_rep_adjustment))

        # Rule-based MCR as baseline
        rule_mcr = compute_mcr(city_tier, s_infra)
        bucket = get_micro_bucket(s_infra)

        # LLM-powered dynamic MCR estimation
        llm_mcr_result = await estimate_dynamic_mcr(city, locality, city_tier, s_infra, inp["sub_type"], rule_mcr, circle_rate)
        llm_mcr = llm_mcr_result.get("estimated_mcr")
        llm_mcr_confidence = llm_mcr_result.get("confidence", 0.0)

        if llm_mcr and isinstance(llm_mcr, (int, float)) and 1.0 <= llm_mcr <= 3.0 and llm_mcr_confidence > 0.4:
            tier_bounds = MCR_TABLE.get(city_tier, MCR_TABLE[3])
            mcr_floor = tier_bounds["peripheral"] * 0.9
            mcr_ceil = tier_bounds["prime"] * 1.15
            llm_mcr_clamped = max(mcr_floor, min(mcr_ceil, llm_mcr))
            blend_weight = min(llm_mcr_confidence, 0.6)
            mcr = round(rule_mcr * (1 - blend_weight) + llm_mcr_clamped * blend_weight, 3)
            mcr_source = "blended_rule_llm"
        else:
            mcr = rule_mcr
            mcr_source = "rule_based"

        mcr = max(1.05, min(2.20, mcr))
        f_loc = compute_f_loc(s_infra, s_nbhd)

        # LLM micro-market intelligence
        micro_market = await analyze_micro_market(
            city, locality, inp["property_type"], inp["sub_type"],
            city_tier, poi_breakdown, inp["built_up_area_sqft"],
        )

        return {
            "circle_rate_per_sqft": circle_rate,
            "circle_rate_match": cr_match,
            "infra_score": round(s_infra, 4),
            "neighborhood_quality": round(s_nbhd, 4),
            "city_tier": city_tier,
            "city": city,
            "locality": locality,
            "state": state,
            "district": district,
            "mcr": mcr,
            "mcr_source": mcr_source,
            "rule_based_mcr": rule_mcr,
            "llm_mcr": llm_mcr_result,
            "micro_bucket": bucket,
            "f_loc": round(f_loc, 4),
            "poi_breakdown": poi_breakdown,
            "poi_counts": poi_counts,
            "micro_market_intelligence": micro_market,
            "s_nbhd_raw": round(s_nbhd_raw, 4),
            "builder_rep_score": builder_rep_score,
            "builder_rep_adjustment": round(builder_rep_adjustment, 4),
        }
