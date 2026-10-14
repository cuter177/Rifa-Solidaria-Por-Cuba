"""Punto de entrada de la Rifa Solidaria por Cuba.

Uso:
    python main.py                       # se puede cargar el archivo desde el boton
    python main.py participantes.xlsx    # carga directa
    python main.py lista.csv --validar   # solo comprueba el archivo, sin abrir ventana
"""

from __future__ import annotations

import argparse
import os
import sys


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rifa",
        description="Ruleta de sorteo con VTK: carga un Excel o CSV y gira.",
    )
    parser.add_argument("archivo", nargs="?", default=None,
                        help="Lista de participantes (.xlsx, .xlsm, .csv)")
    parser.add_argument("--validar", action="store_true",
                        help="Comprueba el archivo y muestra un resumen, sin abrir la ventana")
    parser.add_argument("--semilla", type=int, default=None,
                        help="Semilla aleatoria, para pruebas reproducibles")
    return parser


def principal(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    from . import datos

    if args.archivo:
        if not os.path.exists(args.archivo):
            print(f"ERROR: no existe el archivo '{args.archivo}'", file=sys.stderr)
            return 2
        try:
            participantes = datos.cargar(args.archivo)
        except datos.ErrorDatos as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        print(f"OK: {datos.resumen(participantes)}")
        if args.validar:
            ancho = max((len(p.nombre) for p in participantes), default=0)
            for p in participantes[:20]:
                print(f"  {p.numero:>5}  {p.nombre}")
            if len(participantes) > 20:
                print(f"  ... y {len(participantes) - 20} mas")
            return 0

    try:
        import vtk  # noqa: F401
    except ImportError:
        print(
            "ERROR: falta VTK.\n"
            "Ejecuta primero:  ./run.sh   (crea el entorno virtual e instala las dependencias)",
            file=sys.stderr,
        )
        return 2

    from .app import RifaApp

    app = RifaApp(args.archivo)
    if args.semilla is not None:
        import random
        app.rng = random.Random(args.semilla)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
