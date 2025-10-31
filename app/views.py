from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Dict, List

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from . import ACTIVE_MINUTES_PER_SHIFT, DIAMETER_SPEEDS, SHIFT_INFO
from .db import get_db


bp = Blueprint("main", __name__)


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT id, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        error = None
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Kullanıcı adı veya şifre hatalı."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash("Sisteme giriş yapıldı.", "success")
            return redirect(url_for("main.dashboard"))
        flash(error, "error")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Oturum kapatıldı.", "success")
    return redirect(url_for("main.login"))


@bp.before_app_request
def load_logged_in_user() -> None:
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
    else:
        g.user = (
            get_db()
            .execute(
                "SELECT id, username FROM users WHERE id = ?",
                (user_id,),
            )
            .fetchone()
        )


@bp.route("/", methods=("GET", "POST"))
@bp.route("/dashboard", methods=("GET", "POST"))
def dashboard():
    db = get_db()

    sections = db.execute(
        "SELECT id, name FROM sections ORDER BY id"
    ).fetchall()
    machines = db.execute(
        "SELECT id, name, section_id FROM machines ORDER BY section_id, name"
    ).fetchall()
    machines_by_section: Dict[int, List[dict]] = defaultdict(list)
    for machine in machines:
        machines_by_section[machine["section_id"]].append({
            "id": machine["id"],
            "name": machine["name"],
        })

    machines_by_section = dict(machines_by_section)
    for section in sections:
        machines_by_section.setdefault(section["id"], [])

    selected_date = request.args.get("date")
    if request.method == "POST":
        selected_date = request.form.get("entry_date") or date.today().isoformat()
        return handle_entry_submission(db, selected_date, machines_by_section)

    if not selected_date:
        selected_date = date.today().isoformat()

    entries_by_shift = fetch_entries_by_shift(db, selected_date)

    return render_template(
        "dashboard.html",
        sections=sections,
        machines_by_section=machines_by_section,
        entries_by_shift=entries_by_shift,
        selected_date=selected_date,
    )


def handle_entry_submission(db, selected_date: str, machines_by_section):
    try:
        entry_date = request.form.get("entry_date", selected_date)
        datetime.strptime(entry_date, "%Y-%m-%d")
    except (TypeError, ValueError):
        flash("Geçerli bir tarih seçiniz.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    try:
        shift_number = int(request.form.get("shift_number", "1"))
    except ValueError:
        shift_number = 1

    if shift_number not in SHIFT_INFO:
        flash("Geçersiz vardiya seçimi.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    section_id = request.form.get("section_id")
    machine_id = request.form.get("machine_id")
    diameter_value = request.form.get("diameter_mm")
    produced_length_value = request.form.get("produced_length")
    notes = request.form.get("notes", "").strip()

    try:
        section_id_int = int(section_id)
        machine_id_int = int(machine_id)
        diameter_mm = int(diameter_value)
        produced_length = float(produced_length_value)
    except (TypeError, ValueError):
        flash("Lütfen tüm alanları doğru şekilde doldurunuz.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    if diameter_mm not in DIAMETER_SPEEDS:
        flash("Tanımlanmayan bir çap seçtiniz.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    if produced_length < 0:
        flash("Üretilen miktar negatif olamaz.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    valid_machine = any(
        m["id"] == machine_id_int for m in machines_by_section.get(section_id_int, [])
    )
    if not valid_machine:
        flash("Seçilen makine ilgili bölümde bulunmuyor.", "error")
        return redirect(url_for("main.dashboard", date=selected_date))

    speed = DIAMETER_SPEEDS[diameter_mm]
    theoretical_output = speed * ACTIVE_MINUTES_PER_SHIFT
    efficiency = (produced_length / theoretical_output) * 100 if theoretical_output else 0.0

    db.execute(
        """
        INSERT INTO production_entries (
            entry_date,
            shift_number,
            section_id,
            machine_id,
            diameter_mm,
            produced_length,
            notes,
            created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            entry_date,
            shift_number,
            section_id_int,
            machine_id_int,
            diameter_mm,
            produced_length,
            notes or None,
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()

    flash(
        "Üretim kaydı başarıyla eklendi. Verimlilik: %.1f%%" % efficiency,
        "success",
    )
    return redirect(url_for("main.dashboard", date=entry_date))


def fetch_entries_by_shift(db, selected_date: str):
    rows = db.execute(
        """
        SELECT pe.*, s.name AS section_name, m.name AS machine_name
        FROM production_entries pe
        JOIN sections s ON pe.section_id = s.id
        JOIN machines m ON pe.machine_id = m.id
        WHERE pe.entry_date = ?
        ORDER BY pe.shift_number, s.id, m.name, pe.id
        """,
        (selected_date,),
    ).fetchall()

    entries_by_shift = defaultdict(list)
    for row in rows:
        speed = DIAMETER_SPEEDS.get(row["diameter_mm"], 0)
        theoretical_output = speed * ACTIVE_MINUTES_PER_SHIFT
        efficiency = (row["produced_length"] / theoretical_output * 100) if theoretical_output else 0
        entries_by_shift[row["shift_number"]].append(
            {
                "id": row["id"],
                "section_name": row["section_name"],
                "machine_name": row["machine_name"],
                "diameter_mm": row["diameter_mm"],
                "produced_length": row["produced_length"],
                "theoretical_output": theoretical_output,
                "efficiency": efficiency,
                "notes": row["notes"],
            }
        )
    return dict(entries_by_shift)
