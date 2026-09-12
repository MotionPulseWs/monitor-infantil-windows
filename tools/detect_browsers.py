"""Lista los navegadores (Chromium) y perfiles de un usuario — paso de instalacion.

El instalador lo llama tras elegir la cuenta del menor, para mostrar QUE se va a
monitorear (Chrome, Edge, Opera GX, etc. + sus perfiles). Tambien sirve de prueba.

Uso:
    python tools/detect_browsers.py                 # usuario ACTUAL (prueba local)
    python tools/detect_browsers.py --sid S-1-5-21-...   # cuenta del menor (instalacion)

Con --sid resuelve el perfil del menor desde el registro (necesita permisos para
leer ese perfil: el instalador corre como administrador; el monitor, como SYSTEM).
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.browser_history import find_history_files  # noqa: E402
from src.winprofile import resolve_user_paths  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Lista navegadores/perfiles a monitorear.")
    ap.add_argument("--sid", help="SID de la cuenta del menor (si se omite, usa el usuario actual)")
    args = ap.parse_args()

    if args.sid:
        env = resolve_user_paths(args.sid)
        if env is None:
            print(f"ERROR: no se pudo resolver el perfil del SID {args.sid}.", file=sys.stderr)
            return 1
        print(f"Perfil del menor: {env['USERPROFILE']}")
    else:
        env = dict(os.environ)
        print(f"Perfil del usuario actual: {env.get('USERPROFILE', '(desconocido)')}")

    print(f"  LOCALAPPDATA: {env.get('LOCALAPPDATA')}")
    print(f"  APPDATA:      {env.get('APPDATA')}\n")

    found = find_history_files(env)
    if not found:
        print("No se detectaron navegadores basados en Chromium con historial.")
        return 0

    print("Navegadores detectados (se monitorearan estos):")
    for browser, profile, path in found:
        print(f"  - {browser:10s} [{profile}]  ->  {path}")
    print(f"\nTotal: {len(found)} perfil(es).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
