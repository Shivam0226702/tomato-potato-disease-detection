#!/usr/bin/env python3
"""
app.py — Farmer-Facing Plant Health Diagnostic Assistant.

A clean, modern web interface for diagnosing Tomato and Potato leaf diseases.
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
        padding: 1.2rem;
        border-radius: 10px;
        background-color: #F7FAFC;
        border: 1px solid #E2E8F0;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    .status-healthy {
        color: #22543D;
        font-weight: 700;
        font-size: 1.3rem;
    }
    .status-disease {
        color: #742A2A;
        font-weight: 700;
        font-size: 1.3rem;
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
            from leaf photographs.
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
        '<div class="sub-header">Upload a leaf photo of a tomato or potato plant for an instant health diagnosis.</div>',
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
            with st.spinner("Diagnosing leaf condition..."):
                try:
                    uploaded_file.seek(0)
                    result = predict_image(
                        uploaded_file,
                        model=model,
                        class_names=class_names,
                        device=device,
                        top_k=3,
                    )
                except Exception:
                    st.error("❌ An error occurred during diagnosis. Please try another image.")
                    return

            crop = result["crop"]
            disease = result["disease"]
            confidence = result["confidence"] * 100.0
            is_healthy = disease.lower() == "healthy"

            # ── 4. Diagnosis Result ────────────────────────────────────
            st.divider()
            st.markdown("### Diagnosis Result")

            crop_icon = "🍅" if crop.lower() == "tomato" else "🥔"

            if is_healthy:
                st.success(f"✅ **Healthy Crop** — No signs of disease detected on this {crop.lower()} leaf.")
            else:
                st.warning(f"⚠️ **Condition Identified:** {crop} leaf exhibiting symptoms of **{disease}**.")

            # Summary Metrics
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric(label="Crop Identified", value=f"{crop_icon} {crop}")
            with m2:
                status_label = "Healthy" if is_healthy else disease
                st.metric(label="Condition", value=status_label)
            with m3:
                st.metric(label="Diagnostic Confidence", value=f"{confidence:.1f}%")

            # Basic Information Card
            with st.container():
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                if is_healthy:
                    st.markdown(
                        f"""
                        <div class="status-healthy">🌿 Healthy {crop} Leaf</div>
                        <p style="margin-top: 0.5rem; color: #4A5568;">
                        The leaf exhibits normal pigmentation and texture without visible fungal blight lesions. 
                        Continue standard crop care and regular monitoring.
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"""
                        <div class="status-disease">⚠️ {crop} — {disease}</div>
                        <p style="margin-top: 0.5rem; color: #4A5568;">
                        Symptoms consistent with <b>{disease}</b> were identified with <b>{confidence:.1f}%</b> confidence.
                        Ensure adequate plant spacing, avoid overhead watering, and inspect neighboring plants.
                        </p>
                        """,
                        unsafe_allow_html=True,
                    )
                st.markdown('</div>', unsafe_allow_html=True)

            # Option to test another image
            st.info("💡 To check another leaf, click **'Analyze Another Leaf'** above or choose a new file.")

    else:
        st.info("👆 Select a leaf image above to begin diagnosis.")


if __name__ == "__main__":
    main()
