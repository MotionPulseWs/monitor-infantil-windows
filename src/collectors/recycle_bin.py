"""Papelera de reciclaje: eliminaciones y vaciado (spec §3.4 y §3.5).

Cada archivo enviado a la papelera crea un par oculto en
C:\\$Recycle.Bin\\<SID-del-usuario>\\ :
  - $I......  -> metadatos: ruta original, tamano, fecha/hora (FILETIME) de borrado.
  - $R......  -> contenido real.

§3.4 Eliminaciones: al detectar un nuevo $I*, parsear su cabecera binaria para
     extraer ruta original, tamano y hora de eliminacion. Formato publico:

     Windows 10/11 ($I, version 2):
       offset 0  : 8 bytes  header (version = 2)
       offset 8  : 8 bytes  tamano del archivo original (uint64 LE)
       offset 16 : 8 bytes  fecha de borrado (FILETIME LE)
       offset 24 : 4 bytes  longitud del nombre en chars (uint32 LE)
       offset 28 : ruta original en UTF-16LE terminada en NUL

§3.5 Vaciado: se detecta aparte. Mantener el set de $I* conocidos por carpeta;
     si en una ventana corta desaparecen varios de golpe (p.ej. >=2 en <2 s, o el
     conteo pasa de N>0 a 0 sin un 'restaurar' previo), se registra "papelera
     vaciada" con la hora detectada. watchdog (on_deleted) lo capta casi en vivo.
"""
from __future__ import annotations

import struct
from datetime import datetime
from pathlib import Path

from src.state import StateStore
from src.utils.timeutil import filetime_to_utc

try:
    from watchdog.events import FileSystemEventHandler
except ImportError:
    FileSystemEventHandler = object  # type: ignore


def parse_i_file(path: Path) -> dict:
    """Parsea un archivo $I y devuelve {original_path, size_bytes, deleted_ts_utc}."""
    data = path.read_bytes()
    version = struct.unpack_from("<q", data, 0)[0]
    size_bytes = struct.unpack_from("<Q", data, 8)[0]
    filetime = struct.unpack_from("<Q", data, 16)[0]
    if version >= 2:
        name_len = struct.unpack_from("<I", data, 24)[0]
        name_bytes = data[28:28 + name_len * 2]
    else:  # $I version 1 (Windows antiguos): nombre fijo de 260 chars desde offset 24
        name_bytes = data[24:24 + 260 * 2]
    original_path = name_bytes.decode("utf-16-le", errors="replace").split("\x00", 1)[0]
    return {
        "original_path": original_path,
        "size_bytes": size_bytes,
        "deleted_ts_utc": filetime_to_utc(filetime),
    }


class RecycleBinWatcher(FileSystemEventHandler):
    def __init__(self, state: StateStore, recycle_dir: Path, empty_window_seconds: float = 2.0):
        self.state = state
        self.recycle_dir = recycle_dir
        self.empty_window_seconds = empty_window_seconds
        self._known_i_files: set[str] = set()
        self._recent_deletions: list[datetime] = []

    def scan_initial(self) -> None:
        """Puebla el set inicial de $I* conocidos al arrancar."""
        # TODO: listar $I* actuales en recycle_dir.
        raise NotImplementedError

    def on_created(self, event) -> None:
        """Nuevo $I* -> parsear y registrar una eliminacion (spec §3.4)."""
        # TODO: si el basename empieza con '$I', parse_i_file + state.add_recycle_deletion.
        raise NotImplementedError

    def on_deleted(self, event) -> None:
        """Desaparicion de $I* -> alimentar la heuristica de vaciado (spec §3.5)."""
        # TODO: acumular timestamps; si >=2 en empty_window_seconds o el conteo llega a 0,
        #       registrar un evento de "papelera vaciada".
        raise NotImplementedError
