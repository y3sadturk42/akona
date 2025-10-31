import sqlite3
from typing import Any, Dict, Optional

import click
from flask import current_app, g
from werkzeug.security import generate_password_hash


SECTION_NAMES = [
    "Yağmurlama Bölümü",
    "Yuvarlak Damlama Bölümü",
    "Yassı Damlama Bölümü",
    "Granür Bölümü",
    "Enjeksiyon Bölümü",
    "Mandal Takma Bölümü",
    "Perçin Bölümü",
]

RAIN_MACHINES = ["L1", "L2", "L3"]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_: Optional[BaseException] = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            section_id INTEGER NOT NULL,
            FOREIGN KEY(section_id) REFERENCES sections(id),
            UNIQUE(name, section_id)
        );

        CREATE TABLE IF NOT EXISTS production_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_date TEXT NOT NULL,
            shift_number INTEGER NOT NULL CHECK(shift_number BETWEEN 1 AND 3),
            section_id INTEGER NOT NULL,
            machine_id INTEGER NOT NULL,
            diameter_mm INTEGER NOT NULL,
            produced_length REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(section_id) REFERENCES sections(id),
            FOREIGN KEY(machine_id) REFERENCES machines(id)
        );
        """
    )
    seed_reference_data(db)


def seed_reference_data(db: sqlite3.Connection) -> None:
    for name in SECTION_NAMES:
        db.execute(
            "INSERT OR IGNORE INTO sections (name) VALUES (?)",
            (name,),
        )

    section_lookup: Dict[str, int] = {}
    for row in db.execute("SELECT id, name FROM sections"):
        section_lookup[row["name"]] = row["id"]

    rain_section_id = section_lookup.get("Yağmurlama Bölümü")
    if rain_section_id is not None:
        for machine_name in RAIN_MACHINES:
            db.execute(
                "INSERT OR IGNORE INTO machines (name, section_id) VALUES (?, ?)",
                (machine_name, rain_section_id),
            )

    db.commit()

    ensure_default_user(db)


def ensure_default_user(db: sqlite3.Connection) -> None:
    user = db.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if user is None:
        password_hash = generate_password_hash("admin123")
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            ("admin", password_hash),
        )
        db.commit()


def init_app(app: Any) -> None:
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Initialize the database and seed reference data."""
        init_db()
        click.echo("Initialized the database.")
