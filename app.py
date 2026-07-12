"""OptiCrop — Flask application (with user authentication).
 
Serves the dashboard UI and a full REST API for crop recommendations,
suitability scoring, crop library, prediction history, CSV / PDF export,
and research statistics.
 
Run:
 
    python model_training.py    # once, to produce model artifacts
    python app.py               # http://127.0.0.1:5000
"""
 
from __future__ import annotations
 
import json
import logging
import os
from typing import Any, Dict, List
 
import joblib
import numpy as np
from flask import (
    Flask, Response, jsonify, render_template, request, send_file,
    session, url_for,
)
 
import database
import utils
from auth import auth_bp, login_required, current_user
 
# ---------------------------------------------------------------------------
# App + logging
# ---------------------------------------------------------------------------
 
app = Flask(__name__, template_folder="templates", static_folder="static")
 
# SECRET_KEY is required for Flask sessions (login state).
# In production set this to a long random string via an environment variable.
app.secret_key = os.environ.get("SECRET_KEY", "opticrop-change-me-in-production-2024")
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("opticrop")
 
ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(ROOT, "model")
 
_model = None
_scaler = None
_encoder = None
_metrics: Dict[str, Any] = {}
 
 
def _load_artifacts() -> None:
    """Lazily load the trained model + scaler + label encoder + metrics."""
    global _model, _scaler, _encoder, _metrics
    if _model is not None:
        return
    model_path = os.path.join(MODEL_DIR, "crop_model.joblib")
    if not os.path.exists(model_path):
        raise RuntimeError(
            "Model artifacts not found. Run `python model_training.py` first."
        )
    _model = joblib.load(model_path)
    _scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
    _encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.joblib"))
    metrics_path = os.path.join(MODEL_DIR, "metrics.json")
    if os.path.exists(metrics_path):
        with open(metrics_path) as f:
            _metrics = json.load(f)
    log.info("model loaded: %s", _metrics.get("best_model", "unknown"))
    _ensure_dataset_and_model_rows()
 
 
_dataset_id = None
_model_id = None
 
 
def _ensure_dataset_and_model_rows() -> None:
    """Idempotently create the ER-diagram Dataset + MLModel rows that
    describe the artifacts we just loaded (safe to call every startup)."""
    global _dataset_id, _model_id
    dataset_csv = os.path.join(ROOT, "dataset", "Crop_recommendation.csv")
    total_records = _metrics.get("n_samples")
    if total_records is None and os.path.exists(dataset_csv):
        with open(dataset_csv) as f:
            total_records = max(sum(1 for _ in f) - 1, 0)  # minus header row
    _dataset_id = database.get_or_create_dataset(
        dataset_name="Crop_recommendation.csv",
        source="dataset/Crop_recommendation.csv",
        total_records=total_records or 0,
    )
    _model_id = database.get_or_create_ml_model(
        dataset_id=_dataset_id,
        model_name=_metrics.get("best_model", "unknown"),
        accuracy=_metrics.get("accuracy"),
    )
 
 
# Initialize DB immediately (cheap). Also creates the users table and the
# ER-diagram entities (soil_data, crop, dataset, ml_model, report).
database.init_db()
database.seed_crop_table(utils.CROP_META)
 
# Register auth blueprint (/login, /register, /logout, /forgot-password, /reset-password/<token>)
app.register_blueprint(auth_bp)
 
 
# ---------------------------------------------------------------------------
# Page routes  — ALL protected with @login_required
# ---------------------------------------------------------------------------
 
_NAV = [
    {"slug": "dashboard",   "path": "/",             "label": "Overview",              "icon": "layout-dashboard"},
    {"slug": "recommend",   "path": "/recommend",    "label": "Smart Recommendation",  "icon": "sparkles"},
    {"slug": "suitability", "path": "/suitability",  "label": "Suitability Assessment","icon": "gauge"},
    {"slug": "library",     "path": "/library",      "label": "Crop Library",          "icon": "book-open"},
    {"slug": "research",    "path": "/research",     "label": "Research & Policy",     "icon": "bar-chart-3"},
    {"slug": "history",     "path": "/history",      "label": "Prediction History",    "icon": "history"},
    {"slug": "about",       "path": "/about",        "label": "About",                 "icon": "info"},
]
 
 
def _render(template: str, active: str, **context: Any) -> str:
    """Wrapper that injects nav + brand + current user context into every page."""
    return render_template(
        template,
        nav=_NAV,
        active=active,
        brand="OptiCrop",
        user=current_user(),   # ← available in every template as {{ user }}
        **context,
    )
 
 
@app.route("/")
@login_required
def page_dashboard() -> str:
    stats = database.aggregate_stats()
    return _render(
        "dashboard.html", active="dashboard",
        stats=stats, crops_count=len(utils.CROP_META),
    )
 
 
@app.route("/recommend")
@login_required
def page_recommend() -> str:
    return _render("recommend.html", active="recommend",
                   bounds=utils.FEATURE_BOUNDS, labels=utils.FEATURE_LABELS,
                   units=utils.FEATURE_UNITS)
 
 
@app.route("/suitability")
@login_required
def page_suitability() -> str:
    return _render("suitability.html", active="suitability",
                   crops=utils.list_crops(),
                   bounds=utils.FEATURE_BOUNDS, labels=utils.FEATURE_LABELS,
                   units=utils.FEATURE_UNITS)
 
 
@app.route("/library")
@login_required
def page_library() -> str:
    return _render("library.html", active="library",
                   crops=utils.list_crops())
 
 
@app.route("/research")
@login_required
def page_research() -> str:
    try:
        _load_artifacts()
    except RuntimeError:
        pass
    return _render(
        "research.html", active="research",
        metrics=_metrics, stats=database.aggregate_stats(),
    )
 
 
@app.route("/history")
@login_required
def page_history() -> str:
    return _render("history.html", active="history")
 
 
@app.route("/about")
@login_required
def page_about() -> str:
    return _render("about.html", active="about")
 
 
# ---------------------------------------------------------------------------
# REST API  — ALL protected with @login_required
# ---------------------------------------------------------------------------
 
def _err(msg: str, status: int = 400, **extra: Any) -> Response:
    payload = {"ok": False, "error": msg, **extra}
    return Response(json.dumps(payload), status=status, mimetype="application/json")
 
 
@app.post("/api/predict")
@login_required
def api_predict() -> Response:
    try:
        _load_artifacts()
    except RuntimeError as e:
        return _err(str(e), 503)
 
    payload = request.get_json(silent=True) or request.form.to_dict()
    features, errors = utils.validate_features(payload)
    if errors:
        return _err("Validation failed.", 422, details=errors)
 
    X = np.array([[features[k] for k in utils.FEATURES]], dtype=float)
    Xs = _scaler.transform(X)
    if hasattr(_model, "predict_proba"):
        probs = _model.predict_proba(Xs)[0]
    else:
        pred = int(_model.predict(Xs)[0])
        probs = np.zeros(len(_encoder.classes_)); probs[pred] = 1.0
 
    order = np.argsort(probs)[::-1]
    top3: List[Dict[str, Any]] = []
    for i in order[:3]:
        name = str(_encoder.classes_[i])
        top3.append({
            "crop": name,
            "confidence": round(float(probs[i]) * 100, 2),
            "meta": utils.get_crop_meta(name),
        })
 
    best = top3[0]
 
    # ── ER-diagram wiring: User -> SoilData -> Prediction <- Crop, MLModel ──
    user = current_user()
    soil_id = database.insert_soil_data(
        features, user_id=(user["user_id"] if user else None),
    )
    crop_id = database.get_or_create_crop_id(best["crop"], best.get("meta"))
 
    pred_id = database.insert_prediction(
        features, best["crop"], best["confidence"], top3,
        soil_id=soil_id, crop_id=crop_id, model_id=_model_id,
    )
 
    # ── Report entity: generated right after the recommendation ────────────
    meta = best.get("meta") or {}
    summary = (
        f"OptiCrop recommends {best['crop'].title()} with "
        f"{best['confidence']:.2f}% confidence for the submitted field "
        f"conditions (N={features['N']}, P={features['P']}, K={features['K']}, "
        f"T={features['temperature']}°C, H={features['humidity']}%, "
        f"pH={features['ph']}, Rainfall={features['rainfall']}mm)."
    )
    recommendations = "; ".join(filter(None, [
        f"Ideal season: {meta.get('season')}" if meta.get("season") else None,
        f"Water requirement: {meta.get('water')}" if meta.get("water") else None,
        f"Fertilizer guidance: {meta.get('fertilizer')}" if meta.get("fertilizer") else None,
        f"Ideal pH range: {meta.get('ph_range')}" if meta.get("ph_range") else None,
    ])) or "See crop library for detailed cultivation guidance."
    report_id = database.insert_report(pred_id, summary, recommendations)
 
    return jsonify({
        "ok": True,
        "id": pred_id,
        "report_id": report_id,
        "prediction": best,
        "top3": top3,
        "input": features,
        "image_url": url_for("static",
                             filename="images/crops/placeholder.svg"),
    })
 
 
@app.post("/api/suitability")
@login_required
def api_suitability() -> Response:
    payload = request.get_json(silent=True) or request.form.to_dict()
    crop = (payload.get("crop") or "").strip().lower()
    if not crop:
        return _err("Field 'crop' is required.", 422)
    features, errors = utils.validate_features(payload)
    if errors:
        return _err("Validation failed.", 422, details=errors)
 
    report = utils.suitability_report(crop, features)
    if "error" in report:
        return _err(report["error"], 404)
    return jsonify({"ok": True, "report": report})
 
 
@app.get("/api/crops")
@login_required
def api_crops() -> Response:
    return jsonify({"ok": True, "crops": utils.list_crops()})
 
 
@app.get("/api/crops/<name>")
@login_required
def api_crop(name: str) -> Response:
    meta = utils.get_crop_meta(name)
    if not meta:
        return _err(f"Unknown crop '{name}'.", 404)
    return jsonify({"ok": True, "crop": {"slug": name.lower(), **meta}})
 
 
@app.get("/api/history")
@login_required
def api_history() -> Response:
    q = request.args.get("q", "", type=str)
    limit = min(max(request.args.get("limit", 100, type=int), 1), 500)
    rows = database.search_predictions(q, limit)
    return jsonify({"ok": True, "count": len(rows), "rows": rows})
 
 
@app.get("/api/history.csv")
@login_required
def api_history_csv() -> Response:
    """Export prediction history as CSV — scoped to the current search (`q`),
    exactly like the table shown on the Prediction History page. Omit `q`
    to export everything."""
    q = request.args.get("q", "", type=str)
    rows = database.all_predictions(query=q)
    csv_text = utils.rows_to_csv(rows)
    filename = f"opticrop_history_{q}.csv" if q else "opticrop_history.csv"
    return Response(
        csv_text, mimetype="text/csv",
        headers={"Content-Disposition":
                 f"attachment; filename={filename}"},
    )
 
 
@app.get("/api/history/<int:pred_id>/report.pdf")
@login_required
def api_history_pdf(pred_id: int) -> Response:
    row = database.get_prediction(pred_id)
    if not row:
        return _err("Prediction not found.", 404)
    pdf = utils.prediction_pdf(row)
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition":
                 f"attachment; filename=opticrop_report_{pred_id}.pdf"},
    )
 
 
@app.get("/api/stats")
@login_required
def api_stats() -> Response:
    try:
        _load_artifacts()
    except RuntimeError as e:
        return _err(str(e), 503)
    return jsonify({
        "ok": True,
        "model": {
            "name": _metrics.get("best_model"),
            "accuracy": _metrics.get("accuracy"),
            "macro_f1": _metrics.get("macro_f1"),
            "model_scores": _metrics.get("model_scores", {}),
            "n_samples": _metrics.get("n_samples"),
            "n_features": _metrics.get("n_features"),
            "n_classes": _metrics.get("n_classes"),
            "classes": _metrics.get("classes", []),
            "feature_importance": _metrics.get("feature_importance") or {},
            "confusion_matrix": _metrics.get("confusion_matrix", []),
        },
        "usage": database.aggregate_stats(),
    })
 
 
# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
 
@app.errorhandler(404)
def not_found(_e):
    if request.path.startswith("/api/"):
        return _err("Not found.", 404)
    return _render("dashboard.html", active="dashboard",
                   stats=database.aggregate_stats(),
                   crops_count=len(utils.CROP_META)), 404
 
 
@app.errorhandler(500)
def server_error(e):
    log.exception("server error: %s", e)
    if request.path.startswith("/api/"):
        return _err("Internal server error.", 500)
    return _render("dashboard.html", active="dashboard",
                   stats=database.aggregate_stats(),
                   crops_count=len(utils.CROP_META)), 500
 
 
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)