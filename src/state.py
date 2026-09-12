"""Estado local persistente (spec §7).

Guarda los eventos capturados en una base SQLite local para poder reconstruir
el correo si el script se reinicia a media jornada, y para consolidar varios
dias pendientes si la PC estuvo apagada (spec §6).

Una tabla por modulo. Todas las horas se guardan en UTC (ISO 8601).
La base vive en la ruta [storage].state_db y NO se versiona (ver .gitignore).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS process_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    pid           INTEGER,
    event         TEXT NOT NULL,          -- 'open' | 'close'
    ts_utc        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS web_visits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    url           TEXT NOT NULL,
    title         TEXT,
    domain        TEXT,
    category      TEXT,                   -- juegos | adulto | dudoso | normal
    visit_ts_utc  TEXT NOT NULL,
    browser       TEXT
);

CREATE TABLE IF NOT EXISTS downloads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    file_name     TEXT,
    target_path   TEXT,
    source_url    TEXT,
    size_bytes    INTEGER,
    state         TEXT,                   -- complete | canceled | interrupted
    suspicious    INTEGER DEFAULT 0,
    start_ts_utc  TEXT,
    end_ts_utc    TEXT
);

CREATE TABLE IF NOT EXISTS recycle_deletions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    original_path  TEXT,
    size_bytes     INTEGER,
    deleted_ts_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recycle_empty_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_ts_utc TEXT NOT NULL,
    files_removed  INTEGER
);

-- Marca la ultima jornada ya enviada por correo, para no reenviar.
CREATE TABLE IF NOT EXISTS report_log (
    report_date   TEXT PRIMARY KEY,       -- fecha local (America/Lima) YYYY-MM-DD
    sent_ts_utc   TEXT NOT NULL
);
"""


class StateStore:
    """Envoltura fina sobre SQLite. Un StateStore por ejecucion del monitor."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # --- Escritura (cada collector llama a lo suyo) ---
    # TODO: add_process_event, add_web_visit, add_download,
    #       add_recycle_deletion, add_recycle_empty_event.

    # --- Lectura para el reporte ---
    # TODO: fetch_* por rango de fechas (una jornada o varias pendientes).
    # TODO: pending_report_dates() -> list[str]  (fechas con datos aun no enviadas).
    # TODO: mark_report_sent(report_date).
    # Nota: la correlacion descarga->borrado se arma en report/correlate.py cruzando
    #       downloads y recycle_deletions por nombre de archivo (basename).

    def close(self) -> None:
        self.conn.close()
