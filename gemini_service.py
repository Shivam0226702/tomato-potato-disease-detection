#!/usr/bin/env python3
"""gemini_service.py — Agricultural Assistant Engine powered by Google Gemini API.

Provides conversational agronomic Q&A for tomato and potato farmers using Google's
official `google-genai` SDK and asynchronous content generation.

COMPLIANCE & SAFETY PRINCIPLES:
1. Agronomic Persona: "Ask PlantCare", specialized in tomato & potato crop management.
2. Safety Guardrails: Never invent specific pesticide brands, chemical concentrations,
   or mixing ratios. Emphasize manufacturer product labels and local extension approvals.
3. Diagnostic Integrity: Never claim to diagnose a plant definitively from text alone.
   Incorporate active leaf scan context when available, without overriding the model.
4. Robust Resilience: Gracefully handle missing keys, invalid keys, rate limits (429),
   timeouts, and network issues without crashing the PlantCare application.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

# Load local environment configuration from .env or .env.txt in project root
_proj_root = Path(__file__).resolve().parent
if (_proj_root / ".env").exists():
    load_dotenv(dotenv_path=_proj_root / ".env")
elif (_proj_root / ".env.txt").exists():
    load_dotenv(dotenv_path=_proj_root / ".env.txt")
else:
    load_dotenv()

# Google GenAI imports
try:
    from google import genai
    from google.genai import errors, types
    HAS_GENAI_LIB = True
except ImportError:
    HAS_GENAI_LIB = False
    genai = None
    types = None
    errors = None


# Default configuration — use active, currently supported Gemini models
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3-flash-preview", "gemini-flash-latest"]
MAX_QUESTION_LENGTH = 1000
MAX_OUTPUT_TOKENS = 1024
REQUEST_TIMEOUT_SECONDS = 30.0

# General Agronomic Disclaimer
AGRONOMIC_DISCLAIMER = (
    "Educational Advisory: PlantCare AI provides supportive agronomic guidance based on standard "
    "agricultural best practices. Chemical regulations, pesticide availability, and disease strains "
    "vary regionally. Always inspect the official manufacturer product label, wear personal protective equipment (PPE), "
    "and consult your local agricultural extension service or certified crop advisor before applying treatments."
)

# System instruction defining the Ask PlantCare agricultural assistant
SYSTEM_INSTRUCTION = """You are "Ask PlantCare", a friendly, knowledgeable, and practical agricultural assistant specifically dedicated to Tomato and Potato farmers.

CORE SCOPE & EXPERTISE:
1. Solanaceae foliar diseases: Early Blight (Alternaria solani), Late Blight (Phytophthora infestans), and Healthy plant maintenance.
2. Field management: Irrigation hygiene (drip vs overhead), aeration and spacing, pruning infected foliage, soil health, crop rotation, and sanitation.
3. Cultural and preventive practices: Mulching, resistant cultivars, field scouting techniques, and weather monitoring.
4. Communication: Use simple, plain, respectful language suitable for growers and agricultural students. Explain technical terms (e.g., "conidia", "systemic", "chlorosis") in simple practical analogies. Provide step-by-step guidance where applicable.
5. When important information is missing (such as plant growth stage, recent rainfall/humidity, or field scale), ask a polite follow-up question.

STRICT SAFETY & COMPLIANCE RULES:
- NEVER claim that you can confirm a plant disease solely from conversational text. Physical leaf inspection or diagnostic imaging is essential.
- NEVER override or contradict the EfficientNet-B0 visual model's diagnosed condition if scan context is provided.
- NEVER invent proprietary pesticide brand names, arbitrary chemical concentrations, dilution ratios, or mixing instructions.
- For chemical disease management, refer ONLY to general active ingredient categories (e.g., protectant copper-based formulations, mancozeb/chlorothalonil protectants, or locally approved translaminar/systemic fungicides).
- ALWAYS emphasize that growers must read and strictly follow the official manufacturer product label, wear proper PPE (gloves, mask, protective eyewear), adhere to Pre-Harvest Intervals (PHI), and verify local agricultural extension approvals.
- NEVER promise or guarantee a "cure" for a plant. Fungicides protect healthy foliage and suppress disease progression; they cannot revive necrotic or dead leaf tissue.
- If a question is outside agriculture or tomato/potato farming, politely explain Ask PlantCare's agricultural scope and suggest sample tomato/potato questions.
- Keep answers concise, structured (using clear markdown headings and bullet points), and immediately actionable by default.
"""


def get_api_key() -> Optional[str]:
    """Retrieve and clean GEMINI_API_KEY from environment variables."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    return key if key else None


def get_configured_model() -> str:
    """Retrieve preferred model name from GEMINI_MODEL or fallback to default."""
    model = os.getenv("GEMINI_MODEL", "").strip()
    return model if model else DEFAULT_MODEL


def is_gemini_configured() -> bool:
    """Check whether google-genai library and an API key are both available."""
    return HAS_GENAI_LIB and bool(get_api_key())


def _build_context_prompt(question: str, context: Optional[Dict[str, Any]] = None) -> str:
    """Format the user question with any active scan context."""
    if not context or not (context.get("crop") or context.get("disease")):
        return question

    crop = context.get("crop", "Unknown")
    disease = context.get("disease", "Unknown")
    confidence = context.get("confidence")
    severity = context.get("severity") or context.get("severity_level")
    affected_pct = context.get("affected_percentage") or context.get("affected_pct")

    context_lines = [
        "--- ACTIVE SCAN CONTEXT ---",
        f"Crop: {crop}",
        f"Detected Condition: {disease}",
    ]
    if confidence is not None:
        try:
            conf_val = float(confidence)
            context_lines.append(f"Model Prediction Confidence: {conf_val:.1f}% (Pattern score; not absolute diagnostic certainty)")
        except (ValueError, TypeError):
            pass
    if severity:
        context_lines.append(f"Estimated Morphological Severity: {severity}")
    if affected_pct is not None:
        try:
            pct_val = float(affected_pct)
            context_lines.append(f"Visual Leaf Affected Area: {pct_val:.1f}%")
        except (ValueError, TypeError):
            pass

    context_lines.append("--- END SCAN CONTEXT ---\n")
    context_lines.append(f"Farmer Question: {question}")
    return "\n".join(context_lines)


def _build_conversation_contents(
    current_prompt: str,
    history: Optional[List[Dict[str, str]]] = None,
) -> List[Any]:
    """Construct multi-turn Content list for the Google GenAI SDK."""
    contents: List[Any] = []

    if history and types:
        # Include up to the last 6 previous conversation turns to preserve token limits
        recent_history = history[-6:]
        for turn in recent_history:
            role = turn.get("role", "").lower()
            text = turn.get("text", "").strip()
            if not text:
                continue

            if role in ["user"]:
                contents.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text)],
                    )
                )
            elif role in ["assistant", "model"]:
                contents.append(
                    types.Content(
                        role="model",
                        parts=[types.Part.from_text(text=text)],
                    )
                )

    # Append current user prompt
    if types:
        contents.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=current_prompt)],
            )
        )
    return contents


def _detect_crop_and_disease(text: str, context: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    """Detect crop and disease mentions for metadata tagging."""
    t = text.lower()
    crop = "Tomato & Potato"
    if "tomato" in t and "potato" not in t:
        crop = "Tomato"
    elif "potato" in t and "tomato" not in t:
        crop = "Potato"
    elif context and context.get("crop"):
        crop = str(context["crop"])

    disease = "General Plant Health"
    if "early blight" in t:
        disease = "Early Blight"
    elif "late blight" in t:
        disease = "Late Blight"
    elif "healthy" in t:
        disease = "Healthy Foliage Care"
    elif context and context.get("disease"):
        disease = str(context["disease"])

    return crop, disease


async def query_gemini_agronomist(
    question: str,
    context: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Ask an agricultural question to the Google Gemini API asynchronously.

    Args:
        question: Farmer's natural language question.
        context: Optional active scan context dict (crop, disease, severity, etc.).
        history: Optional previous chat history list [{"role": "user"|"assistant", "text": "..."}].

    Returns:
        Dict with keys:
            - answer (str): Formatted markdown response.
            - crop (str): Crop identifier.
            - disease (str): Disease identifier.
            - sources (List[str]): Source attribution.
            - disclaimer (str): Agronomic advisory notice.
            - is_ai (bool): True if generated by Gemini.
            - model (Optional[str]): Name of model used.
            - error (Optional[str]): Error code if request failed.
    """
    clean_q = question.strip()

    # 1. Validation: Empty Question
    if not clean_q:
        return {
            "answer": "Please enter a question regarding tomato or potato plant health, blight management, or irrigation practices.",
            "crop": "Tomato & Potato",
            "disease": "General Plant Health",
            "sources": ["PlantCare"],
            "disclaimer": AGRONOMIC_DISCLAIMER,
            "is_ai": False,
            "model": None,
            "error": "EMPTY_QUESTION",
        }

    # 2. Validation: Maximum Question Length
    if len(clean_q) > MAX_QUESTION_LENGTH:
        return {
            "answer": (
                f"Your question exceeds the maximum supported length ({len(clean_q)} / {MAX_QUESTION_LENGTH} characters). "
                "Please shorten your question to focus on a specific symptom, spray timing, or management practice."
            ),
            "crop": "Tomato & Potato",
            "disease": "General Plant Health",
            "sources": ["PlantCare"],
            "disclaimer": AGRONOMIC_DISCLAIMER,
            "is_ai": False,
            "model": None,
            "error": "QUESTION_TOO_LONG",
        }

    crop_tag, disease_tag = _detect_crop_and_disease(clean_q, context)

    # 3. Validation: Missing SDK or API Key
    api_key = get_api_key()
    if not HAS_GENAI_LIB:
        return {
            "answer": (
                "### ⚠️ Google GenAI Library Not Installed\n\n"
                "The `google-genai` Python library is required to run Ask PlantCare with Gemini.\n"
                "Run `pip install google-genai` and restart the backend server."
            ),
            "crop": crop_tag,
            "disease": disease_tag,
            "sources": ["PlantCare System"],
            "disclaimer": AGRONOMIC_DISCLAIMER,
            "is_ai": False,
            "model": None,
            "error": "SDK_NOT_INSTALLED",
        }

    if not api_key:
        return {
            "answer": (
                "### 🌿 Ask PlantCare — Setup Required\n\n"
                "Google Gemini integration is ready, but no **`GEMINI_API_KEY`** was detected in the environment.\n\n"
                "**How to configure your Gemini API Key:**\n"
                "1. Copy `.env.example` to `.env` in the project root:\n"
                "   ```bash\n"
                "   cp .env.example .env\n"
                "   ```\n"
                "2. Open `.env` and paste your key:\n"
                "   ```env\n"
                "   GEMINI_API_KEY=your_actual_api_key_here\n"
                "   ```\n"
                "3. Restart the backend server (`python api.py`).\n\n"
                "> *Get a free API key from Google AI Studio at: https://aistudio.google.com/app/apikey*"
            ),
            "crop": crop_tag,
            "disease": disease_tag,
            "sources": ["PlantCare Configuration"],
            "disclaimer": AGRONOMIC_DISCLAIMER,
            "is_ai": False,
            "model": None,
            "error": "MISSING_API_KEY",
        }

    # 4. Construct Prompt & Contents
    full_user_prompt = _build_context_prompt(clean_q, context)
    contents = _build_conversation_contents(full_user_prompt, history)
    preferred_model = get_configured_model()

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.3,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    # 5. Execute API Call with Async Timeout & Model Fallback
    client = genai.Client(api_key=api_key)
    models_to_try = [preferred_model] + [m for m in FALLBACK_MODELS if m != preferred_model]

    last_error_detail = ""
    last_error_type = "API_ERROR"

    for model_name in models_to_try:
        try:
            # Asynchronous call wrapped in timeout
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config,
                ),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            # Extract generated response text
            reply_text = response.text if response and response.text else ""
            if not reply_text:
                raise ValueError("Received empty response from Gemini API.")

            return {
                "answer": reply_text.strip(),
                "crop": crop_tag,
                "disease": disease_tag,
                "sources": [f"Google Gemini ({model_name})", "PlantCare Agronomic Knowledge"],
                "disclaimer": AGRONOMIC_DISCLAIMER,
                "is_ai": True,
                "model": model_name,
                "error": None,
            }

        except asyncio.TimeoutError:
            last_error_type = "TIMEOUT"
            last_error_detail = f"Gemini request timed out after {REQUEST_TIMEOUT_SECONDS} seconds. The network may be slow or unresponsive."
            break  # Timeout applies to all, do not retry other models indefinitely

        except errors.ClientError as err:
            err_code = getattr(err, "code", 0)
            err_msg = str(getattr(err, "message", str(err)))

            # Invalid API Key (HTTP 400 with key invalid message)
            if err_code == 400 and ("key not valid" in err_msg.lower() or "invalid api key" in err_msg.lower()):
                return {
                    "answer": (
                        "### 🔒 Invalid Gemini API Key\n\n"
                        "Google Gemini rejected the provided API key (HTTP 400: `API key not valid`).\n\n"
                        "Please verify your `GEMINI_API_KEY` in `.env`:\n"
                        "- Ensure there are no surrounding quotes or trailing spaces.\n"
                        "- Check that the key is active in your [Google AI Studio](https://aistudio.google.com/app/apikey) dashboard.\n"
                        "- Restart `python api.py` after updating `.env`."
                    ),
                    "crop": crop_tag,
                    "disease": disease_tag,
                    "sources": ["Google Gemini API"],
                    "disclaimer": AGRONOMIC_DISCLAIMER,
                    "is_ai": False,
                    "model": model_name,
                    "error": "INVALID_API_KEY",
                }

            # Quota or Rate Limit Exceeded (HTTP 429)
            if err_code == 429 or "resource_exhausted" in err_msg.lower() or "quota" in err_msg.lower():
                return {
                    "answer": (
                        "### ⏳ Gemini API Rate Limit Exceeded\n\n"
                        "The request exceeded the current Google Gemini API rate limits or quota (HTTP 429).\n\n"
                        "**Recommendations:**\n"
                        "- Wait 30–60 seconds before sending another question.\n"
                        "- Check your usage limits in Google AI Studio."
                    ),
                    "crop": crop_tag,
                    "disease": disease_tag,
                    "sources": ["Google Gemini API"],
                    "disclaimer": AGRONOMIC_DISCLAIMER,
                    "is_ai": False,
                    "model": model_name,
                    "error": "RATE_LIMIT_EXCEEDED",
                }

            # Model not found / deprecated / unavailable (try next fallback model)
            if err_code == 404 or "not found" in err_msg.lower() or "no longer available" in err_msg.lower():
                last_error_type = "MODEL_NOT_FOUND"
                last_error_detail = f"Model '{model_name}' is unavailable ({err_msg}). Trying fallback..."
                continue

            last_error_type = f"CLIENT_ERROR_{err_code}"
            last_error_detail = f"Gemini API client error ({err_code}): {err_msg}"
            continue

        except errors.ServerError as err:
            s_code = getattr(err, "code", 500)
            s_msg = str(getattr(err, "message", str(err)))
            last_error_type = "SERVER_ERROR"
            last_error_detail = f"Google Gemini server error ({s_code}): {s_msg}. Trying fallback..."
            continue

        except Exception as err:
            err_str = str(err)
            if "connect" in err_str.lower() or "network" in err_str.lower():
                last_error_type = "NETWORK_ERROR"
                last_error_detail = "Failed to connect to Google Gemini API servers. Please check your internet connection."
            else:
                last_error_type = "UNEXPECTED_ERROR"
                last_error_detail = f"Unexpected error while communicating with Gemini API: {err_str}"
            break

    # If all models/attempts failed, return clear structured error response
    return {
        "answer": (
            f"### ⚠️ Agronomic Assistant Communication Error\n\n"
            f"Unable to complete Gemini AI request: **{last_error_detail}**\n\n"
            "Please check your network connection, API key configuration, or try again in a few moments."
        ),
        "crop": crop_tag,
        "disease": disease_tag,
        "sources": ["PlantCare Error Handler"],
        "disclaimer": AGRONOMIC_DISCLAIMER,
        "is_ai": False,
        "model": None,
        "error": last_error_type,
    }
