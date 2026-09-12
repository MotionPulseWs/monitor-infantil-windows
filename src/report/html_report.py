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

__all__ = ["render_pill", "row_background", "severity", "render_row", "render_table",
           "page", "build_report"]

_PAGE_CSS = """
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color: #111827; }
  h1 { font-size: 20px; }
  h2 { font-size: 15px; margin-top: 28px; color: #374151; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }
  th { background: #f9fafb; color: #6b7280; font-weight: 600; }
  .leyenda { margin: 12px 0 4px; display: flex; gap: 8px; flex-wrap: wrap; }
  small { color: #6b7280; }
  td.wrap { word-break: break-all; max-width: 380px; }
"""


def render_row(cells: list[str], category: str | None = None) -> str:
    """Una fila <tr> con resaltado de fondo segun la categoria (si aplica)."""
    bg = row_background(category) if category else None
    style = f' style="background:{bg};"' if bg else ""
    return f"<tr{style}>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


def render_table(title: str, headers: list[str], rows_html: str) -> str:
    """Una seccion <h2> + <table> con encabezados y filas ya renderizadas."""
    ths = "".join(f"<th>{h}</th>" for h in headers)
    body = rows_html or f'<tr><td colspan="{len(headers)}"><small>sin registros</small></td></tr>'
    return f"<h2>{title}</h2>\n<table><thead><tr>{ths}</tr></thead><tbody>{body}</tbody></table>"


def page(title: str, body: str) -> str:
    """Envuelve el cuerpo en un documento HTML completo con estilos inline."""
    return (f'<!doctype html>\n<html lang="es"><head><meta charset="utf-8">'
            f"<title>{title}</title><style>{_PAGE_CSS}</style></head>\n<body>{body}</body></html>\n")


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
