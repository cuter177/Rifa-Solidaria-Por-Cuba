#!/usr/bin/env bash
# Crea el entorno virtual (si falta), instala las dependencias y abre la ruleta.
#
#   ./run.sh                            -> abre la ruleta vacia
#   ./run.sh ejemplos/participantes.csv -> carga ese archivo
#
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$RAIZ/.venv"
PY="$VENV/bin/python"

if [[ ! -x "$PY" ]]; then
    echo "==> Creando entorno virtual en .venv"
    python3 -m venv "$VENV"
fi

if ! "$PY" -c "import vtk, openpyxl" >/dev/null 2>&1; then
    echo "==> Instalando dependencias (la primera vez descarga ~200 MB de VTK)"
    "$PY" -m pip install --upgrade pip
    "$PY" -m pip install -r "$RAIZ/requirements.txt"
fi

# Si no se pasa archivo, se usa el ejemplo cuando existe.
if [[ $# -eq 0 && -f "$RAIZ/ejemplos/participantes.csv" ]]; then
    set -- "$RAIZ/ejemplos/participantes.csv"
fi

exec "$PY" "$RAIZ/main.py" "$@"
