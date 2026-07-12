from __future__ import annotations

import json
import os
import sys
import warnings
from typing import Dict, Tuple

import joblib
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix, f1_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(ROOT, "dataset")
DATASET_PATH = os.path.join(DATASET_DIR, "Crop_recommendation.csv")
MODEL_DIR = os.path.join(ROOT, "model")
EDA_DIR = os.path.join(ROOT, "static", "images", "eda")

DATASET_URLS = [
    "https://raw.githubusercontent.com/Gladiator07/Harvestify/master/Data-processed/crop_recommendation.csv",
    "https://raw.githubusercontent.com/gabbygab1233/Crop-Recommender/main/Crop_recommendation.csv",
    "https://raw.githubusercontent.com/arunperala/Modern-Farming-using-MachineLearning/main/Data-processed/crop_recommendation.csv",
]

FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]


def ensure_dirs() -> None:
    """Create all output directories."""
    for d in (DATASET_DIR, MODEL_DIR, EDA_DIR):
        os.makedirs(d, exist_ok=True)


def download_dataset() -> None:
    """Download the Crop Recommendation dataset if it isn't already present.

    Tries several public mirrors and falls back to the next on any failure.
    """
    if os.path.exists(DATASET_PATH):
        return
    last_err: Exception | None = None
    for url in DATASET_URLS:
        try:
            print(f"→ downloading dataset from {url}")
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            content = r.content
            # Sanity check: must contain expected header
            head = content[:200].decode("utf-8", errors="ignore").lower()
            if "label" not in head or "temperature" not in head:
                raise ValueError("unexpected file contents")
            with open(DATASET_PATH, "wb") as f:
                f.write(content)
            print(f"  saved to {DATASET_PATH}")
            return
        except Exception as e:  # noqa: BLE001
            last_err = e
            print(f"  failed ({e}); trying next mirror…")
    raise RuntimeError(
        "Could not download the Crop Recommendation dataset from any mirror. "
        "Download it manually and place it at "
        f"'{DATASET_PATH}'. Last error: {last_err}"
    )


def load_and_clean() -> pd.DataFrame:
    """Load CSV, coerce dtypes, drop duplicates, report missing values."""
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


def run_eda(df: pd.DataFrame) -> None:
    """Generate all EDA plots as PNG files under static/images/eda/."""
    sns.set_theme(style="whitegrid", context="talk")

    # 1) Missing-value bar chart (always saved even if all zero)
    fig, ax = plt.subplots(figsize=(9, 4))
    df.isna().sum().plot(kind="bar", ax=ax, color="#0f3d2e")
    ax.set_title("Missing values per column")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "missing.png"), dpi=140)
    plt.close(fig)

    # 2) Correlation heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(
        df[FEATURES].corr(), annot=True, fmt=".2f",
        cmap="crest", ax=ax, cbar_kws={"shrink": 0.8},
    )
    ax.set_title("Feature correlation")
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "correlation_heatmap.png"), dpi=140)
    plt.close(fig)

    # 3) Histograms
    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    for ax, col in zip(axes.flatten(), FEATURES):
        sns.histplot(df[col], kde=True, ax=ax, color="#2f855a")
        ax.set_title(col)
    axes.flatten()[-1].axis("off")
    fig.suptitle("Feature distributions", y=1.02, fontsize=18)
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "histograms.png"), dpi=140,
                bbox_inches="tight")
    plt.close(fig)

    # 4) Class balance
    fig, ax = plt.subplots(figsize=(12, 5))
    df["label"].value_counts().plot(kind="bar", ax=ax, color="#0f3d2e")
    ax.set_title("Samples per crop")
    ax.set_ylabel("count")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "class_balance.png"), dpi=140)
    plt.close(fig)

    # 5) Pairplot (subset to keep runtime reasonable)
    sample = df.sample(min(600, len(df)), random_state=42)
    g = sns.pairplot(
        sample, vars=FEATURES[:5], hue="label",
        palette="crest", plot_kws={"s": 12, "alpha": 0.6},
        height=1.8,
    )
    g.fig.suptitle("Pairwise feature relationships", y=1.02)
    g.fig.savefig(os.path.join(EDA_DIR, "pairplot.png"),
                  dpi=120, bbox_inches="tight")
    plt.close(g.fig)

    print(f"→ EDA plots written to {EDA_DIR}")


def train_and_evaluate(df: pd.DataFrame) -> Dict:
    """Train multiple models, keep the best, save artifacts."""
    X = df[FEATURES].values
    y_raw = df["label"].values

    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, stratify=y, random_state=42,
    )

    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, random_state=42, n_jobs=-1),
        "LogisticRegression": LogisticRegression(
            max_iter=2000, random_state=42),
        "KNN": KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
        "SVC": SVC(kernel="rbf", C=2.0, probability=True, random_state=42),
        "GaussianNB": GaussianNB(),
    }

    scores: Dict[str, float] = {}
    best_name = ""
    best_model = None
    best_acc = -1.0
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        scores[name] = round(float(acc), 4)
        print(f"  {name:20s} accuracy = {acc:.4f}")
        if acc > best_acc:
            best_acc = acc
            best_name = name
            best_model = model

    assert best_model is not None
    preds = best_model.predict(X_test)
    macro_f1 = float(f1_score(y_test, preds, average="macro"))
    report = classification_report(
        y_test, preds, target_names=list(le.classes_), output_dict=True,
        zero_division=0,
    )
    cm = confusion_matrix(y_test, preds)

    # Confusion matrix plot
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(
        cm, annot=False, cmap="crest",
        xticklabels=le.classes_, yticklabels=le.classes_, ax=ax,
    )
    ax.set_title(f"Confusion matrix — {best_name}")
    ax.set_xlabel("predicted"); ax.set_ylabel("actual")
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "confusion_matrix.png"), dpi=140)
    plt.close(fig)

    # Feature importance (or coefficient magnitudes for linear models)
    importance = _feature_importance(best_model)
    if importance is not None:
        fig, ax = plt.subplots(figsize=(9, 4.5))
        order = np.argsort(importance)[::-1]
        ax.bar(np.array(FEATURES)[order], importance[order], color="#0f3d2e")
        ax.set_title(f"Feature importance — {best_name}")
        ax.set_ylabel("importance")
        fig.tight_layout()
        fig.savefig(os.path.join(EDA_DIR, "feature_importance.png"), dpi=140)
        plt.close(fig)

    # Persist artifacts
    joblib.dump(best_model, os.path.join(MODEL_DIR, "crop_model.joblib"))
    joblib.dump(scaler,     os.path.join(MODEL_DIR, "scaler.joblib"))
    joblib.dump(le,         os.path.join(MODEL_DIR, "label_encoder.joblib"))

    metrics = {
        "best_model": best_name,
        "accuracy": round(float(best_acc), 4),
        "macro_f1": round(macro_f1, 4),
        "model_scores": scores,
        "classes": list(le.classes_),
        "classification_report": report,
        "confusion_matrix": cm.tolist(),
        "feature_importance": (
            {f: float(v) for f, v in zip(FEATURES, importance)}
            if importance is not None else None
        ),
        "n_samples": int(len(df)),
        "n_features": len(FEATURES),
        "n_classes": int(len(le.classes_)),
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"→ best model: {best_name}  acc={best_acc:.4f}  macro-F1={macro_f1:.4f}")
    print(f"→ artifacts saved to {MODEL_DIR}")
    return metrics


def _feature_importance(model) -> np.ndarray | None:
    """Best-effort feature importance for the chosen estimator."""
    if hasattr(model, "feature_importances_"):
        return np.asarray(model.feature_importances_, dtype=float)
    if hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        return np.abs(coef).mean(axis=0)
    return None


def main() -> int:
    """Entry point."""
    ensure_dirs()
    download_dataset()
    df = load_and_clean()
    run_eda(df)
    train_and_evaluate(df)
    print("✓ training complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
