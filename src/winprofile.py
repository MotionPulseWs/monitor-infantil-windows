"""Resolucion del perfil de un usuario de Windows a partir de su SID (spec §8).

CLAVE: el monitor corre como SYSTEM, no como el menor. Por eso NO puede usar sus
propias variables %APPDATA% / %LOCALAPPDATA% (apuntarian al perfil de SYSTEM).
Las rutas del menor se derivan de su SID, que el instalador ya elige:

  HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ProfileList\\<SID>
      -> ProfileImagePath  (ej. C:\\Users\\menor)

De la carpeta de perfil se derivan:
  %LOCALAPPDATA% = <perfil>\\AppData\\Local
  %APPDATA%      = <perfil>\\AppData\\Roaming
  Papelera       = C:\\$Recycle.Bin\\<SID>
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_PROFILE_LIST = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList"


def profile_root_for_sid(sid: str) -> Path | None:
    """Carpeta de perfil del usuario (ej. C:\\Users\\menor) segun su SID, o None."""
    if sys.platform != "win32":
        return None
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{_PROFILE_LIST}\\{sid}") as key:
            raw, _ = winreg.QueryValueEx(key, "ProfileImagePath")
    except OSError:
        return None
    # ProfileImagePath puede ser REG_EXPAND_SZ (ej. %SystemDrive%\Users\menor).
    return Path(os.path.expandvars(raw))


def env_for_profile_root(profile_root: Path) -> dict[str, str]:
    """Construye el 'env' con LOCALAPPDATA/APPDATA/USERPROFILE de ese perfil."""
    return {
        "USERPROFILE": str(profile_root),
        "LOCALAPPDATA": str(profile_root / "AppData" / "Local"),
        "APPDATA": str(profile_root / "AppData" / "Roaming"),
    }


def recycle_bin_for_sid(sid: str, system_drive: str | None = None) -> Path:
    """Ruta de la papelera del usuario: <SystemDrive>\\$Recycle.Bin\\<SID> (spec §3.4)."""
    drive = system_drive or os.environ.get("SystemDrive", "C:")
    return Path(f"{drive}\\$Recycle.Bin") / sid


def resolve_user_paths(target_sid: str) -> dict[str, str] | None:
    """Devuelve {USERPROFILE, LOCALAPPDATA, APPDATA, RECYCLE_BIN} del menor, o None
    si no se pudo resolver el SID.
    """
    root = profile_root_for_sid(target_sid)
    if root is None:
        return None
    env = env_for_profile_root(root)
    env["RECYCLE_BIN"] = str(recycle_bin_for_sid(target_sid))
    return env
