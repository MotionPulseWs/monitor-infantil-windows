"""Agrupacion de visitas por dominio para el reporte (reduce ruido y peso).

En vez de una fila por cada URL/subpagina (GitHub x4, ucsp.edu.pe x50, ...), se
muestra UNA fila por dominio registrable con: cantidad de visitas, rango horario,
navegador(es) y categoria. La categoria del grupo es la de MAYOR severidad de sus
visitas (si alguna subpagina es 'adulto', el grupo entero se marca 'adulto').

Esto mantiene la senal importante (que dominios, cuantas veces, de que tipo) y baja
el tamano del correo de MB a KB — clave para un envio diario durante todo el año.
"""
from __future__ import annotations

from src.categories import severity
from src.collectors.domain_categories import registrable_domain


def group_visits_by_domain(visits: list[dict]) -> list[dict]:
    """Agrupa visitas (de state.fetch_web_visits) por dominio registrable.

    Devuelve una lista de dicts {domain, count, first, last, category, browsers}
    ordenada por severidad (desc) y luego por cantidad de visitas (desc).
    """
    groups: dict[str, dict] = {}
    for v in visits:
        domain = registrable_domain(v["domain"]) if v.get("domain") else "(sin dominio)"
        ts = v["visit_ts_utc"]
        g = groups.get(domain)
        if g is None:
            groups[domain] = {
                "domain": domain, "count": 1, "first": ts, "last": ts,
                "category": v["category"], "browsers": {v["browser"]},
            }
            continue
        g["count"] += 1
        g["first"] = min(g["first"], ts)
        g["last"] = max(g["last"], ts)
        g["browsers"].add(v["browser"])
        if severity(v["category"]) > severity(g["category"]):
            g["category"] = v["category"]

    return sorted(
        groups.values(),
        key=lambda g: (severity(g["category"]), g["count"]),
        reverse=True,
    )
