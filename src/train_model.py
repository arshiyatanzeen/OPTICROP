"""Train and evaluate the OptiCrop crop recommendation model.
Compares 5 classifiers (RandomForest, LogisticRegression, KNN, SVC,
GaussianNB), keeps the best by test accuracy, and persists:
    model/crop_model.joblib
    model/scaler.joblib
    model/label_encoder.joblib
    model/metrics.json
Also writes confusion_matrix.png and feature_importance.png to
static/images/eda/.
Run from the project root:
    python -m src.train_model
"""
from __future__ import annotations
import json
import os
import sys
import warnings
from typing import Dict
import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from .eda import EDA_DIR, run_eda
from .preprocessing import FEATURES, ROOT, build_features, load_and_clean
warnings.filterwarnings("ignore")
MODEL_DIR = os.path.join(ROOT, "model")
def _feature_importance(model) -> np.ndarray | None:
    """Best-effort feature importance for the chosen estimator."""
    if hasattr(model, "feature_importances_"):
        return np.asarray(model.feature_importances_, dtype=float)
    if hasattr(model, "coef_"):
        coef = np.asarray(model.coef_, dtype=float)
        return np.abs(coef).mean(axis=0)
    return None
def train_and_evaluate() -> Dict:
    """Full training pipeline; returns the metrics dict."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs(EDA_DIR, exist_ok=True)
    df = load_and_clean()
    run_eda(df)
    X_scaled, y, scaler, le = build_features(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, stratify=y, random_state=42)
    candidates = {
        "RandomForest": RandomForestClassifier(
            n_estimators=300, random_state=42, n_jobs=-1),
        "LogisticRegression": LogisticRegression(
            max_iter=2000, multi_class="auto", n_jobs=-1),
        "KNN": KNeighborsClassifier(n_neighbors=5, n_jobs=-1),
        "SVC": SVC(kernel="rbf", C=2.0, probability=True, random_state=42),
        "GaussianNB": GaussianNB(),
    }
    scores: Dict[str, float] = {}
    best_name, best_model, best_acc = "", None, -1.0
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        acc = accuracy_score(y_test, model.predict(X_test))
        scores[name] = round(float(acc), 4)
        print(f"  {name:20s} accuracy = {acc:.4f}")
        if acc > best_acc:
            best_acc, best_name, best_model = acc, name, model
    assert best_model is not None
    preds = best_model.predict(X_test)
    macro_f1 = float(f1_score(y_test, preds, average="macro"))
    report = classification_report(y_test, preds,
                                   target_names=list(le.classes_),
                                   output_dict=True, zero_division=0)
    cm = confusion_matrix(y_test, preds)
    # Confusion matrix
    fig, ax = plt.subplots(figsize=(11, 9))
    sns.heatmap(cm, annot=False, cmap="crest",
                xticklabels=le.classes_, yticklabels=le.classes_, ax=ax)
    ax.set_title(f"Confusion matrix — {best_name}")
    ax.set_xlabel("predicted"); ax.set_ylabel("actual")
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "confusion_matrix.png"), dpi=140)
    plt.close(fig)
    # Feature importance
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
            if importance is not None else None),
        "n_samples": int(len(df)),
        "n_features": len(FEATURES),
        "n_classes": int(len(le.classes_)),
    }
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"→ best model: {best_name}  acc={best_acc:.4f}  macro-F1={macro_f1:.4f}")
    print(f"→ artifacts saved to {MODEL_DIR}")
    return metrics
def main() -> int:
    """Entry point."""
    train_and_evaluate()
    print("✓ training complete.")
    return 0
if __name__ == "__main__":
    sys.exit(main())