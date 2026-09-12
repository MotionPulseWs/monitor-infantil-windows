"""Carga de configuracion desde config.ini (spec §6).

Las credenciales SMTP y demas ajustes viven en config.ini (NO versionado).
Usa config.example.ini como plantilla.
"""
from __future__ import annotations

import configparser
from dataclasses import dataclass, field
from pathlib import Path

# Raiz del proyecto = carpeta que contiene a src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.ini"


@dataclass
class SmtpConfig:
    host: str
    port: int
    use_tls: bool
    user: str
    password: str


@dataclass
class ReportConfig:
    recipients: list[str]
    sender_name: str
    attach_excel: bool
    display_timezone: str
    daily_send_time: str


@dataclass
class MonitoringConfig:
    target_user: str
    target_sid: str
    process_poll_seconds: int
    report_check_seconds: int
    watch_folders: list[str]


@dataclass
class CategorizationConfig:
    adult_hostlist: str
    games_hostlist: str
    known_sites_hostlist: str
    suspicious_extensions: list[str]


@dataclass
class StorageConfig:
    state_db: str
    reports_dir: str


@dataclass
class AppConfig:
    smtp: SmtpConfig
    report: ReportConfig
    monitoring: MonitoringConfig
    categorization: CategorizationConfig
    storage: StorageConfig


def _split_list(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_config(path: str | Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    """Lee config.ini y devuelve un AppConfig tipado.

    Lanza FileNotFoundError si no existe (recordar copiar config.example.ini).
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontro {path}. Copia config.example.ini a config.ini y complétalo."
        )

    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")

    return AppConfig(
        smtp=SmtpConfig(
            host=parser.get("smtp", "host"),
            port=parser.getint("smtp", "port"),
            use_tls=parser.getboolean("smtp", "use_tls", fallback=True),
            user=parser.get("smtp", "user"),
            password=parser.get("smtp", "password"),
        ),
        report=ReportConfig(
            recipients=_split_list(parser.get("report", "recipients")),
            sender_name=parser.get("report", "sender_name", fallback="Reporte de actividad"),
            attach_excel=parser.getboolean("report", "attach_excel", fallback=True),
            display_timezone=parser.get("report", "display_timezone", fallback="America/Lima"),
            daily_send_time=parser.get("report", "daily_send_time", fallback="21:00"),
        ),
        monitoring=MonitoringConfig(
            target_user=parser.get("monitoring", "target_user", fallback=""),
            target_sid=parser.get("monitoring", "target_sid", fallback=""),
            process_poll_seconds=parser.getint("monitoring", "process_poll_seconds", fallback=15),
            report_check_seconds=parser.getint("monitoring", "report_check_seconds", fallback=1800),
            watch_folders=_split_list(
                parser.get("monitoring", "watch_folders", fallback="Downloads, Desktop, Documents")
            ),
        ),
        categorization=CategorizationConfig(
            adult_hostlist=parser.get("categorization", "adult_hostlist", fallback=""),
            games_hostlist=parser.get("categorization", "games_hostlist", fallback=""),
            known_sites_hostlist=parser.get(
                "categorization", "known_sites_hostlist", fallback="data/known_sites.txt"
            ),
            suspicious_extensions=_split_list(
                parser.get("categorization", "suspicious_extensions", fallback=".apk, .exe, .zip")
            ),
        ),
        storage=StorageConfig(
            state_db=parser.get("storage", "state_db", fallback="state/monitor_state.db"),
            reports_dir=parser.get("storage", "reports_dir", fallback="reports"),
        ),
    )
