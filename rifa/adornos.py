"""Adornos decorativos: bandera de Cuba, silueta del Che y logos.

Todo se construye como geometria 3D (o imagenes) y se coloca a partir de un
rectangulo en **pixeles de pantalla**. Los actores 2D (botones, textos y la
tarjeta del ganador) se dibujan siempre por encima, asi que los adornos nunca
tapan la interfaz; ademas viven en un plano ``z`` negativo para quedar detras
de la rueda y del sombreado del reveal.
"""

from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile

import vtk

from . import config


# ---------------------------------------------------------------------------
# Geometria auxiliar
# ---------------------------------------------------------------------------
def _estrella(cx, cy, radio, giro=math.pi / 2.0, puntas=5):
    """Vertices de una estrella de ``puntas`` puntas."""
    pts = []
    for k in range(puntas * 2):
        r = radio if k % 2 == 0 else radio * 0.42
        a = giro + k * math.pi / puntas
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _polydata(poligonos, colores=None):
    """``poligonos`` es una lista de ``(puntos, z)``; ``colores`` por celda."""
    puntos = vtk.vtkPoints()
    celdas = vtk.vtkCellArray()
    for pts, z in poligonos:
        celda = vtk.vtkPolygon()
        base = puntos.GetNumberOfPoints()
        for x, y in pts:
            puntos.InsertNextPoint(x, y, z)
        for k in range(len(pts)):
            celda.GetPointIds().InsertNextId(base + k)
        celdas.InsertNextCell(celda)
    pd = vtk.vtkPolyData()
    pd.SetPoints(puntos)
    pd.SetPolys(celdas)
    if colores is not None:
        arr = vtk.vtkUnsignedCharArray()
        arr.SetNumberOfComponents(3)
        for color in colores:
            arr.InsertNextTuple3(*(int(round(c * 255)) for c in color))
        pd.GetCellData().SetScalars(arr)
    return pd


def _actor(pd, color, opacidad=1.0, por_celda=False):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(pd)
    if por_celda:
        mapper.SetScalarModeToUseCellData()
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
    else:
        mapper.ScalarVisibilityOff()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().LightingOff()
    actor.GetProperty().SetOpacity(opacidad)
    actor.PickableOff()
    return actor


class _Elemento:
    """Base: un actor cuya geometria vive en el cuadrado ``[0,1]x[0,1]``."""

    Z = -1.0

    def __init__(self, renderer, z=None):
        self.renderer = renderer
        if z is not None:
            self.Z = z

    def _registrar(self, actor):
        self.actor = actor
        actor.SetPosition(0.0, 0.0, self.Z)
        actor.SetVisibility(False)
        actor.PickableOff()
        self.renderer.AddViewProp(actor)

    def colocar_mundo(self, wx, wy, ww, wh):
        self.actor.SetPosition(wx, wy, self.Z)
        self.actor.SetScale(ww, wh, 1.0)

    def visible(self, valor):
        self.actor.SetVisibility(bool(valor))


# ---------------------------------------------------------------------------
# Bandera de Cuba
# ---------------------------------------------------------------------------
class Bandera(_Elemento):
    """Bandera cubana ondeando, con su triangulo, estrella y asta."""

    def __init__(self, renderer, z=-1.0):
        super().__init__(renderer, z)
        poligonos, colores = self._geometria()
        self._registrar(_actor(_polydata(poligonos, colores), config.BLANCO,
                               por_celda=True))

    def _geometria(self):
        n = 24
        amp = 0.09

        def onda(x):
            # Amplitud creciente hacia el vuelo: el asta queda fija.
            return amp * x * math.sin(2.0 * math.pi * 1.1 * x)

        x0, x1 = 0.05, 1.0
        poligonos, colores = [], []
        for j in range(5):
            y0, y1 = j * 0.2, (j + 1) * 0.2
            abajo, arriba = [], []
            for i in range(n + 1):
                x = x0 + (x1 - x0) * i / n
                abajo.append((x, y0 + onda(x)))
                arriba.append((x, y1 + onda(x)))
            poligonos.append((abajo + arriba[::-1], 0.0))
            colores.append(config.AZUL if j % 2 == 0 else config.BLANCO)

        # Triangulo rojo al asta y estrella blanca encima.
        punta = 0.46
        triangulo = [(x0, onda(x0)), (x0, 1.0 + onda(x0)),
                     (punta, 0.5 + onda(punta))]
        poligonos.append((triangulo, 0.002))
        colores.append(config.ROJO)
        poligonos.append((_estrella(0.18, 0.5 + onda(0.18), 0.15), 0.004))
        colores.append(config.BLANCO)

        # Asta oscura a la izquierda.
        poligonos.append(([(0.0, -0.05), (0.05, -0.05),
                           (0.05, 1.07), (0.0, 1.07)], 0.006))
        colores.append(config.COLOR_AGUJA_BORDE)
        return poligonos, colores


# ---------------------------------------------------------------------------
# Silueta del Che (a partir de una imagen de fondo claro)
# ---------------------------------------------------------------------------
def _abrir_gris(ruta):
    """Abre una imagen y la devuelve en escala de grises.

    Acepta PNG/JPG directamente con Pillow. Si el archivo es un SVG de verdad,
    lo rasteriza con ``rsvg-convert`` o ImageMagick cuando estan disponibles.
    Devuelve ``None`` si no se puede leer.
    """
    try:
        from PIL import Image
    except Exception:  # noqa: BLE001 - Pillow es opcional
        return None

    try:
        return Image.open(ruta).convert("L")
    except Exception:  # noqa: BLE001 - puede ser un SVG
        pass

    ordenes = (
        ("rsvg-convert",
         lambda exe, origen, salida: [exe, "-w", "1400", "-o", salida, origen]),
        ("convert",
         lambda exe, origen, salida: [exe, "-background", "white",
                                      "-density", "150", origen, salida]),
    )
    for nombre, comando in ordenes:
        ejecutable = shutil.which(nombre)
        if not ejecutable:
            continue
        destino = tempfile.mktemp(suffix=".png")
        try:
            subprocess.run(comando(ejecutable, ruta, destino), check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return Image.open(destino).convert("L")
        except Exception:  # noqa: BLE001
            continue
    return None


def _imagen_estencil(ruta, color, opacidad):
    """Convierte una imagen en un estencil del color dado.

    El fondo claro se vuelve transparente y el dibujo (oscuro) opaco, asi que
    sirve tanto para un PNG con alfa como para un JPEG/SVG sobre blanco. Se
    recorta al contenido y se devuelve un ``vtkImageData`` RGBA, o ``None`` si
    no hay forma de procesarla.
    """
    try:
        import numpy as np
        from vtk.util import numpy_support
    except Exception:  # noqa: BLE001 - numpy es opcional
        return None

    imagen = _abrir_gris(ruta)
    if imagen is None:
        return None
    gris = np.asarray(imagen, dtype=np.float32)

    alfa = np.clip((210.0 - gris) / 150.0, 0.0, 1.0)
    alto, ancho = alfa.shape
    rgba = np.empty((alto, ancho, 4), dtype=np.uint8)
    rgba[..., 0] = int(round(color[0] * 255))
    rgba[..., 1] = int(round(color[1] * 255))
    rgba[..., 2] = int(round(color[2] * 255))
    rgba[..., 3] = (alfa * opacidad * 255.0).astype(np.uint8)

    # Recorta los margenes vacios para que el dibujo llene su caja.
    filas = np.where(rgba[..., 3].max(axis=1) > 3)[0]
    cols = np.where(rgba[..., 3].max(axis=0) > 3)[0]
    if len(filas) and len(cols):
        rgba = rgba[filas[0]:filas[-1] + 1, cols[0]:cols[-1] + 1]

    alto, ancho = rgba.shape[:2]
    # VTK coloca el origen abajo: se voltea la imagen en vertical. Hay que
    # conservar la forma (N, 4) para que VTK reconozca el canal alfa.
    plano = np.ascontiguousarray(rgba[::-1].reshape(-1, 4))
    matriz = numpy_support.numpy_to_vtk(plano, deep=True,
                                        array_type=vtk.VTK_UNSIGNED_CHAR)
    imagen = vtk.vtkImageData()
    imagen.SetDimensions(ancho, alto, 1)
    imagen.GetPointData().SetScalars(matriz)
    return imagen


class Che(_Elemento):
    """Silueta del Che como marca de agua grande, por detras de todo."""

    def __init__(self, renderer, z=-2.0):
        super().__init__(renderer, z)
        self._ancho = self._alto = 0
        imagen = _imagen_estencil(config.RUTA_CHE, config.COLOR_CHE,
                                  config.OPACIDAD_CHE)
        self.actor = None
        if imagen is None:
            return
        self._ancho, self._alto = imagen.GetDimensions()[:2]
        actor = vtk.vtkImageActor()
        actor.SetInputData(imagen)
        actor.InterpolateOn()
        self._registrar(actor)

    def colocar_mundo(self, wx, wy, ww, wh):
        if self.actor is None:
            return
        # Mantiene la proporcion de la imagen y la centra en la caja.
        escala = min(ww / self._ancho, wh / self._alto)
        ancho, alto = self._ancho * escala, self._alto * escala
        self.actor.SetPosition(wx + (ww - ancho) / 2.0,
                               wy + (wh - alto) / 2.0, self.Z)
        self.actor.SetScale(escala, escala, 1.0)

    def visible(self, valor):
        if self.actor is not None:
            self.actor.SetVisibility(bool(valor))


# ---------------------------------------------------------------------------
# Logos de las organizaciones
# ---------------------------------------------------------------------------
class Logo(_Elemento):
    """Insignia cuadrada con el logo de una organizacion."""

    def __init__(self, renderer, ruta, z=-1.0):
        super().__init__(renderer, z)
        self.ruta = ruta
        lector = vtk.vtkJPEGReader()
        lector.SetFileName(ruta)
        lector.Update()
        imagen = lector.GetOutput()
        self._ancho, self._alto = imagen.GetDimensions()[:2]
        actor = vtk.vtkImageActor()
        actor.SetInputData(imagen)
        actor.InterpolateOn()

        # Recuadro negro por detras (queda como un borde delgado alrededor).
        marco = _polydata([([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)], 0.0)])
        self._marco = _actor(marco, config.NEGRO)
        self._marco.SetPosition(0.0, 0.0, z - 0.004)
        self._marco.SetVisibility(False)
        self._marco.PickableOff()
        renderer.AddViewProp(self._marco)

        self._registrar(actor)

    def colocar_mundo(self, wx, wy, ww, wh):
        # Las imagenes se miden en pixeles: se escalan a la caja pedida.
        self.actor.SetPosition(wx, wy, self.Z)
        self.actor.SetScale(ww / self._ancho, wh / self._alto, 1.0)
        margen = min(ww, wh) * 0.025
        self._marco.SetPosition(wx - margen, wy - margen, self.Z - 0.004)
        self._marco.SetScale(ww + 2.0 * margen, wh + 2.0 * margen, 1.0)

    def visible(self, valor):
        super().visible(valor)
        self._marco.SetVisibility(bool(valor))


# ---------------------------------------------------------------------------
# Conjunto de adornos
# ---------------------------------------------------------------------------
class Adornos:
    """Agrupa bandera, Che y logos y los reparte segun el tamano de ventana."""

    def __init__(self, renderer):
        self.renderer = renderer
        self._activos = bool(config.MOSTRAR_ADORNOS)
        self.bandera = Bandera(renderer)
        self.che = Che(renderer)
        self.logos = [
            Logo(renderer, ruta) for _, ruta in config.LOGOS if os.path.exists(ruta)
        ]
        self.visible(self._activos)

    def repartir(self, ancho: int, alto: int):
        """Coloca los adornos y devuelve la parte baja del bloque superior.

        El valor devuelto (en pixeles) es donde termina la bandera con sus
        logos, para que la interfaz pueda colocar los botones por debajo sin
        solaparse. ``None`` si los adornos estan ocultos.
        """
        if not self._activos:
            return None

        # Bandera de Cuba arriba a la derecha.
        bw = min(340.0, max(200.0, ancho * 0.24))
        bh = bw * 0.62
        bx = ancho - max(28.0, ancho * 0.025) - bw
        by = alto - max(40.0, alto * 0.05) - bh
        self._colocar(self.bandera, bx, by, bw, bh)

        # Logos de las organizaciones, justo debajo de la bandera.
        tam = min(126.0, max(64.0, min(alto * 0.15, bw * 0.52)))
        hueco = max(16.0, tam * 0.16)
        n = len(self.logos)
        total = n * tam + max(0, n - 1) * hueco
        lx = ancho - max(28.0, ancho * 0.025) - total
        ly = by - hueco * 0.8 - tam
        for logo in self.logos:
            self._colocar(logo, lx, ly, tam, tam)
            lx += tam + hueco

        # Silueta del Che: grande y de fondo, en el panel derecho.
        lado = min(alto * 0.96, ancho * 0.64)
        self._colocar(self.che, ancho * 0.76 - lado / 2.0,
                      alto * 0.50 - lado / 2.0, lado, lado)

        return ly if n else by

    # ------------------------------------------------------------------
    def _colocar(self, elemento, x, y, w, h):
        elemento.colocar_mundo(*self._rect_mundo(x, y, w, h))

    def _rect_mundo(self, x, y, w, h):
        ancho, alto = self.renderer.GetRenderWindow().GetSize()
        ancho, alto = max(1, ancho), max(1, alto)
        camara = self.renderer.GetActiveCamera()
        escala = camara.GetParallelScale()
        aspecto = ancho / float(alto)
        fx, fy, _ = camara.GetFocalPoint()
        ancho_mundo = 2.0 * escala * aspecto
        alto_mundo = 2.0 * escala
        wx = fx + (x - ancho / 2.0) / ancho * ancho_mundo
        wy = fy + (y - alto / 2.0) / alto * alto_mundo
        ww = w / ancho * ancho_mundo
        wh = h / alto * alto_mundo
        return wx, wy, ww, wh

    def visible(self, valor):
        self._activos = bool(valor)
        for elemento in (self.bandera, self.che, *self.logos):
            elemento.visible(self._activos)
