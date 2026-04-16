"""Circle rate lookup from CSV with fuzzy matching."""
import os
import pandas as pd
from rapidfuzz import process, fuzz
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

_df = None
_lookup: dict[tuple, float] = {}


def _load():
    global _df, _lookup
    csv_path = DATA_DIR / "circle_rates.csv"
    _df = pd.read_csv(csv_path)
    _df["locality_lower"] = _df["locality"].str.strip().str.lower()
    _df["district_lower"] = _df["district"].str.strip().str.lower()
    _df["state_lower"] = _df["state"].str.strip().str.lower()
    for _, row in _df.iterrows():
        key = (row["state_lower"], row["district_lower"], row["locality_lower"])
        _lookup[key] = float(row["rate_per_sqft"])


def lookup(state: str, district: str, locality: str) -> dict:
    if _df is None:
        _load()

    locality_slug = locality.strip().lower()
    district_slug = district.strip().lower()
    state_slug = state.strip().lower()

    exact_key = (state_slug, district_slug, locality_slug)
    if exact_key in _lookup:
        return {"rate_per_sqft": _lookup[exact_key], "match_type": "exact"}

    candidates = _df[_df["state_lower"] == state_slug]["locality_lower"].tolist()
    if candidates:
        match = process.extractOne(locality_slug, candidates, scorer=fuzz.token_sort_ratio)
        if match and match[1] > 60:
            matched_row = _df[(_df["state_lower"] == state_slug) & (_df["locality_lower"] == match[0])].iloc[0]
            return {"rate_per_sqft": float(matched_row["rate_per_sqft"]), "match_type": "fuzzy", "matched_locality": match[0], "score": match[1]}

    district_rows = _df[_df["district_lower"] == district_slug]
    if not district_rows.empty:
        avg = float(district_rows["rate_per_sqft"].mean())
        return {"rate_per_sqft": avg, "match_type": "district_average"}

    state_rows = _df[_df["state_lower"] == state_slug]
    if not state_rows.empty:
        avg = float(state_rows["rate_per_sqft"].mean())
        return {"rate_per_sqft": avg, "match_type": "state_average"}

    return {"rate_per_sqft": 5000, "match_type": "national_fallback"}
