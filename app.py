import os
import sqlite3
from datetime import date, datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO

from auth import ldap_check

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

# Persist the secret key across restarts without requiring manual config
_key_file = INSTANCE_DIR / "secret.key"
if not _key_file.exists():
    _key_file.write_bytes(os.urandom(32))

app = Flask(__name__)
app.secret_key = _key_file.read_bytes()

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

DB_PATH = str(INSTANCE_DIR / "incidents.db")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                occurred_on  DATE     NOT NULL,
                perpetrator  TEXT     NOT NULL,
                note         TEXT     NOT NULL,
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# ---------------------------------------------------------------------------
# Auth decorator
# ---------------------------------------------------------------------------

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Public dashboard
# ---------------------------------------------------------------------------

@app.route("/")
def dashboard():
    conn = get_db()
    incidents = conn.execute(
        "SELECT * FROM incidents ORDER BY occurred_on DESC"
    ).fetchall()
    conn.close()

    days_since = None
    if incidents:
        last_date = datetime.strptime(str(incidents[0]["occurred_on"]), "%Y-%m-%d").date()
        days_since = (date.today() - last_date).days

    return render_template("dashboard.html", incidents=incidents, days_since=days_since)


# ---------------------------------------------------------------------------
# Admin — login / logout
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if session.get("admin"):
        return redirect(url_for("admin"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        ok, reason = ldap_check(username, password)
        if ok:
            session["admin"] = True
            session["username"] = username
            return redirect(url_for("admin"))

        flash(reason, "danger")

    return render_template("login.html")


@app.route("/admin/logout")
@require_admin
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Admin — manage incidents
# ---------------------------------------------------------------------------

@app.route("/admin", methods=["GET", "POST"])
@require_admin
def admin():
    if request.method == "POST":
        occurred_on = request.form.get("occurred_on", "").strip()
        perpetrator = request.form.get("perpetrator", "").strip()
        note        = request.form.get("note", "").strip()

        errors = []
        if not occurred_on:
            errors.append("Date is required.")
        else:
            try:
                datetime.strptime(occurred_on, "%Y-%m-%d")
            except ValueError:
                errors.append("Invalid date format.")
        if not perpetrator:
            errors.append("Perpetrator is required.")
        if not note:
            errors.append("Note is required.")

        if errors:
            for e in errors:
                flash(e, "danger")
        else:
            conn = get_db()
            conn.execute(
                "INSERT INTO incidents (occurred_on, perpetrator, note) VALUES (?, ?, ?)",
                (occurred_on, perpetrator, note),
            )
            conn.commit()
            conn.close()
            # Push reload event to all dashboard clients
            socketio.emit("incident_update", namespace="/")
            flash("Incident recorded.", "success")
            return redirect(url_for("admin"))

    conn = get_db()
    incidents = conn.execute(
        "SELECT * FROM incidents ORDER BY occurred_on DESC"
    ).fetchall()
    conn.close()

    return render_template(
        "admin.html",
        incidents=incidents,
        username=session.get("username"),
        today=date.today().isoformat(),
    )


@app.route("/admin/delete/<int:incident_id>", methods=["POST"])
@require_admin
def delete_incident(incident_id: int):
    conn = get_db()
    conn.execute("DELETE FROM incidents WHERE id = ?", (incident_id,))
    conn.commit()
    conn.close()
    socketio.emit("incident_update", namespace="/")
    flash("Incident deleted.", "info")
    return redirect(url_for("admin"))


# ---------------------------------------------------------------------------
# DB init — runs on import (works with both gunicorn and direct execution)
# ---------------------------------------------------------------------------

init_db()

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
