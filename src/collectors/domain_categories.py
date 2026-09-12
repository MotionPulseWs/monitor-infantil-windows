"""Categorizacion de dominios (spec §3.2).

Decision del proyecto: NO se cura una lista propia de dominios. Se usan listas
publicas de referencia ya existentes (hostlists tipo StevenBlack/OISD para
adultos, listas de dominios de juegos conocidos) y, como respaldo, una heuristica
de palabras clave para lo que no aparezca en las listas.

Categorias: 'juegos', 'adulto', 'dudoso', 'normal'.
"""
from __future__ import annotations

# Respaldo por palabras clave cuando el dominio no esta en ninguna hostlist.
GAME_KEYWORDS = ("roblox", "minecraft", "fortnite", "game", "juego", "steam", "epicgames")
ADULT_KEYWORDS = ("porn", "xxx", "sex", "adult", "camgirl", "hentai")


class DomainCategorizer:
    def __init__(self, adult_hostlist_path: str = "", games_hostlist_path: str = ""):
        self._adult: set[str] = set()
        self._games: set[str] = set()
        if adult_hostlist_path:
            self._adult = self._load_hostlist(adult_hostlist_path)
        if games_hostlist_path:
            self._games = self._load_hostlist(games_hostlist_path)

    @staticmethod
    def _load_hostlist(path: str) -> set[str]:
        """Carga una hostlist en formato hosts (0.0.0.0 dominio) o dominio por linea."""
        # TODO: parsear el archivo, ignorar comentarios (#) y normalizar dominios.
        raise NotImplementedError

    def categorize(self, domain: str) -> str:
        """Devuelve 'juegos' | 'adulto' | 'dudoso' | 'normal' para un dominio."""
        # TODO: 1) match exacto/subdominio contra self._adult y self._games;
        #       2) fallback por palabras clave; 3) por defecto 'normal'.
        raise NotImplementedError
