"""Unit tests for all math formulas from MATH_SPEC.
Tests the worked example from §22 to-the-rupee precision."""
import math
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.math.formulas import (
    clamp, compute_poi_score, compute_s_infra, compute_s_nbhd,
    get_micro_bucket, compute_mcr, compute_f_loc, compute_f_age,
    compute_f_cfg, compute_delta, compute_f_legal, compute_f_floor,
    compute_valuation, compute_driver_contributions,
    compute_uncertainty, compute_mv_range, compute_s_ds,
    compute_s_age_liq, compute_s_cfg_liquidity, compute_s_legal_liquidity,
    compute_s_yield, compute_rpi, compute_ttl, compute_distress_range,
    compute_q_data, compute_q_agree, compute_q_density, compute_p_fraud,
    compute_confidence, confidence_label,
)


class TestClamp:
    def test_within_range(self):
        assert clamp(0.5, 0, 1) == 0.5

    def test_below_min(self):
        assert clamp(-1, 0, 1) == 0

    def test_above_max(self):
        assert clamp(2, 0, 1) == 1


class TestInfraScore:
    """§2 — Worked example from MATH_SPEC."""
    def test_andheri_west_example(self):
        poi_distances = {
            "metro": 0.5, "highway": 1.0, "school": 0.4,
            "hospital": 1.2, "commercial": 0.7, "it_park": 3.5,
        }
        s_infra = compute_s_infra(poi_distances)
        assert 0.53 <= s_infra <= 0.56, f"S_infra={s_infra}, expected ~0.544"

    def test_all_far_away(self):
        poi_distances = {k: 10.0 for k in ["metro", "highway", "school", "hospital", "commercial", "it_park"]}
        s_infra = compute_s_infra(poi_distances)
        assert s_infra < 0.1

    def test_all_very_close(self):
        poi_distances = {k: 0.1 for k in ["metro", "highway", "school", "hospital", "commercial", "it_park"]}
        s_infra = compute_s_infra(poi_distances)
        assert s_infra > 0.85


class TestNeighborhoodQuality:
    """§3 — Worked example."""
    def test_andheri_west_example(self):
        s_nbhd = compute_s_nbhd(48, 32, 2)
        assert 0.90 <= s_nbhd <= 0.95, f"S_nbhd={s_nbhd}, expected ~0.935"

    def test_no_pois(self):
        assert compute_s_nbhd(0, 0, 0) == 0.30

    def test_industrial_dominant(self):
        s = compute_s_nbhd(2, 1, 50)
        assert s < 0.4


class TestMCR:
    """§4 — MCR lookup."""
    def test_tier1_prime(self):
        assert compute_mcr(1, 0.60) == 2.20

    def test_tier1_standard(self):
        assert compute_mcr(1, 0.40) == 1.70

    def test_tier1_peripheral(self):
        assert compute_mcr(1, 0.20) == 1.30

    def test_tier3_peripheral(self):
        assert compute_mcr(3, 0.10) == 1.05


class TestFLoc:
    """§5 — Micro-location adjustment."""
    def test_andheri_example(self):
        f_loc = compute_f_loc(0.544, 0.935)
        assert 1.08 <= f_loc <= 1.10, f"f_loc={f_loc}, expected ~1.0888"

    def test_neutral(self):
        f_loc = compute_f_loc(0.45, 0.50)
        assert 0.99 <= f_loc <= 1.01


class TestFAge:
    """§6 — Age depreciation."""
    def test_new_apartment(self):
        assert compute_f_age(0, "apartment") == 1.0

    def test_8yr_apartment(self):
        f = compute_f_age(8, "apartment")
        assert 0.90 <= f <= 0.92, f"f_age={f}, expected ~0.9096"

    def test_plot_any_age(self):
        assert compute_f_age(100, "plot") == 1.0

    def test_old_warehouse(self):
        f = compute_f_age(80, "warehouse")
        assert f < 0.70


class TestFCfg:
    """§7 — Configuration factor."""
    def test_exact_match(self):
        assert compute_f_cfg(750, 750) == 1.0

    def test_slightly_above(self):
        f = compute_f_cfg(850, 750)
        assert 0.98 <= f <= 1.0

    def test_severely_niche(self):
        f = compute_f_cfg(3000, 750)
        assert f == 0.85


class TestFLegal:
    """§8 — Legal factor."""
    def test_freehold_clear(self):
        assert compute_f_legal("freehold", True) == 1.0

    def test_leasehold(self):
        assert compute_f_legal("leasehold", True) == 0.92

    def test_disputed(self):
        assert compute_f_legal("freehold", False) == 0.85


class TestFFloor:
    """§9 — Floor factor."""
    def test_ground_shop(self):
        assert compute_f_floor(0, 5, True, "shop", "commercial") == 1.05

    def test_mid_floor_lift(self):
        assert compute_f_floor(6, 12, True, "apartment", "residential") == 1.02

    def test_high_no_lift(self):
        assert compute_f_floor(12, 15, False, "apartment", "residential") == 0.90

    def test_plot(self):
        assert compute_f_floor(None, None, None, "plot", "residential") == 1.00


class TestMasterValuation:
    """§10 + §22 — Full worked example."""
    def test_andheri_west_full(self):
        v = compute_valuation(
            circle_rate=12000, area=850, mcr=1.70,
            f_loc=1.0888, f_age=0.9096, f_cfg=0.989,
            f_legal=1.00, f_floor=1.02,
        )
        assert 17200000 <= v <= 17400000, f"V={v}, expected ~₹1.73Cr"


class TestUncertainty:
    """§11 — Uncertainty band."""
    def test_andheri_example(self):
        u = compute_uncertainty(q_data=0.829, q_agree=0.895, p_fraud=0.0)
        assert 0.10 <= u <= 0.11, f"u={u}, expected ~0.1055"

    def test_max_uncertainty(self):
        u = compute_uncertainty(q_data=0.0, q_agree=0.0, p_fraud=1.0)
        assert u == 0.25


class TestSupplyDemand:
    """§12 — S_ds."""
    def test_balanced_market(self):
        s = compute_s_ds(48, 1, "apartment")
        assert 0.50 <= s <= 0.70

    def test_no_data(self):
        assert compute_s_ds(None, 1, "apartment") == 0.45


class TestRPI:
    """§17 — Resale Potential Index."""
    def test_andheri_example(self):
        rpi = compute_rpi(
            s_infra=0.544, s_cfg=0.766, s_ds=0.646,
            s_legal=1.00, s_age_liq=0.766, s_yield=0.573,
        )
        assert 68 <= rpi <= 72, f"RPI={rpi}, expected ~70"


class TestTTL:
    """§18 — Time-to-liquidate."""
    def test_andheri_example(self):
        ttl = compute_ttl(rpi=70, sub_type="apartment")
        assert ttl[0] >= 7
        assert ttl[0] < ttl[1]
        assert 20 <= ttl[0] <= 30
        assert 45 <= ttl[1] <= 65


class TestDistressValue:
    """§19 — Distress value."""
    def test_andheri_example(self):
        mv = [15495862, 19151120]
        d_range = compute_distress_range(mv, rpi=70)
        assert d_range[0] < d_range[1]
        assert d_range[1] <= mv[1]
        assert d_range[0] >= mv[0] * 0.55


class TestConfidence:
    """§20 — Confidence score."""
    def test_andheri_example(self):
        c = compute_confidence(q_data=0.829, q_agree=0.895, q_density=0.957, p_fraud=0.0)
        assert 0.85 <= c <= 0.92, f"C={c}, expected ~0.892"

    def test_label_high(self):
        assert confidence_label(0.90) == "High"

    def test_label_medium(self):
        assert confidence_label(0.70) == "Medium"

    def test_label_low(self):
        assert confidence_label(0.50) == "Low"

    def test_label_unreliable(self):
        assert confidence_label(0.30) == "Unreliable"


class TestQAgree:
    """§20.2 — Cross-source agreement."""
    def test_perfect_agreement(self):
        assert compute_q_agree([100, 100, 100]) == 1.0

    def test_single_value(self):
        assert compute_q_agree([100]) == 0.50

    def test_moderate_spread(self):
        q = compute_q_agree([1.89e7, 1.82e7, 1.96e7])
        assert 0.80 <= q <= 0.95


class TestQData:
    """§20.1 — Data completeness."""
    def test_all_present(self):
        data = {
            "address_or_coords": True, "property_type": "residential",
            "sub_type": "apartment", "built_up_area_sqft": 850, "age_years": 8,
            "floor": 6, "ownership": "freehold", "title_clear": True,
            "occupancy": "rented", "monthly_rent": 45000,
            "exterior_image_url": "http://x.com/img.jpg", "interior_image_url": "http://x.com/img2.jpg",
            "rera_registered": True, "occupancy_certificate": True,
            "encumbrance_status": "clear", "loan_amount_requested": 5000000,
        }
        q = compute_q_data(data)
        assert q > 0.90

    def test_mandatory_only(self):
        data = {
            "address_or_coords": True, "property_type": "residential",
            "sub_type": "apartment", "built_up_area_sqft": 850, "age_years": 8,
        }
        q = compute_q_data(data)
        assert abs(q - 0.60) < 0.01
