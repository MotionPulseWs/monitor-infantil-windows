"""Manejo de tiempo (spec §4).

Regla del proyecto: TODAS las marcas de tiempo se guardan internamente en UTC
(timezone-aware). Solo se convierten a la zona local (America/Lima, UTC-5 fijo,
sin horario de verano) al momento de RENDERIZAR el reporte.
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Zona de visualizacion por defecto. Configurable via [report].display_timezone.
LIMA = ZoneInfo("America/Lima")


def now_utc() -> datetime:
    """Instante actual en UTC (aware)."""
    return datetime.now(timezone.utc)


def to_display(dt: datetime, tz: ZoneInfo = LIMA) -> datetime:
    """Convierte un datetime (asume UTC si es naive) a la zona de visualizacion."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz)


def format_local(dt: datetime, tz: ZoneInfo = LIMA, fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Formatea un datetime UTC en hora local para mostrar en el reporte."""
    return to_display(dt, tz).strftime(fmt)


def format_duration(seconds: float) -> str:
    """Segundos -> texto legible para el reporte: '3h 05min', '40min', '25s'."""
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}min"
    if minutes:
        return f"{minutes}min"
    return f"{secs}s"


def filetime_to_utc(filetime: int) -> datetime:
    """Convierte un Windows FILETIME (100-ns desde 1601-01-01) a datetime UTC.

    Usado al parsear la fecha de eliminacion de los archivos $I de la papelera
    (spec §3.4).
    """
    # 11644473600 s entre 1601-01-01 y 1970-01-01; FILETIME esta en unidades de 100 ns.
    unix_seconds = filetime / 10_000_000 - 11644473600
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def chrome_time_to_utc(chrome_timestamp: int) -> datetime:
    """Convierte un timestamp WebKit/Chrome (microsegundos desde 1601-01-01) a UTC.

    Chrome/Edge guardan las horas de visita y descargas en este formato dentro
    del archivo History (spec §3.2 / §3.3).
    """
    unix_seconds = chrome_timestamp / 1_000_000 - 11644473600
    return datetime.fromtimestamp(unix_seconds, tz=timezone.utc)


def utc_to_chrome_time(dt: datetime) -> int:
    """Inverso de chrome_time_to_utc: datetime UTC -> timestamp Chrome (microsegundos).

    Util para filtrar por fecha directamente en la consulta SQL del History.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int((dt.timestamp() + 11644473600) * 1_000_000)
