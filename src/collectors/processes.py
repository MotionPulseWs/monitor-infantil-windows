"""Recoleccion de procesos y tiempo por aplicacion (spec §3.1 y §3.1.1).

Poll periodico con psutil para detectar procesos que se abren/cierran (con hora).
Emparejando apertura/cierre se calcula el TIEMPO ACUMULADO por aplicacion en el
dia (ej. "Chrome: 2h 15min", "Roblox: 3h 05min") para el reporte.
"""
from __future__ import annotations

from src.state import StateStore


class ProcessCollector:
    def __init__(self, state: StateStore, poll_seconds: int = 15):
        self.state = state
        self.poll_seconds = poll_seconds
        self._seen_pids: dict[int, str] = {}

    def poll_once(self) -> None:
        """Un ciclo de muestreo: compara el set de PIDs actual con el anterior,
        registra 'open' para los nuevos y 'close' para los que desaparecieron.
        """
        # TODO: usar psutil.process_iter(['pid', 'name', 'create_time']) y
        #       diffear contra self._seen_pids; escribir eventos con ts UTC.
        raise NotImplementedError

    @staticmethod
    def accumulate_time_per_app(events: list[dict]) -> dict[str, float]:
        """A partir de los pares open/close del dia, devuelve segundos totales por app.

        Un proceso aun abierto al cierre de la jornada se cuenta hasta 'ahora'.
        """
        # TODO: emparejar open/close por nombre de app y sumar duraciones.
        raise NotImplementedError
