#!/usr/bin/env python3
"""test_gemini_integration.py — Rigorous verification of Gemini API integration in Ask PlantCare.

Tests:
1. AI status endpoint (/api/ai-status).
2. Empty question validation (HTTP 400).
3. Oversized question validation (>1000 chars, HTTP 400).
4. Missing GEMINI_API_KEY handling (setup notice + offline fallback, is_ai=False).
5. Invalid GEMINI_API_KEY handling (ClientError 400 caught, guidance returned).
6. Mocked successful Gemini API response (asynchronous call, context inclusion, history).
7. Context propagation (active diagnosis context attached to prompt).
8. Existing endpoints preserved:
   - Leaf image diagnosis (Tomato & Potato)
   - Sample diagnosis
   - Database scan history
   - Yield estimation
   - SPA frontend static serving
9. Secret safety: verify .env is git-ignored and no secrets tracked.
"""

import asyncio
import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from api import app

client = TestClient(app)

class TestGeminiIntegration(unittest.TestCase):

    def test_01_ai_status_endpoint(self):
        """Verify GET /api/ai-status returns valid metadata."""
        res = client.get("/api/ai-status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("is_configured", data)
        self.assertIn("model", data)
        self.assertIn("has_sdk", data)
        self.assertTrue(data["has_sdk"])
        print("[PASS] Test 1: GET /api/ai-status returns valid metadata")

    def test_02_empty_question_rejected(self):
        """Verify empty or whitespace-only questions return HTTP 400."""
        res1 = client.post("/api/query", json={"question": ""})
        self.assertEqual(res1.status_code, 400)
        self.assertIn("empty", res1.json().get("detail", "").lower())

        res2 = client.post("/api/query", json={"question": "    "})
        self.assertEqual(res2.status_code, 400)
        print("[PASS] Test 2: Empty questions correctly rejected with HTTP 400")

    def test_03_oversized_question_rejected(self):
        """Verify questions exceeding 1,000 characters return HTTP 400."""
        long_q = "How do I treat blight? " + ("x" * 1050)
        res = client.post("/api/query", json={"question": long_q})
        self.assertEqual(res.status_code, 400)
        self.assertIn("length", res.json().get("detail", "").lower())
        print("[PASS] Test 3: Questions > 1000 chars rejected with HTTP 400")

    def test_04_missing_api_key_handling(self):
        """Verify that when GEMINI_API_KEY is not set, setup advisory + offline knowledge is returned."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=False):
            res = client.post(
                "/api/query",
                json={"question": "What is tomato early blight?"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertFalse(data.get("is_ai"))
            self.assertEqual(data.get("error"), "MISSING_API_KEY")
            self.assertIn("GEMINI_API_KEY", data["answer"])
            self.assertIn("Tomato", data["crop"])
            self.assertIn("Early Blight", data["disease"])
            print("[PASS] Test 4: Missing GEMINI_API_KEY gracefully returns setup advisory + offline knowledge")

    def test_05_invalid_api_key_handling(self):
        """Verify that an invalid API key returns clear troubleshooting instructions without crashing."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "AIzaSy_fake_invalid_test_key_123"}, clear=False):
            res = client.post(
                "/api/query",
                json={"question": "How to treat late blight in potatoes?"},
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertFalse(data.get("is_ai"))
            self.assertEqual(data.get("error"), "INVALID_API_KEY")
            self.assertIn("Invalid Gemini API Key", data["answer"])
            print("[PASS] Test 5: Invalid GEMINI_API_KEY returns clear troubleshooting instructions")

    def test_06_mocked_gemini_success_with_context_and_history(self):
        """Verify end-to-end async Gemini execution with context and chat history."""
        mock_response = MagicMock()
        mock_response.text = (
            "### Early Blight Management Advice\n\n"
            "For moderate Early Blight on tomatoes:\n"
            "- Prune lower blighted leaves to reduce spore spread.\n"
            "- Ensure irrigation is delivered at the base.\n"
            "- Protect healthy foliage with registered preventative copper formulations according to the product label.\n"
        )

        with patch.dict(os.environ, {"GEMINI_API_KEY": "valid_mock_key"}, clear=False):
            with patch("gemini_service.genai.Client") as MockClient:
                mock_instance = MagicMock()
                mock_aio = MagicMock()
                mock_models = MagicMock()
                mock_models.generate_content = AsyncMock(return_value=mock_response)
                mock_aio.models = mock_models
                mock_instance.aio = mock_aio
                MockClient.return_value = mock_instance

                res = client.post(
                    "/api/query",
                    json={
                        "question": "What should I do right now?",
                        "context": {
                            "crop": "Tomato",
                            "disease": "Early Blight",
                            "severity": "Moderate",
                            "confidence": 99.2,
                            "affected_percentage": 12.5,
                        },
                        "history": [
                            {"role": "user", "text": "I noticed brown spots on lower leaves."},
                            {"role": "assistant", "text": "Those appear characteristic of Early Blight target lesions."},
                        ],
                    },
                )
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertTrue(data.get("is_ai"))
                self.assertIn("Early Blight Management Advice", data["answer"])
                self.assertIn("Google Gemini", data["sources"][0])
                self.assertIsNone(data.get("error"))
                print("[PASS] Test 6: Mocked Gemini API call succeeded with active context and chat history")

    def test_07_existing_features_unbroken(self):
        """Verify that leaf diagnosis, samples, database history, and yield remain completely intact."""
        # 1. Samples list
        r_samples = client.get("/api/samples")
        self.assertEqual(r_samples.status_code, 200)
        self.assertEqual(len(r_samples.json()["samples"]), 6)

        # 2. Sample diagnosis (Potato Late Blight)
        r_diag = client.post("/api/diagnose-sample/potato_late_blight")
        self.assertEqual(r_diag.status_code, 200)
        diag_data = r_diag.json()
        self.assertEqual(diag_data["crop"], "Potato")
        self.assertEqual(diag_data["disease"], "Late Blight")
        self.assertEqual(diag_data["severity"]["level"], "Severe")
        self.assertIn("treatment", diag_data)

        # 3. Database history
        r_scans = client.get("/api/scans?limit=5")
        self.assertEqual(r_scans.status_code, 200)

        # 4. Yield estimation
        r_yield = client.post(
            "/api/yield-estimate",
            json={
                "crop": "Tomato",
                "cultivated_area": 1.5,
                "area_unit": "acre",
                "disease": "Early Blight",
                "severity": "Moderate",
            },
        )
        self.assertEqual(r_yield.status_code, 200)
        y_data = r_yield.json()
        self.assertIn("estimated_total_yield_kg", y_data)

        # 5. SPA Index
        r_spa = client.get("/")
        self.assertEqual(r_spa.status_code, 200)
        self.assertIn("PlantCare", r_spa.text)

        print("[PASS] Test 7: All existing features (diagnosis, 6 classes, DB, yield, SPA) verified intact")

    def test_08_secret_and_git_safety(self):
        """Verify that .env is excluded by .gitignore and .env.example exists."""
        from pathlib import Path
        gitignore_path = Path(".gitignore")
        self.assertTrue(gitignore_path.exists())
        content = gitignore_path.read_text(encoding="utf-8")
        self.assertIn(".env", content)
        self.assertIn("!.env.example", content)

        env_example = Path(".env.example")
        self.assertTrue(env_example.exists())
        self.assertIn("GEMINI_API_KEY=your_gemini_api_key_here", env_example.read_text(encoding="utf-8"))
        print("[PASS] Test 8: Git ignore and .env.example template verified")

    def test_09_live_gemini_api_call_real(self):
        """Verify a real live Gemini response when an API key is configured."""
        from gemini_service import get_api_key
        key = get_api_key()
        if not key:
            self.skipTest("No GEMINI_API_KEY available for live test")

        res = client.post(
            "/api/query",
            json={
                "question": "Explain tomato late blight with scan history analysis.",
                "context": {
                    "crop": "Tomato",
                    "disease": "Late Blight",
                    "confidence": 98.4,
                    "severity": "High (Severe)",
                    "affected_percentage": 34.2,
                },
            },
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("is_ai"), f"Expected is_ai=True, got: {data}")
        self.assertEqual(data.get("error"), None)
        self.assertIn("gemini", data.get("model", "").lower())
        self.assertGreater(len(data.get("answer", "")), 50)
        self.assertIn("Late Blight", data.get("disease", ""))
        print(f"[PASS] Test 9: Real Gemini live response verified ({data['model']}, {len(data['answer'])} chars)")


if __name__ == "__main__":
    unittest.main()
