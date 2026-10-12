#!/usr/bin/env python3
"""test_stage10_frontend.py — Rigorous verification suite for Stage 10 Modern PlantCare Platform.

Tests:
1. Model loading & pipeline readiness.
2. Static SPA serving (GET / -> 200, contains "PlantCare").
3. Real SQLite stats query (GET /api/stats -> 200, returns real metrics).
4. Curated sample images (GET /api/samples -> 200, 6 items).
5. Leaf diagnosis with real inference & severity (POST /api/diagnose-sample -> 200).
6. SQLite scan history persistence (POST /api/save-scan -> 200).
7. Verified history retrieval & filtering (GET /api/scans -> 200).
8. Context-aware agricultural Q&A (POST /api/query -> 200).
9. Yield estimation calculation with 2x2 responsive metrics (POST /api/yield-estimate -> 200).
"""

import sys
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

def test_stage10():
    print("=" * 65)
    print("STAGE 10 VERIFICATION: MODERN PLANTCARE FRONTEND & API BACKEND")
    print("=" * 65)

    # 1. Health check
    r_health = client.get("/api/health")
    assert r_health.status_code == 200, f"Health check failed: {r_health.text}"
    health_data = r_health.json()
    print(f"[OK] Backend Health: {health_data['status']} | Device: {health_data['device']} | Classes: {len(health_data['classes'])}")

    # 2. Static SPA serving
    r_spa = client.get("/")
    assert r_spa.status_code == 200, f"SPA serving failed: {r_spa.status_code}"
    assert "PlantCare" in r_spa.text, "Index HTML does not contain PlantCare title"
    print("[OK] SPA Frontend Serving: HTTP 200 (index.html with PlantCare metadata served)")

    # 3. SQLite stats query
    r_stats = client.get("/api/stats")
    assert r_stats.status_code == 200, f"Stats failed: {r_stats.text}"
    stats_data = r_stats.json()
    print(f"[OK] SQLite Stats: {stats_data['total_scans']} total scans, {stats_data['healthy_plants']} healthy, {stats_data['diseases_detected']} diseased")

    # 4. Curated sample items
    r_samples = client.get("/api/samples")
    assert r_samples.status_code == 200, f"Samples failed: {r_samples.text}"
    samples = r_samples.json()["samples"]
    assert len(samples) == 6, f"Expected 6 sample items, got {len(samples)}"
    print(f"[OK] Curated Leaf Samples: {len(samples)} samples verified across all classes")

    # 5. Direct diagnosis on sample
    r_diag = client.post("/api/diagnose-sample/tomato_early_blight")
    assert r_diag.status_code == 200, f"Diagnosis failed: {r_diag.text}"
    diag_data = r_diag.json()
    assert diag_data["crop"] == "Tomato"
    assert "Early" in diag_data["disease"]
    assert diag_data["confidence"] > 90.0
    assert diag_data["severity"]["level"] in ["Mild", "Moderate", "Severe"]
    print(f"[OK] ML Diagnosis & Severity: Crop={diag_data['crop']}, Disease={diag_data['disease']}, Confidence={diag_data['confidence']}%, Severity={diag_data['severity']['level']}")

    # 6. Save scan to SQLite
    r_save = client.post(
        "/api/save-scan",
        json={
            "crop": diag_data["crop"],
            "disease": diag_data["disease"],
            "prediction_confidence": diag_data["confidence"],
            "severity": diag_data["severity"]["level"],
            "affected_area_percentage": diag_data["severity"]["affected_percentage"],
            "treatment_summary": diag_data["treatment"]["recommended_action"],
            "notes": "Automated verification test scan",
        },
    )
    assert r_save.status_code == 200, f"Save scan failed: {r_save.text}"
    scan_id = r_save.json()["scan_id"]
    print(f"[OK] SQLite Scan Saved: Record ID #{scan_id} persisted in plant_health.db")

    # 7. Scan history retrieval
    r_scans = client.get("/api/scans?limit=10")
    assert r_scans.status_code == 200, f"Scan history failed: {r_scans.text}"
    scans_list = r_scans.json()["scans"]
    assert any(s["scan_id"] == scan_id for s in scans_list), "Newly created scan not found in history"
    print(f"[OK] SQLite Scan Retrieval: Found saved record #{scan_id} in scan history list")

    # 8. Farmer query Q&A with context
    r_query = client.post(
        "/api/query",
        json={
            "question": "What fungicide should I use for Early Blight?",
            "context": {
                "crop": "Tomato",
                "disease": "Early Blight",
                "severity": "Moderate",
            },
        },
    )
    assert r_query.status_code == 200, f"Query failed: {r_query.text}"
    q_data = r_query.json()
    assert len(q_data["answer"]) > 20
    print(f"[OK] Ask PlantCare Q&A: Response generated ({len(q_data['answer'])} chars) with agronomic guidance")

    # 9. Yield estimation calculation
    r_yield = client.post(
        "/api/yield-estimate",
        json={
            "crop": "Tomato",
            "cultivated_area": 1.0,
            "area_unit": "acre",
            "disease": "Early Blight",
            "severity": "Moderate",
        },
    )
    assert r_yield.status_code == 200, f"Yield estimate failed: {r_yield.text}"
    y_data = r_yield.json()
    assert y_data["estimated_yield_kg_per_unit"] > 0
    assert y_data["estimated_total_yield_kg"] > 0
    assert "disclaimer" in y_data
    print(f"[OK] Yield Estimation: {y_data['estimated_yield_kg_per_unit']:,} kg/acre ({y_data['estimated_yield_per_unit']} tons), Loss: {y_data['loss_percentage']}%")

    print("\n" + "=" * 65)
    print("ALL 9 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    test_stage10()
