#!/usr/bin/env python3
"""verify_treatment_contract.py — Verify treatment data contract across all conditions."""

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

samples = [
    "tomato_early_blight",
    "tomato_healthy",
    "potato_early_blight",
    "potato_late_blight",
    "potato_healthy",
]

def run():
    print("Verifying treatment data contract across sample conditions...")
    for sid in samples:
        res = client.post(f"/api/diagnose-sample/{sid}")
        assert res.status_code == 200, f"Failed for sample {sid}: {res.status_code}"
        data = res.json()
        assert "treatment" in data, f"Missing treatment for {sid}"
        t = data["treatment"]
        
        # Check field types
        assert isinstance(t["recommended_action"], str), f"recommended_action is not str in {sid}"
        assert isinstance(t["management_practices"], list), f"management_practices is not list in {sid}"
        assert isinstance(t["treatment_guidance"], (str, list)), f"treatment_guidance is not str or list in {sid}"
        assert isinstance(t["professional_advice"], str), f"professional_advice is not str in {sid}"
        assert isinstance(t["disclaimer"], str), f"disclaimer is not str in {sid}"

        print(f"[OK] {sid}:")
        print(f"     Crop: {data['crop']}, Disease: {data['disease']}, Severity: {data['severity']['level']}")
        print(f"     treatment_guidance type: {type(t['treatment_guidance']).__name__} (length: {len(t['treatment_guidance'])})")
        print(f"     management_practices type: {type(t['management_practices']).__name__} (count: {len(t['management_practices'])})")
        print(f"     recommended_action: {t['recommended_action'][:50]}...")
        print()

    print("ALL TREATMENT DATA CONTRACT CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run()
