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

# Import modular agricultural query engine
from query_engine import answer_query

# Import modular prototype yield estimator
import importlib
import yield_estimator
importlib.reload(yield_estimator)
from yield_estimator import calculate_yield_estimate, YIELD_DISCLAIMER, YieldEstimateResult


def extract_yield_metrics(result: YieldEstimateResult) -> dict:
    """Safely extract both kg and ton values from YieldEstimateResult, guaranteeing math consistency."""
    tons_per_unit = result.estimated_yield_per_unit
    total_tons = result.estimated_total_yield
    r_min_tons = result.range_min
    r_max_tons = result.range_max

    # 1 metric ton = 1,000 kg
    kg_per_unit = getattr(result, "estimated_yield_kg_per_unit", None)
    if kg_per_unit is None:
        kg_per_unit = round(tons_per_unit * 1000.0)

    total_kg = getattr(result, "estimated_total_yield_kg", None)
    if total_kg is None:
        total_kg = round(total_tons * 1000.0)

    range_min_kg = getattr(result, "range_min_kg", None)
    if range_min_kg is None:
        range_min_kg = round(r_min_tons * 1000.0)

    range_max_kg = getattr(result, "range_max_kg", None)
    if range_max_kg is None:
        range_max_kg = round(r_max_tons * 1000.0)

    return {
        "tons_per_unit": tons_per_unit,
        "total_tons": total_tons,
        "range_min_tons": r_min_tons,
        "range_max_tons": r_max_tons,
        "kg_per_unit": kg_per_unit,
        "total_kg": total_kg,
        "range_min_kg": range_min_kg,
        "range_max_kg": range_max_kg,
    }


def render_metric_card(title: str, primary_val: str, secondary_val: str):
    """Render a clean, responsive metric card that prevents text truncation."""
    card_html = f"""
    <div style="
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
    ">
        <div style="font-size: 0.82rem; font-weight: 600; color: #4A5568; text-transform: uppercase; letter-spacing: 0.4px;">
            {title}
        </div>
        <div style="font-size: 1.25rem; font-weight: 700; color: #1E293B; margin-top: 0.25rem; line-height: 1.3; word-break: normal; white-space: normal;">
            {primary_val}
        </div>
        <div style="font-size: 0.85rem; color: #64748B; margin-top: 0.15rem; font-weight: 500;">
            {secondary_val}
        </div>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

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
            * 🌾 **Yield Estimation:** Prototype crop yield and disease impact estimation.
            * 📜 **Scan History:** Review saved diagnostic records.
            * 💬 **Ask PlantCare:** Ask questions about tomato & potato disease management.
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
                "severity": severity_level,
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

            # ── 7. Yield Estimation (Prototype) ────────────────────────
            st.divider()
            st.markdown("### 🌾 Yield Estimation (Prototype)")
            st.caption("Estimated crop yield based on baseline agronomic assumptions and detected disease impact.")

            col_area, col_unit = st.columns([2, 1])
            with col_area:
                cultivated_area = st.number_input(
                    "Cultivated Area:",
                    min_value=0.1,
                    max_value=10000.0,
                    value=1.5 if crop.lower() == "tomato" and disease.lower() != "healthy" else 1.0,
                    step=0.5,
                    format="%.1f",
                    key="diag_cultivated_area",
                    help="Enter your cultivated plot or field size.",
                )
            with col_unit:
                area_unit = st.selectbox(
                    "Unit:",
                    options=["acre", "hectare"],
                    index=0,
                    key="diag_area_unit",
                )

            # Compute yield estimation using active scan context
            yield_res = calculate_yield_estimate(
                crop=crop,
                cultivated_area=cultivated_area,
                area_unit=area_unit,
                disease=disease,
                severity=severity_level,
            )

            with st.container():
                st.markdown('<div class="result-card">', unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <p style="margin: 0; font-size: 0.95rem; color: #2D3748;">
                        <b>Crop:</b> {yield_res.crop} &nbsp;|&nbsp; 
                        <b>Cultivated Area:</b> {yield_res.cultivated_area} {yield_res.area_unit}(s) &nbsp;|&nbsp; 
                        <b>Condition:</b> {yield_res.disease} &nbsp;|&nbsp; 
                        <b>Severity:</b> {yield_res.severity}
                    </p>
                    """,
                    unsafe_allow_html=True,
                )
                y_metrics = extract_yield_metrics(yield_res)

                # Responsive 2x2 card layout preventing truncation
                y_r1_1, y_r1_2 = st.columns(2)
                with y_r1_1:
                    render_metric_card(
                        title="Estimated Yield",
                        primary_val=f"{y_metrics['kg_per_unit']:,.0f} kg/{yield_res.area_unit}",
                        secondary_val=f"({y_metrics['tons_per_unit']:.1f} tons/{yield_res.area_unit})",
                    )
                with y_r1_2:
                    render_metric_card(
                        title="Estimated Total Harvest",
                        primary_val=f"{y_metrics['total_kg']:,.0f} kg",
                        secondary_val=f"({y_metrics['total_tons']:.1f} tons)",
                    )

                y_r2_1, y_r2_2 = st.columns(2)
                with y_r2_1:
                    render_metric_card(
                        title="Expected Harvest Range",
                        primary_val=f"{y_metrics['range_min_kg']:,.0f}–{y_metrics['range_max_kg']:,.0f} kg",
                        secondary_val=f"({y_metrics['range_min_tons']:.1f}–{y_metrics['range_max_tons']:.1f} tons)",
                    )
                with y_r2_2:
                    impact_label = "None" if yield_res.disease == "Healthy" else yield_res.severity
                    render_metric_card(
                        title="Disease Impact",
                        primary_val=impact_label,
                        secondary_val=f"Assumed reduction: {yield_res.loss_percentage:.0f}%",
                    )

                baseline_kg = round(yield_res.baseline_yield_per_acre * 1000.0)
                st.caption(
                    f"ℹ️ Assumed healthy baseline: **{baseline_kg:,.0f} kg/acre ({yield_res.baseline_yield_per_acre:.1f} tons/acre)**. "
                    f"Assumed prototype yield reduction from {yield_res.disease} ({yield_res.severity}): **{yield_res.loss_percentage:.0f}%**. "
                    "Prototype estimate based on an assumed healthy baseline and disease-severity impact factors. "
                    "Actual yield impact varies with crop variety, weather, soil, irrigation, farm management, and disease progression."
                )

                st.markdown(f'<div class="disclaimer-text">{yield_res.disclaimer}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            # ── 8. Save Analysis to Database ───────────────────────────
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
                    yield_notes = (
                        f"Estimated total harvest: {y_metrics['total_kg']:,.0f} kg ({y_metrics['total_tons']:.1f} tons) "
                        f"({y_metrics['kg_per_unit']:,.0f} kg/{yield_res.area_unit} / {y_metrics['tons_per_unit']:.1f} tons/{yield_res.area_unit}) "
                        f"on {yield_res.cultivated_area:.1f} {yield_res.area_unit}(s). "
                        f"Impact: {yield_res.impact_category}."
                    )
                    new_scan_id = save_scan(
                        crop=crop,
                        disease=disease,
                        prediction_confidence=confidence,
                        severity=severity_level,
                        affected_area_percentage=affected_pct,
                        treatment_summary=treatment_summary_text,
                        notes=yield_notes,
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
#  FARMER QUERY VIEW (💬 ASK PLANTCARE)
# ═══════════════════════════════════════════════════════════════════════

def render_query_view():
    """Render farmer question/answer feature for Tomato & Potato plant health."""
    st.subheader("💬 Ask PlantCare")
    st.markdown("Ask agricultural and management questions about your **Tomato** or **Potato** crops.")

    # 1. Active scan context indicator
    active_analysis = st.session_state.get("current_analysis")
    if active_analysis is not None:
        crop = active_analysis["crop"]
        disease = active_analysis["disease"]
        severity = active_analysis["severity_level"]
        crop_icon = "🍅" if crop.lower() == "tomato" else "🥔"
        st.info(
            f"🌱 **Active Leaf Diagnosis Context:** {crop_icon} {crop} — **{disease}** ({severity} severity)  \n"
            f"You can ask follow-up questions directly, such as *\"What should I do now?\"* or *\"What spray should I use?\"*."
        )
    else:
        st.markdown(
            """
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.6rem 0.9rem; margin-bottom: 0.75rem;">
                <small style="color: #718096;">💡 <i>Tip: Scan a leaf in the <b>Leaf Diagnosis</b> tab to enable context-aware questions like "What should I do now?".</i></small>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 2. Example Questions
    st.markdown("**Sample Questions:**")
    ex_col1, ex_col2 = st.columns(2)
    sample_queries = [
        "What is tomato early blight?",
        "How can I prevent late blight?",
        "What should I do if my tomato has early blight?",
        "How does early blight spread?",
        "What should I do for moderate potato late blight?",
    ]

    for i, q_text in enumerate(sample_queries):
        target_col = ex_col1 if i % 2 == 0 else ex_col2
        with target_col:
            if st.button(f"👉 {q_text}", key=f"btn_ex_q_{i}", use_container_width=True):
                st.session_state["pending_query"] = q_text

    # 3. Query Form
    default_text = st.session_state.pop("pending_query", "")

    with st.form(key="plantcare_query_form", clear_on_submit=False):
        user_question = st.text_input(
            "Enter your question:",
            value=default_text,
            placeholder="e.g., What should I do for moderate potato late blight? or What should I do now?",
            key="plantcare_query_input",
        )
        submitted = st.form_submit_button("🔍 Ask PlantCare", type="primary", use_container_width=True)

    # 4. Process Question
    active_q = user_question.strip() if submitted else default_text.strip()
    if active_q:
        with st.spinner("Retrieving agricultural guidance..."):
            res = answer_query(active_q, context=active_analysis)

        with st.container():
            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(f"**Question Asked:** *{active_q}*")
            st.divider()
            st.markdown(res["answer"])
            st.markdown('</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  YIELD ESTIMATION VIEW (🌾 YIELD ESTIMATION)
# ═══════════════════════════════════════════════════════════════════════

def render_yield_view():
    """Render interactive crop yield estimation dashboard with context carryover or manual simulation."""
    st.subheader("🌾 Crop Yield Estimation (Prototype)")
    st.markdown("Estimate expected harvest yield and potential disease impacts for **Tomato** and **Potato** crops.")

    active_analysis = st.session_state.get("current_analysis")

    # ── CASE 1: ACTIVE LEAF DIAGNOSIS EXISTS ──────────────────────────
    if active_analysis is not None:
        active_crop = active_analysis.get("crop", "Tomato")
        active_disease = active_analysis.get("disease", "Healthy")
        active_conf = active_analysis.get("confidence", 0.0)

        # Robustly extract severity: check "severity", "severity_level", etc.
        raw_sev = active_analysis.get("severity") or active_analysis.get("severity_level")
        if not raw_sev or not str(raw_sev).strip():
            active_sev = "Not available"
        else:
            active_sev = str(raw_sev).strip()

        active_affected_pct = active_analysis.get("affected_pct")
        is_reliable = active_analysis.get("is_reliable", True)
        crop_icon = "🍅" if active_crop.lower() == "tomato" else "🥔"

        # Active Diagnosis Context Header & Summary
        st.markdown("### 📋 Active Leaf Diagnosis Context")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric(label="Crop", value=f"{crop_icon} {active_crop}")
        with c2:
            st.metric(label="Condition", value=active_disease)
        with c3:
            st.metric(label="Prediction Confidence", value=f"{active_conf:.1f}%")
            st.caption("Model prediction score")
        with c4:
            if active_sev == "Moderate":
                sev_label = "🟠 Moderate"
            elif active_sev == "Mild":
                sev_label = "🟡 Mild"
            elif active_sev == "Severe":
                sev_label = "🔴 Severe"
            elif "Healthy" in active_sev or active_sev == "None":
                sev_label = "🟢 None (Healthy)"
            elif active_sev == "Not available":
                sev_label = "⚪ Not available"
            elif active_sev == "Uncertain":
                sev_label = "⚪ Uncertain"
            else:
                sev_label = active_sev
            st.metric(label="Severity", value=sev_label)

        if active_affected_pct is not None and is_reliable:
            st.caption(f"**Estimated Leaf Discoloration Area:** `{active_affected_pct:.1f}%` of visible leaf")
        elif not is_reliable and active_disease.lower() != "healthy":
            st.caption("ℹ️ Exact leaf discoloration percentage could not be determined due to background variation.")

        st.divider()

        # Cultivated Area Input
        st.markdown("#### 📐 Cultivated Area")
        col_area, col_unit = st.columns([2, 1])
        with col_area:
            area_val = st.number_input(
                "Cultivated Area:",
                min_value=0.1,
                max_value=10000.0,
                value=1.0,
                step=0.5,
                format="%.1f",
                key="yield_active_area",
                help="Enter your cultivated plot or field size.",
            )
        with col_unit:
            unit_val = st.selectbox(
                "Unit:",
                options=["acre", "hectare"],
                index=0,
                key="yield_active_unit",
            )

        # Calculate Yield Estimate from active diagnosis context
        result = calculate_yield_estimate(
            crop=active_crop,
            cultivated_area=area_val,
            area_unit=unit_val,
            disease=active_disease,
            severity=active_sev,
        )

        # Optional Manual Scenario Simulation Expander
        with st.expander("⚙️ Simulate Alternative Crop or Disease Scenario (Manual Override)"):
            st.caption("Test how harvest estimates change under alternative disease conditions or crops:")
            m_col1, m_col2 = st.columns(2)
            sim_crop_opts = ["Tomato", "Potato"]
            sim_c_idx = sim_crop_opts.index(active_crop) if active_crop in sim_crop_opts else 0
            with m_col1:
                sim_crop = st.selectbox("Simulate Crop:", options=sim_crop_opts, index=sim_c_idx, key="sim_crop")

            sim_dis_opts = ["Healthy", "Early Blight", "Late Blight"]
            sim_d_idx = sim_dis_opts.index(active_disease) if active_disease in sim_dis_opts else 0
            with m_col2:
                sim_disease = st.selectbox("Simulate Condition:", options=sim_dis_opts, index=sim_d_idx, key="sim_disease")

            m_col3, _ = st.columns([1, 1])
            with m_col3:
                if sim_disease == "Healthy":
                    sim_sev = "None (Healthy)"
                    st.selectbox("Simulate Severity:", options=["None (Healthy)"], index=0, disabled=True, key="sim_sev_none")
                else:
                    sim_sev_opts = ["Mild", "Moderate", "Severe"]
                    sim_s_idx = sim_sev_opts.index(active_sev) if active_sev in sim_sev_opts else 1
                    sim_sev = st.selectbox("Simulate Severity:", options=sim_sev_opts, index=sim_s_idx, key="sim_sev")

            use_simulation = st.checkbox("Apply Simulated Scenario to Yield Display", value=False, key="apply_sim")
            if use_simulation:
                result = calculate_yield_estimate(
                    crop=sim_crop,
                    cultivated_area=area_val,
                    area_unit=unit_val,
                    disease=sim_disease,
                    severity=sim_sev,
                )

    # ── CASE 2: NO ACTIVE LEAF ANALYSIS (MANUAL INPUT MODE) ──────────
    else:
        st.markdown(
            """
            <div style="background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1rem;">
                <span style="color: #4A5568;">
                    💡 <b>No active leaf scan found.</b> Select your crop, condition, and plot size below to simulate prototype harvest estimates, 
                    or scan a leaf photo in the <b>Leaf Diagnosis</b> tab to carry over diagnosis automatically.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("#### Crop & Plot Parameters")
        col1, col2 = st.columns(2)
        with col1:
            selected_crop = st.selectbox(
                "Crop:",
                options=["Tomato", "Potato"],
                index=0,
                key="manual_crop",
            )
        with col2:
            selected_disease = st.selectbox(
                "Condition:",
                options=["Healthy", "Early Blight", "Late Blight"],
                index=0,
                key="manual_disease",
            )

        col3, col4 = st.columns(2)
        with col3:
            if selected_disease == "Healthy":
                selected_sev = "None (Healthy)"
                st.selectbox(
                    "Severity:",
                    options=["None (Healthy)"],
                    index=0,
                    disabled=True,
                    key="manual_sev_disabled",
                )
            else:
                selected_sev = st.selectbox(
                    "Severity:",
                    options=["Mild", "Moderate", "Severe"],
                    index=1,
                    key="manual_sev",
                )
        with col4:
            sub_col_a, sub_col_u = st.columns([2, 1])
            with sub_col_a:
                area_val = st.number_input(
                    "Cultivated Area:",
                    min_value=0.1,
                    max_value=10000.0,
                    value=1.0,
                    step=0.5,
                    format="%.1f",
                    key="manual_area",
                    help="Enter your cultivated plot or field size.",
                )
            with sub_col_u:
                unit_val = st.selectbox(
                    "Unit:",
                    options=["acre", "hectare"],
                    index=0,
                    key="manual_unit",
                )

        result = calculate_yield_estimate(
            crop=selected_crop,
            cultivated_area=area_val,
            area_unit=unit_val,
            disease=selected_disease,
            severity=selected_sev,
        )

    # ── DISPLAY YIELD ESTIMATION RESULTS ──────────────────────────────
    st.divider()
    st.markdown("#### 📊 Yield Estimation Result")

    with st.container():
        st.markdown('<div class="result-card">', unsafe_allow_html=True)
        crop_icon = "🍅" if result.crop.lower() == "tomato" else "🥔"
        st.markdown(
            f"""
            <p style="margin: 0; font-size: 1rem; color: #1E293B; line-height: 1.6;">
                <b>Crop:</b> {crop_icon} {result.crop} &nbsp;|&nbsp; 
                <b>Condition:</b> {result.disease} &nbsp;|&nbsp; 
                <b>Severity:</b> {result.severity} &nbsp;|&nbsp; 
                <b>Cultivated Area:</b> {result.cultivated_area} {result.area_unit}(s)
            </p>
            """,
            unsafe_allow_html=True,
        )
        m = extract_yield_metrics(result)

        # Responsive 2x2 card layout preventing truncation
        col_r1_1, col_r1_2 = st.columns(2)
        with col_r1_1:
            render_metric_card(
                title="Estimated Yield",
                primary_val=f"{m['kg_per_unit']:,.0f} kg/{result.area_unit}",
                secondary_val=f"({m['tons_per_unit']:.1f} tons/{result.area_unit})",
            )
        with col_r1_2:
            render_metric_card(
                title="Estimated Total Harvest",
                primary_val=f"{m['total_kg']:,.0f} kg",
                secondary_val=f"({m['total_tons']:.1f} tons)",
            )

        col_r2_1, col_r2_2 = st.columns(2)
        with col_r2_1:
            render_metric_card(
                title="Expected Harvest Range",
                primary_val=f"{m['range_min_kg']:,.0f}–{m['range_max_kg']:,.0f} kg",
                secondary_val=f"({m['range_min_tons']:.1f}–{m['range_max_tons']:.1f} tons)",
            )
        with col_r2_2:
            impact_display = "None" if result.disease == "Healthy" else result.severity
            render_metric_card(
                title="Disease Impact",
                primary_val=impact_display,
                secondary_val=f"Assumed yield reduction: {result.loss_percentage:.0f}%",
            )

        baseline_kg = round(result.baseline_yield_per_acre * 1000.0)
        st.caption(
            f"ℹ️ Assumed healthy baseline: **{baseline_kg:,.0f} kg/acre ({result.baseline_yield_per_acre:.1f} tons/acre)**. "
            f"Assumed prototype yield reduction from {result.disease} ({result.severity}): **{result.loss_percentage:.0f}%**. "
            "Prototype estimate based on an assumed healthy baseline and disease-severity impact factors. "
            "Actual yield impact varies with crop variety, weather, soil, irrigation, farm management, and disease progression."
        )

        st.markdown(f'<div class="disclaimer-text">{result.disclaimer}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


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
    tab_diagnose, tab_yield, tab_history, tab_qa = st.tabs([
        "🔬 Leaf Diagnosis",
        "🌾 Yield Estimation",
        "📜 Scan History",
        "💬 Ask PlantCare",
    ])

    with tab_diagnose:
        render_diagnosis_view(model, class_names, device)

    with tab_yield:
        render_yield_view()

    with tab_history:
        render_history_view()

    with tab_qa:
        render_query_view()


if __name__ == "__main__":
    main()
