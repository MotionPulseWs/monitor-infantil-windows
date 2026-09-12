"""Categorias de riesgo y estilos de badge ("pill") del reporte (spec §3.2, §5).

FUENTE UNICA DE VERDAD para dos cosas relacionadas:
  1) Como se clasifica un dominio web O una aplicacion (categorias de riesgo).
  2) Como se ve cada badge en el reporte HTML (emoji, texto y colores).

Categorias de riesgo (aplican tanto a dominios como a apps del listado de procesos):
  adulto      -> contenido para adultos / pornografia.  ROJO INTENSO, muy llamativo.
  juegos      -> juegos.                                 NARANJA (alerta, menos intensa).
  desconocido -> no aparece en ninguna lista de referencia; hay que revisarlo y
                 clasificarlo a mano. Reemplaza al 'dudoso/otros' del spec original.
                                                          VIOLETA (destaca para revision).
  normal      -> app/sitio conocido y benigno (Word, Excel, sitios comunes).  GRIS.

Flags de evento (no son categorias de dominio, pero comparten el sistema de pills):
  sospechoso        -> descarga .apk/.exe/.zip de origen no confiable (spec §3.3).  ROJO.
  papelera_vaciada  -> evento de vaciado de papelera (spec §3.5).                    ROJO.

Los estilos se escriben INLINE en el HTML porque muchos clientes de correo
descartan las hojas <style> (spec §5: el reporte se lee desde el celular).
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Nombres de categoria (usar estas constantes, no strings sueltos) ---
ADULTO = "adulto"
JUEGOS = "juegos"
DESCONOCIDO = "desconocido"
NORMAL = "normal"

# Categorias de riesgo, de mayor a menor severidad.
RISK_CATEGORIES = (ADULTO, JUEGOS, DESCONOCIDO, NORMAL)

# Flags de evento.
SOSPECHOSO = "sospechoso"
PAPELERA_VACIADA = "papelera_vaciada"


@dataclass(frozen=True)
class PillStyle:
    emoji: str
    label: str
    bg: str               # color de fondo del pill
    fg: str               # color del texto del pill
    row_bg: str | None    # resaltado de fila (None = fila sin resaltar)
    severity: int         # mayor = mas peligroso (para ordenar/priorizar filas)


PILL_STYLES: dict[str, PillStyle] = {
    # --- Categorias de riesgo ---
    ADULTO: PillStyle(
        emoji="🔞", label="contenido para adultos",
        bg="#b91c1c", fg="#ffffff", row_bg="#fee2e2", severity=100,
    ),
    JUEGOS: PillStyle(
        emoji="🎮", label="juegos",
        bg="#f59e0b", fg="#1f2937", row_bg="#fff7ed", severity=60,
    ),
    DESCONOCIDO: PillStyle(
        emoji="🔍", label="sin clasificar — revisar",
        bg="#7c3aed", fg="#ffffff", row_bg="#f5f3ff", severity=40,
    ),
    NORMAL: PillStyle(
        emoji="•", label="normal",
        bg="#e5e7eb", fg="#4b5563", row_bg=None, severity=0,
    ),
    # --- Flags de evento ---
    SOSPECHOSO: PillStyle(
        emoji="⚠️", label="archivo sospechoso",
        bg="#b91c1c", fg="#ffffff", row_bg="#fee2e2", severity=90,
    ),
    PAPELERA_VACIADA: PillStyle(
        emoji="🗑️", label="papelera vaciada",
        bg="#b91c1c", fg="#ffffff", row_bg="#fee2e2", severity=95,
    ),
}


def render_pill(category: str) -> str:
    """Devuelve el HTML de un badge redondeado para la categoria/flag dada.

    Devuelve "" si la categoria no existe (fila sin badge).
    """
    style = PILL_STYLES.get(category)
    if style is None:
        return ""
    return (
        '<span style="display:inline-block;border-radius:999px;'
        "padding:2px 10px;font-size:12px;font-weight:600;line-height:1.6;"
        f'white-space:nowrap;background:{style.bg};color:{style.fg};">'
        f"{style.emoji} {style.label}</span>"
    )


def row_background(category: str) -> str | None:
    """Color de resaltado de fila para la categoria (None = sin resaltar)."""
    style = PILL_STYLES.get(category)
    return style.row_bg if style else None


def severity(category: str) -> int:
    """Severidad numerica (mayor = mas peligroso). Util para ordenar filas."""
    style = PILL_STYLES.get(category)
    return style.severity if style else 0
