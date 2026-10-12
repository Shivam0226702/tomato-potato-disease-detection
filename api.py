#!/usr/bin/env python3
"""api.py — Modern FastAPI Backend for PlantCare Platform.

Exposes REST API endpoints wrapping existing ML inference, severity estimation,
treatment recommendation, SQLite database, Ask PlantCare Q&A, and yield estimator.
"""

from __future__ import annotations

import io
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from PIL import Image
from dotenv import load_dotenv

# Load local environment configuration from .env or .env.txt in project root
_proj_root = Path(__file__).resolve().parent
if (_proj_root / ".env").exists():
    load_dotenv(dotenv_path=_proj_root / ".env")
elif (_proj_root / ".env.txt").exists():
    load_dotenv(dotenv_path=_proj_root / ".env.txt")
else:
    load_dotenv()

# Existing backend modules
from database import (
    DEFAULT_DB_PATH,
    clear_history,
    delete_inspection_record,
    get_connection,
    get_inspection_record_by_id,
    get_inspection_records,
    get_scan_by_id,
    get_scan_history,
    init_db,
    save_inspection_record,
    save_scan,
    update_inspection_record_diagnosis,
)
from predict import (
    RESULTS_DIR,
    get_device,
    load_class_names,
    load_model,
    predict_image,
)
from query_engine import answer_query
from severity import estimate_disease_severity
from treatment import get_treatment_recommendation
from yield_estimator import calculate_yield_estimate, YIELD_DISCLAIMER
from gemini_service import (
    AGRONOMIC_DISCLAIMER,
    HAS_GENAI_LIB,
    get_configured_model,
    is_gemini_configured,
    query_gemini_agronomist,
)

# Initialize FastAPI app
app = FastAPI(
    title="PlantCare API",
    description="Backend services for PlantCare smart plant health platform",
    version="1.0.0",
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
init_db(DEFAULT_DB_PATH)

# Persistent directory for field inspection photos
INSPECTIONS_DIR = Path(__file__).resolve().parent / "data" / "inspections"
INSPECTIONS_DIR.mkdir(parents=True, exist_ok=True)

# Global model state cache
_MODEL = None
_CLASS_NAMES = None
_DEVICE = None


def get_pipeline():
    """Lazy-load PyTorch model into memory once."""
    global _MODEL, _CLASS_NAMES, _DEVICE
    if _MODEL is None:
        _DEVICE = get_device()
        _CLASS_NAMES = load_class_names(RESULTS_DIR)
        _MODEL = load_model(
            model_path=RESULTS_DIR / "best_model.pth",
            class_names=_CLASS_NAMES,
            device=_DEVICE,
        )
    return _MODEL, _CLASS_NAMES, _DEVICE


# ═══════════════════════════════════════════════════════════════════════
#  PYDANTIC REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════

class SaveScanRequest(BaseModel):
    crop: str
    disease: str
    prediction_confidence: float
    severity: str
    affected_area_percentage: Optional[float] = None
    treatment_summary: Optional[str] = ""
    notes: Optional[str] = ""


class ChatHistoryItem(BaseModel):
    role: str
    text: str


class QueryRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[ChatHistoryItem]] = None


class YieldRequest(BaseModel):
    crop: str = "Tomato"
    cultivated_area: float = 1.0
    area_unit: str = "acre"
    disease: str = "Healthy"
    severity: str = "None (Healthy)"


# ═══════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health_check():
    """Verify backend and ML pipeline readiness."""
    model, class_names, device = get_pipeline()
    return {
        "status": "healthy",
        "device": str(device),
        "classes": class_names,
        "database": str(DEFAULT_DB_PATH.name),
    }


def _run_diagnosis(contents: bytes, filename: str) -> Dict[str, Any]:
    """Execute ML prediction, severity estimation, treatment guidance, and yield baseline."""
    # 1. Run disease prediction
    model, class_names, device = get_pipeline()
    pred_res = predict_image(
        io.BytesIO(contents),
        model=model,
        class_names=class_names,
        device=device,
        top_k=3,
    )

    crop = pred_res["crop"]
    disease = pred_res["disease"]
    confidence = round(pred_res["confidence"] * 100.0, 1)
    is_healthy = disease.lower() == "healthy"

    # 2. Run visual severity estimation
    sev_res = estimate_disease_severity(
        io.BytesIO(contents),
        condition=disease,
    )

    severity_level = sev_res["severity_level"]
    affected_pct = sev_res["affected_percentage"]
    is_reliable = sev_res["is_reliable"]
    sev_explanation = sev_res["explanation"]
    sev_disclaimer = sev_res["disclaimer"]

    # 3. Get treatment guidance
    treatment_rec = get_treatment_recommendation(
        crop=crop,
        disease=disease,
        severity=severity_level,
    )

    # 4. Generate default yield estimate (1.0 acre)
    yield_res = calculate_yield_estimate(
        crop=crop,
        cultivated_area=1.0,
        area_unit="acre",
        disease=disease,
        severity=severity_level,
    )

    return {
        "success": True,
        "filename": filename,
        "crop": crop,
        "disease": disease,
        "confidence": confidence,
        "is_healthy": is_healthy,
        "top_predictions": pred_res["top_predictions"],
        "severity": {
            "level": severity_level,
            "affected_percentage": affected_pct,
            "is_reliable": is_reliable,
            "status_color": sev_res.get("status_color", "gray"),
            "summary": sev_res.get("summary", ""),
            "explanation": sev_explanation,
            "disclaimer": sev_disclaimer,
        },
        "treatment": {
            "recommended_action": treatment_rec.recommended_action,
            "management_practices": treatment_rec.management_practices,
            "treatment_guidance": treatment_rec.treatment_guidance,
            "professional_advice": treatment_rec.professional_advice,
            "disclaimer": treatment_rec.disclaimer,
        },
        "default_yield": {
            "crop": yield_res.crop,
            "cultivated_area": yield_res.cultivated_area,
            "area_unit": yield_res.area_unit,
            "estimated_yield_per_unit": yield_res.estimated_yield_per_unit,
            "estimated_yield_kg_per_unit": yield_res.estimated_yield_kg_per_unit,
            "estimated_total_yield": yield_res.estimated_total_yield,
            "estimated_total_yield_kg": yield_res.estimated_total_yield_kg,
            "range_min": yield_res.range_min,
            "range_max": yield_res.range_max,
            "range_min_kg": yield_res.range_min_kg,
            "range_max_kg": yield_res.range_max_kg,
            "loss_percentage": yield_res.loss_percentage,
            "impact_category": yield_res.impact_category,
            "disclaimer": yield_res.disclaimer,
        },
    }


@app.post("/api/diagnose")
async def diagnose_leaf(file: UploadFile = File(...)):
    """Run full plant health diagnosis on uploaded leaf photo."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read binary bytes
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Check maximum file size (15MB)
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum supported image size is 15MB."
        )

    # Validate image decoding
    try:
        img_probe = Image.open(io.BytesIO(contents))
        img_probe.verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Please upload a valid, uncorrupted JPG, PNG, or WEBP leaf image."
        )

    try:
        return _run_diagnosis(contents, file.filename)
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Diagnosis error: {str(err)}")


@app.post("/api/save-scan")
def save_scan_record(req: SaveScanRequest):
    """Save analysis record to SQLite database."""
    try:
        scan_id = save_scan(
            crop=req.crop,
            disease=req.disease,
            prediction_confidence=req.prediction_confidence,
            severity=req.severity,
            affected_area_percentage=req.affected_area_percentage,
            treatment_summary=req.treatment_summary or "",
            notes=req.notes or "",
        )
        return {"success": True, "scan_id": scan_id}
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Database save error: {str(err)}")


@app.get("/api/scans")
def list_scans(limit: int = 100):
    """Retrieve historical scan records from SQLite database."""
    scans = get_scan_history(limit=limit)
    return {"scans": scans, "count": len(scans)}


@app.get("/api/scans/{scan_id}")
def get_scan(scan_id: int):
    """Retrieve single scan detail by ID."""
    scan = get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found")
    return {"scan": scan}


@app.delete("/api/scans")
def clear_all_scans():
    """Clear all historical scan records."""
    clear_history()
    return {"success": True, "message": "All scan records cleared"}


# ═══════════════════════════════════════════════════════════════════════
#  STAGE 11 — GEOSPATIAL FIELD INSPECTIONS
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/inspections")
async def create_field_inspection(
    file: UploadFile = File(...),
    overlay_file: Optional[UploadFile] = File(None),
    latitude: float = Form(...),
    longitude: float = Form(...),
    gps_accuracy: float = Form(...),
    field_name: Optional[str] = Form(""),
    notes: Optional[str] = Form(""),
    timestamp: Optional[str] = Form(None),
):
    """Save captured field inspection photo and GPS telemetry."""
    # 1. Validate primary image file
    contents = await file.read()
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Captured image file is empty.")
    if len(contents) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size exceeds 15MB limit.")

    try:
        img_probe = Image.open(io.BytesIO(contents))
        img_probe.verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image format. Please upload or capture a valid JPG, PNG, or WEBP photograph."
        )

    # 2. Save raw image to persistent data/inspections/
    orig_ext = Path(file.filename or "capture.jpg").suffix.lower()
    if orig_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
        orig_ext = ".jpg"

    unique_token = uuid.uuid4().hex[:12]
    filename = f"field_{unique_token}{orig_ext}"
    target_path = INSPECTIONS_DIR / filename
    target_path.write_bytes(contents)
    image_url = f"/inspections/{filename}"

    # 3. Save overlay image if provided
    overlay_url = None
    if overlay_file is not None:
        try:
            overlay_bytes = await overlay_file.read()
            if len(overlay_bytes) > 0:
                overlay_filename = f"field_{unique_token}_overlay{orig_ext}"
                overlay_path = INSPECTIONS_DIR / overlay_filename
                overlay_path.write_bytes(overlay_bytes)
                overlay_url = f"/inspections/{overlay_filename}"
        except Exception:
            overlay_url = None

    # 4. Save to SQLite database
    insp_id = save_inspection_record(
        latitude=latitude,
        longitude=longitude,
        gps_accuracy=gps_accuracy,
        image_url=image_url,
        overlay_image_url=overlay_url,
        field_name=field_name or "",
        notes=notes or "",
        timestamp=timestamp,
    )

    rec = get_inspection_record_by_id(insp_id)
    return {
        "success": True,
        "inspection_id": insp_id,
        "inspection": rec,
    }


@app.get("/api/inspections")
def list_field_inspections(limit: int = 100):
    """Retrieve list of historical field inspections."""
    recs = get_inspection_records(limit=limit)
    return {"inspections": recs, "count": len(recs)}


@app.get("/api/inspections/{inspection_id}")
def get_field_inspection(inspection_id: int):
    """Retrieve single field inspection record by ID."""
    rec = get_inspection_record_by_id(inspection_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Field inspection record not found.")
    return {"inspection": rec}


@app.post("/api/inspections/{inspection_id}/diagnose")
def diagnose_field_inspection(inspection_id: int):
    """Run disease diagnosis on a saved field inspection image."""
    rec = get_inspection_record_by_id(inspection_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Field inspection record not found.")

    # Locate image file on disk
    img_rel_url = rec["image_url"]
    filename = Path(img_rel_url).name
    img_path = INSPECTIONS_DIR / filename
    if not img_path.exists():
        raise HTTPException(status_code=404, detail=f"Inspection image file not found on disk: {filename}")

    contents = img_path.read_bytes()
    diag_res = _run_diagnosis(contents, filename)

    # Update inspection record in SQLite with diagnosis details
    update_inspection_record_diagnosis(
        inspection_id=inspection_id,
        crop=diag_res["crop"],
        disease=diag_res["disease"],
        prediction_confidence=diag_res["confidence"],
        severity=diag_res["severity"]["level"],
        affected_area_percentage=diag_res["severity"]["affected_percentage"],
        treatment_summary=diag_res["treatment"]["recommended_action"],
    )

    updated_rec = get_inspection_record_by_id(inspection_id)
    return {
        "success": True,
        "diagnosis": diag_res,
        "inspection": updated_rec,
    }


@app.delete("/api/inspections/{inspection_id}")
def delete_field_inspection(inspection_id: int):
    """Delete a field inspection record and its associated image files."""
    rec = get_inspection_record_by_id(inspection_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Field inspection record not found.")

    # Remove files if they exist
    for url_field in ["image_url", "overlay_image_url"]:
        if rec.get(url_field):
            fname = Path(rec[url_field]).name
            fpath = INSPECTIONS_DIR / fname
            if fpath.exists():
                try:
                    fpath.unlink()
                except Exception:
                    pass

    deleted = delete_inspection_record(inspection_id)
    return {"success": deleted, "message": f"Inspection {inspection_id} deleted."}


@app.get("/api/stats")
def get_dashboard_stats():
    """Retrieve aggregate statistics directly from SQLite database."""
    scans = get_scan_history(limit=500)
    total_scans = len(scans)
    healthy_count = sum(1 for s in scans if s["disease"].lower() == "healthy")
    diseased_count = total_scans - healthy_count

    # Disease breakdown
    disease_dist: Dict[str, int] = {}
    crop_dist: Dict[str, int] = {"Tomato": 0, "Potato": 0}

    for s in scans:
        d = s["disease"]
        disease_dist[d] = disease_dist.get(d, 0) + 1
        c = s["crop"]
        if c in crop_dist:
            crop_dist[c] += 1
        else:
            crop_dist[c] = 1

    return {
        "total_scans": total_scans,
        "healthy_plants": healthy_count,
        "diseases_detected": diseased_count,
        "disease_distribution": disease_dist,
        "crop_distribution": crop_dist,
        "recent_scans": scans[:5],
    }


@app.get("/api/ai-status")
def get_ai_status():
    """Check status of Gemini AI assistant integration."""
    return {
        "is_configured": is_gemini_configured(),
        "model": get_configured_model(),
        "has_sdk": HAS_GENAI_LIB,
    }


@app.post("/api/query")
async def ask_plantcare(req: QueryRequest):
    """Submit agricultural question to Gemini assistant or fallback agronomic knowledge engine."""
    clean_q = req.question.strip()
    if not clean_q:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if len(clean_q) > 1000:
        raise HTTPException(
            status_code=400,
            detail=f"Question exceeds maximum supported length ({len(clean_q)}/1000 characters).",
        )

    history_dicts = None
    if req.history:
        history_dicts = [{"role": h.role, "text": h.text} for h in req.history]

    # If Gemini API is configured with an active key
    if is_gemini_configured():
        try:
            return await query_gemini_agronomist(
                clean_q,
                context=req.context,
                history=history_dicts,
            )
        except Exception as exc:
            offline_res = answer_query(clean_q, context=req.context)
            return {
                "answer": (
                    f"### ⚠️ Gemini Assistant Temporary Issue\n\n"
                    f"Could not complete online AI query: {str(exc)}\n\n"
                    f"---\n\n"
                    f"**Offline Agronomic Knowledge Response:**\n\n"
                    f"{offline_res['answer']}"
                ),
                "crop": offline_res.get("crop_detected") or "Tomato / Potato",
                "disease": offline_res.get("disease_detected") or "General Foliar Health",
                "sources": ["PlantCare Offline Knowledge Base"],
                "disclaimer": AGRONOMIC_DISCLAIMER,
                "is_ai": False,
                "model": None,
                "error": "GEMINI_ERROR",
            }

    # When API key is not configured, provide setup instructions with offline knowledge response
    offline_res = answer_query(clean_q, context=req.context)
    setup_notice = (
        "> 🌿 **Note: Google Gemini AI ready for activation**\n"
        "> Add your `GEMINI_API_KEY` to `.env` to enable dynamic generative AI responses.\n"
        "> *(Currently answering using PlantCare's built-in offline Agronomic Knowledge Base)*\n\n"
        "---\n\n"
    )
    return {
        "answer": setup_notice + offline_res["answer"],
        "crop": offline_res.get("crop_detected") or "Tomato / Potato",
        "disease": offline_res.get("disease_detected") or "General Foliar Health",
        "sources": ["PlantCare Offline Knowledge Base", "Extension Guidelines"],
        "disclaimer": AGRONOMIC_DISCLAIMER,
        "is_ai": False,
        "model": None,
        "error": "MISSING_API_KEY",
    }


@app.post("/api/yield-estimate")
def compute_yield_estimate(req: YieldRequest):
    """Calculate prototype crop yield estimate."""
    result = calculate_yield_estimate(
        crop=req.crop,
        cultivated_area=req.cultivated_area,
        area_unit=req.area_unit,
        disease=req.disease,
        severity=req.severity,
    )

    return {
        "crop": result.crop,
        "cultivated_area": result.cultivated_area,
        "area_unit": result.area_unit,
        "disease": result.disease,
        "severity": result.severity,
        "baseline_yield_per_acre": result.baseline_yield_per_acre,
        "estimated_yield_per_unit": result.estimated_yield_per_unit,
        "estimated_yield_kg_per_unit": result.estimated_yield_kg_per_unit,
        "estimated_total_yield": result.estimated_total_yield,
        "estimated_total_yield_kg": result.estimated_total_yield_kg,
        "range_min": result.range_min,
        "range_max": result.range_max,
        "range_min_kg": result.range_min_kg,
        "range_max_kg": result.range_max_kg,
        "loss_percentage": result.loss_percentage,
        "impact_category": result.impact_category,
        "disclaimer": result.disclaimer,
    }


SAMPLE_MAP: Dict[str, Dict[str, Any]] = {
    "tomato_early_blight": {
        "id": "tomato_early_blight",
        "name": "Tomato — Early Blight",
        "crop": "Tomato",
        "condition": "Early Blight",
        "image_url": "/samples/tomato_early_blight.jpg",
        "file_path": Path("frontend/public/samples/tomato_early_blight.jpg"),
    },
    "tomato_healthy": {
        "id": "tomato_healthy",
        "name": "Tomato — Healthy",
        "crop": "Tomato",
        "condition": "Healthy",
        "image_url": "/samples/tomato_healthy.jpg",
        "file_path": Path("frontend/public/samples/tomato_healthy.jpg"),
    },
    "tomato_late_blight": {
        "id": "tomato_late_blight",
        "name": "Tomato — Late Blight",
        "crop": "Tomato",
        "condition": "Late Blight",
        "image_url": "/samples/tomato_late_blight.jpg",
        "file_path": Path("frontend/public/samples/tomato_late_blight.jpg"),
    },
    "potato_early_blight": {
        "id": "potato_early_blight",
        "name": "Potato — Early Blight",
        "crop": "Potato",
        "condition": "Early Blight",
        "image_url": "/samples/potato_early_blight.jpg",
        "file_path": Path("frontend/public/samples/potato_early_blight.jpg"),
    },
    "potato_healthy": {
        "id": "potato_healthy",
        "name": "Potato — Healthy",
        "crop": "Potato",
        "condition": "Healthy",
        "image_url": "/samples/potato_healthy.jpg",
        "file_path": Path("frontend/public/samples/potato_healthy.jpg"),
    },
    "potato_late_blight": {
        "id": "potato_late_blight",
        "name": "Potato — Late Blight",
        "crop": "Potato",
        "condition": "Late Blight",
        "image_url": "/samples/potato_late_blight.jpg",
        "file_path": Path("frontend/public/samples/potato_late_blight.jpg"),
    },
}


@app.get("/api/samples")
def list_sample_images():
    """List curated test sample images for one-click testing."""
    return {
        "samples": [
            {
                "id": v["id"],
                "name": v["name"],
                "crop": v["crop"],
                "condition": v["condition"],
                "image_url": v["image_url"],
            }
            for v in SAMPLE_MAP.values()
        ]
    }


@app.post("/api/diagnose-sample/{sample_id}")
def diagnose_sample_image(sample_id: str):
    """Run diagnosis directly on a curated sample image."""
    if sample_id not in SAMPLE_MAP:
        raise HTTPException(status_code=404, detail=f"Sample '{sample_id}' not found")

    sample_info = SAMPLE_MAP[sample_id]
    fp = sample_info["file_path"]
    if not fp.exists():
        raise HTTPException(status_code=404, detail=f"Sample file not found on disk: {fp}")

    contents = fp.read_bytes()
    res = _run_diagnosis(contents, f"{sample_id}.jpg")
    res["sample_id"] = sample_id
    res["image_url"] = sample_info["image_url"]
    return res


# ═══════════════════════════════════════════════════════════════════════
#  SERVE MODERN REACT FRONTEND (STATIC BUILD)
# ═══════════════════════════════════════════════════════════════════════

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

frontend_dist = Path(__file__).parent / "frontend" / "dist"
frontend_public = Path(__file__).parent / "frontend" / "public"

if (frontend_public / "samples").exists():
    app.mount("/samples", StaticFiles(directory=str(frontend_public / "samples")), name="samples")

# Mount persistent field inspections storage
app.mount("/inspections", StaticFiles(directory=str(INSPECTIONS_DIR)), name="inspections")

if frontend_dist.exists():
    if (frontend_dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        """Serve built React single page application."""
        if full_path.startswith("api/") or full_path.startswith("inspections/"):
            raise HTTPException(status_code=404, detail="Endpoint not found")
        file_path = frontend_dist / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 65)
    print("  PLANTCARE MODERN WEB APP — SERVER STARTING")
    print("  URL: http://127.0.0.1:8000")
    print("  API Docs: http://127.0.0.1:8000/docs")
    print("=" * 65 + "\n")
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
