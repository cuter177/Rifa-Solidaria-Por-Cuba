#!/usr/bin/env python3
"""Lanzador de la Rifa Solidaria por Cuba (raiz del repositorio).

    ./main.py                     abre la ruleta sin participantes
    ./main.py participantes.xlsx  carga el archivo y abre la ruleta
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from rifa.main import principal  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(principal(sys.argv[1:]))
