"""Correlacion descarga -> eliminacion (idea del usuario).

Objetivo: para cada archivo que llega a la papelera, ver si fue descargado el
mismo dia, y cuanto tiempo despues se borro. Asi el reporte puede decir, p.ej.:
"tarea.pdf: descargada 18:10, enviada a la papelera 18:20 (10 min despues)",
dejando registro de que el propio usuario la borro (no un tercero).

El emparejamiento es a nivel de datos: se cruza recycle_deletions con downloads
por NOMBRE de archivo (basename), tomando la descarga mas reciente ANTERIOR al
borrado. Funciona para archivos borrados desde cualquier ruta, no solo Descargas.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import PureWindowsPath


def _basename(path: str) -> str:
    return PureWindowsPath(path).name.lower()


def match_deletion_to_download(
    deleted_path: str,
    deleted_ts_utc: datetime,
    downloads: list[dict],
) -> dict | None:
    """Devuelve la descarga que corresponde al archivo eliminado, o None.

    downloads: filas con al menos 'file_name' (o 'target_path') y 'start_ts_utc'.
    Se elige la descarga con el mismo basename cuya hora sea la mas cercana ANTES
    del borrado. Si el archivo no fue descargado ese dia, devuelve None.
    """
    target = _basename(deleted_path)
    best: dict | None = None
    best_start: datetime | None = None
    for d in downloads:
        name = d.get("file_name") or _basename(d.get("target_path", ""))
        if not name or name.lower() != target:
            continue
        start = d.get("start_ts_utc")
        if start is None or start > deleted_ts_utc:
            continue
        if best_start is None or start > best_start:
            best, best_start = d, start
    return best


def format_gap(download_ts_utc: datetime, deleted_ts_utc: datetime) -> str:
    """Texto legible del tiempo entre descarga y borrado (ej. '10 min despues')."""
    delta: timedelta = deleted_ts_utc - download_ts_utc
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "menos de 1 min despues"
    if minutes < 60:
        return f"{minutes} min despues"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins:02d}min despues" if mins else f"{hours}h despues"
