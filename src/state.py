"""Estado local persistente (spec §7).

Guarda los eventos capturados en una base SQLite local para poder reconstruir
el correo si el script se reinicia a media jornada, y para consolidar varios
dias pendientes si la PC estuvo apagada (spec §6).

Una tabla por modulo. Todas las horas se guardan en UTC (ISO 8601).
La base vive en la ruta [storage].state_db y NO se versiona (ver .gitignore).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime
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
    def add_process_event(self, name: str, pid: int, event: str, ts_utc: datetime) -> None:
        """Registra un evento de proceso ('open' | 'close') con hora UTC (spec §3.1)."""
        self.conn.execute(
            "INSERT INTO process_events (name, pid, event, ts_utc) VALUES (?, ?, ?, ?)",
            (name, pid, event, ts_utc.isoformat()),
        )
        self.conn.commit()

    def add_web_visit(self, url: str, title: str | None, domain: str, category: str,
                      visit_ts_utc: datetime, browser: str) -> None:
        """Registra una visita web categorizada (spec §3.2)."""
        self.conn.execute(
            "INSERT INTO web_visits (url, title, domain, category, visit_ts_utc, browser) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (url, title, domain, category, visit_ts_utc.isoformat(), browser),
        )
        self.conn.commit()

    def add_download(self, file_name: str, target_path: str, source_url: str,
                     size_bytes: int, state: str, suspicious: bool,
                     start_ts_utc: datetime | None, end_ts_utc: datetime | None) -> None:
        """Registra una descarga (spec §3.3)."""
        self.conn.execute(
            "INSERT INTO downloads (file_name, target_path, source_url, size_bytes, "
            "state, suspicious, start_ts_utc, end_ts_utc) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (file_name, target_path, source_url, size_bytes, state, int(suspicious),
             start_ts_utc.isoformat() if start_ts_utc else None,
             end_ts_utc.isoformat() if end_ts_utc else None),
        )
        self.conn.commit()

    # TODO: add_recycle_deletion, add_recycle_empty_event.

    # --- Lectura ---
    def fetch_process_events(self, since_utc: datetime | None = None) -> list[dict]:
        """Devuelve los eventos de proceso (opcionalmente desde since_utc), ordenados."""
        if since_utc is not None:
            cur = self.conn.execute(
                "SELECT name, pid, event, ts_utc FROM process_events "
                "WHERE ts_utc >= ? ORDER BY ts_utc",
                (since_utc.isoformat(),),
            )
        else:
            cur = self.conn.execute(
                "SELECT name, pid, event, ts_utc FROM process_events ORDER BY ts_utc"
            )
        return [
            {
                "name": r["name"],
                "pid": r["pid"],
                "event": r["event"],
                "ts_utc": datetime.fromisoformat(r["ts_utc"]),
            }
            for r in cur.fetchall()
        ]

    def fetch_web_visits(self, since_utc: datetime | None = None) -> list[dict]:
        """Visitas web (opcionalmente desde since_utc), mas recientes primero."""
        sql = ("SELECT url, title, domain, category, visit_ts_utc, browser FROM web_visits")
        params: tuple = ()
        if since_utc is not None:
            sql += " WHERE visit_ts_utc >= ?"
            params = (since_utc.isoformat(),)
        sql += " ORDER BY visit_ts_utc DESC"
        return [
            {
                "url": r["url"], "title": r["title"], "domain": r["domain"],
                "category": r["category"], "browser": r["browser"],
                "visit_ts_utc": datetime.fromisoformat(r["visit_ts_utc"]),
            }
            for r in self.conn.execute(sql, params).fetchall()
        ]

    def fetch_downloads(self, since_utc: datetime | None = None) -> list[dict]:
        """Descargas (opcionalmente desde since_utc por start_ts_utc), recientes primero."""
        sql = ("SELECT file_name, target_path, source_url, size_bytes, state, "
               "suspicious, start_ts_utc, end_ts_utc FROM downloads")
        params: tuple = ()
        if since_utc is not None:
            sql += " WHERE start_ts_utc >= ?"
            params = (since_utc.isoformat(),)
        sql += " ORDER BY start_ts_utc DESC"
        rows = []
        for r in self.conn.execute(sql, params).fetchall():
            rows.append({
                "file_name": r["file_name"], "target_path": r["target_path"],
                "source_url": r["source_url"], "size_bytes": r["size_bytes"],
                "state": r["state"], "suspicious": bool(r["suspicious"]),
                "start_ts_utc": datetime.fromisoformat(r["start_ts_utc"]) if r["start_ts_utc"] else None,
                "end_ts_utc": datetime.fromisoformat(r["end_ts_utc"]) if r["end_ts_utc"] else None,
            })
        return rows

    # --- Lectura para el reporte ---
    # TODO: fetch_* por rango de fechas (una jornada o varias pendientes).
    # TODO: pending_report_dates() -> list[str]  (fechas con datos aun no enviadas).
    # TODO: mark_report_sent(report_date).
    # Nota: la correlacion descarga->borrado se arma en report/correlate.py cruzando
    #       downloads y recycle_deletions por nombre de archivo (basename).

    def close(self) -> None:
        self.conn.close()
