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

# §12 — Absorption priors (monthly unit sales within 1km radius)
# Source: NHB Residex H2-2023, Anarock Q3-2023, JLL India Residential Outlook 2024
# Tier 1: Mumbai, Bangalore, Delhi NCR, Hyderabad, Pune, Chennai
# Tier 2: Ahmedabad, Jaipur, Lucknow, Nagpur, Kochi, Chandigarh, Indore, Surat
# Tier 3: Remaining cities
ABSORPTION_PRIORS = {
    (1, "apartment"): 12, (1, "villa"): 3, (1, "plot"): 2, (1, "shop"): 4, (1, "warehouse"): 0.8, (1, "office"): 3,
    (2, "apartment"): 6,  (2, "villa"): 1.5, (2, "plot"): 1.5, (2, "shop"): 2.5, (2, "warehouse"): 0.4, (2, "office"): 1.5,
    (3, "apartment"): 2.5,(3, "villa"): 0.6, (3, "plot"): 0.8, (3, "shop"): 1.2, (3, "warehouse"): 0.2, (3, "office"): 0.5,
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

# §22 — RERA regulatory factor
# RERA-registered projects: escrow protection, transparent timelines → buyer premium
# Source: NHB impact study 2022 (5–8% price differential in major metros)
RERA_FACTOR_MAP = {True: 1.04, False: 0.96, None: 1.00}

# §23 — Builder reputation scores (0.0–1.0)
# Feeds into S_nbhd adjustment and risk flags
# Source: CRISIL developer credit ratings, RERA compliance records, JLL report 2023
BUILDER_REPUTATION: dict[str, float] = {
    "tata": 0.93, "dlf": 0.92, "oberoi": 0.91, "l&t realty": 0.91,
    "godrej": 0.90, "prestige": 0.90, "sobha": 0.89, "lodha": 0.88,
    "shapoorji pallonji": 0.90, "hiranandani": 0.88, "brigade": 0.87,
    "mahindra lifespace": 0.85, "kalpataru": 0.85, "adani realty": 0.86,
    "raymond realty": 0.83, "puravankara": 0.83, "kolte patil": 0.82,
    "rustomjee": 0.82, "casagrand": 0.80, "runwal": 0.81, "wadhwa": 0.80,
    "raheja": 0.79, "omkar": 0.79, "indiabulls real estate": 0.79,
    "nirmal": 0.77, "emaar india": 0.84, "marvel realtors": 0.78,
    "suntek realty": 0.78, "assets global": 0.75, "arihant": 0.78,
}
BUILDER_REPUTATION_PREMIUM = 0.04   # S_nbhd boost for score ≥ 0.88
BUILDER_REPUTATION_PENALTY = 0.06   # S_nbhd drag for unknown/unlisted builder

# Assertion bounds from §23
ASSERTION_BOUNDS = {
    "S_infra": (0.0, 1.0),
    "S_nbhd": (0.0, 1.0),
    "MCR": (1.05, 2.20),
    "f_loc": (0.85, 1.20),
    "f_age": (0.60, 1.00),
    "f_cfg": (0.85, 1.12),
    "f_legal": (0.85, 1.00),
    "f_floor": (0.85, 1.05),
    "u": (0.08, 0.25),
    "RPI": (0, 100),
    "C": (0.0, 1.0),
    "f_regulatory": (0.96, 1.04),
}
