"""Prueba LOCAL del modulo de procesos (spec §3.1), sin instalar nada ni SMTP.

Dos modos:
  1) Snapshot (por defecto): muestra las apps del usuario abiertas AHORA y cuanto
     tiempo lleva abierta cada una (usa create_time; resultado inmediato).
        python tools/test_processes.py

  2) Watch: corre el poll continuo N segundos contra una BD temporal y luego
     calcula el tiempo por app a partir de los eventos open/close capturados.
     Abre/cierra alguna app durante la prueba para verlo en accion.
        python tools/test_processes.py --watch 30

Nota: se corre como el usuario ACTUAL (sin filtro de cuenta). En produccion el
monitor filtra por la cuenta del menor (target_username).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.processes import (  # noqa: E402
    ProcessCollector, accumulate_time_per_app, intervals_from_events,
)
from src.state import StateStore  # noqa: E402
from src.utils.timeutil import format_duration  # noqa: E402


def _print_table(totals: dict[str, float]) -> None:
    if not totals:
        print("  (ninguna app relevante detectada)")
        return
    width = max(len(app) for app in totals)
    print(f"  {'APLICACION'.ljust(width)}   TIEMPO")
    print(f"  {'-' * width}   ------")
    for app, seconds in totals.items():
        print(f"  {app.ljust(width)}   {format_duration(seconds)}")


def run_snapshot() -> None:
    collector = ProcessCollector()
    intervals = collector.snapshot()
    totals = accumulate_time_per_app(intervals)
    print(f"\nApps abiertas ahora (por el usuario actual): {len(intervals)} procesos relevantes")
    print("Tiempo que lleva abierta cada app:\n")
    _print_table(totals)


def run_watch(seconds: int, interval: int = 3) -> None:
    tmp_db = Path(tempfile.mkdtemp(prefix="monitor_test_")) / "state.db"
    state = StateStore(tmp_db)
    collector = ProcessCollector(state=state, poll_seconds=interval)
    print(f"\nObservando {seconds}s (poll cada {interval}s). "
          f"Abre o cierra alguna app para verlo...\n")
    elapsed = 0
    while elapsed <= seconds:
        collector.poll_once()
        opens = sum(1 for e in state.fetch_process_events() if e["event"] == "open")
        closes = sum(1 for e in state.fetch_process_events() if e["event"] == "close")
        print(f"  t={elapsed:>3}s  eventos: {opens} open / {closes} close", end="\r", flush=True)
        time.sleep(interval)
        elapsed += interval

    events = state.fetch_process_events()
    totals = accumulate_time_per_app(intervals_from_events(events))
    print("\n\nTiempo por app durante la ventana observada:\n")
    _print_table(totals)
    print(f"\n(BD temporal de prueba: {tmp_db})")
    state.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Prueba local del modulo de procesos.")
    ap.add_argument("--watch", type=int, metavar="SEGUNDOS",
                    help="corre el poll continuo N segundos en vez del snapshot")
    args = ap.parse_args()
    if args.watch:
        run_watch(args.watch)
    else:
        run_snapshot()


if __name__ == "__main__":
    main()
