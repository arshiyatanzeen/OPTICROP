"""OptiCrop — Authentication blueprint."""

from __future__ import annotations

import functools
from typing import Any

from flask import (
    Blueprint, redirect, render_template,
    request, session, url_for,
)

import database as db

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return db.get_user_by_id(uid)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("page_dashboard"))

    error = None

    if request.method == "POST":
        email    = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "") or ""

        if not email or not password:
            error = "Email and password are required."
        else:
            user = db.get_user_by_email(email)
            if user is None or not db.check_password(user["password_hash"], password):
                error = "Invalid email or password."
            else:
                session.clear()
                session["user_id"]   = user["user_id"]
                session["user_name"] = user["name"]
                session["user_role"] = user["role"]
                next_url = request.args.get("next") or url_for("page_dashboard")
                return redirect(next_url)

    return render_template(
        "login.html",
        brand="OptiCrop",
        error=error,
        email=request.form.get("email", "") if request.method == "POST" else "",
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("page_dashboard"))

    error   = None
    success = None

    if request.method == "POST":
        name     = (request.form.get("name", "") or "").strip()
        email    = (request.form.get("email", "") or "").strip().lower()
        password = request.form.get("password", "") or ""
        confirm  = request.form.get("confirm_password", "") or ""
        role     = (request.form.get("role", "farmer") or "farmer").strip().lower()

        if not name or not email or not password:
            error = "Name, email, and password are all required."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif db.get_user_by_email(email):
            error = "An account with that email already exists."
        elif role not in ("farmer", "researcher", "agribusiness", "government"):
            error = "Please select a valid role."
        else:
            user_id = db.create_user(name, email, password, role)
            if user_id:
                success = "Account created! You can now log in."
            else:
                error = "Could not create account. Please try again."

    return render_template(
        "register.html",
        brand="OptiCrop",
        error=error,
        success=success,
        form=request.form if request.method == "POST" else {},
    )


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Step 1 of the reset flow: user submits their email and — if it's
    registered — gets a one-time reset link shown directly on this page
    (no email service involved)."""
    if session.get("user_id"):
        return redirect(url_for("page_dashboard"))

    error = None
    reset_url = None
    submitted = False

    if request.method == "POST":
        email = (request.form.get("email", "") or "").strip().lower()
        if not email:
            error = "Please enter your email address."
        else:
            user = db.get_user_by_email(email)
            if user:
                token = db.create_password_reset(user["user_id"])
                reset_url = url_for("auth.reset_password", token=token, _external=True)
            submitted = True

    return render_template(
        "forgot_password.html",
        brand="OptiCrop",
        error=error,
        reset_url=reset_url,
        submitted=submitted,
    )


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
    """Step 2 of the reset flow: user opens the link and sets a new password."""
    if session.get("user_id"):
        return redirect(url_for("page_dashboard"))

    reset_row = db.get_valid_password_reset(token)
    if reset_row is None:
        return render_template(
            "reset_password.html", brand="OptiCrop",
            token=token, invalid=True, error=None,
        )

    error = None
    if request.method == "POST":
        password = request.form.get("password", "") or ""
        confirm = request.form.get("confirm_password", "") or ""
        if len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            db.update_user_password(reset_row["user_id"], password)
            db.consume_password_reset(token)
            return redirect(url_for("auth.login"))

    return render_template(
        "reset_password.html", brand="OptiCrop",
        token=token, invalid=False, error=error,
    )