#!/usr/bin/env python3
"""
severity.py — Modular image-based plant disease severity estimation.

Analyzes the visible proportion of lesion and chlorotic/necrotic discoloration 
on leaf tissue using colorimetric segmentation. Designed as an independent module
that can be easily upgraded with specialized deep segmentation models in the future.
"""

from pathlib import Path
from typing import Union, Dict, Any, Optional
import numpy as np
from PIL import Image

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False


def estimate_disease_severity(
    image_input: Union[str, Path, Image.Image, np.ndarray],
    condition: str = "",
) -> Dict[str, Any]:
    """
    Estimate the visual disease severity of a leaf image based on colorimetric surface analysis.

    IMPORTANT:
    This is an automated visual estimation of symptomatic surface discoloration,
    not an agriculturally certified or laboratory-validated ground truth.

    Args:
        image_input: File path (str/Path), PIL Image, or RGB numpy array.
        condition: Predicted condition string (e.g. 'Early Blight', 'Late Blight', 'Healthy').

    Returns:
        dict containing:
            - severity_level: 'Mild' | 'Moderate' | 'Severe' | 'None (Healthy)' | 'Uncertain'
            - affected_percentage: float (0.0 to 100.0) or None
            - is_reliable: bool
            - status_color: str ('green', 'amber', 'red', 'gray')
            - summary: short title/tag for UI
            - explanation: user-friendly narrative of the estimate
            - disclaimer: scientific/agricultural disclaimer
    """
    disclaimer = (
        "Note: This is an automated visual estimate based on leaf surface discoloration "
        "and is not a laboratory-validated diagnostic ground truth."
    )

    # 1. Condition check: If the crop is healthy, severity is not applicable
    is_healthy = "healthy" in condition.strip().lower()
    if is_healthy:
        return {
            "severity_level": "None (Healthy)",
            "affected_percentage": 0.0,
            "is_reliable": True,
            "status_color": "green",
            "summary": "Healthy Foliage",
            "explanation": "No significant disease lesions or necrotic tissue detected on this leaf.",
            "disclaimer": disclaimer,
        }

    # 2. Dependency check
    if not HAS_CV2:
        return {
            "severity_level": "Uncertain",
            "affected_percentage": None,
            "is_reliable": False,
            "status_color": "gray",
            "summary": "Severity Estimation Unavailable",
            "explanation": "OpenCV library is required for image-based severity analysis.",
            "disclaimer": disclaimer,
        }

    # 3. Standardize image to RGB numpy array
    try:
        if isinstance(image_input, (str, Path)):
            img_path = Path(image_input)
            if not img_path.exists():
                raise FileNotFoundError(f"Image not found: {img_path}")
            bgr = cv2.imread(str(img_path))
            if bgr is None:
                raise ValueError("Failed to decode image file")
            img_rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        elif isinstance(image_input, Image.Image):
            img_rgb = np.array(image_input.convert("RGB"))
        elif isinstance(image_input, np.ndarray):
            img_rgb = image_input
        elif hasattr(image_input, "read"):
            # File-like stream (e.g. Streamlit UploadedFile)
            pil_img = Image.open(image_input)
            img_rgb = np.array(pil_img.convert("RGB"))
        else:
            raise ValueError(f"Unsupported image type: {type(image_input)}")
    except Exception as err:
        return {
            "severity_level": "Uncertain",
            "affected_percentage": None,
            "is_reliable": False,
            "status_color": "gray",
            "summary": "Image Analysis Incomplete",
            "explanation": f"Unable to analyze image pixels: {err}",
            "disclaimer": disclaimer,
        }

    # Resize to standard analysis resolution (e.g. 512 max dim) for consistent morphological scales
    h, w = img_rgb.shape[:2]
    if max(h, w) > 512:
        scale = 512.0 / max(h, w)
        img_rgb = cv2.resize(img_rgb, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    total_pixels = img_rgb.shape[0] * img_rgb.shape[1]
    hsv = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2HSV)

    # 4. Leaf Segmentation (isolate plant tissue from neutral/gray/black backdrops)
    # Plant foliage covers hue ranges from yellow-brown to green: H between 10 and 95
    plant_mask = (
        (hsv[:, :, 1] >= 28) & 
        (hsv[:, :, 2] >= 25) & 
        (hsv[:, :, 0] >= 10) & 
        (hsv[:, :, 0] <= 95)
    )

    # Clean morphological noise (remove small isolated speckles)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    plant_mask = cv2.morphologyEx(plant_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)

    leaf_pixel_count = int(np.sum(plant_mask))
    leaf_ratio = leaf_pixel_count / total_pixels

    # Reliability gate: Leaf area must be clearly distinguishable and cover a reasonable proportion
    if leaf_ratio < 0.05 or leaf_ratio > 0.98:
        return {
            "severity_level": "Uncertain",
            "affected_percentage": None,
            "is_reliable": False,
            "status_color": "gray",
            "summary": "Severity Estimation Uncertain",
            "explanation": (
                "Unable to cleanly distinguish leaf boundaries from the image background. "
                "Ensure the photo clearly features a single leaf on a contrasting background."
            ),
            "disclaimer": disclaimer,
        }

    # 5. Symptomatic / Discolored Tissue Detection
    # Diseased regions (blight lesions, chlorosis, necrotic patches) deviate from healthy green
    r = img_rgb[:, :, 0].astype(np.float32)
    g = img_rgb[:, :, 1].astype(np.float32)
    b = img_rgb[:, :, 2].astype(np.float32)
    exg = 2 * g - r - b  # Excess Green Index

    # Lesion mask within segmented leaf:
    # - Yellow/brown hues (H < 34 in HSV)
    # - Depleted green chlorophyll (Excess Green < 10)
    # - Necrotic browning (Red component comparable to or exceeding Green)
    lesion_mask = plant_mask & (
        (hsv[:, :, 0] < 34) | 
        (exg < 10) | 
        (r > g * 0.95)
    )
    lesion_mask = cv2.morphologyEx(lesion_mask.astype(np.uint8), cv2.MORPH_OPEN, kernel).astype(bool)

    lesion_pixel_count = int(np.sum(lesion_mask))
    affected_pct = round((lesion_pixel_count / leaf_pixel_count) * 100, 1)

    # 6. Severity Categorization (Standard Visual Phytopathology Scale)
    # - Mild: < 10% affected area (localized early spots)
    # - Moderate: 10% - 30% affected area (spreading lesions)
    # - Severe: > 30% affected area (widespread necrosis/blight)
    if affected_pct < 10.0:
        severity_level = "Mild"
        status_color = "amber"
        summary = "Mild Severity"
        explanation = (
            f"Estimated ~{affected_pct}% of the visible leaf surface shows localized discoloration or early spotting. "
            "The infection appears to be in its early stages."
        )
    elif affected_pct <= 30.0:
        severity_level = "Moderate"
        status_color = "amber"
        summary = "Moderate Severity"
        explanation = (
            f"Estimated ~{affected_pct}% of the visible leaf surface exhibits noticeable lesion development and spreading symptoms."
        )
    else:
        severity_level = "Severe"
        status_color = "red"
        summary = "Severe Severity"
        explanation = (
            f"Estimated ~{affected_pct}% of the visible leaf surface shows extensive necrotic blight damage covering large portions of the tissue."
        )

    return {
        "severity_level": severity_level,
        "affected_percentage": affected_pct,
        "is_reliable": True,
        "status_color": status_color,
        "summary": summary,
        "explanation": explanation,
        "disclaimer": disclaimer,
    }
