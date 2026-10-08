#!/usr/bin/env python3
"""
app.py — Farmer-Facing Plant Health Diagnostic Assistant.

A clean, modern web interface for diagnosing Tomato and Potato leaf diseases,
estimating visible disease severity, providing practical treatment recommendations,
and maintaining local SQLite scan history.
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

# Import local SQLite database module
from database import (
    init_db,
    save_scan,
    get_scan_history,
    get_scan_by_id,
    clear_history,
    DEFAULT_DB_PATH,
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
        margin-bottom: 1.25rem;
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
            from leaf photographs, estimate visual disease severity, 
            receive practical treatment guidance, and track scan history.
            """
        )
        st.divider()
        st.subheader("Navigation")
        st.markdown(
            """
            * 🔬 **Leaf Diagnosis:** Upload and analyze leaf photographs.
            * 📜 **Scan History:** Review saved diagnostic records.
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
#  LEAF DIAGNOSIS VIEW
# ═══════════════════════════════════════════════════════════════════════

def render_diagnosis_view(model, class_names, device):
    """Render leaf photo upload, analysis, recommendations, and saving flow."""
    # ── 1. Image Upload ───────────────────────────────────────────────
    st.subheader("1. Upload Leaf Image")
    uploaded_file = st.file_uploader(
        "Upload a leaf photo:",
        type=["jpg", "jpeg", "png", "webp"],
        help="Upload a clear photo of a tomato or potato leaf (JPG or PNG format).",
        key=f"leaf_uploader_{st.session_state.uploader_key}",
    )

    if uploaded_file is not None:
        # Check if a new file was uploaded to reset past analysis state
        file_token = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("current_file_token") != file_token:
            st.session_state.current_file_token = file_token
            st.session_state.current_analysis = None
            st.session_state.is_saved = False
            st.session_state.saved_scan_id = None

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
            st.session_state.current_analysis = None
            st.session_state.current_file_token = None
            st.session_state.is_saved = False
            st.session_state.saved_scan_id = None
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

            # Treatment Decision
            rec = get_treatment_recommendation(
                crop=crop,
                disease=disease,
                severity=severity_level,
            )

            # Store active analysis in session state to persist across reruns
            st.session_state.current_analysis = {
                "token": file_token,
                "crop": crop,
                "disease": disease,
                "confidence": confidence,
                "is_healthy": is_healthy,
                "severity_level": severity_level,
                "affected_pct": affected_pct,
                "is_reliable": is_reliable,
                "sev_explanation": sev_explanation,
                "disclaimer": disclaimer,
                "treatment_rec": rec,
            }
            st.session_state.is_saved = False
            st.session_state.saved_scan_id = None

        # If an active analysis is available for this file, render the full report
        if st.session_state.get("current_analysis") is not None:
            analysis = st.session_state.current_analysis
            crop = analysis["crop"]
            disease = analysis["disease"]
            confidence = analysis["confidence"]
            is_healthy = analysis["is_healthy"]
            severity_level = analysis["severity_level"]
            affected_pct = analysis["affected_pct"]
            is_reliable = analysis["is_reliable"]
            sev_explanation = analysis["sev_explanation"]
            disclaimer = analysis["disclaimer"]
            rec = analysis["treatment_rec"]

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
                st.metric(label="Prediction Confidence", value=f"{confidence:.1f}%")
                st.caption("Confidence indicates the model's prediction score and does not guarantee real-world diagnostic certainty.")
            with m4:
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

                    if affected_pct is not None and is_reliable:
                        st.markdown(f"**Estimated Leaf Discoloration Area:** `{affected_pct:.1f}%` of visible leaf")
                        progress_val = min(max(affected_pct / 100.0, 0.0), 1.0)
                        st.progress(progress_val)

                    if not is_reliable:
                        st.info("ℹ️ Note: Exact severity percentage could not be determined due to background interference.")

                st.markdown(f'<div class="disclaimer-text">{disclaimer}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # ── 6. Treatment Recommendation ────────────────────────────
            st.divider()
            st.markdown("### 🌾 Treatment Recommendation")

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

            st.markdown("#### Management:")
            for practice in rec.management_practices:
                st.markdown(f"- {practice}")

            st.markdown("#### Treatment:")
            st.markdown(rec.treatment_guidance)

            with st.expander("ℹ️ When to Seek Professional / Extension Advice"):
                st.markdown(rec.professional_advice)

            st.markdown(f'<div class="disclaimer-text">{rec.disclaimer}</div>', unsafe_allow_html=True)

            # ── 7. Save Analysis to Database ───────────────────────────
            st.divider()
            st.markdown("### 💾 Save Scan Record")

            if st.session_state.get("is_saved", False):
                saved_id = st.session_state.get("saved_scan_id")
                st.success(f"✅ Analysis saved successfully (Record #{saved_id} in scan history).")
                st.button("💾 Analysis Already Saved", disabled=True, use_container_width=True)
            else:
                if st.button("💾 Save Analysis", type="primary", use_container_width=True):
                    treatment_summary_text = (
                        f"Action: {rec.recommended_action}\n\n"
                        f"Treatment: {rec.treatment_guidance}"
                    )
                    new_scan_id = save_scan(
                        crop=crop,
                        disease=disease,
                        prediction_confidence=confidence,
                        severity=severity_level,
                        affected_area_percentage=affected_pct,
                        treatment_summary=treatment_summary_text,
                    )
                    st.session_state.is_saved = True
                    st.session_state.saved_scan_id = new_scan_id
                    st.success("✅ Analysis saved successfully.")
                    st.rerun()

            st.info("💡 To check another leaf, click **'Analyze Another Leaf'** above or choose a new file.")

    else:
        st.info("👆 Select a leaf image above to begin diagnosis.")


# ═══════════════════════════════════════════════════════════════════════
#  SCAN HISTORY VIEW
# ═══════════════════════════════════════════════════════════════════════

def render_history_view():
    """Render historical scan records, summary metrics, and detail viewer."""
    st.subheader("📜 Plant Health Scan History")
    st.markdown("Review previously saved diagnostic records, disease severities, and treatment summaries.")

    scans = get_scan_history(limit=100)

    if not scans:
        st.info("ℹ️ No saved scans found yet. Analyze a leaf in the diagnosis tab and click **'Save Analysis'** to store records.")
        return

    # Summary Statistics
    total_scans = len(scans)
    healthy_count = sum(1 for s in scans if s["disease"].lower() == "healthy")
    diseased_count = total_scans - healthy_count

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Saved Scans", total_scans)
    with c2:
        st.metric("Healthy Plants", healthy_count)
    with c3:
        st.metric("Diseased Plants", diseased_count)

    st.markdown("#### Past Scans")

    # Table representation
    history_table = []
    for s in scans:
        crop_icon = "🍅" if s["crop"].lower() == "tomato" else "🥔"
        history_table.append({
            "Scan ID": s["scan_id"],
            "Timestamp": s["timestamp"],
            "Crop": f"{crop_icon} {s['crop']}",
            "Condition": s["disease"],
            "Severity": s["severity"],
            "Confidence": f"{s['prediction_confidence']:.1f}%",
        })

    st.dataframe(history_table, use_container_width=True, hide_index=True)

    # Detailed Inspection of a Scan
    st.markdown("#### 🔍 View Scan Details")
    scan_options = {
        f"Scan #{s['scan_id']} — {s['timestamp']} ({s['crop']} {s['disease']} - {s['severity']})": s["scan_id"]
        for s in scans
    }

    selected_label = st.selectbox(
        "Select a scan record to review details:",
        options=list(scan_options.keys()),
        index=0,
    )
    selected_id = scan_options[selected_label]
    selected_scan = get_scan_by_id(selected_id)

    if selected_scan:
        with st.container():
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            is_scan_healthy = selected_scan["disease"].lower() == "healthy"
            crop_icon = "🍅" if selected_scan["crop"].lower() == "tomato" else "🥔"

            if is_scan_healthy:
                st.markdown(
                    f'<div class="status-healthy">🌿 Scan #{selected_scan["scan_id"]}: Healthy {selected_scan["crop"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="status-moderate">⚠️ Scan #{selected_scan["scan_id"]}: {selected_scan["crop"]} — {selected_scan["disease"]} ({selected_scan["severity"]})</div>',
                    unsafe_allow_html=True,
                )

            d1, d2, d3, d4 = st.columns(4)
            with d1:
                st.metric("Date & Time", selected_scan["timestamp"])
            with d2:
                st.metric("Crop", f"{crop_icon} {selected_scan['crop']}")
            with d3:
                st.metric("Prediction Confidence", f"{selected_scan['prediction_confidence']:.1f}%")
            with d4:
                st.metric("Severity", selected_scan["severity"])

            if selected_scan["affected_area_percentage"] is not None:
                st.markdown(f"**Estimated Leaf Discoloration Area:** `{selected_scan['affected_area_percentage']:.1f}%`")

            if selected_scan["treatment_summary"]:
                st.markdown("##### 🌾 Saved Treatment & Management Guidance")
                st.info(selected_scan["treatment_summary"])

            st.markdown('</div>', unsafe_allow_html=True)

    # Optional Management (Clear History)
    with st.expander("⚙️ Manage History Data"):
        st.write("Need to clear previous testing records?")
        if st.button("🗑️ Clear All Scan Records", type="secondary"):
            clear_history()
            st.success("All scan records have been cleared.")
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════
#  MAIN ENTRYPOINT
# ═══════════════════════════════════════════════════════════════════════

def main():
    # Initialize SQLite database schema automatically
    init_db(DEFAULT_DB_PATH)

    # Session state initialization
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0
    if "current_analysis" not in st.session_state:
        st.session_state.current_analysis = None
    if "current_file_token" not in st.session_state:
        st.session_state.current_file_token = None
    if "is_saved" not in st.session_state:
        st.session_state.is_saved = False
    if "saved_scan_id" not in st.session_state:
        st.session_state.saved_scan_id = None

    # Header & Description
    st.markdown('<div class="main-header">🌿 CropHealth Assistant</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub-header">Upload a leaf photo of a tomato or potato plant for an instant health diagnosis, visual severity estimate, and treatment guidance.</div>',
        unsafe_allow_html=True,
    )

    # Initialize model pipeline cleanly without exposing technical details
    try:
        model, class_names, device = get_inference_pipeline()
    except Exception:
        st.error("⚠️ The diagnostic service is temporarily unavailable. Please verify the system setup.")
        return

    render_sidebar()

    # Navigation Tabs
    tab_diagnose, tab_history = st.tabs(["🔬 Leaf Diagnosis", "📜 Scan History"])

    with tab_diagnose:
        render_diagnosis_view(model, class_names, device)

    with tab_history:
        render_history_view()


if __name__ == "__main__":
    main()
