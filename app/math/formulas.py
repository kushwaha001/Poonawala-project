"""Pure math functions implementing every formula from MATH_SPEC.
No LLM calls, no I/O — only deterministic computation."""
import math
from app.config.constants import (
    POI_CONFIG, STRUCTURE_DECAY_RATE, MAX_STRUCTURE_LOSS, STRUCTURE_RATIO,
    CONFIG_ELASTICITY, F_CFG_MIN, F_CFG_MAX, MCR_TABLE,
    INFRA_BUCKET_THRESHOLDS, INFRA_EXPECTED, F_LOC_MIN, F_LOC_MAX,
    F_LEGAL_MAP, F_FLOOR_MAP, U_BASELINE, U_DATA_COEFF, U_AGREE_COEFF,
    U_FRAUD_COEFF, U_MIN, U_MAX, ABSORPTION_PRIORS, AGE_LIQUIDITY_DECAY,
    CONFIG_LIQUIDITY_FACTOR, S_LEGAL_MAP, YIELD_EXPECTED, RPI_WEIGHTS,
    T_BASE_DAYS, HAZARD_EXPONENT, LOG_SPREAD, DISTRESS_BASE, DISTRESS_SLOPE,
    CONFIDENCE_WEIGHTS, AGREEMENT_COEFFICIENT, FRAUD_SEVERITY_WEIGHTS,
    NBHD_DEFAULT_WHEN_NO_DATA, NBHD_DENSITY_CAP, NBHD_DENSITY_LOG_BASE,
    RERA_FACTOR_MAP,
)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# §2 — Infrastructure Proximity Score
def compute_poi_score(distance_km: float, d_ref: float) -> float:
    return math.exp(-distance_km / d_ref)


def compute_s_infra(poi_distances: dict[str, float]) -> float:
    """poi_distances: {category: distance_km}"""
    total = 0.0
    for cat, cfg in POI_CONFIG.items():
        d = poi_distances.get(cat, cfg["search_radius"])
        score = compute_poi_score(d, cfg["d_ref"])
        total += cfg["weight"] * score
    return clamp(total, 0.0, 1.0)


# §3 — Neighborhood Quality Score
def compute_s_nbhd(n_residential: int, n_commercial: int, n_industrial: int) -> float:
    total = n_residential + n_commercial + n_industrial
    if total == 0:
        return NBHD_DEFAULT_WHEN_NO_DATA

    rho_r = n_residential / total
    rho_c = n_commercial / total
    rho_i = n_industrial / total

    base = 0.50 + 0.30 * rho_r + 0.20 * rho_c - 0.40 * rho_i
    density_b = min(NBHD_DENSITY_CAP,
                    NBHD_DENSITY_CAP * math.log(1 + total) / math.log(NBHD_DENSITY_LOG_BASE))
    return clamp(base + density_b, 0.0, 1.0)


# §4 — Market-to-Circle Ratio
def get_micro_bucket(s_infra: float) -> str:
    if s_infra > INFRA_BUCKET_THRESHOLDS["prime"]:
        return "prime"
    elif s_infra > INFRA_BUCKET_THRESHOLDS["standard"]:
        return "standard"
    return "peripheral"


def compute_mcr(city_tier: int, s_infra: float) -> float:
    bucket = get_micro_bucket(s_infra)
    tier = clamp(city_tier, 1, 3)
    return MCR_TABLE[int(tier)][bucket]


# §5 — Micro-Location Adjustment
def compute_f_loc(s_infra: float, s_nbhd: float) -> float:
    bucket = get_micro_bucket(s_infra)
    s_expected = INFRA_EXPECTED[bucket]
    f = 1.0 + 0.25 * (s_infra - s_expected) + 0.15 * (s_nbhd - 0.50)
    return clamp(f, F_LOC_MIN, F_LOC_MAX)


# §6 — Age Factor
def compute_f_age(age_years: int, sub_type: str) -> float:
    s = STRUCTURE_RATIO.get(sub_type, STRUCTURE_RATIO.get("apartment", 0.55))
    decay = 1.0 - math.exp(-STRUCTURE_DECAY_RATE * age_years)
    f = 1.0 - s * MAX_STRUCTURE_LOSS * decay
    return clamp(f, 0.60, 1.00)


# §7 — Configuration Factor
def compute_f_cfg(area_sqft: float, mode_area: float) -> float:
    if mode_area <= 0:
        return 1.0
    delta = abs(area_sqft - mode_area) / mode_area
    f = 1.0 - CONFIG_ELASTICITY * delta
    return clamp(f, F_CFG_MIN, F_CFG_MAX)


def compute_delta(area_sqft: float, mode_area: float) -> float:
    if mode_area <= 0:
        return 0.0
    return abs(area_sqft - mode_area) / mode_area


# §8 — Legal Factor
def compute_f_legal(ownership: str | None, title_clear: bool | None) -> float:
    key = (ownership, title_clear)
    return F_LEGAL_MAP.get(key, 0.95)


# §9 — Floor Factor
def compute_f_floor(floor: int | None, total_floors: int | None,
                    has_lift: bool | None, sub_type: str,
                    property_type: str) -> float:
    if sub_type in ("plot", "villa", "warehouse"):
        return F_FLOOR_MAP["not_applicable"]
    if floor is None:
        return F_FLOOR_MAP["not_applicable"]

    if floor == 0:
        if sub_type == "shop":
            return F_FLOOR_MAP["ground_shop"]
        return F_FLOOR_MAP["ground_residential"]
    elif floor <= 3:
        return F_FLOOR_MAP["low_1_3"]
    elif floor <= 8:
        return F_FLOOR_MAP["mid_4_8"]
    elif floor <= 15:
        if has_lift:
            return F_FLOOR_MAP["high_9_15_lift"]
        return F_FLOOR_MAP["high_9_15_no_lift"]
    else:
        if has_lift:
            return F_FLOOR_MAP["very_high_lift"]
        return F_FLOOR_MAP["very_high_no_lift"]


# §10a — RERA Regulatory Factor
def compute_f_regulatory(rera_registered: bool | None) -> float:
    return RERA_FACTOR_MAP.get(rera_registered, 1.00)


# §10 — Master Valuation
def compute_valuation(circle_rate: float, area: float, mcr: float,
                      f_loc: float, f_age: float, f_cfg: float,
                      f_legal: float, f_floor: float,
                      f_regulatory: float = 1.00) -> float:
    return circle_rate * area * mcr * f_loc * f_age * f_cfg * f_legal * f_floor * f_regulatory


# §10 — Driver contributions
def compute_driver_contributions(mcr: float, f_loc: float, f_age: float,
                                  f_cfg: float, f_legal: float,
                                  f_floor: float,
                                  f_regulatory: float = 1.00) -> list[dict]:
    drivers = [
        {"factor": "market_to_circle_ratio", "value": mcr, "impact_pct": round((mcr - 1.0) * 100, 1), "source_agent": "location_intel"},
        {"factor": "micro_location_adjustment", "value": f_loc, "impact_pct": round((f_loc - 1.0) * 100, 1), "source_agent": "location_intel"},
        {"factor": "age_depreciation", "value": f_age, "impact_pct": round((f_age - 1.0) * 100, 1), "source_agent": "property_char"},
        {"factor": "config_factor", "value": f_cfg, "impact_pct": round((f_cfg - 1.0) * 100, 1), "source_agent": "property_char"},
        {"factor": "legal_factor", "value": f_legal, "impact_pct": round((f_legal - 1.0) * 100, 1), "source_agent": "legal"},
        {"factor": "floor_factor", "value": f_floor, "impact_pct": round((f_floor - 1.0) * 100, 1), "source_agent": "property_char"},
        {"factor": "rera_regulatory_factor", "value": f_regulatory, "impact_pct": round((f_regulatory - 1.0) * 100, 1), "source_agent": "legal"},
    ]
    return sorted(drivers, key=lambda d: abs(d["impact_pct"]), reverse=True)


# §11 — Uncertainty band
def compute_uncertainty(q_data: float, q_agree: float, p_fraud: float) -> float:
    u = (U_BASELINE
         + U_DATA_COEFF * (1.0 - q_data)
         + U_AGREE_COEFF * (1.0 - q_agree)
         + U_FRAUD_COEFF * p_fraud)
    return clamp(u, U_MIN, U_MAX)


def compute_mv_range(v: float, u: float) -> list[int]:
    return [round(v * (1 - u)), round(v * (1 + u))]


# §12 — Supply-Demand Score
def compute_s_ds(listings_1km: int | None, city_tier: int, sub_type: str) -> float:
    if listings_1km is None:
        return 0.45
    m_abs = ABSORPTION_PRIORS.get((city_tier, sub_type), 2)
    moi = listings_1km / max(m_abs, 1)
    return math.exp(-moi / 12.0)


# §13 — Age Liquidity Score
def compute_s_age_liq(age_years: int) -> float:
    return math.exp(-age_years / AGE_LIQUIDITY_DECAY)


# §14 — Configuration Standardness Score (liquidity)
def compute_s_cfg_liquidity(delta: float) -> float:
    return math.exp(-CONFIG_LIQUIDITY_FACTOR * delta)


# §15 — Legal Clarity Score (liquidity)
def compute_s_legal_liquidity(ownership: str | None, title_clear: bool | None) -> float:
    key = (ownership, title_clear)
    return S_LEGAL_MAP.get(key, 0.85)


# §16 — Rental Yield Score
def compute_s_yield(monthly_rent: float | None, v_prior: float,
                    city_tier: int, property_type: str) -> float:
    if monthly_rent is None or v_prior <= 0:
        return 0.50
    annual_yield = (monthly_rent * 12) / v_prior
    ptype = "residential" if property_type == "residential" else "commercial"
    yield_range = YIELD_EXPECTED.get((city_tier, ptype), (0.025, 0.045))
    low, high = yield_range
    span = high - low
    if span <= 0:
        return 0.50
    return clamp((annual_yield - low) / span, 0.0, 1.0)


# §17 — Resale Potential Index
def compute_rpi(s_infra: float, s_cfg: float, s_ds: float,
                s_legal: float, s_age_liq: float, s_yield: float) -> float:
    rpi = 100 * (
        RPI_WEIGHTS["infra"] * s_infra +
        RPI_WEIGHTS["cfg"] * s_cfg +
        RPI_WEIGHTS["ds"] * s_ds +
        RPI_WEIGHTS["legal"] * s_legal +
        RPI_WEIGHTS["age_liq"] * s_age_liq +
        RPI_WEIGHTS["yield"] * s_yield
    )
    return clamp(rpi, 0, 100)


# §18 — Time-to-Liquidate
def compute_ttl(rpi: float, sub_type: str) -> list[int]:
    t_base = T_BASE_DAYS.get(sub_type, 90)
    safe_rpi = max(rpi, 5)
    h = (safe_rpi / 50.0) ** HAZARD_EXPONENT
    tau_median = t_base / h
    tau_low = max(7, round(tau_median * math.exp(-LOG_SPREAD)))
    tau_high = round(tau_median * math.exp(LOG_SPREAD))
    return [tau_low, tau_high]


# §19 — Distress Value
def compute_distress_range(mv_range: list[int], rpi: float) -> list[int]:
    d = DISTRESS_BASE + DISTRESS_SLOPE * (1.0 - rpi / 100.0)
    d_low = round(mv_range[0] * (1 - d) * 0.95)
    d_high = round(mv_range[1] * (1 - d) * 1.05)
    return [d_low, d_high]


# §20.1 — Data completeness
def compute_q_data(input_data: dict) -> float:
    mandatory = ["address_or_coords", "property_type", "sub_type", "built_up_area_sqft", "age_years"]
    optional = ["floor", "ownership", "title_clear", "occupancy", "monthly_rent",
                "exterior_image_url", "interior_image_url"]
    m_present = sum(1 for f in mandatory if input_data.get(f) is not None)
    o_present = sum(1 for f in optional if input_data.get(f) is not None)
    return 0.60 * (m_present / len(mandatory)) + 0.40 * (o_present / len(optional))


# §20.2 — Cross-source agreement
def compute_q_agree(values: list[float]) -> float:
    valid = [v for v in values if v is not None and v > 0]
    if len(valid) < 2:
        return 0.50
    mu = sum(valid) / len(valid)
    variance = sum((v - mu) ** 2 for v in valid) / len(valid)
    sigma = math.sqrt(variance)
    cv = sigma / mu if mu > 0 else 0
    return math.exp(-AGREEMENT_COEFFICIENT * cv)


# §20.3 — Locality data density
def compute_q_density(listings_1km: int | None) -> float:
    if listings_1km is None:
        return 0.30
    return min(1.0, math.log(1 + listings_1km) / math.log(51))


# §20.4 — Fraud penalty
def compute_p_fraud(fraud_flags: list[dict]) -> float:
    total = sum(FRAUD_SEVERITY_WEIGHTS.get(f.get("severity", "low"), 0.10) for f in fraud_flags)
    return min(1.0, total)


# §20.5 — Combined confidence
def compute_confidence(q_data: float, q_agree: float, q_density: float, p_fraud: float) -> float:
    c = (CONFIDENCE_WEIGHTS["data"] * q_data +
         CONFIDENCE_WEIGHTS["agree"] * q_agree +
         CONFIDENCE_WEIGHTS["density"] * q_density +
         CONFIDENCE_WEIGHTS["fraud"] * (1 - p_fraud))
    return clamp(c, 0.0, 1.0)


def confidence_label(c: float) -> str:
    if c >= 0.85:
        return "High"
    elif c >= 0.65:
        return "Medium"
    elif c >= 0.45:
        return "Low"
    return "Unreliable"
