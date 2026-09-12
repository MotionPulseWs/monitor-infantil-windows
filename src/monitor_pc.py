"""Punto de entrada del monitor (spec §7).

Corre en segundo plano mientras hay sesion iniciada:
  - Poll de procesos cada [monitoring].process_poll_seconds.
  - Observadores watchdog para descargas y papelera (tiempo casi real).
  - Cada [monitoring].report_check_seconds (30 min por defecto) evalua si toca
    consolidar y enviar el resumen del dia (o varios dias pendientes).

En produccion se lanza headless con pythonw.exe via Tarea Programada (ver
install/install_task.ps1). Para probar en desarrollo:  python src\\monitor_pc.py

Ejecutar como modulo desde la raiz del proyecto:  python -m src.monitor_pc
(o  python src\\monitor_pc.py  ajustando sys.path).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

# Permite ejecutar tanto `python -m src.monitor_pc` como `python src/monitor_pc.py`.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.state import StateStore
from src.winprofile import resolve_user_paths as _resolve_sid


def resolve_user_paths(target_user: str, target_sid: str) -> dict[str, str]:
    """Resuelve %LOCALAPPDATA%, %APPDATA% y $Recycle.Bin\\<SID> del menor (spec §8).

    Necesario porque el proceso corre como SYSTEM, no como el menor, asi que no
    basta con las variables de entorno del proceso actual. Ver src/winprofile.py.
    """
    if not target_sid:
        raise ValueError(
            "Falta [monitoring].target_sid en config.ini. Corre el instalador "
            "(install/install_task.ps1) para elegir la cuenta del menor y su SID."
        )
    env = _resolve_sid(target_sid)
    if env is None:
        raise RuntimeError(f"No se pudo resolver el perfil del SID {target_sid} (usuario {target_user}).")
    return env


def run() -> None:
    config = load_config()
    state = StateStore(config.storage.state_db)

    # TODO:
    #  1) resolve_user_paths(); instanciar collectors (procesos, historial,
    #     descargas, papelera) y arrancar observadores watchdog.
    #  2) bucle principal: poll de procesos + chequeo periodico de envio.
    #  3) al tocar envio: consolidar dias pendientes, construir HTML (+xlsx),
    #     mailer.send_report(), marcar report_log.

    try:
        while True:
            # TODO: process_collector.poll_once()
            # TODO: si toca -> maybe_send_daily_report(config, state)
            time.sleep(config.monitoring.process_poll_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        state.close()


if __name__ == "__main__":
    run()
