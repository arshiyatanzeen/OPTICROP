"""Data loading, cleaning and preprocessing for OptiCrop.
Responsibilities:
- Download the Crop Recommendation dataset if it isn't already local.
- Load the CSV into a pandas DataFrame.
- Coerce dtypes, strip whitespace, drop duplicates / NaN rows.
- Fit / return the StandardScaler and LabelEncoder used by the model.
This module is imported by `train_model.py` and `eda.py`. It has no
side-effects at import time — call the functions explicitly.
"""
from __future__ import annotations
import os
from typing import Tuple
import numpy as np
import pandas as pd
import requests
from sklearn.preprocessing import LabelEncoder, StandardScaler
# ---------------------------------------------------------------------------
# Paths (resolved from the project root — one level above /src)
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(ROOT, "dataset")
DATASET_PATH = os.path.join(DATASET_DIR, "Crop_recommendation.csv")
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
DATASET_URLS = [
    "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv",
    "https://raw.githubusercontent.com/gabbygab1233/Crop-Recommender/main/Crop_recommendation.csv",
    "https://raw.githubusercontent.com/arunperala/Modern-Farming-using-MachineLearning/main/Data-processed/crop_recommendation.csv",
]
def download_dataset() -> None:
    """Fetch the Kaggle Crop Recommendation CSV from a public mirror."""
    if os.path.exists(DATASET_PATH):
        return
    os.makedirs(DATASET_DIR, exist_ok=True)
    last_err: Exception | None = None
    for url in DATASET_URLS:
        try:
            print(f"→ downloading dataset from {url}")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            head = r.content[:200].decode("utf-8", errors="ignore").lower()
            if "label" not in head or "temperature" not in head:
                raise ValueError("unexpected file contents")
            with open(DATASET_PATH, "wb") as f:
                f.write(r.content)
            print(f"  saved to {DATASET_PATH}")
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  failed ({e}); trying next mirror…")
    raise RuntimeError(
        f"Could not download the dataset. Place it at '{DATASET_PATH}'. "
        f"Last error: {last_err}"
    )
def load_and_clean() -> pd.DataFrame:
    """Load the CSV, coerce dtypes, drop duplicates and NaN rows."""
    download_dataset()
    df = pd.read_csv(DATASET_PATH)
    df.columns = [c.strip() for c in df.columns]
    for f in FEATURES:
        df[f] = pd.to_numeric(df[f], errors="coerce")
    df["label"] = df["label"].astype(str).str.strip().str.lower()
    df = df.drop_duplicates().reset_index(drop=True)
    missing = df.isna().sum()
    print("→ missing values per column:")
    print(missing.to_string())
    df = df.dropna().reset_index(drop=True)
    print(f"→ cleaned dataset: {len(df)} rows, {df['label'].nunique()} classes")
    return df
def build_features(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray,
                                              StandardScaler, LabelEncoder]:
    """Return (X_scaled, y_encoded, fitted_scaler, fitted_label_encoder)."""
    X = df[FEATURES].values
    y_raw = df["label"].values
    le = LabelEncoder()
    y = le.fit_transform(y_raw)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    return X_scaled, y, scaler, le