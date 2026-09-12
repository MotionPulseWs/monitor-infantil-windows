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


def resolve_user_paths(target_user: str, target_sid: str) -> dict[str, Path]:
    """Resuelve %LOCALAPPDATA% y $Recycle.Bin\\<SID> del menor (spec §8, punto 2).

    Necesario porque el proceso puede correr como SYSTEM, no como el menor, asi
    que no basta con las variables de entorno del proceso actual.
    """
    # TODO: construir rutas a partir de target_user / target_sid.
    raise NotImplementedError


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
