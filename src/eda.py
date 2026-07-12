"""Exploratory Data Analysis plots for OptiCrop.
Generates PNG figures under `static/images/eda/`:
- missing.png                (missing values per column)
- correlation_heatmap.png    (feature correlation)
- histograms.png             (feature distributions)
- class_balance.png          (samples per crop)
- pairplot.png               (pairwise feature relationships)
Called by `train_model.py`, but can also be executed directly:
    python -m src.eda
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from .preprocessing import FEATURES, ROOT, load_and_clean
EDA_DIR = os.path.join(ROOT, "static", "images", "eda")
def run_eda(df: pd.DataFrame) -> None:
    """Save all EDA figures as PNGs."""
    os.makedirs(EDA_DIR, exist_ok=True)
    sns.set_theme(style="whitegrid", context="talk")
    # 1) Missing-value bar chart
    fig, ax = plt.subplots(figsize=(9, 4))
    df.isna().sum().plot(kind="bar", ax=ax, color="#0f3d2e")
    ax.set_title("Missing values per column")
    ax.set_ylabel("count")
    fig.tight_layout()
    fig.savefig(os.path.join(EDA_DIR, "missing.png"), dpi=140)
    plt.close(fig)
    # 2) Correlation heatmap
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(df[FEATURES].corr(), annot=True, fmt=".2f",
                cmap="crest", ax=ax, cbar_kws={"shrink": 0.8})
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
    fig.savefig(os.path.join(EDA_DIR, "histograms.png"),
                dpi=140, bbox_inches="tight")
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
    # 5) Pairplot (sampled for speed)
    sample = df.sample(min(600, len(df)), random_state=42)
    g = sns.pairplot(sample, vars=FEATURES[:5], hue="label",
                     palette="crest", plot_kws={"s": 12, "alpha": 0.6},
                     height=1.8)
    g.fig.suptitle("Pairwise feature relationships", y=1.02)
    g.fig.savefig(os.path.join(EDA_DIR, "pairplot.png"),
                  dpi=120, bbox_inches="tight")
    plt.close(g.fig)
    print(f"→ EDA plots written to {EDA_DIR}")
if __name__ == "__main__":
    run_eda(load_and_clean())