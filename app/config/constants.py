"""
Single source of truth for all tunable constants.
Every constant from MATH_SPEC §24 lives here.
"""

# §2 — POI categories: (weight, reference_distance_km, search_radius_km)
POI_CONFIG = {
    "metro":      {"weight": 0.20, "d_ref": 1.0, "search_radius": 3.0},
    "highway":    {"weight": 0.15, "d_ref": 1.5, "search_radius": 3.0},
    "school":     {"weight": 0.15, "d_ref": 0.8, "search_radius": 2.0},
    "hospital":   {"weight": 0.15, "d_ref": 1.5, "search_radius": 3.0},
    "commercial": {"weight": 0.20, "d_ref": 2.0, "search_radius": 3.0},
    "it_park":    {"weight": 0.15, "d_ref": 3.0, "search_radius": 5.0},
}

# §6 — Age depreciation
STRUCTURE_DECAY_RATE = 0.04   # k
MAX_STRUCTURE_LOSS = 0.60     # D_max

STRUCTURE_RATIO = {
    "plot": 0.00,
    "villa": 0.35,
    "apartment": 0.55,
    "apartment_highrise": 0.60,
    "shop": 0.50,
    "office": 0.55,
    "warehouse": 0.65,
}

# §7 — Configuration factor
CONFIG_ELASTICITY = 0.08   # φ
F_CFG_MIN = 0.85
F_CFG_MAX = 1.12

# §4 — MCR table (city_tier -> bucket -> value)
MCR_TABLE = {
    1: {"prime": 2.20, "standard": 1.70, "peripheral": 1.30},
    2: {"prime": 1.60, "standard": 1.30, "peripheral": 1.10},
    3: {"prime": 1.20, "standard": 1.10, "peripheral": 1.05},
}

# §5 — Micro-location adjustment
INFRA_BUCKET_THRESHOLDS = {"prime": 0.55, "standard": 0.30}
INFRA_EXPECTED = {"prime": 0.70, "standard": 0.45, "peripheral": 0.20}
F_LOC_MIN = 0.85
F_LOC_MAX = 1.20

# §8 — Legal factor
F_LEGAL_MAP = {
    ("freehold", True): 1.00,
    ("freehold", None): 0.95,
    ("leasehold", True): 0.92,
    ("leasehold", None): 0.92,
    ("leasehold", False): 0.92,
    ("freehold", False): 0.85,
    (None, None): 0.95,
    (None, True): 0.95,
    (None, False): 0.85,
}

# §9 — Floor factor
F_FLOOR_MAP = {
    "ground_residential": 0.97,
    "ground_shop": 1.05,
    "low_1_3": 1.00,
    "mid_4_8": 1.02,
    "high_9_15_lift": 1.03,
    "high_9_15_no_lift": 0.90,
    "very_high_lift": 1.02,
    "very_high_no_lift": 0.85,
    "not_applicable": 1.00,
}

# §11 — Uncertainty band
U_BASELINE = 0.08
U_DATA_COEFF = 0.10
U_AGREE_COEFF = 0.08
U_FRAUD_COEFF = 0.06
U_MIN = 0.08
U_MAX = 0.25

# §12 — Absorption priors (monthly sales within 1km)
ABSORPTION_PRIORS = {
    (1, "apartment"): 8, (1, "villa"): 2, (1, "plot"): 1, (1, "shop"): 3, (1, "warehouse"): 0.5, (1, "office"): 2,
    (2, "apartment"): 4, (2, "villa"): 1, (2, "plot"): 1, (2, "shop"): 2, (2, "warehouse"): 0.3, (2, "office"): 1,
    (3, "apartment"): 2, (3, "villa"): 0.5, (3, "plot"): 0.5, (3, "shop"): 1, (3, "warehouse"): 0.2, (3, "office"): 0.5,
}

# §13 — Age liquidity decay
AGE_LIQUIDITY_DECAY = 30  # years

# §14 — Config standardness liquidity factor
CONFIG_LIQUIDITY_FACTOR = 2.0

# §15 — Legal clarity for liquidity
S_LEGAL_MAP = {
    ("freehold", True): 1.00,
    ("freehold", None): 0.85,
    ("leasehold", True): 0.75,
    ("leasehold", None): 0.75,
    ("leasehold", False): 0.75,
    ("freehold", False): 0.40,
    (None, None): 0.85,
    (None, True): 0.85,
    (None, False): 0.40,
}

# §16 — Rental yield expected ranges
YIELD_EXPECTED = {
    (1, "residential"): (0.020, 0.035),
    (1, "commercial"): (0.050, 0.080),
    (2, "residential"): (0.025, 0.045),
    (2, "commercial"): (0.055, 0.090),
    (3, "residential"): (0.030, 0.050),
    (3, "commercial"): (0.060, 0.100),
}

# §17 — RPI weights
RPI_WEIGHTS = {
    "infra": 0.30,
    "cfg": 0.20,
    "ds": 0.20,
    "legal": 0.15,
    "age_liq": 0.10,
    "yield": 0.05,
}

# §18 — Time-to-liquidate
T_BASE_DAYS = {
    "apartment": 60,
    "villa": 90,
    "shop": 75,
    "office": 100,
    "plot": 120,
    "warehouse": 150,
}
HAZARD_EXPONENT = 1.5
LOG_SPREAD = 0.40  # σ_τ

# §19 — Distress discount
DISTRESS_BASE = 0.15
DISTRESS_SLOPE = 0.25

# §20 — Confidence score
CONFIDENCE_WEIGHTS = {
    "data": 0.40,
    "agree": 0.30,
    "density": 0.20,
    "fraud": 0.10,
}
AGREEMENT_COEFFICIENT = 3.0

# §20.4 — Fraud severity weights
FRAUD_SEVERITY_WEIGHTS = {"low": 0.10, "medium": 0.25, "high": 0.50}

# §21.3 — Min viable areas by config
MIN_CONFIG_AREAS = {
    "1BHK": 300,
    "1RK": 200,
    "2BHK": 550,
    "3BHK": 850,
    "4BHK": 1200,
    "5BHK": 1800,
}

# §3 — Neighborhood quality defaults
NBHD_DEFAULT_WHEN_NO_DATA = 0.30
NBHD_DENSITY_CAP = 0.20
NBHD_DENSITY_LOG_BASE = 101

# §16b — Rental income operational defaults by (city_tier, property_type)
VACANCY_DEFAULTS = {
    (1, "residential"): 0.05, (1, "commercial"): 0.10,
    (2, "residential"): 0.07, (2, "commercial"): 0.12,
    (3, "residential"): 0.08, (3, "commercial"): 0.15,
}
OPEX_DEFAULTS = {
    "residential": 0.18,   # maintenance, PM fees, property tax, insurance
    "commercial": 0.28,    # higher maintenance + management costs
    "industrial": 0.22,
}

# §16c — Net capitalisation rate expected ranges (post vacancy + opex)
NET_YIELD_EXPECTED = {
    (1, "residential"): (0.014, 0.024),
    (1, "commercial"): (0.032, 0.052),
    (2, "residential"): (0.016, 0.030),
    (2, "commercial"): (0.036, 0.058),
    (3, "residential"): (0.018, 0.034),
    (3, "commercial"): (0.040, 0.066),
}

# §22 — Reconstruction / replacement cost (₹/sqft, 2024–25 rates)
CONSTRUCTION_COST_PER_SQFT = {
    (1, "apartment"): 2200, (1, "villa"): 2800, (1, "shop"): 2500,
    (1, "office"): 2600, (1, "warehouse"): 1800, (1, "other"): 2000,
    (2, "apartment"): 1800, (2, "villa"): 2200, (2, "shop"): 1900,
    (2, "office"): 2000, (2, "warehouse"): 1400, (2, "other"): 1700,
    (3, "apartment"): 1400, (3, "villa"): 1700, (3, "shop"): 1500,
    (3, "office"): 1600, (3, "warehouse"): 1100, (3, "other"): 1300,
}
RECONSTRUCTION_DEPRECIATION_RATE = 0.015   # 1.5 %/yr straight-line; cap at 70 %

# §23 — Realizable value & forced sale
TRANSACTION_COST_PCT = 0.05      # 5 % (2.5 % brokerage + 1 % legal + 1.5 % misc)
FORCED_SALE_FACTOR  = 0.72       # FSV = 72 % of FMV mid-point (RBI/NHB: 60–75 %)

# §24 — Regulatory compliance haircut factors (multiplicative)
REGULATORY_HAIRCUTS = {
    "no_oc":                  0.92,   # Missing Occupancy Certificate
    "no_cc":                  0.95,   # Missing Completion Certificate
    "no_rera_uc":             0.95,   # Under-construction, not RERA-registered
    "litigation":             0.80,   # Active litigation pending
    "encumbrance_mortgage":   0.90,   # Existing first charge / mortgage
    "encumbrance_attachment": 0.70,   # Court attachment order
    "encumbrance_disputed":   0.75,   # Disputed / unresolved encumbrance
    "plan_deviation_gt10pct": 0.95,   # Built area deviates > 10 % from approved plan
}

# Assertion bounds from §23
ASSERTION_BOUNDS = {
    "S_infra": (0.0, 1.0),
    "S_nbhd": (0.0, 1.0),
    "MCR": (1.05, 2.20),
    "f_loc": (0.85, 1.20),
    "f_age": (0.60, 1.00),
    "f_cfg": (0.85, 1.12),
    "f_legal": (0.85, 1.00),       # ownership/title factor only
    "f_regulatory": (0.40, 1.00),  # compliance factor
    "f_floor": (0.85, 1.05),
    "u": (0.08, 0.25),
    "RPI": (0, 100),
    "C": (0.0, 1.0),
}
