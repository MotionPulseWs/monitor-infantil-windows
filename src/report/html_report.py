"""Reporte HTML (spec §5).

Una tabla por modulo: tiempo por app, navegacion categorizada, descargas,
papelera-eliminados, papelera-vaciada. Pensado para leerse desde el celular
(cuerpo del correo, sin depender de abrir adjunto).

Marcado visual (ver src/categories.py, fuente unica de verdad):
  - Cada visita/archivo/app lleva un BADGE tipo "pill" (insignia redondeada) segun
    su categoria: 🔞 adultos (rojo), 🎮 juegos (naranja), 🔍 desconocido (violeta,
    "revisar"), • normal (gris). NO se resalta solo la fila: siempre va el badge.
  - Ademas la fila se resalta con un fondo suave acorde a la categoria (adulto,
    juegos, desconocido, sospechoso y "papelera vaciada"); 'normal' no se resalta.

Todas las horas se muestran ya convertidas a America/Lima (ver utils.timeutil).
"""
from __future__ import annotations

# render_pill / row_background / severity viven en el modulo central de categorias.
from src.categories import render_pill, row_background, severity  # re-export para el reporte

__all__ = ["render_pill", "row_background", "severity", "build_report"]


def build_report(sections_by_date: dict) -> str:
    """Construye el HTML completo del correo.

    sections_by_date: si hay varios dias pendientes (PC apagada), se agrupa por
    fecha con una seccion por dia (spec §6). Devuelve el string HTML.

    Por cada fecha, una tabla por modulo. En cada fila con categoria/flag:
      - anteponer render_pill(categoria) en su celda de estado;
      - aplicar row_background(categoria) como fondo de la fila (si no es None);
      - opcionalmente ordenar por severity() para que lo mas peligroso vaya arriba.
    """
    # TODO: armar las tablas por modulo usando render_pill()/row_background().
    #       Para un ejemplo funcional del marcado, ver tools/preview_report.py.
    raise NotImplementedError
