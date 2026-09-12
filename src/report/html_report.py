"""Reporte HTML (spec §5).

Una tabla por modulo: tiempo por app, navegacion categorizada, descargas,
papelera-eliminados, papelera-vaciada. Pensado para leerse desde el celular
(cuerpo del correo, sin depender de abrir adjunto).

Marcado visual:
  - Cada visita/archivo marcado lleva un BADGE tipo "pill" (insignia redondeada),
    p.ej. "⚠️ dominio de juegos" o "🔞 dominio para adultos" — NO solo resaltar
    la fila.
  - Filas resaltadas (fondo rojo/naranja): contenido adulto, juegos no permitidos,
    .apk/.exe/.zip sospechosos, y el evento "papelera vaciada".

Todas las horas se muestran ya convertidas a America/Lima (ver utils.timeutil).
"""
from __future__ import annotations

# Estilos "pill" por categoria (se inyectan inline o en un <style> del correo).
PILL_STYLES = {
    "juegos": ("⚠️ dominio de juegos", "#f59e0b"),
    "adulto": ("🔞 dominio para adultos", "#dc2626"),
    "dudoso": ("❔ dudoso", "#6b7280"),
    "sospechoso": ("⚠️ archivo sospechoso", "#dc2626"),
    "papelera_vaciada": ("🗑️ papelera vaciada", "#dc2626"),
}


def render_pill(category: str) -> str:
    """Devuelve el HTML de un badge redondeado para la categoria dada."""
    # TODO: <span style="border-radius:999px;padding:2px 8px;...">etiqueta</span>
    raise NotImplementedError


def build_report(sections_by_date: dict) -> str:
    """Construye el HTML completo del correo.

    sections_by_date: si hay varios dias pendientes (PC apagada), se agrupa por
    fecha con una seccion por dia (spec §6). Devuelve el string HTML.
    """
    # TODO: por cada fecha -> tabla de cada modulo; aplicar render_pill y
    #       resaltado de filas segun categoria/sospecha.
    raise NotImplementedError
