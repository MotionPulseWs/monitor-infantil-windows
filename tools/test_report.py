"""Genera un reporte HTML con DATOS REALES de esta PC (prueba local).

Lee el historial y descargas de los navegadores del usuario actual + un snapshot
de apps abiertas, categoriza y arma el reporte. Sirve para ver "como sale" antes
de conectar el envio por correo.

Privacidad: a la consola solo se imprimen CONTEOS (no URLs). El detalle va al
archivo HTML local en reports/ (ignorado por git). Es tu propia data, en tu PC.

Uso:
    python tools/test_report.py            # ultimas 24h
    python tools/test_report.py --days 3
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import webbrowser
from collections import Counter
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.categories import render_pill  # noqa: E402
from src.collectors.browser_history import BrowserHistoryCollector  # noqa: E402
from src.collectors.domain_categories import DomainCategorizer  # noqa: E402
from src.collectors.processes import ProcessCollector, accumulate_time_per_app  # noqa: E402
from src.report.aggregate import group_visits_by_domain  # noqa: E402
from src.report.html_report import page, render_row, render_table  # noqa: E402
from src.state import StateStore  # noqa: E402
from src.utils.timeutil import format_duration, format_local, now_utc  # noqa: E402
from src.categories import severity  # noqa: E402

MAX_VISIT_ROWS = 300  # tope de filas de navegacion mostradas (las marcadas van arriba)


def _human_size(n: int) -> str:
    size = float(n or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def main() -> None:
    ap = argparse.ArgumentParser(description="Reporte con datos reales de esta PC.")
    ap.add_argument("--days", type=int, default=1, help="cuantos dias hacia atras (def. 1)")
    ap.add_argument("--detailed", action="store_true",
                    help="navegacion por URL en vez de agrupada por dominio")
    ap.add_argument("--no-open", action="store_true", help="no abrir el navegador al terminar")
    args = ap.parse_args()
    since = now_utc() - timedelta(days=args.days)

    state = StateStore(Path(tempfile.mkdtemp(prefix="monitor_report_")) / "state.db")
    categorizer = DomainCategorizer(
        known_sites_hostlist_path=str(PROJECT_ROOT / "data" / "known_sites.txt")
    )

    # 1) Historial + descargas reales
    print(f"Leyendo historial de navegadores (ultimos {args.days} dia/s)...")
    collector = BrowserHistoryCollector(state, categorizer)
    for s in collector.collect_all(since_utc=since):
        print(f"  {s['browser']:10s} [{s['profile']}]: {s['visits']} visitas, {s['downloads']} descargas")

    visits = state.fetch_web_visits(since_utc=since)
    downloads = state.fetch_downloads(since_utc=since)

    # 2) Snapshot de apps abiertas
    apps = accumulate_time_per_app(ProcessCollector().snapshot())

    # 3) Resumen por categoria a consola (sin URLs)
    cats = Counter(v["category"] for v in visits)
    print("\nVisitas por categoria:", dict(cats))
    print(f"Descargas: {len(downloads)} ({sum(d['suspicious'] for d in downloads)} sospechosas)")
    print(f"Apps abiertas: {len(apps)}")

    # 4) Construir HTML
    app_rows = "".join(render_row([a, format_duration(sec)]) for a, sec in apps.items())

    if args.detailed:
        visits.sort(key=lambda v: (severity(v["category"]), v["visit_ts_utc"]), reverse=True)
        shown = visits[:MAX_VISIT_ROWS]
        nav_rows = "".join(
            render_row(
                [format_local(v["visit_ts_utc"], fmt="%d/%m %H:%M"),
                 f'<span class="wrap">{v["domain"]}</span>',
                 f'<span class="wrap">{(v["title"] or "")[:80]}</span>',
                 v["browser"], render_pill(v["category"])],
                v["category"],
            )
            for v in shown
        )
        nav_title = f"Navegacion web — detalle ({len(visits)} visitas"
        nav_title += f", mostrando {len(shown)})" if len(shown) < len(visits) else ")"
        nav_table = render_table(nav_title, ["Hora", "Dominio", "Titulo", "Navegador", "Categoria"], nav_rows)
    else:
        groups = group_visits_by_domain(visits)
        nav_rows = "".join(
            render_row(
                [f'<span class="wrap">{g["domain"]}</span>',
                 str(g["count"]),
                 f'{format_local(g["first"], fmt="%d/%m %H:%M")} → {format_local(g["last"], fmt="%H:%M")}',
                 ", ".join(sorted(g["browsers"])),
                 render_pill(g["category"])],
                g["category"],
            )
            for g in groups
        )
        nav_table = render_table(
            f"Navegacion web — {len(groups)} dominios ({len(visits)} visitas)",
            ["Dominio", "Visitas", "Rango horario", "Navegador", "Categoria"], nav_rows,
        )

    dl_rows = "".join(
        render_row(
            [format_local(d["start_ts_utc"], fmt="%d/%m %H:%M") if d["start_ts_utc"] else "—",
             f'<span class="wrap">{d["file_name"]}</span>',
             f'<span class="wrap">{d["source_url"][:60]}</span>',
             _human_size(d["size_bytes"]), d["state"],
             render_pill("sospechoso") if d["suspicious"] else ""],
            "sospechoso" if d["suspicious"] else None,
        )
        for d in downloads
    )

    body = (
        "<h1>Reporte de actividad — DATOS REALES (prueba local)</h1>"
        f"<p><small>Ultimos {args.days} dia/s · horas en America/Lima</small></p>"
        + render_table("Apps abiertas ahora (tiempo abierto)", ["Aplicacion", "Tiempo"], app_rows)
        + nav_table
        + render_table(f"Descargas ({len(downloads)})",
                       ["Hora", "Archivo", "Origen", "Tamano", "Estado", ""], dl_rows)
    )

    out = PROJECT_ROOT / "reports" / "report_real.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page("Reporte real", body), encoding="utf-8")
    state.close()
    print(f"\nReporte generado: {out}")
    if not args.no_open:
        try:
            webbrowser.open(out.as_uri())
        except Exception:
            print("Abrelo manualmente en tu navegador.")


if __name__ == "__main__":
    main()
