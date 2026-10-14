"""Herramienta de desarrollo: captura fotogramas de la ruleta a PNG.

Sirve para revisar el aspecto de la aplicacion sin interactuar a mano.

    .venv/bin/python tools/capturas.py [archivo.csv] [carpeta_destino]

Genera:
    01_cargada.png     ruleta recien cargada
    02_giro_*.png      distintos momentos del giro
    03_reveal_*.png    sombreado y aparicion del nombre
    04_final.png       despues del clic, con la rueda reconstruida
"""

from __future__ import annotations

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

import vtk  # noqa: E402

from rifa import geometria as g  # noqa: E402
from rifa.app import Estado, RifaApp  # noqa: E402


class Capturador:
    def __init__(self, render_window, carpeta):
        self.render_window = render_window
        self.carpeta = carpeta
        os.makedirs(carpeta, exist_ok=True)
        self.filtro = vtk.vtkWindowToImageFilter()
        self.filtro.SetInput(render_window)
        self.filtro.SetInputBufferTypeToRGB()
        self.filtro.ReadFrontBufferOff()
        self.escritor = vtk.vtkPNGWriter()
        self.escritor.SetInputConnection(self.filtro.GetOutputPort())

    def tomar(self, nombre):
        self.render_window.Render()
        self.filtro.Modified()
        self.filtro.Update()
        ruta = os.path.join(self.carpeta, f"{nombre}.png")
        self.escritor.SetFileName(ruta)
        self.escritor.Write()
        print(f"   -> {os.path.relpath(ruta, RAIZ)}")


def main(argv):
    archivo = argv[0] if argv else os.path.join(RAIZ, "ejemplos", "participantes.csv")
    destino = argv[1] if len(argv) > 1 else "/tmp/opencode/capturas"

    app = RifaApp()
    app.render_window.SetOffScreenRendering(1)
    app.render_window.SetSize(1360, 820)
    app.renderer.SetUseFXAA(True)
    app.render_window.Render()
    app.interactor.Initialize()

    if not app.cargar(archivo):
        print("ERROR: no se pudo cargar", archivo)
        return 1
    capt = Capturador(app.render_window, destino)
    print("estado:", app.estado.value, "| sectores:", app.rueda.num_sectores)
    capt.tomar("01_cargada")

    # ---- giro ----
    app.girar()
    esperado = app.indice_ganador
    n = len(app.restantes)
    t0 = app.anim["t0"]
    duracion = app.anim["duracion"]
    for etiqueta, fraccion in (("10", 0.10), ("45", 0.45), ("85", 0.85), ("100", 1.0)):
        app._paso_giro(t0 + duracion * fraccion)
        capt.tomar(f"02_giro_{etiqueta}")

    real = g.indice_bajo_aguja(app.theta, n)
    print(f"   ganador previsto={esperado} real={real}  {'OK' if real == esperado else 'MAL'}")
    if real != esperado:
        return 2

    # ---- reveal ----
    r0 = app.reveal_t0
    ganador = app.restantes[app.indice_ganador]
    print(f"   ganador: Nº {ganador.numero} - {ganador.nombre}")
    for etiqueta, dt in (("020", 0.20), ("060", 0.60), ("110", 1.10), ("260", 2.60)):
        app._paso_reveal(r0 + dt)
        capt.tomar(f"03_reveal_{etiqueta}")

    # ---- clic para cerrar ----
    app._terminar_reveal()
    capt.tomar("04_final")
    print(f"   estado final={app.estado.value} restantes={len(app.restantes)} "
          f"ganados={len(app.ganadores)}")
    if app.estado not in (Estado.LISTO, Estado.FIN):
        return 3

    # ---- segundo giro sobre la rueda reconstruida ----
    if app.estado == Estado.LISTO:
        app.girar()
        t0 = app.anim["t0"]
        app._paso_giro(t0 + app.anim["duracion"])
        capt.tomar("05_segundo_giro")
        n = len(app.restantes)
        if g.indice_bajo_aguja(app.theta, n) != app.indice_ganador:
            print("MAL: el segundo giro no coincide")
            return 4
        app._terminar_reveal()
        capt.tomar("06_tras_segundo_clic")

    print("CAPTURAS OK en", destino)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
