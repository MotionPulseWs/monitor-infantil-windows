"""Recoleccion de procesos y tiempo por aplicacion (spec §3.1 y §3.1.1).

Poll periodico con psutil para detectar procesos que se abren/cierran (con hora).
Emparejando apertura/cierre se calcula el TIEMPO ACUMULADO por aplicacion en el
dia (ej. "Chrome: 2h 15min", "Roblox: 3h 05min") para el reporte.

Detalle importante: el tiempo por app es la UNION de los intervalos en que la app
tuvo >=1 proceso vivo, NO la suma de cada proceso. Asi Chrome con 10 procesos
abiertos 2h cuenta 2h, no 20h.
"""
from __future__ import annotations

import ctypes
import sys
from collections import defaultdict
from ctypes import wintypes
from datetime import datetime, timezone

import psutil  # dependencia de terceros (requirements.txt)

from src.state import StateStore
from src.utils.timeutil import now_utc


def visible_window_pids() -> set[int] | None:
    """PIDs que tienen una ventana de nivel superior VISIBLE y con titulo.

    Es la mejor senal, sin dependencias extra, de "app con la que el usuario
    interactua" (vs. cientos de servicios/procesos de fondo). Solo Windows;
    devuelve None si no se puede determinar (para no filtrar de mas).
    """
    if sys.platform != "win32":
        return None
    try:
        user32 = ctypes.windll.user32
    except (AttributeError, OSError):
        return None

    pids: set[int] = set()

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _callback(hwnd, _lparam):
        if user32.IsWindowVisible(hwnd) and user32.GetWindowTextLengthW(hwnd) > 0:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value:
                pids.add(pid.value)
        return True

    user32.EnumWindows(_callback, 0)
    return pids

# Nombres "amigables" para las apps mas comunes (exe en minuscula -> etiqueta).
# Ampliable; lo que no este aqui se muestra con el nombre del exe sin ".exe".
FRIENDLY_NAMES = {
    "winword.exe": "Word", "excel.exe": "Excel", "powerpnt.exe": "PowerPoint",
    "outlook.exe": "Outlook", "onenote.exe": "OneNote",
    "chrome.exe": "Chrome", "msedge.exe": "Edge", "firefox.exe": "Firefox",
    "brave.exe": "Brave", "opera.exe": "Opera",
    "robloxplayerbeta.exe": "Roblox", "minecraft.exe": "Minecraft",
    "steam.exe": "Steam", "epicgameslauncher.exe": "Epic Games",
    "discord.exe": "Discord", "spotify.exe": "Spotify", "vlc.exe": "VLC",
    "code.exe": "VS Code", "notepad.exe": "Bloc de notas", "whatsapp.exe": "WhatsApp",
    "telegram.exe": "Telegram", "zoom.exe": "Zoom",
}

# Procesos de sistema / segundo plano que NO son "apps que el menor usa".
# Se filtran del reporte. Ampliable segun lo que aparezca de ruido.
IGNORE_NAMES = {
    "", "system", "system idle process", "registry", "memory compression",
    "smss.exe", "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "svchost.exe", "dwm.exe", "explorer.exe", "runtimebroker.exe",
    "dllhost.exe", "conhost.exe", "taskhostw.exe", "sihost.exe", "ctfmon.exe",
    "searchapp.exe", "searchhost.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "textinputhost.exe", "applicationframehost.exe",
    "systemsettings.exe", "backgroundtaskhost.exe", "smartscreen.exe",
    "securityhealthsystray.exe", "securityhealthservice.exe", "audiodg.exe",
    "fontdrvhost.exe", "spoolsv.exe", "wmiprvse.exe", "taskmgr.exe",
    "python.exe", "pythonw.exe", "py.exe",  # el propio monitor / herramientas
    "msmpeng.exe", "nissrv.exe", "wudfhost.exe", "lockapp.exe", "widgets.exe",
}


def friendly_name(proc_name: str | None) -> str:
    """Convierte 'WINWORD.EXE' -> 'Word', o 'algo.exe' -> 'algo'."""
    if not proc_name:
        return "desconocido"
    low = proc_name.lower()
    if low in FRIENDLY_NAMES:
        return FRIENDLY_NAMES[low]
    return proc_name[:-4] if low.endswith(".exe") else proc_name


def accumulate_time_per_app(intervals: list[tuple[str, datetime, datetime]]) -> dict[str, float]:
    """De una lista de (app, inicio_utc, fin_utc) devuelve {app: segundos totales}.

    Usa la UNION de intervalos por app (procesos solapados no se suman dos veces).
    Devuelto ordenado de mayor a menor tiempo.
    """
    by_app: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
    for app, start, end in intervals:
        if start and end and end >= start:
            by_app[app].append((start, end))

    totals: dict[str, float] = {}
    for app, ivs in by_app.items():
        ivs.sort(key=lambda x: x[0])
        merged: list[list] = []
        for start, end in ivs:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], end)
            else:
                merged.append([start, end])
        totals[app] = sum((end - start).total_seconds() for start, end in merged)

    return dict(sorted(totals.items(), key=lambda kv: kv[1], reverse=True))


def intervals_from_events(events: list[dict], end_utc: datetime | None = None) -> list[tuple[str, datetime, datetime]]:
    """Convierte eventos open/close (de la BD de estado) en intervalos por proceso.

    Empareja cada 'close' con el 'open' del mismo pid. Un proceso aun abierto al
    final del rango se cierra en end_utc (por defecto, ahora).
    """
    end_utc = end_utc or now_utc()
    open_map: dict[int, tuple[str, datetime]] = {}
    intervals: list[tuple[str, datetime, datetime]] = []
    for ev in sorted(events, key=lambda e: e["ts_utc"]):
        pid, app, ts, kind = ev["pid"], ev["name"], ev["ts_utc"], ev["event"]
        if kind == "open":
            open_map[pid] = (app, ts)
        elif kind == "close" and pid in open_map:
            app_name, open_ts = open_map.pop(pid)
            intervals.append((app_name, open_ts, ts))
    for app_name, open_ts in open_map.values():
        intervals.append((app_name, open_ts, end_utc))
    return intervals


class ProcessCollector:
    def __init__(
        self,
        state: StateStore | None = None,
        poll_seconds: int = 15,
        target_username: str | None = None,
        ignore_names: set[str] | None = None,
        gui_only: bool = True,
    ):
        self.state = state
        self.poll_seconds = poll_seconds
        self.target_username = target_username.lower() if target_username else None
        self.ignore = ignore_names if ignore_names is not None else IGNORE_NAMES
        self.gui_only = gui_only
        self._seen: dict[int, tuple[str, datetime]] = {}  # pid -> (name, create_utc)
        # PIDs que en ALGUN momento mostraron una ventana visible (se acumula, para
        # que una app que se minimiza a la bandeja siga contando mientras vive).
        self._app_pids: set[int] = set()

    def _owned_by_target(self, username: str | None) -> bool:
        if not self.target_username:
            return True  # sin filtro (modo prueba local: cuenta todo el usuario actual)
        if not username:
            return False
        return username.split("\\")[-1].lower() == self.target_username

    def _refresh_app_pids(self) -> bool:
        """Actualiza el set de PIDs con ventana. Devuelve True si el filtro por
        ventana esta activo (Windows); False si no se pudo determinar."""
        pids = visible_window_pids() if self.gui_only else None
        if pids is None:
            return False
        self._app_pids |= pids
        return True

    def _relevant(self, info: dict, gui_active: bool) -> bool:
        if (info.get("name") or "").lower() in self.ignore:
            return False
        if not self._owned_by_target(info.get("username")):
            return False
        if gui_active and info["pid"] not in self._app_pids:
            return False  # sin ventana visible => proceso de fondo, no una "app usada"
        return True

    def _iter_relevant(self):
        gui_active = self._refresh_app_pids()
        for proc in psutil.process_iter(["pid", "name", "username", "create_time"]):
            try:
                info = proc.info
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if self._relevant(info, gui_active):
                yield info

    def snapshot(self) -> list[tuple[str, datetime, datetime]]:
        """Apps del usuario abiertas AHORA como intervalos [create_time, ahora].

        Permite ver al instante cuanto lleva abierta cada app, sin esperar al poll.
        """
        now = now_utc()
        intervals = []
        for info in self._iter_relevant():
            create = datetime.fromtimestamp(info["create_time"], tz=timezone.utc)
            intervals.append((friendly_name(info["name"]), create, now))
        return intervals

    def poll_once(self) -> None:
        """Un ciclo del bucle continuo: registra en la BD de estado 'open' para PIDs
        nuevos (con su create_time real) y 'close' para los que desaparecieron.
        """
        if self.state is None:
            raise RuntimeError("poll_once necesita un StateStore")
        now = now_utc()
        current: dict[int, tuple[str, datetime]] = {}
        for info in self._iter_relevant():
            create = datetime.fromtimestamp(info["create_time"], tz=timezone.utc)
            current[info["pid"]] = (info["name"], create)

        for pid, (name, create) in current.items():
            if pid not in self._seen:
                self.state.add_process_event(friendly_name(name), pid, "open", create)
        for pid, (name, _create) in self._seen.items():
            if pid not in current:
                self.state.add_process_event(friendly_name(name), pid, "close", now)
        self._seen = current
