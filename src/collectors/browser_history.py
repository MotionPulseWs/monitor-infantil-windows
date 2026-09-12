"""Historial de navegacion (spec §3.2) — navegadores basados en Chromium.

Chrome, Edge, Opera/Opera GX y Brave son TODOS Chromium: mismo esquema SQLite
(tablas urls/visits/downloads) en su archivo `History`. El mismo codigo de lectura
sirve para todos; solo cambia la RUTA del perfil.

Rutas confirmadas en Windows:
  Chrome    %LOCALAPPDATA%\\Google\\Chrome\\User Data\\<perfil>\\History
  Edge      %LOCALAPPDATA%\\Microsoft\\Edge\\User Data\\<perfil>\\History
  Opera GX  %APPDATA%\\Opera Software\\Opera GX Stable\\<perfil>\\History   (Roaming!)
  Opera     %APPDATA%\\Opera Software\\Opera Stable\\<perfil>\\History      (Roaming!)
  Brave     %LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\User Data\\<perfil>\\History

<perfil> suele ser 'Default', pero puede haber 'Profile 1', 'Profile 2', ...
Se escanean todos.

IMPORTANTE: el archivo History suele estar BLOQUEADO mientras el navegador esta
abierto -> copiar a un archivo temporal antes de abrirlo con sqlite3.
"""
from __future__ import annotations

import os
from pathlib import Path

from src.collectors.domain_categories import DomainCategorizer
from src.state import StateStore

# navegador -> (variable de entorno base, ruta relativa a la carpeta CONTENEDORA de perfiles)
CHROMIUM_BROWSERS: dict[str, tuple[str, str]] = {
    "Chrome": ("LOCALAPPDATA", r"Google\Chrome\User Data"),
    "Edge": ("LOCALAPPDATA", r"Microsoft\Edge\User Data"),
    "Opera GX": ("APPDATA", r"Opera Software\Opera GX Stable"),
    "Opera": ("APPDATA", r"Opera Software\Opera Stable"),
    "Brave": ("LOCALAPPDATA", r"BraveSoftware\Brave-Browser\User Data"),
}

FIREFOX_PROFILES_GLOB = r"Mozilla\Firefox\Profiles\*\places.sqlite"


def find_history_files(env: dict[str, str] | None = None) -> list[tuple[str, str, Path]]:
    """Ubica los `History` de todos los navegadores Chromium instalados y sus perfiles.

    Devuelve una lista de (navegador, perfil, ruta_al_History).
    env: por defecto os.environ (usuario actual, para pruebas locales). En produccion
    se pasan las rutas del perfil del MENOR (resueltas via su SID), no las del proceso.
    """
    env = env or dict(os.environ)
    found: list[tuple[str, str, Path]] = []
    for browser, (var, rel) in CHROMIUM_BROWSERS.items():
        base = env.get(var)
        if not base:
            continue
        container = Path(base) / rel
        if not container.is_dir():
            continue
        for profile_dir in sorted(p for p in container.iterdir() if p.is_dir()):
            if profile_dir.name != "Default" and not profile_dir.name.startswith("Profile"):
                continue
            history = profile_dir / "History"
            if history.exists():
                found.append((browser, profile_dir.name, history))
    return found


class BrowserHistoryCollector:
    def __init__(self, state: StateStore, categorizer: DomainCategorizer, env: dict[str, str] | None = None):
        self.state = state
        self.categorizer = categorizer
        self.env = env

    @staticmethod
    def _copy_locked_db(src: Path) -> Path:
        """Copia el archivo bloqueado a un temporal y devuelve la ruta temporal."""
        # TODO: shutil.copy2 a un tempfile; devolver la ruta para abrir con sqlite3.
        #       (Confirmado que funciona incluso con el navegador abierto.)
        raise NotImplementedError

    def collect_all(self) -> None:
        """Recorre todos los navegadores/perfiles detectados y vuelca visitas y
        descargas a la BD de estado, etiquetando el navegador y categorizando dominios.
        """
        # TODO: for browser, profile, hist in find_history_files(self.env):
        #           copia = self._copy_locked_db(hist)
        #           self._read_visits(copia, browser); self._read_downloads(copia, browser)
        raise NotImplementedError

    def _read_visits(self, history_db_copy: Path, browser: str) -> None:
        # TODO: SELECT url, title, last_visit_time FROM urls JOIN visits;
        #       chrome_time_to_utc; categorizar dominio; state.add_web_visit(...).
        raise NotImplementedError

    def _read_downloads(self, history_db_copy: Path, browser: str) -> None:
        # TODO: SELECT target_path, tab_url, total_bytes, state, start_time, end_time
        #       FROM downloads; marcar sospechosos; state.add_download(...).
        raise NotImplementedError

    def collect_firefox(self) -> None:
        """Firefox (places.sqlite) — opcional segun spec ('si es facil')."""
        raise NotImplementedError
