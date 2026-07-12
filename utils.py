"""Validation, crop metadata, PDF/CSV helpers used by the Flask app."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

# ---------------------------------------------------------------------------
# Feature schema
# ---------------------------------------------------------------------------

FEATURES: Tuple[str, ...] = (
    "N", "P", "K", "temperature", "humidity", "ph", "rainfall",
)

# Realistic min/max bounds (used for validation + suitability scoring).
FEATURE_BOUNDS: Dict[str, Tuple[float, float]] = {
    "N": (0, 200),
    "P": (0, 200),
    "K": (0, 220),
    "temperature": (-5, 55),
    "humidity": (0, 100),
    "ph": (0, 14),
    "rainfall": (0, 400),
}

FEATURE_LABELS: Dict[str, str] = {
    "N": "Nitrogen (N)",
    "P": "Phosphorous (P)",
    "K": "Potassium (K)",
    "temperature": "Temperature (°C)",
    "humidity": "Humidity (%)",
    "ph": "Soil pH",
    "rainfall": "Rainfall (mm)",
}

FEATURE_UNITS: Dict[str, str] = {
    "N": "kg/ha",
    "P": "kg/ha",
    "K": "kg/ha",
    "temperature": "°C",
    "humidity": "%",
    "ph": "",
    "rainfall": "mm",
}


def validate_features(payload: Dict[str, Any]) -> Tuple[Dict[str, float], List[str]]:
    """Coerce + validate an input payload. Returns (clean_dict, errors)."""
    clean: Dict[str, float] = {}
    errors: List[str] = []
    for key in FEATURES:
        if key not in payload or payload[key] in ("", None):
            errors.append(f"{FEATURE_LABELS[key]} is required.")
            continue
        try:
            value = float(payload[key])
        except (TypeError, ValueError):
            errors.append(f"{FEATURE_LABELS[key]} must be a number.")
            continue
        lo, hi = FEATURE_BOUNDS[key]
        if value < lo or value > hi:
            errors.append(
                f"{FEATURE_LABELS[key]} must be between {lo} and {hi}."
            )
            continue
        clean[key] = value
    return clean, errors


# ---------------------------------------------------------------------------
# Crop metadata (22 crops in the Crop Recommendation dataset)
# ---------------------------------------------------------------------------

CROP_META: Dict[str, Dict[str, Any]] = {
    "rice": {
        "name": "Rice", "emoji": "🌾", "color": "#7cc4a0",
        "category": "Cereal", "season": "Kharif (Jun–Nov)",
        "description": "Staple cereal grown in flooded paddies; thrives in warm, humid climates.",
        "benefits": ["Global staple food", "High calorie yield per hectare", "Supports rural livelihoods"],
        "soil": "Clay loam with good water retention",
        "water": "High (1200–1800 mm)",
        "fertilizer": "N-rich (urea) + moderate P & K; split doses through tillering & panicle stages",
        "ideal_temperature": "20–35 °C",
        "expected_yield": "4–6 t/ha",
        "ph_range": "5.5–7.0",
        "rainfall_range": "150–300 mm/month",
    },
    "maize": {
        "name": "Maize", "emoji": "🌽", "color": "#f5c451",
        "category": "Cereal", "season": "Kharif / Rabi",
        "description": "Versatile C4 cereal used for food, feed, and industrial starch.",
        "benefits": ["Fast growth cycle", "High biomass", "Multiple end uses"],
        "soil": "Well-drained loam",
        "water": "Medium (500–800 mm)",
        "fertilizer": "Balanced NPK; nitrogen top-dressing at knee-high stage",
        "ideal_temperature": "18–27 °C",
        "expected_yield": "5–8 t/ha",
        "ph_range": "5.8–7.0",
        "rainfall_range": "60–110 mm/month",
    },
    "chickpea": {
        "name": "Chickpea", "emoji": "🫘", "color": "#c8a165",
        "category": "Pulse", "season": "Rabi (Oct–Mar)",
        "description": "Cool-season legume that fixes atmospheric nitrogen.",
        "benefits": ["Improves soil nitrogen", "Rich protein source", "Drought tolerant"],
        "soil": "Well-drained sandy loam",
        "water": "Low (300–400 mm)",
        "fertilizer": "Low N (starter), moderate P; rhizobium inoculation",
        "ideal_temperature": "15–25 °C",
        "expected_yield": "1.5–2.5 t/ha",
        "ph_range": "6.0–8.0",
        "rainfall_range": "40–80 mm/month",
    },
    "kidneybeans": {
        "name": "Kidney Beans", "emoji": "🫘", "color": "#a03e3e",
        "category": "Pulse", "season": "Kharif",
        "description": "High-protein legume, sensitive to heat and waterlogging.",
        "benefits": ["Protein & fiber rich", "Nitrogen fixation", "Short duration"],
        "soil": "Well-drained loam",
        "water": "Medium (400–500 mm)",
        "fertilizer": "Low N, moderate P & K",
        "ideal_temperature": "15–25 °C",
        "expected_yield": "1.2–2.0 t/ha",
        "ph_range": "6.0–7.5",
        "rainfall_range": "60–120 mm/month",
    },
    "pigeonpeas": {
        "name": "Pigeon Peas", "emoji": "🫛", "color": "#b98a3d",
        "category": "Pulse", "season": "Kharif",
        "description": "Deep-rooted perennial legume tolerant to drought.",
        "benefits": ["Deep root system", "Nitrogen fixing", "Fodder + food"],
        "soil": "Well-drained loam to clay loam",
        "water": "Low–medium (400–600 mm)",
        "fertilizer": "Starter N + P; rhizobium inoculation",
        "ideal_temperature": "20–30 °C",
        "expected_yield": "1.0–2.0 t/ha",
        "ph_range": "6.0–7.5",
        "rainfall_range": "60–120 mm/month",
    },
    "mothbeans": {
        "name": "Moth Beans", "emoji": "🫘", "color": "#c58a4b",
        "category": "Pulse", "season": "Kharif",
        "description": "Highly drought-tolerant pulse of arid regions.",
        "benefits": ["Extreme drought tolerance", "Erosion control", "Nutritious"],
        "soil": "Sandy soils",
        "water": "Very low (200–300 mm)",
        "fertilizer": "Minimal; starter P",
        "ideal_temperature": "24–32 °C",
        "expected_yield": "0.5–1.0 t/ha",
        "ph_range": "6.0–8.0",
        "rainfall_range": "30–70 mm/month",
    },
    "mungbean": {
        "name": "Mung Bean", "emoji": "🌱", "color": "#7bb661",
        "category": "Pulse", "season": "Kharif / Summer",
        "description": "Short-duration legume, excellent rotation crop.",
        "benefits": ["60–90 day cycle", "Nitrogen fixing", "High digestibility"],
        "soil": "Loam to sandy loam",
        "water": "Low (350–450 mm)",
        "fertilizer": "Low N, moderate P; rhizobium",
        "ideal_temperature": "25–35 °C",
        "expected_yield": "0.8–1.2 t/ha",
        "ph_range": "6.2–7.2",
        "rainfall_range": "50–90 mm/month",
    },
    "blackgram": {
        "name": "Black Gram", "emoji": "⚫", "color": "#3b2f2f",
        "category": "Pulse", "season": "Kharif",
        "description": "Protein-rich pulse widely used in South Asian cuisine.",
        "benefits": ["Protein rich", "Nitrogen fixing", "Short duration"],
        "soil": "Well-drained loam",
        "water": "Medium (400–500 mm)",
        "fertilizer": "Low N, moderate P & K",
        "ideal_temperature": "25–35 °C",
        "expected_yield": "0.8–1.2 t/ha",
        "ph_range": "6.0–7.5",
        "rainfall_range": "60–100 mm/month",
    },
    "lentil": {
        "name": "Lentil", "emoji": "🥣", "color": "#c98b5a",
        "category": "Pulse", "season": "Rabi",
        "description": "Cool-season lens-shaped pulse, high in protein and iron.",
        "benefits": ["High protein & iron", "Improves soil fertility", "Frost tolerant"],
        "soil": "Loam / clay loam",
        "water": "Low (300–400 mm)",
        "fertilizer": "Low N, moderate P",
        "ideal_temperature": "15–25 °C",
        "expected_yield": "1.0–1.5 t/ha",
        "ph_range": "6.0–8.0",
        "rainfall_range": "40–70 mm/month",
    },
    "pomegranate": {
        "name": "Pomegranate", "emoji": "🍎", "color": "#c0392b",
        "category": "Fruit", "season": "Perennial",
        "description": "Drought-tolerant fruit crop with antioxidant-rich arils.",
        "benefits": ["High market value", "Long shelf life", "Antioxidant rich"],
        "soil": "Well-drained loam",
        "water": "Medium (500–800 mm)",
        "fertilizer": "Balanced NPK + micronutrients (Zn, B)",
        "ideal_temperature": "18–35 °C",
        "expected_yield": "15–25 t/ha",
        "ph_range": "6.5–7.5",
        "rainfall_range": "40–80 mm/month",
    },
    "banana": {
        "name": "Banana", "emoji": "🍌", "color": "#f1c40f",
        "category": "Fruit", "season": "Perennial",
        "description": "Tropical monocarpic herb with continuous year-round harvest.",
        "benefits": ["Year-round income", "High yield", "Nutrient dense"],
        "soil": "Rich loam with high organic matter",
        "water": "High (1200–2000 mm)",
        "fertilizer": "Heavy K + N; regular organic mulching",
        "ideal_temperature": "20–35 °C",
        "expected_yield": "40–60 t/ha",
        "ph_range": "6.0–7.5",
        "rainfall_range": "100–180 mm/month",
    },
    "mango": {
        "name": "Mango", "emoji": "🥭", "color": "#f39c12",
        "category": "Fruit", "season": "Perennial (harvest Apr–Jul)",
        "description": "King of fruits; long-lived tropical tree.",
        "benefits": ["High export value", "Long productive life", "Diverse cultivars"],
        "soil": "Deep well-drained loam",
        "water": "Medium (750–1200 mm)",
        "fertilizer": "Balanced NPK; K + P before flowering",
        "ideal_temperature": "24–30 °C",
        "expected_yield": "8–15 t/ha",
        "ph_range": "5.5–7.5",
        "rainfall_range": "80–150 mm/month",
    },
    "grapes": {
        "name": "Grapes", "emoji": "🍇", "color": "#6c3483",
        "category": "Fruit", "season": "Perennial",
        "description": "High-value vine crop for table use and wine.",
        "benefits": ["Premium market price", "Multiple products", "Trellis efficient"],
        "soil": "Well-drained sandy loam",
        "water": "Medium (600–800 mm)",
        "fertilizer": "Moderate NPK; foliar micronutrients",
        "ideal_temperature": "15–35 °C",
        "expected_yield": "18–25 t/ha",
        "ph_range": "6.5–7.5",
        "rainfall_range": "50–90 mm/month",
    },
    "watermelon": {
        "name": "Watermelon", "emoji": "🍉", "color": "#27ae60",
        "category": "Fruit", "season": "Summer",
        "description": "Warm-season vine producing large juicy fruit.",
        "benefits": ["Quick cash crop", "High water content", "Summer demand"],
        "soil": "Sandy loam",
        "water": "Medium (400–600 mm)",
        "fertilizer": "Balanced NPK; K at fruiting",
        "ideal_temperature": "22–32 °C",
        "expected_yield": "20–35 t/ha",
        "ph_range": "6.0–7.0",
        "rainfall_range": "40–80 mm/month",
    },
    "muskmelon": {
        "name": "Muskmelon", "emoji": "🍈", "color": "#f5b041",
        "category": "Fruit", "season": "Summer",
        "description": "Aromatic warm-season melon with high sugar content.",
        "benefits": ["Sweet aroma", "Short duration", "High price"],
        "soil": "Sandy loam",
        "water": "Medium (400–500 mm)",
        "fertilizer": "Balanced NPK",
        "ideal_temperature": "24–30 °C",
        "expected_yield": "15–25 t/ha",
        "ph_range": "6.0–7.0",
        "rainfall_range": "30–70 mm/month",
    },
    "apple": {
        "name": "Apple", "emoji": "🍎", "color": "#e74c3c",
        "category": "Fruit", "season": "Perennial (temperate)",
        "description": "Temperate pome fruit; requires chilling hours.",
        "benefits": ["Long storage life", "Premium markets", "Value-added processing"],
        "soil": "Well-drained loam",
        "water": "Medium (700–1000 mm)",
        "fertilizer": "Balanced NPK + Ca, B",
        "ideal_temperature": "15–24 °C",
        "expected_yield": "10–20 t/ha",
        "ph_range": "5.5–6.5",
        "rainfall_range": "60–120 mm/month",
    },
    "orange": {
        "name": "Orange", "emoji": "🍊", "color": "#e67e22",
        "category": "Fruit", "season": "Perennial",
        "description": "Popular citrus with vitamin C rich juice.",
        "benefits": ["Vitamin C", "Global market", "Long productive life"],
        "soil": "Well-drained loam",
        "water": "Medium (900–1200 mm)",
        "fertilizer": "Balanced NPK + Zn, Fe",
        "ideal_temperature": "15–30 °C",
        "expected_yield": "12–20 t/ha",
        "ph_range": "6.0–7.5",
        "rainfall_range": "80–140 mm/month",
    },
    "papaya": {
        "name": "Papaya", "emoji": "🥭", "color": "#e59866",
        "category": "Fruit", "season": "Perennial",
        "description": "Fast-growing tropical fruit tree; high in papain enzyme.",
        "benefits": ["Fast return", "Multiple harvests", "Medicinal value"],
        "soil": "Well-drained loam",
        "water": "Medium (1000–1500 mm)",
        "fertilizer": "Balanced NPK monthly",
        "ideal_temperature": "22–32 °C",
        "expected_yield": "35–50 t/ha",
        "ph_range": "6.0–7.0",
        "rainfall_range": "80–150 mm/month",
    },
    "coconut": {
        "name": "Coconut", "emoji": "🥥", "color": "#8b6f47",
        "category": "Plantation", "season": "Perennial",
        "description": "Long-lived coastal palm with year-round harvest.",
        "benefits": ["Multiple products", "Long productive life", "Coastal suitability"],
        "soil": "Sandy loam, coastal",
        "water": "High (1500–2500 mm)",
        "fertilizer": "N-P-K + Mg annually",
        "ideal_temperature": "22–32 °C",
        "expected_yield": "60–100 nuts/tree/yr",
        "ph_range": "5.2–8.0",
        "rainfall_range": "100–250 mm/month",
    },
    "cotton": {
        "name": "Cotton", "emoji": "☁️", "color": "#ecf0f1",
        "category": "Fiber", "season": "Kharif",
        "description": "Primary global fiber crop; long growing season.",
        "benefits": ["Fiber + oilseed", "Industrial demand", "Byproduct feed"],
        "soil": "Deep black cotton soil / loam",
        "water": "Medium (700–1200 mm)",
        "fertilizer": "Balanced NPK; split N",
        "ideal_temperature": "21–30 °C",
        "expected_yield": "1.5–2.5 t/ha lint",
        "ph_range": "6.0–8.0",
        "rainfall_range": "60–120 mm/month",
    },
    "jute": {
        "name": "Jute", "emoji": "🌿", "color": "#a3b18a",
        "category": "Fiber", "season": "Kharif (warm humid)",
        "description": "Bast fiber crop; second most produced natural fiber worldwide.",
        "benefits": ["Biodegradable fiber", "Fast growth", "Retting adds value"],
        "soil": "Alluvial loam",
        "water": "High (1200–1500 mm)",
        "fertilizer": "Moderate N, low P & K",
        "ideal_temperature": "24–37 °C",
        "expected_yield": "2.5–3.5 t/ha fiber",
        "ph_range": "6.0–7.5",
        "rainfall_range": "120–250 mm/month",
    },
    "coffee": {
        "name": "Coffee", "emoji": "☕", "color": "#6f4e37",
        "category": "Plantation", "season": "Perennial",
        "description": "Shade-loving tropical shrub grown for its beans.",
        "benefits": ["Premium export crop", "Long life span", "Agroforestry compatible"],
        "soil": "Well-drained loam with organic matter",
        "water": "High (1500–2500 mm)",
        "fertilizer": "Balanced NPK + micronutrients",
        "ideal_temperature": "18–24 °C",
        "expected_yield": "0.8–1.5 t/ha",
        "ph_range": "5.5–6.5",
        "rainfall_range": "120–220 mm/month",
    },
}


# Numeric ideal ranges (from dataset distributions) used for suitability scoring.
CROP_IDEAL_RANGES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "rice":        {"N": (60, 100), "P": (35, 60),  "K": (35, 45),  "temperature": (20, 27), "humidity": (80, 85), "ph": (5.5, 7.0), "rainfall": (180, 300)},
    "maize":       {"N": (60, 100), "P": (35, 60),  "K": (15, 25),  "temperature": (18, 27), "humidity": (55, 75), "ph": (5.8, 7.0), "rainfall": (60, 110)},
    "chickpea":    {"N": (20, 50),  "P": (55, 80),  "K": (75, 85),  "temperature": (17, 23), "humidity": (14, 20), "ph": (6.0, 8.0), "rainfall": (60, 100)},
    "kidneybeans": {"N": (10, 40),  "P": (55, 80),  "K": (15, 25),  "temperature": (15, 25), "humidity": (18, 25), "ph": (5.5, 6.5), "rainfall": (60, 150)},
    "pigeonpeas":  {"N": (10, 40),  "P": (55, 80),  "K": (15, 25),  "temperature": (20, 30), "humidity": (30, 70), "ph": (5.0, 7.5), "rainfall": (90, 200)},
    "mothbeans":   {"N": (10, 40),  "P": (35, 60),  "K": (15, 25),  "temperature": (24, 32), "humidity": (40, 65), "ph": (5.5, 7.5), "rainfall": (40, 100)},
    "mungbean":    {"N": (10, 40),  "P": (35, 60),  "K": (15, 25),  "temperature": (25, 35), "humidity": (75, 90), "ph": (6.2, 7.2), "rainfall": (50, 90)},
    "blackgram":   {"N": (20, 60),  "P": (55, 80),  "K": (15, 25),  "temperature": (25, 35), "humidity": (60, 75), "ph": (6.0, 7.5), "rainfall": (60, 100)},
    "lentil":      {"N": (10, 40),  "P": (55, 80),  "K": (15, 25),  "temperature": (15, 25), "humidity": (60, 70), "ph": (6.0, 8.0), "rainfall": (40, 70)},
    "pomegranate": {"N": (10, 40),  "P": (5, 25),   "K": (35, 45),  "temperature": (18, 35), "humidity": (85, 95), "ph": (6.5, 7.5), "rainfall": (100, 130)},
    "banana":      {"N": (80, 120), "P": (70, 95),  "K": (45, 55),  "temperature": (25, 32), "humidity": (75, 85), "ph": (6.0, 7.5), "rainfall": (100, 180)},
    "mango":       {"N": (10, 40),  "P": (15, 35),  "K": (25, 35),  "temperature": (27, 32), "humidity": (45, 55), "ph": (5.5, 7.5), "rainfall": (90, 100)},
    "grapes":      {"N": (10, 40),  "P": (120, 145),"K": (195, 205),"temperature": (15, 35), "humidity": (80, 85), "ph": (6.5, 7.5), "rainfall": (65, 75)},
    "watermelon":  {"N": (95, 105), "P": (10, 20),  "K": (45, 55),  "temperature": (24, 27), "humidity": (80, 90), "ph": (6.0, 7.0), "rainfall": (45, 60)},
    "muskmelon":   {"N": (95, 105), "P": (10, 20),  "K": (45, 55),  "temperature": (26, 30), "humidity": (90, 95), "ph": (6.0, 7.0), "rainfall": (20, 30)},
    "apple":       {"N": (10, 40),  "P": (120, 145),"K": (195, 205),"temperature": (21, 24), "humidity": (90, 95), "ph": (5.5, 6.5), "rainfall": (100, 125)},
    "orange":      {"N": (10, 40),  "P": (5, 20),   "K": (5, 15),   "temperature": (15, 25), "humidity": (90, 95), "ph": (6.0, 7.5), "rainfall": (100, 120)},
    "papaya":      {"N": (30, 60),  "P": (45, 65),  "K": (45, 55),  "temperature": (22, 32), "humidity": (90, 95), "ph": (6.0, 7.0), "rainfall": (40, 250)},
    "coconut":     {"N": (10, 40),  "P": (5, 25),   "K": (25, 35),  "temperature": (25, 30), "humidity": (90, 100),"ph": (5.5, 6.5), "rainfall": (140, 180)},
    "cotton":      {"N": (110, 140),"P": (35, 60),  "K": (15, 25),  "temperature": (22, 26), "humidity": (75, 85), "ph": (6.0, 8.0), "rainfall": (70, 100)},
    "jute":        {"N": (60, 100), "P": (35, 60),  "K": (35, 45),  "temperature": (23, 27), "humidity": (70, 90), "ph": (6.0, 7.5), "rainfall": (150, 200)},
    "coffee":      {"N": (80, 120), "P": (15, 35),  "K": (25, 35),  "temperature": (23, 28), "humidity": (50, 70), "ph": (5.5, 6.5), "rainfall": (140, 200)},
}


def get_crop_meta(name: str) -> Dict[str, Any]:
    """Return metadata for a crop (case-insensitive). Empty dict if unknown."""
    key = (name or "").strip().lower()
    return CROP_META.get(key, {})


def list_crops() -> List[Dict[str, Any]]:
    """Return the full crop library as a list of dicts (with slug)."""
    out: List[Dict[str, Any]] = []
    for slug, meta in CROP_META.items():
        out.append({"slug": slug, **meta})
    return sorted(out, key=lambda c: c["name"])


# ---------------------------------------------------------------------------
# Suitability scoring
# ---------------------------------------------------------------------------

@dataclass
class ParamScore:
    key: str
    label: str
    value: float
    ideal_low: float
    ideal_high: float
    score: float          # 0..100
    status: str           # excellent / good / moderate / poor
    suggestion: str


def _score_range(value: float, low: float, high: float, span: Tuple[float, float]) -> float:
    """Return 0..100 suitability score using a trapezoidal function around [low,high]."""
    if low <= value <= high:
        return 100.0
    total = max(span[1] - span[0], 1e-6)
    if value < low:
        distance = low - value
    else:
        distance = value - high
    # Falls linearly to 0 after 40% of the total feature span.
    tolerance = 0.4 * total
    score = max(0.0, 100.0 * (1 - distance / tolerance))
    return round(score, 2)


def _status_band(score: float) -> str:
    if score >= 85: return "excellent"
    if score >= 70: return "good"
    if score >= 50: return "moderate"
    if score >= 30: return "poor"
    return "unsuitable"


def _suggestion(key: str, value: float, low: float, high: float) -> str:
    label = FEATURE_LABELS[key]
    unit = FEATURE_UNITS[key]
    if low <= value <= high:
        return f"{label} is within the ideal range."
    if value < low:
        gap = round(low - value, 2)
        if key == "ph":
            return f"Soil is too acidic — raise pH by ~{gap} using agricultural lime."
        return f"Increase {label} by ~{gap} {unit} (currently below optimum)."
    gap = round(value - high, 2)
    if key == "ph":
        return f"Soil is too alkaline — lower pH by ~{gap} using sulfur or organic matter."
    return f"Reduce {label} by ~{gap} {unit} (currently above optimum)."


def suitability_report(crop: str, features: Dict[str, float]) -> Dict[str, Any]:
    """Compute per-parameter scores + overall suitability for a chosen crop."""
    slug = (crop or "").strip().lower()
    ideal = CROP_IDEAL_RANGES.get(slug)
    if not ideal:
        return {"error": f"Unknown crop '{crop}'."}

    params: List[Dict[str, Any]] = []
    total = 0.0
    for key in FEATURES:
        lo, hi = ideal[key]
        span = FEATURE_BOUNDS[key]
        val = float(features[key])
        score = _score_range(val, lo, hi, span)
        params.append({
            "key": key,
            "label": FEATURE_LABELS[key],
            "unit": FEATURE_UNITS[key],
            "value": val,
            "ideal_low": lo,
            "ideal_high": hi,
            "score": score,
            "status": _status_band(score),
            "suggestion": _suggestion(key, val, lo, hi),
        })
        total += score

    overall = round(total / len(FEATURES), 2)
    return {
        "crop": slug,
        "meta": get_crop_meta(slug),
        "overall_score": overall,
        "overall_status": _status_band(overall),
        "parameters": params,
    }


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def rows_to_csv(rows: Iterable[Dict[str, Any]]) -> str:
    """Serialize prediction rows to CSV text (Excel-friendly)."""
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM so Excel opens it correctly
    writer = csv.writer(buf)
    writer.writerow([
        "id", "Timestamp", "N", "P", "K", "temperature", "humidity",
        "ph", "rainfall", "predicted_crop", "confidence (%)",
    ])
    for r in rows:
        # Prefix with a single quote so Excel treats the timestamp as text
        # and shows it exactly as on the website (no ### / auto-date reformat).
        ts = f"'{r['created_at']}"
        writer.writerow([
            r["id"], ts, r["N"], r["P"], r["K"],
            r["temperature"], r["humidity"], r["ph"], r["rainfall"],
            r["predicted_crop"], f"{r['confidence']:.2f}",
        ])
    return buf.getvalue()



# ---------------------------------------------------------------------------
# PDF export (ReportLab)
# ---------------------------------------------------------------------------

def prediction_pdf(row: Dict[str, Any]) -> bytes:
    """Render a single prediction record as a styled PDF report."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    )

    meta = get_crop_meta(row["predicted_crop"])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="OptiCrop Recommendation Report",
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="H1", fontName="Helvetica-Bold",
        fontSize=20, leading=25, textColor=colors.HexColor("#0f3d2e"),
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        name="Sub", fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=colors.HexColor("#6b7280"),
        spaceBefore=6, spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        name="H2", fontName="Helvetica-Bold",
        fontSize=13, leading=16, textColor=colors.HexColor("#0f3d2e"),
        spaceBefore=14, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="Body2", fontName="Helvetica",
        fontSize=10, leading=14, textColor=colors.HexColor("#111827"),
    ))
    # Cell-safe paragraph styles: text wraps inside its column instead of
    # overflowing past the table border.
    cell_style = ParagraphStyle(
        name="Cell", fontName="Helvetica",
        fontSize=9.5, leading=13, textColor=colors.HexColor("#111827"),
    )
    cell_head_style = ParagraphStyle(
        name="CellHead", fontName="Helvetica-Bold",
        fontSize=9.5, leading=13, textColor=colors.white,
    )
    cell_label_style = ParagraphStyle(
        name="CellLabel", fontName="Helvetica-Bold",
        fontSize=9.5, leading=13, textColor=colors.HexColor("#0f3d2e"),
    )

    def P_(text: Any, style=cell_style) -> Paragraph:
        """Wrap a table cell value as a word-wrapping Paragraph."""
        return Paragraph("" if text is None else str(text), style)

    story = []
    story.append(Paragraph("OptiCrop \u2014 Crop Recommendation Report", styles["H1"]))
    story.append(Paragraph(
        f"Generated on {row['created_at']}  \u2022  Report ID #{row['id']}",
        styles["Sub"],
    ))

    story.append(Paragraph("Recommendation", styles["H2"]))
    story.append(Paragraph(
        f"<b>{meta.get('name', row['predicted_crop']).title()}</b> "
        f"\u2014 confidence <b>{row['confidence']:.1f}%</b>",
        styles["Body2"],
    ))
    if meta:
        story.append(Spacer(1, 4))
        story.append(Paragraph(meta.get("description", ""), styles["Body2"]))

    story.append(Paragraph("Input Parameters", styles["H2"]))
    data = [[P_("Parameter", cell_head_style), P_("Value", cell_head_style), P_("Unit", cell_head_style)]]
    for key in FEATURES:
        data.append([
            P_(FEATURE_LABELS[key]),
            P_(f"{row[key]:g}"),
            P_(FEATURE_UNITS[key] or "\u2014"),
        ])
    tbl = Table(data, colWidths=[7 * cm, 5 * cm, 4 * cm], repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f3d2e")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
            [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)

    if meta:
        story.append(Paragraph("Agronomy Guide", styles["H2"]))
        guide = [
            ["Category", meta.get("category")],
            ["Season", meta.get("season")],
            ["Ideal Temperature", meta.get("ideal_temperature")],
            ["Suitable pH", meta.get("ph_range")],
            ["Rainfall", meta.get("rainfall_range")],
            ["Water Requirement", meta.get("water")],
            ["Suitable Soil", meta.get("soil")],
            ["Fertilizer", meta.get("fertilizer")],
            ["Expected Yield", meta.get("expected_yield")],
        ]
        guide_data = [[P_(label, cell_label_style), P_(value)] for label, value in guide]
        # Narrower label column, wider value column — long fertilizer/soil
        # guidance now wraps onto multiple lines instead of running off
        # the page.
        g = Table(guide_data, colWidths=[4.2 * cm, 11.8 * cm], repeatRows=0)
        g.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0f7f2")),
            ("ROWBACKGROUNDS", (1, 0), (1, -1),
                [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e5e7eb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        story.append(g)

    doc.build(story)
    return buf.getvalue()