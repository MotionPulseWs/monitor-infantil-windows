"""Historial de navegacion (spec §3.2).

Lee el historial de navegadores Chromium (Chrome, Edge; mismo esquema SQLite en
%LOCALAPPDATA%\\...\\User Data\\Default\\History) y, si aplica, Firefox
(places.sqlite). Extrae URL, titulo y fecha/hora de visita, y categoriza el
dominio con DomainCategorizer.

IMPORTANTE: el archivo History suele estar BLOQUEADO mientras el navegador esta
abierto -> copiar a un archivo temporal antes de abrirlo con sqlite3.
"""
from __future__ import annotations

from pathlib import Path

from src.collectors.domain_categories import DomainCategorizer
from src.state import StateStore

# Rutas relativas al perfil del menor (%LOCALAPPDATA%). Se resuelven con el SID/target_user.
CHROMIUM_HISTORY_PATHS = {
    "chrome": r"Google\Chrome\User Data\Default\History",
    "edge": r"Microsoft\Edge\User Data\Default\History",
}
FIREFOX_PROFILES_GLOB = r"Mozilla\Firefox\Profiles\*\places.sqlite"


class BrowserHistoryCollector:
    def __init__(self, state: StateStore, categorizer: DomainCategorizer, user_local_appdata: Path):
        self.state = state
        self.categorizer = categorizer
        self.local_appdata = user_local_appdata

    @staticmethod
    def _copy_locked_db(src: Path) -> Path:
        """Copia el archivo bloqueado a un temporal y devuelve la ruta temporal."""
        # TODO: shutil.copy2 a un tempfile; devolver la ruta para abrir con sqlite3.
        raise NotImplementedError

    def collect_chromium(self, browser: str) -> None:
        """Lee la tabla 'urls'/'visits' del History de un navegador Chromium."""
        # TODO: copiar DB bloqueada; SELECT url, title, last_visit_time;
        #       convertir chrome_time_to_utc; categorizar dominio; guardar en state.
        raise NotImplementedError

    def collect_firefox(self) -> None:
        """Lee moz_places/moz_historyvisits de Firefox (si esta instalado)."""
        # TODO: opcional segun spec ("si es facil").
        raise NotImplementedError
