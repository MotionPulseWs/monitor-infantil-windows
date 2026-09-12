"""Genera un HTML de MUESTRA para revisar visualmente el reporte.

No usa datos reales ni toca el navegador/papelera. Sirve para dos cosas:
  1) Ver los badges/colores de las 4 categorias y los flags de evento.
  2) Probar de verdad el categorizador (src/collectors/domain_categories.py) con
     la lista data/known_sites.txt + heuristica, y la correlacion descarga->borrado.

Uso (desde la raiz del proyecto):
    python tools/preview_report.py
Luego abre el archivo que imprime al final en tu navegador.
"""
from __future__ import annotations

import sys
import webbrowser
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.categories import (  # noqa: E402
    ADULTO, DESCONOCIDO, JUEGOS, NORMAL, PAPELERA_VACIADA, SOSPECHOSO,
    render_pill, row_background,
)
from src.collectors.domain_categories import DomainCategorizer  # noqa: E402
from src.report.correlate import format_gap, match_deletion_to_download  # noqa: E402
from src.utils.timeutil import format_local  # noqa: E402

# Categorizador real, usando nuestra lista de conocidos (sin hostlists de adulto/juegos:
# esas caen en la heuristica de palabras clave, suficiente para la muestra).
CATEGORIZER = DomainCategorizer(known_sites_hostlist_path=str(PROJECT_ROOT / "data" / "known_sites.txt"))

# --- Navegacion (los dominios se clasifican EN VIVO con el categorizador) ---
NAV_SAMPLE = [
    ("20:14", "pornhub.com", "(bloqueado por filtro)"),
    ("19:50", "roblox.com", "Roblox - Jugar"),
    ("19:32", "sitio-nuevo-raro.xyz", "Descargas gratis!!"),
    ("18:10", "docs.google.com", "Documento sin titulo"),
    ("17:45", "wikipedia.org", "Tarea de historia"),
    ("17:20", "mi-colegio.edu.pe", "Aula virtual"),
]

APPS_SAMPLE = [
    ("Roblox", "3h 05min", JUEGOS),
    ("Chrome", "2h 15min", NORMAL),
    ("WINWORD.EXE (Word)", "1h 40min", NORMAL),
    ("instalador_desconocido.exe", "12min", DESCONOCIDO),
]

DOWNLOADS_SAMPLE = [
    ("juego_crackeado.apk", "cdn-raro.net", SOSPECHOSO),
    ("tarea.pdf", "aula.colegio.edu.pe", NORMAL),
]

# Descargas del dia (para la correlacion con la papelera). Horas en UTC.
DOWNLOADS_FOR_CORRELATION = [
    {"file_name": "tarea.pdf", "start_ts_utc": datetime(2025, 9, 12, 23, 10, tzinfo=timezone.utc)},
]

# Archivos que llegaron a la papelera (spec §3.4). Horas en UTC.
DELETIONS_SAMPLE = [
    {
        "original_path": r"C:\Users\menor\Downloads\tarea.pdf",
        "size_bytes": 240_000,
        "deleted_ts_utc": datetime(2025, 9, 12, 23, 20, tzinfo=timezone.utc),
    },
    {
        "original_path": r"C:\Users\menor\Documents\foto_familiar.jpg",
        "size_bytes": 1_800_000,
        "deleted_ts_utc": datetime(2025, 9, 13, 2, 3, tzinfo=timezone.utc),
    },
]


def _row(cells: list[str], category: str | None) -> str:
    bg = row_background(category) if category else None
    style = f' style="background:{bg};"' if bg else ""
    tds = "".join(f"<td>{c}</td>" for c in cells)
    return f"<tr{style}>{tds}</tr>"


def _table(title: str, headers: list[str], rows_html: str) -> str:
    ths = "".join(f"<th>{h}</th>" for h in headers)
    return f"""
    <h2>{title}</h2>
    <table>
      <thead><tr>{ths}</tr></thead>
      <tbody>{rows_html}</tbody>
    </table>
    """


def _basename(path: str) -> str:
    return PureWindowsPath(path).name


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def build_preview_html() -> str:
    # Navegacion: categoria decidida en vivo por el categorizador.
    nav_rows = ""
    for hora, dominio, titulo in NAV_SAMPLE:
        cat = CATEGORIZER.categorize(dominio)
        nav_rows += _row([hora, dominio, titulo, render_pill(cat)], cat)

    app_rows = "".join(
        _row([app, tiempo, render_pill(cat)], cat) for app, tiempo, cat in APPS_SAMPLE
    )
    dl_rows = "".join(
        _row([archivo, origen, render_pill(cat)], cat) for archivo, origen, cat in DOWNLOADS_SAMPLE
    )

    # Papelera - archivos eliminados, con correlacion contra las descargas del dia.
    del_rows = ""
    for d in DELETIONS_SAMPLE:
        match = match_deletion_to_download(d["original_path"], d["deleted_ts_utc"], DOWNLOADS_FOR_CORRELATION)
        if match:
            gap = format_gap(match["start_ts_utc"], d["deleted_ts_utc"])
            origen = f'🔗 descargado hoy {format_local(match["start_ts_utc"], fmt="%H:%M")} · <b>borrado {gap}</b>'
        else:
            origen = "—"
        del_rows += _row([
            format_local(d["deleted_ts_utc"], fmt="%H:%M"),
            _basename(d["original_path"]),
            d["original_path"],
            _human_size(d["size_bytes"]),
            origen,
        ], None)

    papelera_vaciada_row = _row(
        [format_local(datetime(2025, 9, 13, 2, 3, tzinfo=timezone.utc), fmt="%H:%M"),
         "Se vaciaron 14 archivos de golpe", render_pill(PAPELERA_VACIADA)],
        PAPELERA_VACIADA,
    )

    leyenda = " ".join(render_pill(c) for c in (ADULTO, JUEGOS, DESCONOCIDO, NORMAL))

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Preview de reporte</title>
<style>
  body {{ font-family: -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color: #111827; }}
  h1 {{ font-size: 20px; }}
  h2 {{ font-size: 15px; margin-top: 28px; color: #374151; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid #e5e7eb; vertical-align: top; }}
  th {{ background: #f9fafb; color: #6b7280; font-weight: 600; }}
  .leyenda {{ margin: 12px 0 4px; display: flex; gap: 8px; flex-wrap: wrap; }}
  small {{ color: #6b7280; }}
</style></head>
<body>
  <h1>Reporte de actividad — MUESTRA (datos ficticios)</h1>
  <div class="leyenda">{leyenda}</div>
  {_table("Tiempo por aplicacion", ["Aplicacion", "Tiempo total", "Categoria"], app_rows)}
  {_table("Navegacion web", ["Hora", "Dominio", "Titulo", "Categoria"], nav_rows)}
  {_table("Descargas", ["Archivo", "Origen", "Estado"], dl_rows)}
  {_table("Papelera — archivos eliminados", ["Hora", "Archivo", "Ruta original", "Tamano", "Correlacion"], del_rows)}
  {_table("Papelera — vaciada", ["Hora", "Detalle", "Evento"], papelera_vaciada_row)}
  <p><small>La hora se muestra en America/Lima; internamente se guarda en UTC.</small></p>
</body></html>
"""


def main() -> None:
    out_dir = PROJECT_ROOT / "reports"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "preview_report.html"
    out_file.write_text(build_preview_html(), encoding="utf-8")
    print(f"Preview generado: {out_file}")
    try:
        webbrowser.open(out_file.as_uri())
    except Exception:
        print("Abrelo manualmente en tu navegador.")


if __name__ == "__main__":
    main()
