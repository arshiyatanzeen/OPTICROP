"""SQLite persistence layer for prediction history + users.
 
Schema follows the project ER diagram:
 
    User (1) ──submits many──> SoilData (1) ──generates one──> Prediction
    Crop (1) ──generates many──> Prediction
    MLModel (1) ──generates many──> Prediction
    Dataset (1) ──trains many──> MLModel
    Prediction (1) ──generates many──> Report
 
`predictions` is kept as the original flat table (so existing history /
CSV / PDF-report code keeps working unchanged) and gains three new
nullable FK columns — soil_id, crop_id, model_id — added automatically
to any pre-existing database via a migration in init_db().
"""
 
from __future__ import annotations
 
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
 
from werkzeug.security import check_password_hash, generate_password_hash
 
DB_DIR = os.path.join(os.path.dirname(__file__), "database")
DB_PATH = os.path.join(DB_DIR, "predictions.db")
 
RESET_TOKEN_TTL_MINUTES = 30
 
 
def _connect() -> sqlite3.Connection:
    """Open a SQLite connection with row-dict access."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
 
 
def init_db() -> None:
    """Create every table on first run, and migrate an older database
    (from before the ER-diagram entities existed) in place."""
    with _connect() as conn:
        # ── predictions (original table, kept flat for backward compat) ────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                N REAL NOT NULL,
                P REAL NOT NULL,
                K REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity REAL NOT NULL,
                ph REAL NOT NULL,
                rainfall REAL NOT NULL,
                predicted_crop TEXT NOT NULL,
                confidence REAL NOT NULL,
                top3_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_predictions_crop ON predictions(predicted_crop)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_predictions_created_at ON predictions(created_at)"
        )
 
        # ── users ────────────────────────────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role          TEXT NOT NULL DEFAULT 'farmer',
                created_at    TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email)"
        )
 
        # ── password_resets (forgot-password flow) ─────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_resets (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used       INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
 
        # ── SoilData ─────────────────────────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS soil_data (
                soil_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                nitrogen    REAL NOT NULL,
                phosphorus  REAL NOT NULL,
                potassium   REAL NOT NULL,
                temperature REAL NOT NULL,
                humidity    REAL NOT NULL,
                ph          REAL NOT NULL,
                rainfall    REAL NOT NULL,
                season      TEXT,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_soildata_user ON soil_data(user_id)"
        )
 
        # ── Crop (reference table, seeded from utils.CROP_META) ────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS crop (
                crop_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                crop_name  TEXT NOT NULL UNIQUE,
                crop_type  TEXT,
                season     TEXT,
                optimal_ph TEXT
            )
            """
        )
 
        # ── Dataset ──────────────────────────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS dataset (
                dataset_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_name  TEXT NOT NULL,
                source        TEXT,
                total_records INTEGER,
                last_updated  TEXT
            )
            """
        )
 
        # ── MLModel ──────────────────────────────────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_model (
                model_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id  INTEGER,
                model_name  TEXT NOT NULL,
                accuracy    REAL,
                trained_at  TEXT,
                FOREIGN KEY (dataset_id) REFERENCES dataset(dataset_id)
            )
            """
        )
 
        # ── Report (one prediction -> many reports) ─────────────────────────
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS report (
                report_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                prediction_id   INTEGER NOT NULL,
                generated_date  TEXT NOT NULL,
                summary         TEXT,
                recommendations TEXT,
                FOREIGN KEY (prediction_id) REFERENCES predictions(id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_report_prediction ON report(prediction_id)"
        )
 
        # ── migrate predictions -> add soil_id / crop_id / model_id ────────
        _migrate_predictions_fk_columns(conn)
 
 
def _migrate_predictions_fk_columns(conn: sqlite3.Connection) -> None:
    """Add soil_id / crop_id / model_id to an existing `predictions` table
    created before the ER-diagram entities existed. Old rows simply keep
    these columns NULL — nothing is lost or renumbered."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(predictions)").fetchall()]
    if "soil_id" not in cols:
        conn.execute("ALTER TABLE predictions ADD COLUMN soil_id INTEGER")
    if "crop_id" not in cols:
        conn.execute("ALTER TABLE predictions ADD COLUMN crop_id INTEGER")
    if "model_id" not in cols:
        conn.execute("ALTER TABLE predictions ADD COLUMN model_id INTEGER")
 
 
# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------
 
def create_user(name: str, email: str, password: str, role: str = "farmer") -> Optional[int]:
    """Hash password and insert a new user. Returns user_id or None on failure."""
    hashed = generate_password_hash(password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with _connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO users (name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, email.lower().strip(), hashed, role, now),
            )
            return int(cur.lastrowid)
    except sqlite3.IntegrityError:
        # email already exists
        return None
 
 
def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Look up a user by email address; returns a dict or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.lower().strip(),)
        ).fetchone()
    return dict(row) if row else None
 
 
def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Look up a user by primary key; returns a dict or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (int(user_id),)
        ).fetchone()
    return dict(row) if row else None
 
 
def check_password(password_hash: str, password: str) -> bool:
    """Return True if the plain-text password matches the stored hash."""
    return check_password_hash(password_hash, password)
 
 
def update_user_password(user_id: int, new_password: str) -> None:
    """Set a new password for a user (used by the reset-password flow)."""
    hashed = generate_password_hash(new_password)
    with _connect() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (hashed, int(user_id)),
        )
 
 
# ---------------------------------------------------------------------------
# Password reset helpers ("forgot password")
# ---------------------------------------------------------------------------
 
def create_password_reset(user_id: int) -> str:
    """Generate a fresh one-time reset token for a user (invalidating any
    earlier unused tokens) and return it."""
    token = secrets.token_urlsafe(32)
    now = datetime.now()
    expires = now + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    with _connect() as conn:
        conn.execute(
            "UPDATE password_resets SET used = 1 WHERE user_id = ? AND used = 0",
            (user_id,),
        )
        conn.execute(
            """
            INSERT INTO password_resets (token, user_id, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
            """,
            (token, user_id, now.strftime("%Y-%m-%d %H:%M:%S"),
             expires.strftime("%Y-%m-%d %H:%M:%S")),
        )
    return token
 
 
def get_valid_password_reset(token: str) -> Optional[Dict[str, Any]]:
    """Return the reset row if `token` exists, is unused, and hasn't expired."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM password_resets WHERE token = ?", (token,)
        ).fetchone()
    if not row:
        return None
    row = dict(row)
    if row["used"]:
        return None
    if datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S") < datetime.now():
        return None
    return row
 
 
def consume_password_reset(token: str) -> None:
    """Mark a reset token as used so it can't be replayed."""
    with _connect() as conn:
        conn.execute(
            "UPDATE password_resets SET used = 1 WHERE token = ?", (token,)
        )
 
 
# ---------------------------------------------------------------------------
# Crop (reference table)
# ---------------------------------------------------------------------------
 
def seed_crop_table(crop_meta: Dict[str, Dict[str, Any]]) -> None:
    """Populate the `crop` reference table from utils.CROP_META, once.
    Safe to call on every startup — existing rows are left untouched."""
    with _connect() as conn:
        existing = {r["crop_name"] for r in conn.execute("SELECT crop_name FROM crop").fetchall()}
        for slug, meta in crop_meta.items():
            name = meta.get("name", slug).lower()
            if name in existing:
                continue
            conn.execute(
                """
                INSERT INTO crop (crop_name, crop_type, season, optimal_ph)
                VALUES (?, ?, ?, ?)
                """,
                (name, meta.get("category"), meta.get("season"), meta.get("ph_range")),
            )
 
 
def get_or_create_crop_id(crop_name: str, meta: Optional[Dict[str, Any]] = None) -> int:
    """Look up crop_id by name (case-insensitive), inserting it if missing."""
    name = crop_name.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT crop_id FROM crop WHERE crop_name = ?", (name,)
        ).fetchone()
        if row:
            return int(row["crop_id"])
        meta = meta or {}
        cur = conn.execute(
            """
            INSERT INTO crop (crop_name, crop_type, season, optimal_ph)
            VALUES (?, ?, ?, ?)
            """,
            (name, meta.get("category"), meta.get("season"), meta.get("ph_range")),
        )
        return int(cur.lastrowid)
 
 
# ---------------------------------------------------------------------------
# Dataset + MLModel
# ---------------------------------------------------------------------------
 
def get_or_create_dataset(dataset_name: str, source: str,
                          total_records: int) -> int:
    """Idempotent upsert of the dataset row used to train the model; returns
    dataset_id. Updates total_records/last_updated if the row already
    exists."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        row = conn.execute(
            "SELECT dataset_id FROM dataset WHERE dataset_name = ?", (dataset_name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE dataset SET total_records = ?, last_updated = ?, source = ? "
                "WHERE dataset_id = ?",
                (total_records, now, source, row["dataset_id"]),
            )
            return int(row["dataset_id"])
        cur = conn.execute(
            """
            INSERT INTO dataset (dataset_name, source, total_records, last_updated)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_name, source, total_records, now),
        )
        return int(cur.lastrowid)
 
 
def get_or_create_ml_model(dataset_id: Optional[int], model_name: str,
                           accuracy: Optional[float]) -> int:
    """Idempotent upsert of the currently-deployed model row; returns
    model_id. If a row for this model_name already exists it is updated
    with the latest accuracy/trained_at instead of duplicating."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        row = conn.execute(
            "SELECT model_id FROM ml_model WHERE model_name = ?", (model_name,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE ml_model SET accuracy = ?, trained_at = ?, dataset_id = ? "
                "WHERE model_id = ?",
                (accuracy, now, dataset_id, row["model_id"]),
            )
            return int(row["model_id"])
        cur = conn.execute(
            """
            INSERT INTO ml_model (dataset_id, model_name, accuracy, trained_at)
            VALUES (?, ?, ?, ?)
            """,
            (dataset_id, model_name, accuracy, now),
        )
        return int(cur.lastrowid)
 
 
# ---------------------------------------------------------------------------
# SoilData
# ---------------------------------------------------------------------------
 
def insert_soil_data(features: Dict[str, float], user_id: Optional[int] = None,
                     season: Optional[str] = None) -> int:
    """Insert the raw field-parameter reading a user submitted; return soil_id."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO soil_data
                (user_id, nitrogen, phosphorus, potassium, temperature,
                 humidity, ph, rainfall, season, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, features["N"], features["P"], features["K"],
                features["temperature"], features["humidity"],
                features["ph"], features["rainfall"], season, now,
            ),
        )
        return int(cur.lastrowid)
 
 
# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
 
def insert_report(prediction_id: int, summary: str, recommendations: str) -> int:
    """Create the Report row generated right after a recommendation."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO report (prediction_id, generated_date, summary, recommendations)
            VALUES (?, ?, ?, ?)
            """,
            (prediction_id, now, summary, recommendations),
        )
        return int(cur.lastrowid)
 
 
def get_report_for_prediction(prediction_id: int) -> Optional[Dict[str, Any]]:
    """Return the most recent report generated for a prediction, if any."""
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT * FROM report WHERE prediction_id = ?
            ORDER BY report_id DESC LIMIT 1
            """,
            (prediction_id,),
        ).fetchone()
    return dict(row) if row else None
 
 
# ---------------------------------------------------------------------------
# Prediction helpers
# ---------------------------------------------------------------------------
 
def insert_prediction(features: Dict[str, float], crop: str,
                      confidence: float, top3: List[Dict[str, Any]],
                      soil_id: Optional[int] = None,
                      crop_id: Optional[int] = None,
                      model_id: Optional[int] = None) -> int:
    """Insert a new prediction row; return its id. soil_id/crop_id/model_id
    are optional so this still works exactly as before if the ER-diagram
    wiring isn't used by a caller."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO predictions
                (created_at, N, P, K, temperature, humidity, ph, rainfall,
                 predicted_crop, confidence, top3_json, soil_id, crop_id, model_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                features["N"], features["P"], features["K"],
                features["temperature"], features["humidity"],
                features["ph"], features["rainfall"],
                crop, confidence, json.dumps(top3),
                soil_id, crop_id, model_id,
            ),
        )
        return int(cur.lastrowid)
 
 
def get_prediction(pred_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single prediction row as a dict."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM predictions WHERE id = ?", (pred_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None
 
 
def search_predictions(query: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    """Search predictions by crop name; newest first."""
    q = f"%{query.strip().lower()}%" if query else "%"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM predictions
            WHERE LOWER(predicted_crop) LIKE ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (q, int(limit)),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
 
 
def all_predictions(query: str = "") -> List[Dict[str, Any]]:
    """Return predictions for CSV export, newest first.
 
    `query` filters by crop name exactly like search_predictions, so the
    CSV export always matches whatever is currently shown/searched in the
    Prediction History table — pass "" (default) to export everything.
    """
    q = f"%{query.strip().lower()}%" if query else "%"
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM predictions
            WHERE LOWER(predicted_crop) LIKE ?
            ORDER BY id DESC
            """,
            (q,),
        ).fetchall()
    return [_row_to_dict(r) for r in rows]
 
 
def aggregate_stats() -> Dict[str, Any]:
    """Return summary stats for the Research dashboard."""
    with _connect() as conn:
        total = conn.execute(
            "SELECT COUNT(*) AS c FROM predictions"
        ).fetchone()["c"]
        crops = conn.execute(
            """
            SELECT predicted_crop AS crop, COUNT(*) AS c
            FROM predictions
            GROUP BY predicted_crop
            ORDER BY c DESC
            LIMIT 10
            """
        ).fetchall()
        recent = conn.execute(
            """
            SELECT SUBSTR(created_at, 1, 10) AS day, COUNT(*) AS c
            FROM predictions
            GROUP BY day
            ORDER BY day DESC
            LIMIT 14
            """
        ).fetchall()
    return {
        "total": int(total),
        "top_crops": [{"crop": r["crop"], "count": int(r["c"])} for r in crops],
        "by_day": list(reversed([
            {"day": r["day"], "count": int(r["c"])} for r in recent
        ])),
    }
 
 
def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a sqlite Row into a plain dict with parsed JSON."""
    d = dict(row)
    try:
        d["top3"] = json.loads(d.pop("top3_json", "[]"))
    except (TypeError, ValueError):
        d["top3"] = []
    return d