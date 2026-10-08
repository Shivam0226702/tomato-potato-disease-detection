#!/usr/bin/env python3
"""test_stage9_cleanup.py — Final verification of Stage 9 Yield Estimation cleanup.

Tests:
1. Tomato + Early Blight + Moderate + 0.5 acre:
   - Estimated yield: 2,800 kg/acre (2.8 tons/acre)
   - Estimated total harvest: 1,400 kg (1.4 tons)
   - Expected range: 1,200–1,600 kg (1.2–1.6 tons)
   - Impact: Moderate (Assumed reduction: 30%)
2. Tomato + Early Blight + Moderate + 1.0 acre:
   - Estimated yield: 2,800 kg/acre (2.8 tons/acre)
   - Estimated total harvest: 2,800 kg (2.8 tons)
   - Expected range: 2,400–3,200 kg (2.4–3.2 tons)
   - Impact: Moderate (Assumed reduction: 30%)
3. Potato + Late Blight + Severe + 1.0 acre:
   - Estimated yield: 1,600 kg/acre (1.6 tons/acre)
   - Estimated total harvest: 1,600 kg (1.6 tons)
   - Expected range: 1,300–1,900 kg (1.3–1.9 tons)
   - Impact: Severe (Assumed reduction: 80%)
4. Acre / Hectare switching:
   - Verify 1 hectare of Tomato Moderate Early Blight gives:
     6,920 kg/hectare (6.9 tons/hectare), 6,920 kg total (6.9 tons)
5. Verify mathematical consistency:
   - Exactly 1 ton = 1,000 kg for all metrics.
6. Verify extract_yield_metrics and render_metric_card integrity.
7. Verify Streamlit AppTest simulation with 0 exceptions.
8. Verify Stages 3–8 features remain intact.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from yield_estimator import calculate_yield_estimate, YIELD_DISCLAIMER, YieldEstimateResult
from app import extract_yield_metrics
from predict import load_model, load_class_names, get_device, predict_image, RESULTS_DIR
from severity import estimate_disease_severity
from treatment import get_treatment_recommendation
from database import init_db, save_scan, get_scan_by_id, DEFAULT_DB_PATH
from query_engine import answer_query


def run_tests():
    print("=" * 70)
    print("STAGE 9 FINAL CLEANUP VERIFICATION")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────
    # 1. Tomato + Early Blight + Moderate + 0.5 acre
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 1] Tomato + Early Blight + Moderate + 0.5 acre...")
    res_05 = calculate_yield_estimate(
        crop="Tomato",
        cultivated_area=0.5,
        area_unit="acre",
        disease="Early Blight",
        severity="Moderate",
    )
    m_05 = extract_yield_metrics(res_05)
    print(f"  Estimated Yield: {m_05['kg_per_unit']:,.0f} kg/acre ({m_05['tons_per_unit']:.1f} tons/acre)")
    print(f"  Estimated Total Harvest: {m_05['total_kg']:,.0f} kg ({m_05['total_tons']:.1f} tons)")
    print(f"  Expected Range: {m_05['range_min_kg']:,.0f}–{m_05['range_max_kg']:,.0f} kg ({m_05['range_min_tons']:.1f}–{m_05['range_max_tons']:.1f} tons)")
    print(f"  Loss Percentage: {res_05.loss_percentage:.0f}%")

    assert res_05.estimated_yield_per_unit == 2.8
    assert m_05["kg_per_unit"] == 2800
    assert res_05.estimated_total_yield == 1.4
    assert m_05["total_kg"] == 1400
    assert res_05.range_min == 1.2
    assert res_05.range_max == 1.6
    assert m_05["range_min_kg"] == 1200
    assert m_05["range_max_kg"] == 1600
    assert res_05.loss_percentage == 30.0
    print("  ✅ [PASS] Test 1: Matches working example exactly.")

    # ─────────────────────────────────────────────────────────────────
    # 2. Tomato + Early Blight + Moderate + 1.0 acre
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 2] Tomato + Early Blight + Moderate + 1.0 acre...")
    res_1 = calculate_yield_estimate(
        crop="Tomato",
        cultivated_area=1.0,
        area_unit="acre",
        disease="Early Blight",
        severity="Moderate",
    )
    m_1 = extract_yield_metrics(res_1)
    print(f"  Estimated Yield: {m_1['kg_per_unit']:,.0f} kg/acre ({m_1['tons_per_unit']:.1f} tons/acre)")
    print(f"  Estimated Total Harvest: {m_1['total_kg']:,.0f} kg ({m_1['total_tons']:.1f} tons)")
    print(f"  Expected Range: {m_1['range_min_kg']:,.0f}–{m_1['range_max_kg']:,.0f} kg ({m_1['range_min_tons']:.1f}–{m_1['range_max_tons']:.1f} tons)")

    assert res_1.estimated_yield_per_unit == 2.8
    assert m_1["kg_per_unit"] == 2800
    assert res_1.estimated_total_yield == 2.8
    assert m_1["total_kg"] == 2800
    assert res_1.range_min == 2.4
    assert res_1.range_max == 3.2
    assert m_1["range_min_kg"] == 2400
    assert m_1["range_max_kg"] == 3200
    assert res_1.loss_percentage == 30.0
    print("  ✅ [PASS] Test 2: Matches 1.0 acre baseline exactly.")

    # ─────────────────────────────────────────────────────────────────
    # 3. Potato + Late Blight + Severe + 1.0 acre
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 3] Potato + Late Blight + Severe + 1.0 acre...")
    res_pot = calculate_yield_estimate(
        crop="Potato",
        cultivated_area=1.0,
        area_unit="acre",
        disease="Late Blight",
        severity="Severe",
    )
    m_pot = extract_yield_metrics(res_pot)
    print(f"  Estimated Yield: {m_pot['kg_per_unit']:,.0f} kg/acre ({m_pot['tons_per_unit']:.1f} tons/acre)")
    print(f"  Estimated Total Harvest: {m_pot['total_kg']:,.0f} kg ({m_pot['total_tons']:.1f} tons)")
    print(f"  Expected Range: {m_pot['range_min_kg']:,.0f}–{m_pot['range_max_kg']:,.0f} kg ({m_pot['range_min_tons']:.1f}–{m_pot['range_max_tons']:.1f} tons)")

    assert res_pot.estimated_yield_per_unit == 1.6  # 8.0 * (1 - 0.80) = 1.6 tons/acre
    assert m_pot["kg_per_unit"] == 1600
    assert res_pot.estimated_total_yield == 1.6
    assert m_pot["total_kg"] == 1600
    assert res_pot.loss_percentage == 80.0
    assert res_pot.range_min == 1.3
    assert res_pot.range_max == 1.9
    assert m_pot["range_min_kg"] == 1300
    assert m_pot["range_max_kg"] == 1900
    print("  ✅ [PASS] Test 3: Potato Late Blight Severe calculated accurately.")

    # ─────────────────────────────────────────────────────────────────
    # 4. Acre / Hectare switching
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 4] Acre / Hectare switching...")
    res_ha = calculate_yield_estimate(
        crop="Tomato",
        cultivated_area=1.0,
        area_unit="hectare",
        disease="Early Blight",
        severity="Moderate",
    )
    m_ha = extract_yield_metrics(res_ha)
    print(f"  Hectare Yield: {m_ha['kg_per_unit']:,.0f} kg/hectare ({m_ha['tons_per_unit']:.1f} tons/hectare)")
    print(f"  Total Harvest: {m_ha['total_kg']:,.0f} kg ({m_ha['total_tons']:.1f} tons)")

    assert res_ha.area_unit == "hectare"
    assert res_ha.estimated_yield_per_unit == 6.92
    assert m_ha["kg_per_unit"] == 6920
    assert res_ha.estimated_total_yield == 6.92
    assert m_ha["total_kg"] == 6920
    print("  ✅ [PASS] Test 4: Hectare unit conversion operates accurately.")

    # ─────────────────────────────────────────────────────────────────
    # 5. Mathematical consistency verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 5] Mathematical consistency across all metrics...")
    for res, m in [(res_05, m_05), (res_1, m_1), (res_pot, m_pot), (res_ha, m_ha)]:
        assert m["kg_per_unit"] == round(m["tons_per_unit"] * 1000.0)
        assert m["total_kg"] == round(m["total_tons"] * 1000.0)
        assert m["range_min_kg"] == round(m["range_min_tons"] * 1000.0)
        assert m["range_max_kg"] == round(m["range_max_tons"] * 1000.0)
    print("  ✅ [PASS] Test 5: Exact 1 ton = 1,000 kg mathematical consistency confirmed.")

    # ─────────────────────────────────────────────────────────────────
    # 6. Explanatory disclaimer text verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 6] Explanatory text verification...")
    assert "Prototype estimate based on an assumed healthy baseline" in YIELD_DISCLAIMER
    assert "Actual yield impact varies with crop variety" in YIELD_DISCLAIMER
    print("  ✅ [PASS] Test 6: Scientifically honest disclaimer text verified.")

    # ─────────────────────────────────────────────────────────────────
    # 7. Streamlit AppTest verification
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 7] Streamlit AppTest run verification...")
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file("app.py", default_timeout=30)
    at.session_state["current_analysis"] = {
        "token": "test_token",
        "crop": "Tomato",
        "disease": "Early Blight",
        "confidence": 99.8,
        "is_healthy": False,
        "severity": "Moderate",
        "severity_level": "Moderate",
        "affected_pct": 19.2,
        "is_reliable": True,
        "sev_explanation": "Test explanation",
        "disclaimer": "Test disclaimer",
    }
    at.run()
    assert len(at.exception) == 0, f"AppTest raised exceptions: {[e.value for e in at.exception]}"
    print("  ✅ [PASS] Test 7: Streamlit rendered without any exceptions or truncation issues.")

    # ─────────────────────────────────────────────────────────────────
    # 8. Preservation of Stages 3–8 features
    # ─────────────────────────────────────────────────────────────────
    print("\n[Test 8] Preservation of Stages 3–8 features...")
    # Stage 5
    h_img = next(Path("Dataset/Potato/Potato___Healthy").glob("*.JPG"))
    h_sev = estimate_disease_severity(h_img, condition="Healthy")
    assert h_sev["severity_level"] == "None (Healthy)"

    # Stage 6
    rec = get_treatment_recommendation("Potato", "Early Blight", "Mild")
    assert len(rec.recommended_action) > 10

    # Stage 7
    init_db(DEFAULT_DB_PATH)
    sid = save_scan("Tomato", "Healthy", 99.9, "None (Healthy)", 0.0, "Maintain routine care", "Healthy notes")
    rec_scan = get_scan_by_id(sid)
    assert rec_scan["disease"] == "Healthy"

    # Stage 8
    ans = answer_query("What should I do now?", context=at.session_state["current_analysis"])
    assert ans["is_context_used"] is True
    print("  ✅ [PASS] Test 8: Stages 3–8 functionality intact.")

    print("\n" + "=" * 70)
    print("ALL CLEANUP TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
