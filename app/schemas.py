"""Pydantic models for all I/O contracts."""
from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, model_validator


class PropertyInput(BaseModel):
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    property_type: Literal["residential", "commercial", "industrial"]
    sub_type: Literal["apartment", "villa", "plot", "shop", "warehouse", "office", "other"]
    built_up_area_sqft: float
    age_years: int

    carpet_area_sqft: Optional[float] = None
    land_parcel_sqft: Optional[float] = None
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    has_lift: Optional[bool] = None
    configuration: Optional[str] = None
    ownership: Optional[Literal["freehold", "leasehold"]] = None
    title_clear: Optional[bool] = None
    occupancy: Optional[Literal["self_occupied", "rented", "vacant"]] = None
    monthly_rent: Optional[float] = None
    exterior_image_url: Optional[str] = None
    interior_image_url: Optional[str] = None
    declared_value: Optional[float] = None

    # ── Legal & Regulatory Compliance ──────────────────────────────────
    rera_registered: Optional[bool] = None           # RERA Act 2016
    occupancy_certificate: Optional[bool] = None     # OC from local authority
    completion_certificate: Optional[bool] = None    # CC from competent authority
    encumbrance_status: Optional[Literal[
        "clear", "existing_mortgage", "attachment_order", "disputed"
    ]] = None
    litigation_pending: Optional[bool] = None        # Active court case / injunction
    approved_plan_area_sqft: Optional[float] = None  # Sanctioned plan area

    # ── Rental Income Parameters ────────────────────────────────────────
    vacancy_rate_pct: Optional[float] = None   # % vacancy; default: tier/type-specific
    opex_ratio_pct: Optional[float] = None     # % of gross rent as operating expenses

    # ── Loan Parameters ─────────────────────────────────────────────────
    loan_amount_requested: Optional[float] = None

    @model_validator(mode="after")
    def check_location(self):
        if not self.address and (self.latitude is None or self.longitude is None):
            raise ValueError("Either address or (latitude, longitude) must be provided")
        return self


class KeyDriver(BaseModel):
    factor: str
    impact: str
    source_agent: str


class RiskFlag(BaseModel):
    flag: str
    severity: Literal["low", "medium", "high"]
    source_agent: str
    explanation: Optional[str] = None


class ValuationOutput(BaseModel):
    market_value_range: list[int]
    distress_value_range: list[int]
    forced_sale_value: Optional[int] = None
    realizable_value: Optional[int] = None
    reconstruction_value: Optional[int] = None
    resale_potential_index: int
    estimated_time_to_sell_days: list[int]
    confidence_score: float
    key_drivers: list[KeyDriver]
    risk_flags: list[RiskFlag]
    explanation: str
    agent_trace: dict
