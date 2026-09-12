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
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse

from src.categories import NORMAL
from src.collectors.domain_categories import DomainCategorizer
from src.state import StateStore
from src.utils.timeutil import chrome_time_to_utc, utc_to_chrome_time

# downloads.state (Chromium) -> texto legible
_DOWNLOAD_STATE = {0: "en progreso", 1: "completo", 2: "cancelado", 3: "interrumpido", 4: "interrumpido"}


def domain_of(url: str) -> str:
    """Extrae el dominio (host) de una URL, sin usuario ni puerto ni 'www.'."""
    try:
        host = urlparse(url).netloc.lower().split("@")[-1].split(":")[0]
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host

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
    def __init__(
        self,
        state: StateStore,
        categorizer: DomainCategorizer,
        env: dict[str, str] | None = None,
        suspicious_extensions: tuple[str, ...] = (".apk", ".exe", ".zip"),
    ):
        self.state = state
        self.categorizer = categorizer
        self.env = env
        self.suspicious_extensions = tuple(e.lower() for e in suspicious_extensions)

    @staticmethod
    def _copy_locked_db(src: Path) -> Path:
        """Copia el History (bloqueado si el navegador esta abierto) + sus sidecars
        -wal/-shm a un directorio temporal y devuelve la ruta de la copia.
        """
        tmpdir = Path(tempfile.mkdtemp(prefix="monitor_hist_"))
        dst = tmpdir / "History"
        shutil.copy2(src, dst)
        for suffix in ("-wal", "-shm"):
            sidecar = src.with_name(src.name + suffix)
            if sidecar.exists():
                shutil.copy2(sidecar, tmpdir / (dst.name + suffix))
        return dst

    def collect_all(self, since_utc: datetime | None = None) -> list[dict]:
        """Recorre navegadores/perfiles detectados y vuelca visitas + descargas a la
        BD de estado. Devuelve un resumen por navegador (para logs, sin URLs).
        """
        summary = []
        for browser, profile, history in find_history_files(self.env):
            try:
                copy = self._copy_locked_db(history)
            except OSError:
                continue
            try:
                visits = self._read_visits(copy, browser, since_utc)
                downloads = self._read_downloads(copy, browser, since_utc)
                summary.append({"browser": browser, "profile": profile,
                                "visits": visits, "downloads": downloads})
            finally:
                shutil.rmtree(copy.parent, ignore_errors=True)
        return summary

    def _read_visits(self, history_db_copy: Path, browser: str, since_utc: datetime | None) -> int:
        sql = ("SELECT urls.url, urls.title, visits.visit_time "
               "FROM visits JOIN urls ON urls.id = visits.url")
        params: tuple = ()
        if since_utc is not None:
            sql += " WHERE visits.visit_time >= ?"
            params = (utc_to_chrome_time(since_utc),)
        conn = sqlite3.connect(history_db_copy)
        count = 0
        try:
            for url, title, visit_time in conn.execute(sql, params):
                if not url:
                    continue
                domain = domain_of(url)
                category = self.categorizer.categorize(domain) if domain else "desconocido"
                self.state.add_web_visit(url, title, domain, category,
                                         chrome_time_to_utc(visit_time), browser)
                count += 1
        finally:
            conn.close()
        return count

    def _read_downloads(self, history_db_copy: Path, browser: str, since_utc: datetime | None) -> int:
        sql = ("SELECT target_path, tab_url, referrer, total_bytes, received_bytes, "
               "state, start_time, end_time FROM downloads")
        params: tuple = ()
        if since_utc is not None:
            sql += " WHERE start_time >= ?"
            params = (utc_to_chrome_time(since_utc),)
        conn = sqlite3.connect(history_db_copy)
        count = 0
        try:
            for row in conn.execute(sql, params):
                target_path, tab_url, referrer, total, received, state, start, end = row
                source_url = tab_url or referrer or ""
                file_name = PureWindowsPath(target_path).name if target_path else ""
                self.state.add_download(
                    file_name=file_name,
                    target_path=target_path or "",
                    source_url=source_url,
                    size_bytes=int(total or received or 0),
                    state=_DOWNLOAD_STATE.get(state, "desconocido"),
                    suspicious=self._is_suspicious(file_name, source_url),
                    start_ts_utc=chrome_time_to_utc(start) if start else None,
                    end_ts_utc=chrome_time_to_utc(end) if end else None,
                )
                count += 1
        finally:
            conn.close()
        return count

    def _is_suspicious(self, file_name: str, source_url: str) -> bool:
        """Sospechoso: extension .apk/.exe/.zip Y origen NO confiable (no 'normal')."""
        if not file_name.lower().endswith(self.suspicious_extensions):
            return False
        domain = domain_of(source_url)
        if not domain:
            return True  # sin origen conocido + extension riesgosa
        return self.categorizer.categorize(domain) != NORMAL

    def collect_firefox(self) -> None:
        """Firefox (places.sqlite) — opcional segun spec ('si es facil')."""
        raise NotImplementedError
