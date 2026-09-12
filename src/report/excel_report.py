"""Reporte Excel opcional (spec §5).

Adjunto .xlsx generado con openpyxl como respaldo/archivo historico descargable:
una hoja por modulo (procesos/tiempo por app, navegacion, descargas,
papelera-eliminados, papelera-vaciada).

Se genera solo si [report].attach_excel = true.
"""
from __future__ import annotations

from pathlib import Path


def build_workbook(sections_by_date: dict, output_path: Path) -> Path:
    """Genera el .xlsx con una hoja por modulo y devuelve la ruta del archivo."""
    # TODO: openpyxl.Workbook(); una hoja por modulo; escribir filas con horas
    #       ya convertidas a America/Lima; guardar en output_path (reports_dir).
    raise NotImplementedError
