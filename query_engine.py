"""query_engine.py — Natural language retrieval and question-answering engine for PlantCare.

Matches farmer queries against the structured knowledge base in knowledge_base.py
and provides context-aware answers based on active leaf scan results.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from knowledge_base import GENERAL_DISCLAIMER, KNOWLEDGE_BASE


# Agricultural keywords indicating an on-topic plant health question
AGRICULTURAL_KEYWORDS = {
    "tomato", "tomatoes", "potato", "potatoes", "blight", "early blight", "late blight",
    "leaf", "leaves", "crop", "crops", "plant", "plants", "fungus", "fungal", "fungicide",
    "disease", "diseases", "spray", "spraying", "rot", "mold", "spores", "yield",
    "water", "watering", "irrigation", "soil", "fertilizer", "mulch", "prune", "pruning",
    "healthy", "symptom", "symptoms", "prevent", "prevention", "treat", "treatment",
    "cure", "heal", "infestans", "alternaria", "tuber", "tubers", "foliage", "seed",
    "spot", "spots", "yellow", "brown", "black", "target", "bullseye", "chlorosis",
    "harvest", "extension", "agronomist", "scout", "scouting",
}

# Patterns indicating contextual deictic queries referring to active scan
CONTEXT_PATTERNS = [
    r"what\s+(should|can|do)\s+i\s+do(\s+now)?",
    r"what\s+to\s+do(\s+now)?",
    r"what\s+are\s+the\s+next\s+steps",
    r"how\s+(should|can)\s+i\s+treat\s+this",
    r"how\s+to\s+treat\s+this",
    r"what\s+is\s+my\s+diagnosis",
    r"what\s+is\s+wrong\s+with\s+my\s+plant",
    r"is\s+this\s+(serious|severe|bad|curable)",
    r"what\s+spray\s+should\s+i\s+use",
    r"can\s+this\s+be\s+(cured|fixed|saved)",
    r"how\s+severe\s+is\s+it",
    r"tell\s+me\s+about\s+this\s+result",
    r"next\s+steps",
]


def _is_contextual_query(clean_q: str) -> bool:
    """Check if the user is asking about their currently analyzed plant."""
    for pattern in CONTEXT_PATTERNS:
        if re.search(pattern, clean_q):
            return True
    return False


def _is_out_of_scope(clean_q: str) -> bool:
    """Check if the query has zero agricultural/plant relevance."""
    words = set(re.findall(r"\b[a-z]{3,}\b", clean_q))
    # If any agricultural keyword intersects, it's on-topic
    if any(kw in clean_q for kw in AGRICULTURAL_KEYWORDS):
        return False
    # Common out-of-scope non-farming terms
    out_of_scope_cues = {
        "france", "paris", "president", "capital", "movie", "song", "weather",
        "crypto", "bitcoin", "code", "python", "programming", "car", "sports",
        "football", "basketball", "recipe", "cake", "cookie", "pizza", "flight",
    }
    if words.intersection(out_of_scope_cues):
        return True
    # If no agricultural keywords at all were matched
    return len(words.intersection(AGRICULTURAL_KEYWORDS)) == 0


def _extract_crop(text: str, context_crop: Optional[str] = None) -> Optional[str]:
    """Detect crop from question text or fallback to context."""
    text_lower = text.lower()
    has_tomato = "tomato" in text_lower or "tomatoes" in text_lower
    has_potato = "potato" in text_lower or "potatoes" in text_lower or "tuber" in text_lower

    if has_tomato and not has_potato:
        return "Tomato"
    if has_potato and not has_tomato:
        return "Potato"
    if has_tomato and has_potato:
        return "Tomato & Potato"

    # Fallback to active context if available
    if context_crop:
        return context_crop
    return None


def _extract_disease(text: str, context_disease: Optional[str] = None) -> Optional[str]:
    """Detect disease condition from question text or fallback to context."""
    text_lower = text.lower()
    has_early = "early blight" in text_lower or "alternaria" in text_lower or "target spot" in text_lower
    has_late = "late blight" in text_lower or "phytophthora" in text_lower or "water-soaked" in text_lower
    has_healthy = "healthy" in text_lower or "normal leaf" in text_lower

    if has_early and not has_late:
        return "Early Blight"
    if has_late and not has_early:
        return "Late Blight"
    if has_healthy:
        return "Healthy"

    if context_disease:
        return context_disease
    return None


def _extract_severity(text: str, context_severity: Optional[str] = None) -> Optional[str]:
    """Detect severity level from text or fallback to context."""
    text_lower = text.lower()
    if re.search(r"\b(severe|heavy|critical|urgent)\b", text_lower):
        return "Severe"
    if re.search(r"\b(moderate|medium)\b", text_lower):
        return "Moderate"
    if re.search(r"\b(mild|minor|light)\b", text_lower):
        return "Mild"

    if context_severity and context_severity in ["Mild", "Moderate", "Severe"]:
        return context_severity
    return None


def _extract_intent(text: str) -> str:
    """Identify the primary agronomic intent of the question."""
    t = text.lower()
    if any(w in t for w in ["prevent", "prevention", "stop", "avoid", "protect"]):
        return "prevention"
    if any(w in t for w in ["symptom", "symptoms", "sign", "look like", "spot", "identify", "appearance"]):
        return "symptoms"
    if any(w in t for w in ["cause", "spread", "transmission", "weather", "humidity", "how does it spread", "where does it come from"]):
        return "causes_and_spread"
    if any(w in t for w in ["treat", "treatment", "cure", "spray", "fungicide", "manage", "action", "what should i do", "how to treat"]):
        return "treatment"
    if any(w in t for w in ["what is", "tell me about", "explain", "describe", "define"]):
        return "overview"
    return "general"


def answer_query(question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Answer a farmer question using structured knowledge and active scan context.

    Args:
        question: Farmer's natural language question string.
        context: Optional dictionary containing active scan details:
            {
                "crop": "Tomato" / "Potato",
                "disease": "Early Blight" / "Late Blight" / "Healthy",
                "confidence": float,
                "severity_level": "Mild" / "Moderate" / "Severe" / "None (Healthy)",
                "affected_pct": float or None,
                "treatment_rec": TreatmentRecommendation,
            }

    Returns:
        Dictionary with:
            - answer: Formatted markdown string.
            - intent: Identified intent category.
            - crop_detected: Detected or inferred crop name.
            - disease_detected: Detected or inferred disease name.
            - is_context_used: Boolean indicating if active scan context was used.
    """
    clean_q = question.strip().lower()
    if not clean_q:
        return {
            "answer": "Please ask a question about tomato or potato crop health, disease prevention, or treatment recommendations.",
            "intent": "empty",
            "crop_detected": None,
            "disease_detected": None,
            "is_context_used": False,
        }

    has_explicit_crop = ("tomato" in clean_q or "potato" in clean_q or "tomatoes" in clean_q or "potatoes" in clean_q)
    has_explicit_disease = ("early blight" in clean_q or "late blight" in clean_q or "healthy" in clean_q)
    is_explicit_crop_disease = (has_explicit_crop and has_explicit_disease)

    # ── 1. Check for Contextual Deictic Reference ("What should I do now?") ───
    if _is_contextual_query(clean_q) and not is_explicit_crop_disease:
        if context is not None and context.get("crop") and context.get("disease"):
            crop = context["crop"]
            disease = context["disease"]
            confidence = context.get("confidence", 0.0)
            severity = context.get("severity_level", "Uncertain")
            rec = context.get("treatment_rec")

            ans_lines = [
                f"### 🌾 Advisory for Your Current Diagnosis: {crop} — {disease}",
                "",
                f"**Current Scan Summary:**",
                f"- **Crop:** {crop}",
                f"- **Detected Condition:** {disease}",
                f"- **Prediction Confidence:** `{confidence:.1f}%` *(visual pattern score; does not guarantee 100% certainty)*",
                f"- **Estimated Severity:** `{severity}`",
                "",
            ]

            if disease.lower() == "healthy":
                ans_lines.extend([
                    "#### 🌿 Action for Healthy Plants:",
                    "Your leaf appears healthy with normal green foliage. **No chemical spraying is recommended.**",
                    "",
                    "#### 🛠️ Recommended Preventive Care:",
                    "- Continue routine field scouting twice weekly.",
                    "- Water at the base (drip or soaker hose) to keep leaves dry.",
                    "- Mulch around plant bases to prevent soil splashing.",
                    "- Maintain balanced nutrition without excessive nitrogen.",
                ])
            else:
                if rec:
                    ans_lines.extend([
                        "#### 🚨 Immediate Recommended Action:",
                        f"> {rec.recommended_action}",
                        "",
                        "#### 🛠️ Cultural & Management Practices:",
                    ])
                    for practice in rec.management_practices[:4]:
                        ans_lines.append(f"- {practice}")
                    ans_lines.extend([
                        "",
                        "#### 🧪 Treatment Guidance:",
                        rec.treatment_guidance,
                        "",
                        "#### ℹ️ Extension / Professional Guidance:",
                        rec.professional_advice,
                    ])
                else:
                    ans_lines.append("Please refer to the treatment recommendation card generated in the Leaf Diagnosis tab.")

            ans_lines.extend([
                "",
                "---",
                f"*{GENERAL_DISCLAIMER}*",
            ])

            return {
                "answer": "\n".join(ans_lines),
                "intent": "context_followup",
                "crop_detected": crop,
                "disease_detected": disease,
                "is_context_used": True,
            }
        else:
            return {
                "answer": (
                    "### ℹ️ No Active Leaf Scan Found\n\n"
                    "You asked for next steps regarding a current plant, but **no leaf has been analyzed yet in this session**.\n\n"
                    "1. Switch to the **🔬 Leaf Diagnosis** tab to upload and scan a leaf photograph.\n"
                    "2. Or ask a specific question including your crop and condition, such as:\n"
                    "   * *\"What should I do for moderate tomato early blight?\"*\n"
                    "   * *\"How do I treat potato late blight?\"*\n\n"
                    "---  \n"
                    f"*{GENERAL_DISCLAIMER}*"
                ),
                "intent": "context_missing",
                "crop_detected": None,
                "disease_detected": None,
                "is_context_used": False,
            }

    # ── 2. Check for Out-of-Scope Queries ──────────────────────────────────────
    if _is_out_of_scope(clean_q):
        return {
            "answer": (
                "### 🌿 PlantCare Agricultural Assistant Scope\n\n"
                "I am specifically designed to answer plant health and management questions for **Tomato** and **Potato** crops, "
                "focusing on **Early Blight**, **Late Blight**, and **Healthy Foliage Care**.\n\n"
                "Your question appears to be outside this agricultural scope.\n\n"
                "**Sample questions you can ask:**\n"
                "- *\"What is tomato early blight?\"*\n"
                "- *\"How can I prevent potato late blight?\"*\n"
                "- *\"How does early blight spread?\"*\n"
                "- *\"What should I do for moderate potato late blight?\"*\n"
                "- *\"How can I keep healthy tomato plants disease-free?\"*\n\n"
                "---  \n"
                f"*{GENERAL_DISCLAIMER}*"
            ),
            "intent": "out_of_scope",
            "crop_detected": None,
            "disease_detected": None,
            "is_context_used": False,
        }

    # ── 3. Extract Entities & Intent ──────────────────────────────────────────
    ctx_crop = context.get("crop") if context else None
    ctx_disease = context.get("disease") if context else None
    ctx_severity = context.get("severity_level") if context else None

    crop = _extract_crop(clean_q, context_crop=ctx_crop)
    disease = _extract_disease(clean_q, context_disease=ctx_disease)
    severity = _extract_severity(clean_q, context_severity=ctx_severity)
    intent = _extract_intent(clean_q)

    # ── 4. Retrieve Structured Knowledge ──────────────────────────────────────
    # Map to knowledge base key case-insensitively
    kb_key = None
    if disease == "Healthy":
        kb_key = "Healthy_Foliage"
    elif crop and disease:
        target_token = f"{crop}___{disease.replace(' ', '_')}".lower()
        for k in KNOWLEDGE_BASE:
            if k.lower() == target_token:
                kb_key = k
                break

    # If crop or disease is partially missing, handle intelligently
    if kb_key is None:
        if disease == "Early Blight":
            kb_key = "Tomato___Early_blight"  # Representative for early blight
            crop = crop or "Tomato (or Potato)"
        elif disease == "Late Blight":
            kb_key = "Tomato___Late_blight"   # Representative for late blight
            crop = crop or "Tomato (or Potato)"
        elif crop in ["Tomato", "Potato"]:
            # General crop question without specific disease
            kb_entry_early = KNOWLEDGE_BASE[f"{crop}___Early_blight"]
            kb_entry_late = KNOWLEDGE_BASE[f"{crop}___Late_blight"]
            ans_lines = [
                f"### 🌿 {crop} Health & Blight Management Overview",
                "",
                f"The two most common and destructive foliar diseases affecting {crop.lower()} crops are:",
                "",
                f"1. **Early Blight (*Alternaria solani*):**",
                f"   - **Symptoms:** Concentric dark brown 'bullseye' target spots starting on older lower leaves.",
                f"   - **Conditions:** Warm, humid weather with alternating rain and sunshine.",
                f"   - **Management:** Remove infected lower leaves, mulch base, avoid overhead watering.",
                "",
                f"2. **Late Blight (*Phytophthora infestans*):**",
                f"   - **Symptoms:** Fast-spreading, water-soaked brown/black lesions with delicate white fuzzy mold under humid mornings.",
                f"   - **Conditions:** Cool, foggy, overcast, wet weather (> 90% humidity).",
                f"   - **Management:** Highly contagious emergency. Promptly prune or rogue infected plants; apply preventive barrier sprays to healthy crops.",
                "",
                "**Tip:** You can upload a leaf photo to the **🔬 Leaf Diagnosis** tab for automated identification and visual severity rating.",
                "",
                "---",
                f"*{GENERAL_DISCLAIMER}*",
            ]
            return {
                "answer": "\n".join(ans_lines),
                "intent": "crop_overview",
                "crop_detected": crop,
                "disease_detected": None,
                "is_context_used": False,
            }
        else:
            # Fallback to general Solanaceae blight overview
            kb_key = "Tomato___Early_blight"

    data = KNOWLEDGE_BASE[kb_key]
    crop_display = data["crop"]
    disease_display = data["disease"]

    ans_lines = [f"### 🌾 {crop_display} — {disease_display}"]

    # Branch according to detected intent
    if intent == "prevention":
        ans_lines.extend([
            f"**Preventative Cultural Practices for {crop_display} {disease_display}:**",
            "",
        ])
        for p in data["prevention"]:
            ans_lines.append(f"- {p}")
        ans_lines.extend([
            "",
            "#### 🧪 Chemical / Protectant Note:",
            "Preventive barrier sprays (such as copper-based formulations or bio-protectants) should only be applied "
            "before disease infection during weather periods favorable to spore germination. Always follow official product labels.",
        ])

    elif intent == "symptoms":
        ans_lines.extend([
            f"**Typical Symptoms of {crop_display} {disease_display}:**",
            f"*(Pathogen: {data['pathogen']})*",
            "",
        ])
        for s in data["symptoms"]:
            ans_lines.append(f"- {s}")
        ans_lines.extend([
            "",
            "**Favorable Weather Conditions:**",
        ])
        for c in data["causes_and_favorable_conditions"]:
            ans_lines.append(f"- {c}")

    elif intent == "causes_and_spread":
        ans_lines.extend([
            f"**Causes & Transmission of {crop_display} {disease_display}:**",
            f"*(Pathogen: {data['pathogen']})*",
            "",
            "**Favorable Environmental Triggers:**",
        ])
        for c in data["causes_and_favorable_conditions"]:
            ans_lines.append(f"- {c}")
        ans_lines.extend([
            "",
            "**How It Spreads:**",
        ])
        for t in data["transmission"]:
            ans_lines.append(f"- {t}")

    elif intent == "treatment":
        ans_lines.extend([
            f"**Management & Treatment Guidance for {crop_display} {disease_display}:**",
            "",
        ])
        if severity and severity in data.get("treatment_guidance", {}):
            ans_lines.extend([
                f"#### Guidance for **{severity} Severity**:",
                f"> {data['treatment_guidance'][severity]}",
                "",
            ])
        else:
            ans_lines.append("#### Tiered Severity Guidance:")
            for lvl, text in data.get("treatment_guidance", {}).items():
                ans_lines.append(f"- **{lvl} Severity:** {text}")
            ans_lines.append("")

        ans_lines.extend([
            "#### 🛠️ Essential Cultural Steps:",
        ])
        for p in data["prevention"][:3]:
            ans_lines.append(f"- {p}")
        ans_lines.extend([
            "",
            "#### ℹ️ When to Consult Extension:",
            data["when_to_seek_advice"],
        ])

    else:  # Overview / Definition
        ans_lines.extend([
            f"*(Pathogen: {data['pathogen']})*",
            "",
            data["overview"],
            "",
            "#### Key Symptoms:",
        ])
        for s in data["symptoms"][:3]:
            ans_lines.append(f"- {s}")
        ans_lines.extend([
            "",
            "#### Top Prevention Practices:",
        ])
        for p in data["prevention"][:3]:
            ans_lines.append(f"- {p}")

    ans_lines.extend([
        "",
        "---",
        f"*{GENERAL_DISCLAIMER}*",
    ])

    return {
        "answer": "\n".join(ans_lines),
        "intent": intent,
        "crop_detected": crop_display,
        "disease_detected": disease_display,
        "is_context_used": False,
    }
