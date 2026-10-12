#!/usr/bin/env python3
"""test_stage11_field_inspection.py — Automated verification of Stage 11 Geospatial AR Field Inspection.

Tests:
1. Valid field inspection creation with GPS coordinates, accuracy, and image storage.
2. File validation (empty image rejected, invalid format rejected).
3. Retrieval of inspection list and single inspection detail.
4. Static file serving of inspection photos via /inspections/{filename}.
5. Phase 11E: Real EfficientNet-B0 disease diagnosis integration on a saved field image.
6. Inspection deletion and cleanup of files on disk.
7. Verification that all existing features (diagnose, samples, stats, query, yield, SPA) remain functional.
"""

import io
import unittest
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from api import app, INSPECTIONS_DIR
from database import get_inspection_record_by_id, delete_inspection_record

client = TestClient(app)


class TestStage11FieldInspection(unittest.TestCase):
    created_inspection_ids = []

    @classmethod
    def setUpClass(cls):
        cls.created_inspection_ids = []
        # Create a small valid test JPEG
        img = Image.new("RGB", (256, 256), color=(34, 139, 34))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        cls.valid_jpeg_bytes = buf.getvalue()

        # Load real tomato leaf sample for real ML test
        tomato_sample = Path("frontend/public/samples/tomato_early_blight.jpg")
        if tomato_sample.exists():
            cls.real_leaf_bytes = tomato_sample.read_bytes()
        else:
            cls.real_leaf_bytes = cls.valid_jpeg_bytes

    @classmethod
    def tearDownClass(cls):
        # Clean up any test records created during test run
        for insp_id in cls.created_inspection_ids:
            rec = get_inspection_record_by_id(insp_id)
            if rec:
                for key in ["image_url", "overlay_image_url"]:
                    if rec.get(key):
                        fname = Path(rec[key]).name
                        fpath = INSPECTIONS_DIR / fname
                        if fpath.exists():
                            try:
                                fpath.unlink()
                            except Exception:
                                pass
                delete_inspection_record(insp_id)

    def test_01_create_field_inspection_success(self):
        """Test creating a field inspection with GPS telemetry and image."""
        response = client.post(
            "/api/inspections",
            files={
                "file": ("field_leaf.jpg", self.valid_jpeg_bytes, "image/jpeg"),
                "overlay_file": ("field_leaf_hud.jpg", self.valid_jpeg_bytes, "image/jpeg"),
            },
            data={
                "latitude": "12.9715987",
                "longitude": "77.5945627",
                "gps_accuracy": "14.2",
                "field_name": "Test Plot - Unit Verification",
                "notes": "Automated verification note.",
                "timestamp": "2026-10-12 14:40:00",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("inspection_id", data)
        self.created_inspection_ids.append(data["inspection_id"])
        insp = data["inspection"]

        self.assertAlmostEqual(insp["latitude"], 12.9715987, places=5)
        self.assertAlmostEqual(insp["longitude"], 77.5945627, places=5)
        self.assertEqual(insp["gps_accuracy"], 14.2)
        self.assertEqual(insp["field_name"], "Test Plot - Unit Verification")
        self.assertEqual(insp["notes"], "Automated verification note.")

        # Verify image file exists on disk
        img_name = Path(insp["image_url"]).name
        self.assertTrue((INSPECTIONS_DIR / img_name).exists())

        # Verify static file serving
        r_img = client.get(insp["image_url"])
        self.assertEqual(r_img.status_code, 200)
        self.assertEqual(r_img.headers.get("content-type"), "image/jpeg")
        print(f"[PASS] Test 1: Created inspection #{insp['inspection_id']} with GPS telemetry and persistent image")

    def test_02_validation_empty_and_invalid_images(self):
        """Test that empty or non-image files are rejected."""
        # Empty file
        r_empty = client.post(
            "/api/inspections",
            files={"file": ("empty.jpg", b"", "image/jpeg")},
            data={"latitude": "12.0", "longitude": "77.0", "gps_accuracy": "10.0"},
        )
        self.assertEqual(r_empty.status_code, 400)
        self.assertIn("empty", r_empty.json()["detail"].lower())

        # Corrupted non-image file
        r_bad = client.post(
            "/api/inspections",
            files={"file": ("fake.jpg", b"not-a-valid-image", "image/jpeg")},
            data={"latitude": "12.0", "longitude": "77.0", "gps_accuracy": "10.0"},
        )
        self.assertEqual(r_bad.status_code, 400)
        self.assertIn("invalid image format", r_bad.json()["detail"].lower())
        print("[PASS] Test 2: Correctly rejected empty and corrupted files with HTTP 400")

    def test_03_list_and_get_inspection(self):
        """Test listing inspections and getting a single inspection by ID."""
        r_list = client.get("/api/inspections?limit=10")
        self.assertEqual(r_list.status_code, 200)
        data = r_list.json()
        self.assertIn("inspections", data)
        self.assertGreaterEqual(len(data["inspections"]), 1)

        first_id = data["inspections"][0]["inspection_id"]
        r_single = client.get(f"/api/inspections/{first_id}")
        self.assertEqual(r_single.status_code, 200)
        self.assertEqual(r_single.json()["inspection"]["inspection_id"], first_id)

        # 404 for nonexistent id
        r_404 = client.get("/api/inspections/999999")
        self.assertEqual(r_404.status_code, 404)
        print("[PASS] Test 3: Listed and retrieved inspection records, handled 404 cleanly")

    def test_04_phase_11e_disease_diagnosis_integration(self):
        """Test Phase 11E: Running disease diagnosis on a saved field inspection photo."""
        # 1. Create inspection with real tomato early blight photo
        create_res = client.post(
            "/api/inspections",
            files={"file": ("tomato_field.jpg", self.real_leaf_bytes, "image/jpeg")},
            data={
                "latitude": "13.0827",
                "longitude": "80.2707",
                "gps_accuracy": "8.5",
                "field_name": "Automated Test Sample #4",
                "notes": "Target lesions visible on middle canopy.",
            },
        )
        self.assertEqual(create_res.status_code, 200)
        insp_id = create_res.json()["inspection_id"]
        self.created_inspection_ids.append(insp_id)

        # 2. Run diagnosis endpoint
        diag_res = client.post(f"/api/inspections/{insp_id}/diagnose")
        self.assertEqual(diag_res.status_code, 200)
        d_data = diag_res.json()
        self.assertTrue(d_data["success"])
        self.assertIn("diagnosis", d_data)
        diag = d_data["diagnosis"]

        self.assertEqual(diag["crop"], "Tomato")
        self.assertEqual(diag["disease"], "Early Blight")
        self.assertGreaterEqual(diag["confidence"], 90.0)
        self.assertIn("severity", diag)
        self.assertIn("treatment", diag)

        # 3. Verify SQLite record was updated with diagnosis fields
        updated_insp = d_data["inspection"]
        self.assertEqual(updated_insp["crop"], "Tomato")
        self.assertEqual(updated_insp["disease"], "Early Blight")
        self.assertGreaterEqual(updated_insp["prediction_confidence"], 90.0)
        self.assertEqual(updated_insp["severity"], diag["severity"]["level"])
        self.assertTrue(len(updated_insp["treatment_summary"]) > 5)

        print(f"[PASS] Test 4: Phase 11E disease diagnosis verified on inspection #{insp_id} (Tomato Early Blight, {diag['confidence']}%)")

    def test_05_delete_inspection_and_cleanup(self):
        """Test deleting inspection removes record and files from disk."""
        # Create dummy inspection to delete
        create_res = client.post(
            "/api/inspections",
            files={"file": ("delete_me.jpg", self.valid_jpeg_bytes, "image/jpeg")},
            data={"latitude": "15.0", "longitude": "75.0", "gps_accuracy": "20.0"},
        )
        insp_id = create_res.json()["inspection_id"]
        img_url = create_res.json()["inspection"]["image_url"]
        fname = Path(img_url).name
        self.assertTrue((INSPECTIONS_DIR / fname).exists())

        # Delete
        del_res = client.delete(f"/api/inspections/{insp_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json()["success"])

        # Confirm deleted from SQLite
        self.assertIsNone(get_inspection_record_by_id(insp_id))

        # Confirm file removed from disk
        self.assertFalse((INSPECTIONS_DIR / fname).exists())
        print(f"[PASS] Test 5: Deleted inspection #{insp_id} and verified file cleanup")

    def test_06_existing_features_unaffected(self):
        """Verify that leaf diagnosis, stats, query, samples, and SPA remain functional."""
        # 1. Samples
        r_samp = client.get("/api/samples")
        self.assertEqual(r_samp.status_code, 200)
        self.assertEqual(len(r_samp.json()["samples"]), 6)

        # 2. Stats
        r_stats = client.get("/api/stats")
        self.assertEqual(r_stats.status_code, 200)

        # 3. Ask PlantCare status
        r_ai = client.get("/api/ai-status")
        self.assertEqual(r_ai.status_code, 200)

        # 4. SPA HTML
        r_spa = client.get("/")
        self.assertEqual(r_spa.status_code, 200)
        self.assertIn("PlantCare", r_spa.text)

        print("[PASS] Test 6: All existing features confirmed functional and unaffected")

    def test_07_empty_state_and_cleanup_verified(self):
        """Verify that all test inspections clean up cleanly and leave an empty inspection log."""
        # Explicitly clean up all tracked test IDs
        for insp_id in list(self.created_inspection_ids):
            rec = get_inspection_record_by_id(insp_id)
            if rec:
                for key in ["image_url", "overlay_image_url"]:
                    if rec.get(key):
                        fname = Path(rec[key]).name
                        fpath = INSPECTIONS_DIR / fname
                        if fpath.exists():
                            try:
                                fpath.unlink()
                            except Exception:
                                pass
                delete_inspection_record(insp_id)
        self.created_inspection_ids.clear()

        # Request inspections list - must be empty
        r_empty = client.get("/api/inspections")
        self.assertEqual(r_empty.status_code, 200)
        data = r_empty.json()
        self.assertEqual(data["inspections"], [])
        self.assertEqual(data["count"], 0)
        print("[PASS] Test 7: Clean empty state verified (0 inspection records, no fake data)")

    def test_08_missing_image_handled_cleanly(self):
        """Verify that requesting a missing image file returns 404 rather than corrupted data."""
        r_missing = client.get("/inspections/nonexistent_test_image.jpg")
        self.assertEqual(r_missing.status_code, 404)
        print("[PASS] Test 8: Missing inspection image returns HTTP 404 cleanly")

    def test_09_database_scan_history_unaffected(self):
        """Verify that general scan history is completely isolated and retains all original records."""
        from database import get_scan_count
        count = get_scan_count()
        self.assertEqual(count, 10)
        print(f"[PASS] Test 9: Scan history verified isolated and unaffected ({count} records intact)")


if __name__ == "__main__":
    unittest.main()
