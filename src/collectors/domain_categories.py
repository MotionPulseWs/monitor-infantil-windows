"""Categorizacion de dominios (spec §3.2).

Listas de adulto/juegos: publicas de referencia (StevenBlack/OISD, etc.) +
heuristica de palabras clave como respaldo. Lista de "conocidos" (-> normal):
curada a mano en data/known_sites.txt (unica excepcion, decidida con el usuario)
para separar 'normal' de 'desconocido'.

Categorias (ver src/categories.py): adulto | juegos | normal | desconocido.

Regla clave: lo que NO se puede confirmar cae en 'desconocido' (para revisar),
NO en 'normal'. 'normal' exige aparecer en la lista de conocidos.
"""
from __future__ import annotations

from pathlib import Path

from src.categories import ADULTO, DESCONOCIDO, JUEGOS, NORMAL

# Respaldo por palabras clave cuando el dominio no esta en ninguna hostlist.
GAME_KEYWORDS = ("roblox", "minecraft", "fortnite", "game", "juego", "steam", "epicgames")
ADULT_KEYWORDS = ("porn", "xxx", "sex", "adult", "camgirl", "hentai")


def _normalize(domain: str) -> str:
    """Minusculas, sin espacios, sin 'www.' ni punto final."""
    d = domain.strip().lower().rstrip(".")
    if d.startswith("www."):
        d = d[4:]
    return d


# Sufijos publicos de dos etiquetas mas comunes (para no agrupar 'ucsp.edu.pe' y
# 'otra.edu.pe' como si fueran el mismo sitio). No es la PSL completa, pero cubre
# los casos frecuentes (sobre todo .pe). Ampliable.
_MULTI_LABEL_SUFFIXES = {
    "edu.pe", "gob.pe", "com.pe", "org.pe", "net.pe", "nom.pe", "mil.pe", "sld.pe",
    "co.uk", "org.uk", "ac.uk", "gov.uk",
    "com.mx", "org.mx", "gob.mx", "com.ar", "com.br", "com.co", "com.ec", "com.bo",
    "com.ve", "com.py", "com.uy", "com.cl", "co.jp", "com.au", "co.in", "com.tr",
    "com.sg", "com.hk", "com.tw",
}


def registrable_domain(host: str) -> str:
    """Dominio 'registrable' (eTLD+1) de un host, para agrupar en el reporte.

    github.com                  -> github.com
    docs.google.com             -> google.com
    campus.ucsp.edu.pe          -> ucsp.edu.pe   (reconoce 'edu.pe' como sufijo)
    """
    host = _normalize(host)
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return host
    if ".".join(parts[-2:]) in _MULTI_LABEL_SUFFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _matches(domain: str, entries: set[str]) -> bool:
    """True si el dominio coincide con alguna entrada de la lista.

    - entrada normal 'ejemplo.com' -> coincide con ejemplo.com y *.ejemplo.com
    - entrada con punto inicial '.edu.pe' -> regla de sufijo: cualquier *.edu.pe
    """
    domain = _normalize(domain)
    for entry in entries:
        if entry.startswith("."):
            suffix = entry[1:]
            if domain == suffix or domain.endswith("." + suffix):
                return True
        elif domain == entry or domain.endswith("." + entry):
            return True
    return False


def _keyword_hit(domain: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in domain for kw in keywords)


class DomainCategorizer:
    def __init__(
        self,
        adult_hostlist_path: str = "",
        games_hostlist_path: str = "",
        known_sites_hostlist_path: str = "",
    ):
        self._adult = self._load_hostlist(adult_hostlist_path)
        self._games = self._load_hostlist(games_hostlist_path)
        self._known = self._load_hostlist(known_sites_hostlist_path)

    @staticmethod
    def _load_hostlist(path: str) -> set[str]:
        """Carga una lista de dominios. Acepta formato hosts (0.0.0.0 dominio) o
        un dominio por linea. Ignora comentarios (#), lineas vacias y IPs.
        Conserva el punto inicial de las reglas de sufijo (.edu.pe).
        """
        if not path:
            return set()
        file = Path(path)
        if not file.exists():
            return set()

        entries: set[str] = set()
        for raw in file.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            # Formato hosts: "0.0.0.0 dominio" / "127.0.0.1 dominio"
            parts = line.split()
            token = parts[-1] if len(parts) > 1 else parts[0]
            token = token.strip().lower()
            if not token or token in {"0.0.0.0", "127.0.0.1", "localhost"}:
                continue
            # Normaliza el nucleo; re-agrega el punto inicial de la regla de sufijo.
            leading_dot = token.startswith(".")
            core = _normalize(token[1:] if leading_dot else token)
            if core:
                entries.add(("." + core) if leading_dot else core)
        return entries

    def categorize(self, domain: str) -> str:
        """Clasifica un dominio en adulto | juegos | normal | desconocido.

        Orden: 1) hostlist adultos  2) hostlist juegos  3) lista de conocidos
        (allowlist explicito gana sobre las heuristicas)  4) keyword adulto
        5) keyword juegos  6) por defecto -> desconocido.
        """
        d = _normalize(domain)
        if _matches(d, self._adult):
            return ADULTO
        if _matches(d, self._games):
            return JUEGOS
        if _matches(d, self._known):
            return NORMAL
        if _keyword_hit(d, ADULT_KEYWORDS):
            return ADULTO
        if _keyword_hit(d, GAME_KEYWORDS):
            return JUEGOS
        return DESCONOCIDO
