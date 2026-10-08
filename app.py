#!/usr/bin/env python3
"""
app.py — Farmer-Facing Plant Health Diagnostic Assistant.

A clean, modern web interface for diagnosing Tomato and Potato leaf diseases
and estimating visible disease severity.
"""

from pathlib import Path
from PIL import Image, UnidentifiedImageError
import streamlit as st

# Import reusable model loading and inference logic from predict.py
from predict import (
    load_model,
    load_class_names,
    get_device,
    predict_image,
    RESULTS_DIR,
)

# Import modular image-based severity estimation
from severity import estimate_disease_severity

# Import modular treatment and spray decision engine
from treatment import get_treatment_recommendation

# ═══════════════════════════════════════════════════════════════════════
#  PAGE CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="CropHealth — Plant Leaf Disease Diagnostic",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Custom minimal CSS for a clean, professional agricultural look
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E4620;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4A5568;
        margin-bottom: 1.5rem;
    }
    .result-card {
        padding: 1.25rem;
        border-radius: 10px;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .status-healthy {
        color: #22543D;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .status-mild {
        color: #B7791F;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .status-moderate {
        color: #C05621;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .status-severe {
        color: #9B2C2C;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .status-uncertain {
        color: #4A5568;
        font-weight: 700;
        font-size: 1.25rem;
    }
    .disclaimer-text {
        font-size: 0.82rem;
        color: #718096;
        font-style: italic;
        margin-top: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════
#  CACHED INFERENCE PIPELINE
# ═══════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def get_inference_pipeline():
    """Load diagnostic model and class labels into memory once."""
    device = get_device()
    class_names = load_class_names(RESULTS_DIR)
    model = load_model(
        model_path=RESULTS_DIR / "best_model.pth",
        class_names=class_names,
        device=device,
    )
    return model, class_names, device


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR (USER-FRIENDLY GUIDE ONLY)
# ═══════════════════════════════════════════════════════════════════════

def render_sidebar():
    """Render clean user guide and tips for farmers/growers."""
    with st.sidebar:
        st.header("🌿 CropHealth Guide")
        st.markdown(
            """
            Welcome to the **Plant Leaf Health Diagnostic Tool**.
            
            This application helps growers identify potential crop diseases 
            from leaf photographs and estimates the visual extent of damage.
            """
        )
        st.divider()
        st.subheader("Supported Crops")
        st.markdown(
            """
            * 🍅 **Tomato**
            * 🥔 **Potato**
            """
        )
        st.divider()
        st.subheader("Photo Tips for Best Results")
        st.markdown(
            """
            1. **Focus on a single leaf** filling most of the frame.
            2. Ensure **clear daylight** without heavy shadows.
            3. Avoid blurry or out-of-focus photos.
            4. Capture the surface where symptoms appear most visibly.
            """
        )


# ═══════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════

def main():
    # Session state to allow resetting the uploader cleanly
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0

    # Header & Description
    st.markdown('<div class="main-header">🌿 CropHealth Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Upload a leaf photo of a tomato or potato plant for an instant health diagnosis and visual severity estimate.</div>',
        unsafe_allow_html=True,
    )

    # Initialize model pipeline cleanly without exposing technical details
    try:
        model, class_names, device = get_inference_pipeline()
    except Exception:
        st.error("⚠️ The diagnostic service is temporarily unavailable. Please verify the system setup.")
        return

    render_sidebar()

    # ── 1. Image Upload ───────────────────────────────────────────────
    st.subheader("1. Upload Leaf Image")
    uploaded_file = st.file_uploader(
        "Upload a leaf photo:",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload a clear photo of a tomato or potato leaf (JPG or PNG format).",
        key=f"leaf_uploader_{st.session_state.uploader_key}",
    )

    if uploaded_file is not None:
        # Validate image integrity
        try:
            image = Image.open(uploaded_file)
            image.verify()
            uploaded_file.seek(0)
            image = Image.open(uploaded_file)
        except (UnidentifiedImageError, OSError, ValueError):
            st.error("❌ Unable to read this file. Please upload a valid JPG or PNG photo.")
            return

        # ── 2. Image Preview ──────────────────────────────────────────
        st.markdown("### Leaf Preview")
        st.image(image, caption="Selected Leaf Image", use_container_width=True)

        # ── 3. Prediction Action ──────────────────────────────────────
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            analyze_clicked = st.button("🔍 Analyze Leaf Health", type="primary", use_container_width=True)
        with col_btn2:
            reset_clicked = st.button("🔄 Analyze Another Leaf", use_container_width=True)

        if reset_clicked:
            st.session_state.uploader_key += 1
            st.rerun()

        if analyze_clicked:
            with st.spinner("Diagnosing leaf condition and estimating severity..."):
                try:
                    # 1. Primary Disease Classification (Inference)
                    uploaded_file.seek(0)
                    result = predict_image(
                        uploaded_file,
                        model=model,
                        class_names=class_names,
                        device=device,
                        top_k=3,
                    )

                    # 2. Separate Image-Based Severity Estimation
                    uploaded_file.seek(0)
                    severity_result = estimate_disease_severity(
                        uploaded_file,
                        condition=result["disease"],
                    )
                except Exception:
                    st.error("❌ An error occurred during diagnosis. Please try another image.")
                    return

            crop = result["crop"]
            disease = result["disease"]
            confidence = result["confidence"] * 100.0
            is_healthy = disease.lower() == "healthy"

            severity_level = severity_result["severity_level"]
            affected_pct = severity_result["affected_percentage"]
            is_reliable = severity_result["is_reliable"]
            sev_explanation = severity_result["explanation"]
            disclaimer = severity_result["disclaimer"]

            # ── 4. Diagnosis Result ────────────────────────────────────
            st.divider()
            st.markdown("### Diagnosis Result")

            crop_icon = "🍅" if crop.lower() == "tomato" else "🥔"

            if is_healthy:
                st.success(f"✅ **Healthy Crop** — No signs of disease detected on this {crop.lower()} leaf.")
            else:
                st.warning(f"⚠️ **Condition Identified:** {crop} leaf exhibiting symptoms of **{disease}**.")

            # Summary Metrics (4 clean columns)
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric(label="Crop Identified", value=f"{crop_icon} {crop}")
            with m2:
                status_label = "Healthy" if is_healthy else disease
                st.metric(label="Disease Detected", value=status_label)
            with m3:
                st.metric(label="Diagnostic Confidence", value=f"{confidence:.1f}%")
            with m4:
                # Severity metric display with clean badge
                if is_healthy:
                    sev_display = "🟢 None"
                elif severity_level == "Mild":
                    sev_display = "🟡 Mild"
                elif severity_level == "Moderate":
                    sev_display = "🟠 Moderate"
                elif severity_level == "Severe":
                    sev_display = "🔴 Severe"
                else:
                    sev_display = "⚪ Uncertain"
                st.metric(label="Estimated Severity", value=sev_display)

            # ── 5. Detailed Health & Severity Information Card ─────────
            with st.container():
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                
                if is_healthy:
                    st.markdown(
                        f"""
                        <div class="status-healthy">🌿 Healthy {crop} Foliage</div>
                        <p style="margin-top: 0.5rem; color: #4A5568;">
                        The leaf exhibits normal green coloration and texture without visible fungal blight lesions. 
                        Continue standard crop care and regular monitoring.
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    # Class for severity styling
                    status_class = (
                        "status-mild" if severity_level == "Mild"
                        else "status-moderate" if severity_level == "Moderate"
                        else "status-severe" if severity_level == "Severe"
                        else "status-uncertain"
                    )

                    st.markdown(
                        f"""
                        <div class="{status_class}">⚠️ {crop} — {disease} ({severity_level} Severity)</div>
                        <p style="margin-top: 0.5rem; color: #4A5568;">
                        {sev_explanation}
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Visual progress bar of estimated affected leaf surface (if quantifiable)
                    if affected_pct is not None and is_reliable:
                        st.markdown(f"**Estimated Leaf Discoloration Area:** `{affected_pct:.1f}%` of visible leaf")
                        progress_val = min(max(affected_pct / 100.0, 0.0), 1.0)
                        st.progress(progress_val)

                    if not is_reliable:
                        st.info("ℹ️ Note: Exact severity percentage could not be determined due to background interference.")

                # Transparent agricultural disclaimer
                st.markdown(f'<div class="disclaimer-text">{disclaimer}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # ── 6. Treatment Recommendation ────────────────────────────
            st.divider()
            st.markdown("### 🌾 Treatment Recommendation")

            rec = get_treatment_recommendation(
                crop=crop,
                disease=disease,
                severity=severity_level,
            )

            # Disease & Estimated Severity Overview
            st.markdown(
                f"""
                <div class="result-card">
                    <p style="margin: 0; font-size: 1rem; color: #2D3748;">
                        <b>Disease:</b> {rec.crop} {rec.disease}<br>
                        <b>Estimated severity:</b> {rec.severity}
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Recommended Action
            st.markdown("#### Recommended action:")
            if is_healthy:
                st.success(rec.recommended_action)
            elif severity_level == "Mild":
                st.info(rec.recommended_action)
            elif severity_level == "Moderate":
                st.warning(rec.recommended_action)
            elif severity_level == "Severe":
                st.error(rec.recommended_action)
            else:
                st.info(rec.recommended_action)

            # Management (Cultural / Sanitation / Monitoring)
            st.markdown("#### Management:")
            for practice in rec.management_practices:
                st.markdown(f"- {practice}")

            # Treatment (General Categories & Extension Guidance)
            st.markdown("#### Treatment:")
            st.markdown(rec.treatment_guidance)

            # Professional Advisory Expander
            with st.expander("ℹ️ When to Seek Professional / Extension Advice"):
                st.markdown(rec.professional_advice)

            # Educational Disclaimer
            st.markdown(f'<div class="disclaimer-text">{rec.disclaimer}</div>', unsafe_allow_html=True)

            # Option to test another image
            st.info("💡 To check another leaf, click **'Analyze Another Leaf'** above or choose a new file.")


    else:
        st.info("👆 Select a leaf image above to begin diagnosis.")


if __name__ == "__main__":
    main()
