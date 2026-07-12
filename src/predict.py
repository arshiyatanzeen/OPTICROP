"""Inference helpers for OptiCrop.
Loads the persisted RandomForest model + scaler + label encoder from
`model/` and exposes a simple `predict_crop()` function used by the
Flask API in `app.py`.
Usage:
    from src.predict import predict_crop
    result = predict_crop({
        "N": 90, "P": 42, "K": 43,
        "temperature": 20.8, "humidity": 82.0,
        "ph": 6.5, "rainfall": 202.9,
    })
    # → {"crop": "rice", "confidence": 0.98, "top3": [...]}
"""
from __future__ import annotations
import os
from typing import Any, Dict, List
import joblib
import numpy as np
from .preprocessing import FEATURES, ROOT
MODEL_DIR = os.path.join(ROOT, "model")
MODEL_PATH = os.path.join(MODEL_DIR, "crop_model.joblib")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.joblib")
ENCODER_PATH = os.path.join(MODEL_DIR, "label_encoder.joblib")
# Lazy singletons
_model = None
_scaler = None
_encoder = None
def _load() -> None:
    """Load model artifacts once and cache them in module globals."""
    global _model, _scaler, _encoder
    if _model is not None:
        return
    for p in (MODEL_PATH, SCALER_PATH, ENCODER_PATH):
        if not os.path.exists(p):
            raise FileNotFoundError(
                f"Missing model artifact '{p}'. Run `python -m src.train_model` first."
            )
    _model = joblib.load(MODEL_PATH)
    _scaler = joblib.load(SCALER_PATH)
    _encoder = joblib.load(ENCODER_PATH)
def predict_crop(features: Dict[str, float], top_k: int = 3) -> Dict[str, Any]:
    """Predict the best crop for a soil/climate feature dict.
    Parameters
    ----------
    features : dict
        Keys must include N, P, K, temperature, humidity, ph, rainfall.
    top_k : int
        Number of top predictions to return with per-class probability.
    Returns
    -------
    dict with keys:
        crop        (str)   — best crop name
        confidence  (float) — probability of the best crop (0..1)
        top3        (list)  — [{"crop": str, "probability": float}, ...]
    """
    _load()
    row = np.array([[float(features[f]) for f in FEATURES]])
    row_scaled = _scaler.transform(row)
    # Probabilities (fall back to one-hot if the estimator has none)
    if hasattr(_model, "predict_proba"):
        proba = _model.predict_proba(row_scaled)[0]
    else:
        pred_idx = int(_model.predict(row_scaled)[0])
        proba = np.zeros(len(_encoder.classes_), dtype=float)
        proba[pred_idx] = 1.0
    order = np.argsort(proba)[::-1]
    top: List[Dict[str, Any]] = [
        {"crop": str(_encoder.classes_[i]),
         "probability": round(float(proba[i]), 4)}
        for i in order[:top_k]
    ]
    return {
        "crop": top[0]["crop"],
        "confidence": top[0]["probability"],
        "top3": top,
    }