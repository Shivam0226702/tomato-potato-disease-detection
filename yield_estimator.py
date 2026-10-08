"""yield_estimator.py — Prototype Crop Yield Estimation Module.

Provides transparent, rule-based prototype yield estimates for Tomato and Potato
crops based on baseline agronomic assumptions and estimated disease/severity impacts.

SCIENTIFIC & AGRONOMIC NOTICE:
This module does NOT use ML regression and does NOT claim scientifically validated
yield predictions. Crop yield is governed by numerous complex variables including
crop genetics, soil fertility, seasonal weather, planting density, irrigation, and
pest pressure. These calculations serve solely as an educational planning prototype.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


# Conversion factor: 1 hectare = 2.4710538 acres
HECTARE_TO_ACRE = 2.4710538
ACRE_TO_HECTARE = 0.4046856

# Standard prototype baseline yields for healthy crops (in metric tons per acre)
DEFAULT_BASELINE_YIELDS_PER_ACRE: Dict[str, float] = {
    "Tomato": 4.0,  # Baseline fresh-market field tomato yield assumption (tons/acre)
    "Potato": 8.0,  # Baseline field potato yield assumption (tons/acre)
}

# Estimated disease & severity loss impact factors (% yield reduction from baseline)
# Format: {condition_key: {severity_level: reduction_percentage}}
SEVERITY_LOSS_FACTORS: Dict[str, Dict[str, float]] = {
    "Healthy": {
        "None (Healthy)": 0.0,
        "None": 0.0,
        "Mild": 0.0,
        "Moderate": 0.0,
        "Severe": 0.0,
        "Uncertain": 0.0,
        "Not available": 0.0,
    },
    "Early Blight": {
        "None (Healthy)": 0.0,
        "Mild": 0.10,       # 10% estimated potential loss
        "Moderate": 0.30,   # 30% estimated potential loss
        "Severe": 0.55,     # 55% estimated potential loss
        "Uncertain": 0.25,  # 25% default assumption
        "Not available": 0.25,  # 25% default assumption when severity not available
    },
    "Late Blight": {
        "None (Healthy)": 0.0,
        "Mild": 0.20,       # 20% estimated potential loss (aggressive pathogen)
        "Moderate": 0.50,   # 50% estimated potential loss
        "Severe": 0.80,     # 80% estimated potential loss (critical vine collapse)
        "Uncertain": 0.45,  # 45% default assumption
        "Not available": 0.45,  # 45% default assumption when severity not available
    },
}

# Qualitative disease impact categories
IMPACT_CATEGORIES: Dict[str, Dict[str, str]] = {
    "Healthy": {
        "None (Healthy)": "None (Healthy)",
        "default": "None (Healthy)",
    },
    "Early Blight": {
        "Mild": "Low Impact (-10%)",
        "Moderate": "Moderate Impact (-30%)",
        "Severe": "High Impact (-55%)",
        "Uncertain": "Estimated Moderate (-25%)",
        "Not available": "Estimated Moderate (-25%)",
        "default": "Moderate Impact",
    },
    "Late Blight": {
        "Mild": "Moderate Impact (-20%)",
        "Moderate": "High Impact (-50%)",
        "Severe": "Critical Impact (-80%)",
        "Uncertain": "Estimated High (-45%)",
        "Not available": "Estimated High (-45%)",
        "default": "High Impact",
    },
}

YIELD_DISCLAIMER = (
    "Prototype estimate based on an assumed healthy baseline and disease-severity impact factors. "
    "Actual yield impact varies with crop variety, weather, soil, irrigation, farm management, and disease progression. "
    "This should not be treated as a guaranteed harvest prediction."
)


@dataclass
class YieldEstimateResult:
    """Structured result of prototype yield estimation."""

    crop: str
    cultivated_area: float
    area_unit: str  # "acre" or "hectare"
    area_in_acres: float
    disease: str
    severity: str
    baseline_yield_per_acre: float
    estimated_yield_per_acre: float
    estimated_yield_per_unit: float
    estimated_total_yield: float
    range_min: float
    range_max: float
    loss_percentage: float
    impact_category: str
    disclaimer: str

    @property
    def estimated_yield_kg_per_unit(self) -> float:
        """Estimated yield per unit in kilograms (1 metric ton = 1,000 kg)."""
        return round(self.estimated_yield_per_unit * 1000.0)

    @property
    def estimated_total_yield_kg(self) -> float:
        """Estimated total harvest in kilograms (1 metric ton = 1,000 kg)."""
        return round(self.estimated_total_yield * 1000.0)

    @property
    def range_min_kg(self) -> float:
        """Estimated minimum expected harvest range in kilograms."""
        return round(self.range_min * 1000.0)

    @property
    def range_max_kg(self) -> float:
        """Estimated maximum expected harvest range in kilograms."""
        return round(self.range_max * 1000.0)


def normalize_disease_name(disease: str) -> str:
    """Normalize input disease string to 'Healthy', 'Early Blight', or 'Late Blight'."""
    d = disease.strip().lower()
    if "early" in d:
        return "Early Blight"
    elif "late" in d:
        return "Late Blight"
    elif "healthy" in d:
        return "Healthy"
    return "Healthy"


def normalize_severity_name(severity: Optional[str]) -> str:
    """Normalize severity level string."""
    if not severity or not str(severity).strip():
        return "Not available"
    s = str(severity).strip()
    s_lower = s.lower()
    if "mild" in s_lower:
        return "Mild"
    elif "moderate" in s_lower:
        return "Moderate"
    elif "severe" in s_lower:
        return "Severe"
    elif "healthy" in s_lower:
        return "None (Healthy)"
    elif "not available" in s_lower or s_lower in ("n/a", "na", "unknown"):
        return "Not available"
    elif "uncertain" in s_lower:
        return "Uncertain"
    elif "none" in s_lower:
        return "None (Healthy)"
    return s


def calculate_yield_estimate(
    crop: str,
    cultivated_area: float,
    area_unit: str = "acre",
    disease: str = "Healthy",
    severity: str = "None (Healthy)",
    custom_baseline_per_acre: Optional[float] = None,
) -> YieldEstimateResult:
    """Calculate transparent prototype crop yield estimate.

    Args:
        crop: 'Tomato' or 'Potato'.
        cultivated_area: Numeric value of land area (> 0).
        area_unit: 'acre' or 'hectare'.
        disease: 'Healthy', 'Early Blight', or 'Late Blight'.
        severity: 'None (Healthy)', 'Mild', 'Moderate', 'Severe', or 'Uncertain'.
        custom_baseline_per_acre: Optional override for healthy baseline yield per acre.

    Returns:
        YieldEstimateResult with full metrics, ranges, and disclaimers.
    """
    # 1. Validate & normalize inputs safely
    norm_crop = "Tomato" if "tomato" in crop.lower() else "Potato"
    norm_unit = "hectare" if "hectare" in area_unit.lower() else "acre"

    try:
        area_val = float(cultivated_area)
        if area_val <= 0.0:
            area_val = 1.0
    except (ValueError, TypeError):
        area_val = 1.0

    norm_disease = normalize_disease_name(disease)
    norm_severity = normalize_severity_name(severity)

    # If disease is Healthy, severity is always None (Healthy)
    if norm_disease == "Healthy":
        norm_severity = "None (Healthy)"

    # 2. Determine baseline yield per acre
    if custom_baseline_per_acre is not None and custom_baseline_per_acre > 0:
        baseline_per_acre = float(custom_baseline_per_acre)
    else:
        baseline_per_acre = DEFAULT_BASELINE_YIELDS_PER_ACRE.get(norm_crop, 4.0)

    # 3. Determine severity loss factor
    disease_factors = SEVERITY_LOSS_FACTORS.get(norm_disease, SEVERITY_LOSS_FACTORS["Healthy"])
    loss_factor = disease_factors.get(norm_severity, disease_factors.get("Moderate", 0.0))

    # 4. Calculate estimated yield per acre
    retention_factor = max(0.0, 1.0 - loss_factor)
    est_yield_per_acre = round(baseline_per_acre * retention_factor, 2)

    # 5. Convert area to acres for total yield computation
    if norm_unit == "hectare":
        area_in_acres = area_val * HECTARE_TO_ACRE
        # Yield per hectare = yield per acre * HECTARE_TO_ACRE
        est_yield_per_unit = round(est_yield_per_acre * HECTARE_TO_ACRE, 2)
    else:
        area_in_acres = area_val
        est_yield_per_unit = est_yield_per_acre

    # 6. Total estimated yield (metric tons)
    est_total_yield = round(est_yield_per_acre * area_in_acres, 2)

    # 7. Expected range (+/- 15% for moderate/mild, +/- 20% for severe, +/- 10% for healthy)
    if norm_disease == "Healthy":
        uncertainty = 0.10
    elif norm_severity == "Severe":
        uncertainty = 0.20
    else:
        uncertainty = 0.15

    range_min = round(max(0.0, est_total_yield * (1.0 - uncertainty)), 1)
    range_max = round(est_total_yield * (1.0 + uncertainty), 1)

    # 8. Impact category label
    impact_dict = IMPACT_CATEGORIES.get(norm_disease, IMPACT_CATEGORIES["Healthy"])
    impact_category = impact_dict.get(norm_severity, impact_dict.get("default", "Moderate Impact"))

    return YieldEstimateResult(
        crop=norm_crop,
        cultivated_area=area_val,
        area_unit=norm_unit,
        area_in_acres=round(area_in_acres, 3),
        disease=norm_disease,
        severity=norm_severity,
        baseline_yield_per_acre=baseline_per_acre,
        estimated_yield_per_acre=est_yield_per_acre,
        estimated_yield_per_unit=est_yield_per_unit,
        estimated_total_yield=est_total_yield,
        range_min=range_min,
        range_max=range_max,
        loss_percentage=round(loss_factor * 100.0, 1),
        impact_category=impact_category,
        disclaimer=YIELD_DISCLAIMER,
    )
