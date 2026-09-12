"""Descargas de archivos (spec §3.3).

Fuente primaria: la tabla 'downloads' DENTRO del mismo archivo History de
Chrome/Edge (no es un archivo aparte): nombre, ruta destino, URL origen, tamano,
hora inicio/fin y estado (complete/canceled/interrupted). Registro objetivo de
lo descargado, independiente de lo que muestre el navegador a simple vista.

Respaldo: watchdog sobre carpetas tipicas (Descargas/Escritorio/Documentos) para
capturar archivos que lleguen por otra via.

Se marcan como SOSPECHOSOS los .apk/.exe/.zip de dominios no confiables.
Por ahora esto NO genera alerta inmediata: solo entra al resumen diario.
"""
from __future__ import annotations

from pathlib import Path

from src.state import StateStore

# Handler de watchdog para el respaldo por carpetas se define aqui o en un modulo aparte.
try:
    from watchdog.events import FileSystemEventHandler
except ImportError:  # watchdog es dependencia de terceros
    FileSystemEventHandler = object  # type: ignore


class DownloadsHistoryCollector:
    """Lee la tabla 'downloads' del History Chromium (copiando la DB bloqueada)."""

    def __init__(self, state: StateStore, suspicious_extensions: list[str]):
        self.state = state
        self.suspicious_extensions = [e.lower() for e in suspicious_extensions]

    def collect_chromium(self, history_db_copy: Path) -> None:
        # TODO: SELECT target_path, tab_url, total_bytes, state, start_time, end_time
        #       FROM downloads; marcar suspicious segun extension + dominio; guardar.
        raise NotImplementedError

    def _is_suspicious(self, file_name: str, source_domain: str) -> bool:
        # TODO: extension en suspicious_extensions Y dominio no confiable.
        raise NotImplementedError


class DownloadFolderWatcher(FileSystemEventHandler):
    """Respaldo en tiempo real sobre Descargas/Escritorio/Documentos (spec §3.3)."""

    def __init__(self, state: StateStore):
        self.state = state

    def on_created(self, event) -> None:
        # TODO: registrar archivo nuevo como descarga (fuente = 'filesystem').
        raise NotImplementedError
