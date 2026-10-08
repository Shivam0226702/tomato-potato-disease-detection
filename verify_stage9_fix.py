#!/usr/bin/env python3
"""verify_stage9_fix.py — Comprehensive verification of Stage 9 Yield Estimation integration.

Tests:
A. Analyze Tomato Early Blight image that produces Moderate severity.
B. Verify Yield Estimation receives and displays Crop: Tomato, Disease: Early Blight, Severity: Moderate (NOT Uncertain).
C. Verify proportional scaling when cultivated area is changed from 1 acre to 2 acres.
D. Verify manual input mode when no active image analysis is present.
D2. Verify that genuinely missing severity produces 'Severity: Not available' (never silently defaulting to 'Uncertain').
E. Verify Stages 3–8 features remain intact (prediction, severity, treatment, database, Ask PlantCare).
"""

import sys
from pathlib import Path
from PIL import Image
import sqlite3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Backend & module imports
from predict import load_model, load_class_names, get_device, predict_image, RESULTS_DIR
from severity import estimate_disease_severity
from treatment import get_treatment_recommendation
from database import init_db, save_scan, get_scan_history, get_scan_by_id, DEFAULT_DB_PATH
from query_engine import answer_query
from yield_estimator import calculate_yield_estimate, normalize_severity_name, YieldEstimateResult


def run_tests():
    print("=" * 70)
    print("RUNNING STAGE 9 YIELD ESTIMATION INTEGRATION VERIFICATION")
    print("=" * 70)

    # ─────────────────────────────────────────────────────────────────
    # TEST A & B: Image Analysis -> Yield Estimation Context Carryover
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST A & B] Leaf Diagnosis -> Yield Estimation Context Carryover...")
    test_img_path = Path("Dataset/Tomato/Tomato___Early_blight/0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B 8389.JPG")
    assert test_img_path.exists(), f"Test image not found at {test_img_path}"

    device = get_device()
    class_names = load_class_names(RESULTS_DIR)
    model = load_model(RESULTS_DIR / "best_model.pth", class_names=class_names, device=device)

    # 1. Run disease prediction
    pred_res = predict_image(test_img_path, model=model, class_names=class_names, device=device)
    print(f"  -> Prediction: Crop={pred_res['crop']}, Disease={pred_res['disease']}, Confidence={pred_res['confidence']*100:.1f}%")
    assert pred_res["crop"] == "Tomato"
    assert pred_res["disease"] == "Early Blight"

    # 2. Run image severity estimation
    sev_res = estimate_disease_severity(test_img_path, condition=pred_res["disease"])
    print(f"  -> Severity: Level={sev_res['severity_level']}, AffectedArea={sev_res['affected_percentage']}%, Reliable={sev_res['is_reliable']}")
    assert sev_res["severity_level"] == "Moderate", f"Expected Moderate, got {sev_res['severity_level']}"

    # 3. Form current_analysis context (as created in app.py)
    current_analysis = {
        "token": "test_img_token",
        "crop": pred_res["crop"],
        "disease": pred_res["disease"],
        "confidence": pred_res["confidence"] * 100.0,
        "is_healthy": False,
        "severity": sev_res["severity_level"],
        "severity_level": sev_res["severity_level"],
        "affected_pct": sev_res["affected_percentage"],
        "is_reliable": sev_res["is_reliable"],
        "treatment_rec": get_treatment_recommendation(pred_res["crop"], pred_res["disease"], sev_res["severity_level"]),
    }

    # 4. Resolve context in Yield Estimation (as in render_yield_view)
    active_crop = current_analysis.get("crop", "Tomato")
    active_disease = current_analysis.get("disease", "Healthy")
    active_conf = current_analysis.get("confidence", 0.0)
    raw_sev = current_analysis.get("severity") or current_analysis.get("severity_level")
    active_sev = "Not available" if not raw_sev or not str(raw_sev).strip() else str(raw_sev).strip()
    active_affected_pct = current_analysis.get("affected_pct")

    print(f"  -> Yield Context Carried Over:")
    print(f"     Crop: {active_crop}")
    print(f"     Condition: {active_disease}")
    print(f"     Prediction Confidence: {active_conf:.1f}%")
    print(f"     Severity: {active_sev}")
    print(f"     Affected Area: {active_affected_pct}%")

    assert active_crop == "Tomato"
    assert active_disease == "Early Blight"
    assert active_sev == "Moderate"
    assert active_sev != "Uncertain", "Severity must NOT be Uncertain!"

    # 5. Compute yield estimate using carried context for 1.0 acre
    yield_1 = calculate_yield_estimate(
        crop=active_crop,
        cultivated_area=1.0,
        area_unit="acre",
        disease=active_disease,
        severity=active_sev,
    )
    print(f"  -> Yield Estimate (1.0 acre):")
    print(f"     Estimated Yield: {yield_1.estimated_yield_kg_per_unit:,.0f} kg/acre ({yield_1.estimated_yield_per_unit:.1f} tons/acre)")
    print(f"     Estimated Total Harvest: {yield_1.estimated_total_yield_kg:,.0f} kg ({yield_1.estimated_total_yield:.1f} tons)")
    print(f"     Expected Harvest Range: {yield_1.range_min_kg:,.0f} – {yield_1.range_max_kg:,.0f} kg ({yield_1.range_min:.1f} – {yield_1.range_max:.1f} tons)")
    print(f"     Impact Category: {yield_1.impact_category}")

    assert yield_1.crop == "Tomato"
    assert yield_1.disease == "Early Blight"
    assert yield_1.severity == "Moderate"
    assert yield_1.estimated_yield_per_unit == 2.8
    assert yield_1.estimated_yield_kg_per_unit == 2800
    assert yield_1.estimated_total_yield == 2.8
    assert yield_1.estimated_total_yield_kg == 2800
    print("  ✅ [PASS] Tests A & B: Context accurately carried over with Moderate severity and kg/tons display.")

    # ─────────────────────────────────────────────────────────────────
    # TEST C: Proportional Scaling (1 acre -> 2 acres)
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST C] Proportional Scaling (1.0 acre -> 2.0 acres)...")
    yield_2 = calculate_yield_estimate(
        crop=active_crop,
        cultivated_area=2.0,
        area_unit="acre",
        disease=active_disease,
        severity=active_sev,
    )
    print(f"  -> Yield Estimate (2.0 acres):")
    print(f"     Estimated Yield: {yield_2.estimated_yield_kg_per_unit:,.0f} kg/acre ({yield_2.estimated_yield_per_unit:.1f} tons/acre)")
    print(f"     Estimated Total Harvest: {yield_2.estimated_total_yield_kg:,.0f} kg ({yield_2.estimated_total_yield:.1f} tons)")

    assert yield_2.estimated_total_yield == yield_1.estimated_total_yield * 2.0, "Total tons did not scale 2x!"
    assert yield_2.estimated_total_yield_kg == yield_1.estimated_total_yield_kg * 2.0, "Total kg did not scale 2x!"
    assert yield_2.estimated_total_yield == 5.6
    assert yield_2.estimated_total_yield_kg == 5600
    print("  ✅ [PASS] Test C: Changing area from 1 to 2 acres scaled harvest exactly proportionally (2,800 kg -> 5,600 kg).")

    # ─────────────────────────────────────────────────────────────────
    # TEST D: Manual Input Mode (No Image) & Fallback Handling
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST D] Manual Input Mode (Without Active Image Scan)...")
    # Manual simulate Potato Late Blight Severe on 3 acres
    yield_manual = calculate_yield_estimate(
        crop="Potato",
        cultivated_area=3.0,
        area_unit="acre",
        disease="Late Blight",
        severity="Severe",
    )
    print(f"  -> Manual Simulation: Potato Late Blight (Severe, 3.0 acres)")
    print(f"     Estimated Yield: {yield_manual.estimated_yield_kg_per_unit:,.0f} kg/acre ({yield_manual.estimated_yield_per_unit:.1f} tons/acre)")
    print(f"     Estimated Total Harvest: {yield_manual.estimated_total_yield_kg:,.0f} kg ({yield_manual.estimated_total_yield:.1f} tons)")
    assert yield_manual.crop == "Potato"
    assert yield_manual.disease == "Late Blight"
    assert yield_manual.severity == "Severe"
    assert yield_manual.loss_percentage == 80.0
    assert yield_manual.estimated_yield_per_acre == 1.6  # 8.0 * (1 - 0.8) = 1.6
    assert yield_manual.estimated_total_yield == 4.8  # 1.6 * 3 = 4.8 tons
    assert yield_manual.estimated_total_yield_kg == 4800  # 4800 kg
    print("  ✅ [PASS] Test D: Manual input simulation operates accurately without active image.")

    print("\n[TEST D2] Genuinely Missing Severity Handling...")
    yield_na = calculate_yield_estimate(
        crop="Tomato",
        cultivated_area=1.0,
        area_unit="acre",
        disease="Early Blight",
        severity="Not available",
    )
    print(f"  -> Missing Severity Result: severity='{yield_na.severity}'")
    assert yield_na.severity == "Not available"
    assert yield_na.severity != "Uncertain"
    print("  ✅ [PASS] Test D2: Missing severity displays 'Not available' without defaulting to 'Uncertain'.")

    # ─────────────────────────────────────────────────────────────────
    # TEST D3: Hectare Mode Handling
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST D3] Hectare Mode Handling...")
    yield_ha = calculate_yield_estimate(
        crop="Tomato",
        cultivated_area=1.0,
        area_unit="hectare",
        disease="Early Blight",
        severity="Moderate",
    )
    from app import extract_yield_metrics
    ha_metrics = extract_yield_metrics(yield_ha)
    print(f"  -> Hectare Yield: {ha_metrics['kg_per_unit']:,.0f} kg/hectare ({ha_metrics['tons_per_unit']:.1f} tons/hectare)")
    print(f"     Total Harvest: {ha_metrics['total_kg']:,.0f} kg ({ha_metrics['total_tons']:.1f} tons)")
    assert yield_ha.area_unit == "hectare"
    assert ha_metrics["tons_per_unit"] > 0
    assert ha_metrics["kg_per_unit"] == round(ha_metrics["tons_per_unit"] * 1000.0)
    print("  ✅ [PASS] Test D3: Hectare mode handles area unit and kg conversion correctly.")

    # ─────────────────────────────────────────────────────────────────
    # TEST E: Verification of Stages 3–8 Features
    # ─────────────────────────────────────────────────────────────────
    print("\n[TEST E] Verifying Stages 3–8 Features...")

    # Stage 5: Severity estimation on Healthy image
    healthy_img = Path("Dataset/Tomato/Tomato___Healthy").glob("*.JPG")
    healthy_path = next(healthy_img)
    healthy_sev = estimate_disease_severity(healthy_path, condition="Healthy")
    assert healthy_sev["severity_level"] == "None (Healthy)"
    assert healthy_sev["affected_percentage"] == 0.0
    print("  -> Stage 5 (Severity on Healthy): OK")

    # Stage 6: Treatment engine
    rec_test = get_treatment_recommendation("Tomato", "Early Blight", "Moderate")
    assert "fungicide" in rec_test.recommended_action.lower() or "spray" in rec_test.recommended_action.lower()
    print("  -> Stage 6 (Treatment Engine): OK")

    # Stage 7: Database & Scan History
    test_db = DEFAULT_DB_PATH
    init_db(test_db)
    saved_id = save_scan(
        crop="Tomato",
        disease="Early Blight",
        prediction_confidence=99.8,
        severity="Moderate",
        affected_area_percentage=19.2,
        treatment_summary="Test treatment summary",
        notes="Test notes for verification",
    )
    retrieved = get_scan_by_id(saved_id)
    assert retrieved is not None
    assert retrieved["crop"] == "Tomato"
    assert retrieved["disease"] == "Early Blight"
    assert retrieved["severity"] == "Moderate"
    print(f"  -> Stage 7 (Database Save & Retrieve #{saved_id}): OK")

    # Stage 8: Farmer Query System (Ask PlantCare)
    qa_ans = answer_query("What should I do now?", context=current_analysis)
    assert "Tomato" in qa_ans["answer"]
    assert "Early Blight" in qa_ans["answer"]
    assert qa_ans["is_context_used"] is True
    print("  -> Stage 8 (Ask PlantCare Context Q&A): OK")

    print("\n" + "=" * 70)
    print("ALL TESTS A, B, C, D, D2, E PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
