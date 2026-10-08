#!/usr/bin/env python3
"""
treatment.py — Modular Treatment and Spray Decision Engine.

Provides sensible, grower-facing agronomic guidance based on:
  - Crop (Tomato / Potato)
  - Detected Condition (Early Blight, Late Blight, Healthy)
  - Estimated Severity (Mild, Moderate, Severe, None, Uncertain)

SAFETY & COMPLIANCE PRINCIPLES:
  1. For healthy plants, DO NOT recommend chemical sprays; provide cultural monitoring advice.
  2. Never invent specific pesticide trade names, precise chemical concentrations, or arbitrary spray intervals.
  3. Keep treatment categories general (e.g. copper-based protective formulations, registered fungicides).
  4. Always defer to locally approved agricultural extension services, certified agronomists, and official product labels.
  5. Include non-chemical, preventive, and cultural practices (pruning, spacing, irrigation hygiene).
  6. Present guidance as supportive management advice, never as a guaranteed cure.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TreatmentRecommendation:
    """Structured treatment and management recommendation data object."""
    crop: str
    disease: str
    severity: str
    recommended_action: str
    management_practices: List[str]
    treatment_guidance: str
    professional_advice: str
    disclaimer: str = (
        "Educational Advisory: This guidance is based on general agricultural best practices. "
        "Fungicide regulations, approved products, and environmental restrictions vary by region. "
        "Always consult your local agricultural extension office or certified crop advisor and "
        "strictly adhere to the official product label before applying any agricultural treatment."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crop": self.crop,
            "disease": self.disease,
            "severity": self.severity,
            "recommended_action": self.recommended_action,
            "management_practices": self.management_practices,
            "treatment_guidance": self.treatment_guidance,
            "professional_advice": self.professional_advice,
            "disclaimer": self.disclaimer,
        }


# ═══════════════════════════════════════════════════════════════════════
#  DECISION ENGINE RULE REPOSITORY
# ═══════════════════════════════════════════════════════════════════════

def _healthy_recommendation(crop: str) -> TreatmentRecommendation:
    """Guidance for healthy tomato and potato crops."""
    crop_title = crop.title()
    return TreatmentRecommendation(
        crop=crop_title,
        disease="Healthy Foliage",
        severity="None (Healthy)",
        recommended_action=(
            "No chemical treatment needed. Continue routine field monitoring and maintain "
            "healthy cultural practices to prevent fungal development."
        ),
        management_practices=[
            "Water at the base of the plant (drip or furrow irrigation) to avoid wetting foliage.",
            "Water early in the morning so any accidental surface moisture evaporates quickly during the day.",
            "Ensure proper plant and row spacing to encourage canopy airflow and sunlight penetration.",
            "Apply mulch around the base of plants to prevent soil-splash from contacting lower leaves.",
            "Maintain balanced soil nutrition; avoid excessive nitrogen which creates dense, overly humid canopies.",
            "Scout plants 1–2 times per week, particularly on lower leaves and after periods of rain or heavy dew.",
        ],
        treatment_guidance=(
            "No chemical spraying is recommended for healthy plants. Applying unnecessary fungicides "
            "increases production costs, risks chemical runoff, and may disrupt beneficial microorganisms."
        ),
        professional_advice=(
            "Keep up routine monitoring. If neighboring fields report active blight outbreaks, "
            "consult local agricultural extension alerts for regional preventive recommendations."
        ),
    )


def _tomato_early_blight_recommendation(severity: str) -> TreatmentRecommendation:
    """Guidance for Tomato Early Blight (Alternaria solani)."""
    sev_lower = severity.lower()
    
    if "mild" in sev_lower:
        action = (
            "Prune isolated infected lower leaves immediately. Increase canopy airflow and monitor "
            "closely; chemical intervention is generally not needed if lesions remain localized."
        )
        treatment = (
            "Chemical spraying is typically unnecessary at this stage if diseased leaves are promptly removed. "
            "If extended warm, humid weather is forecast, preventive organic bio-fungicides or mild copper-based "
            "protective sprays approved in your area may be considered according to manufacturer label instructions."
        )
    elif "moderate" in sev_lower:
        action = (
            "Remove moderately blighted foliage, clean up fallen plant debris, and consider applying "
            "a registered protective fungicide to stop the fungus from spreading to upper foliage and fruit."
        )
        treatment = (
            "Consider applying a locally registered protective fungicide (such as copper-based formulations or "
            "approved broad-spectrum protectants). Always confirm approved active ingredients with your local agricultural "
            "extension service and strictly follow the official product label for application rates and pre-harvest intervals."
        )
    else:  # Severe or Uncertain
        action = (
            "Urgent canopy intervention required. Heavily prune damaged lower foliage or rogue severely collapsed plants "
            "to prevent complete vine defoliation and fruit infection."
        )
        treatment = (
            "Therapeutic or translaminar fungicide applications registered in your jurisdiction may be needed to halt "
            "canopy loss. Consult a local certified agronomist for current regional resistance-management recommendations "
            "and approved commercial fungicides."
        )

    return TreatmentRecommendation(
        crop="Tomato",
        disease="Early Blight",
        severity=severity,
        recommended_action=action,
        management_practices=[
            "Prune diseased lower leaves with clean, sanitized shears; disinfect cutting tools between plants.",
            "Safely dispose of infected foliage off-field (do not add infected leaves to compost piles).",
            "Stake or trellis tomato vines to keep leaves and fruit elevated off damp soil.",
            "Apply straw or plastic mulch around the plant base to create a physical barrier against soil-splashed spores.",
            "Irrigate exclusively at soil level using drip systems; avoid overhead sprinkler irrigation.",
            "Plan a 2–3 year crop rotation with non-solanaceous crops (avoid planting following potatoes, eggplants, or peppers).",
        ],
        treatment_guidance=treatment,
        professional_advice=(
            "Contact your local agricultural extension service or university plant clinic if lesions rapidly spread "
            "into the mid-canopy despite sanitation, or if brown sunken lesions begin appearing on tomato stems or fruit."
        ),
    )


def _tomato_late_blight_recommendation(severity: str) -> TreatmentRecommendation:
    """Guidance for Tomato Late Blight (Phytophthora infestans)."""
    sev_lower = severity.lower()
    
    if "mild" in sev_lower:
        action = (
            "Immediate protective action required. Late blight spreads rapidly under cool, wet conditions. "
            "Prune infected plant parts into sealed bags and inspect the entire planting."
        )
        treatment = (
            "Because late blight can destroy healthy vines within days, consider applying a locally registered protective "
            "fungicide (e.g., copper-based or approved contact protectants) to shield uninfected surrounding foliage. "
            "Check local agricultural extension disease forecasts and strictly follow manufacturer product labels."
        )
    elif "moderate" in sev_lower:
        action = (
            "High-priority intervention. Prune affected stems, isolate the area, halt all overhead watering, "
            "and consider an approved translaminar or systemic fungicide to arrest lesion spread."
        )
        treatment = (
            "Application of locally registered fungicides with targeted activity against oomycetes is strongly advised. "
            "Consult regional agricultural extension spray guides for approved active ingredients and rotate chemical classes "
            "according to FRAC guidelines to prevent fungicide resistance."
        )
    else:  # Severe or Uncertain
        action = (
            "Emergency crop salvage. Late blight damage is extensive. Rogue and destroy severely blighted plants to prevent "
            "spores from decimating neighboring plots. Harvest mature unblemished green tomatoes immediately."
        )
        treatment = (
            "Severe late blight may require therapeutic fungicides if portions of the crop can still be saved. "
            "Consult your local agricultural extension service immediately for emergency guidance and label directions."
        )

    return TreatmentRecommendation(
        crop="Tomato",
        disease="Late Blight",
        severity=severity,
        recommended_action=action,
        management_practices=[
            "Immediately remove infected foliage or whole plants during dry conditions to reduce airborne spore dispersal.",
            "Place infected plant material directly into sealed bags and dispose of away from growing areas; do not compost.",
            "Eliminate nearby volunteer tomato or potato plants and solanaceous weeds (such as nightshades) which harbor spores.",
            "Ensure maximum spacing and air movement between vines to reduce leaf wetness duration.",
            "Stop all overhead irrigation immediately; keep foliage as dry as possible.",
            "Harvest mature fruit immediately if disease pressure is high, before fruit rot develops.",
        ],
        treatment_guidance=treatment,
        professional_advice=(
            "Late blight is a community-level agricultural concern. Promptly notify your local agricultural extension officer "
            "or cooperative service to check for regional outbreak alerts and recommended local action plans."
        ),
    )


def _potato_early_blight_recommendation(severity: str) -> TreatmentRecommendation:
    """Guidance for Potato Early Blight (Alternaria solani)."""
    sev_lower = severity.lower()

    if "mild" in sev_lower:
        action = (
            "Scout field, remove scattered infected lower leaves, and ensure adequate hill coverage over developing tubers. "
            "Chemical application is generally not required if symptoms remain minimal."
        )
        treatment = (
            "Chemical spraying is not typically necessary for mild, isolated spotting during dry weather. "
            "Continue regular scouting; if warm, wet weather is expected, consult local extension guides for preventive options."
        )
    elif "moderate" in sev_lower:
        action = (
            "Maintain canopy protection and remove heavily spotted lower leaves. Ensure foliage is dry and consider "
            "applying a locally approved protective fungicide."
        )
        treatment = (
            "Consider applying an approved protective fungicide (such as copper-based products or registered contact fungicides) "
            "labeled for potatoes in your jurisdiction. Strictly follow the product label for application rates and harvest intervals."
        )
    else:  # Severe or Uncertain
        action = (
            "Intensive management required to prevent early defoliation and tuber contamination. Ensure hills are deeply covered "
            "to prevent spores from washing down to tubers."
        )
        treatment = (
            "Consult a local agricultural extension specialist for recommended curative or translaminar fungicides to preserve "
            "remaining green canopy until tuber bulking is finished."
        )

    return TreatmentRecommendation(
        crop="Potato",
        disease="Early Blight",
        severity=severity,
        recommended_action=action,
        management_practices=[
            "Maintain deep, wide hills over growing tubers to shield them from fungal spores washed down by rain.",
            "Avoid overhead irrigation in late afternoon or evening to minimize nighttime leaf moisture.",
            "Maintain balanced plant nutrition (particularly potassium and nitrogen) to delay natural vine senescence.",
            "Ensure vines are completely dead and dry (mechanically or chemically vine-killed) 2–3 weeks before harvesting tubers.",
            "Never harvest tubers in wet soil conditions to avoid skinning and spore inoculation.",
            "Rotate potato fields for 3–4 years away from potatoes, tomatoes, and other solanaceous crops.",
        ],
        treatment_guidance=treatment,
        professional_advice=(
            "Seek guidance from an agricultural extension agent if early blight causes premature canopy dying before "
            "tuber bulking is complete, or if storage tubers show sunken, dry corky rot."
        ),
    )


def _potato_late_blight_recommendation(severity: str) -> TreatmentRecommendation:
    """Guidance for Potato Late Blight (Phytophthora infestans)."""
    sev_lower = severity.lower()

    if "mild" in sev_lower:
        action = (
            "Treat as an urgent priority. Late blight develops exponentially in cool, humid weather. "
            "Scout low-lying or shaded field rows and apply protective measures promptly."
        )
        treatment = (
            "Apply a locally approved preventive protective fungicide to healthy foliage across the planting to establish "
            "a protective barrier before rainfall or heavy dew events. Defer to local agricultural extension recommendations and product labels."
        )
    elif "moderate" in sev_lower:
        action = (
            "Immediate disease suppression required to stop vine collapse and tuber rot. Hill soil deeply around rows "
            "to prevent motile spores from washing into soil."
        )
        treatment = (
            "Apply locally registered systemic or translaminar late blight fungicides. Rotate active ingredients across "
            "different FRAC chemical groups to mitigate resistance risks, and follow label directions strictly."
        )
    else:  # Severe or Uncertain
        action = (
            "Critical emergency condition. If vines are severely collapsed and tubers are near maturity, desiccate/kill vines "
            "immediately to stop spore production before tubers are infected in the ground."
        )
        treatment = (
            "Immediate consultation with your local agricultural extension service or certified crop advisor is strongly recommended. "
            "Follow regional emergency disease management protocols and product label requirements."
        )

    return TreatmentRecommendation(
        crop="Potato",
        disease="Late Blight",
        severity=severity,
        recommended_action=action,
        management_practices=[
            "Hill potatoes deeply to create a soil buffer that prevents motile zoospores from reaching tubers.",
            "Immediately destroy cull piles, volunteer potato plants, and neighboring weed hosts (e.g. nightshades).",
            "Halt all overhead irrigation; ensure fields drain properly.",
            "If vine blight is widespread near maturity, kill and dry vines 2–3 weeks before digging to prevent tuber rot at harvest.",
            "Delay harvest until vines are completely dead and soil is dry; do not harvest wet tubers.",
            "Inspect stored potatoes regularly and immediately discard any tubers showing reddish-brown surface rot.",
        ],
        treatment_guidance=treatment,
        professional_advice=(
            "Potato late blight is a high-impact regional disease. Report active outbreaks to your local agricultural extension "
            "office and monitor regional blight monitoring services (such as university pest alerts)."
        ),
    )


# ═══════════════════════════════════════════════════════════════════════
#  PUBLIC DECISION ENGINE INTERFACE
# ═══════════════════════════════════════════════════════════════════════

def get_treatment_recommendation(
    crop: str,
    disease: str,
    severity: str = "Uncertain",
) -> TreatmentRecommendation:
    """
    Generate agronomic treatment and management recommendations based on diagnosis and severity.

    Args:
        crop: Crop name ('Tomato' or 'Potato')
        disease: Disease name ('Early Blight', 'Late Blight', 'Healthy')
        severity: Severity estimate ('Mild', 'Moderate', 'Severe', 'None (Healthy)', 'Uncertain')

    Returns:
        TreatmentRecommendation dataclass instance with actionable grower guidance.
    """
    crop_clean = crop.strip().title()
    disease_clean = disease.strip().title()
    
    # Check if healthy
    if "Healthy" in disease_clean:
        return _healthy_recommendation(crop_clean)

    # Route by crop and disease
    if crop_clean == "Tomato":
        if "Early Blight" in disease_clean:
            return _tomato_early_blight_recommendation(severity)
        elif "Late Blight" in disease_clean:
            return _tomato_late_blight_recommendation(severity)
        else:
            return _tomato_early_blight_recommendation(severity)

    elif crop_clean == "Potato":
        if "Early Blight" in disease_clean:
            return _potato_early_blight_recommendation(severity)
        elif "Late Blight" in disease_clean:
            return _potato_late_blight_recommendation(severity)
        else:
            return _potato_early_blight_recommendation(severity)

    else:
        # Fallback for unknown crop name
        if "Late Blight" in disease_clean:
            return _tomato_late_blight_recommendation(severity)
        elif "Healthy" in disease_clean:
            return _healthy_recommendation("Plant")
        else:
            return _tomato_early_blight_recommendation(severity)
