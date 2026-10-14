"""Piezas de interfaz 2D reutilizables (botones, rectangulos, textos).

Notas importantes sobre VTK descubiertas durante el desarrollo:

* ``vtkRenderer.AddActor2D`` ya no existe en VTK 9.7: se usa ``AddViewProp``.
* ``vtkPolyDataMapper2D`` NO escala la geometria con ``SetPosition2``; por eso
  los rectangulos se construyen directamente en **coordenadas de pantalla
  (pixeles)** y se reconstruyen al redimensionar la ventana.
* Los actores 2D se dibujan siempre por encima de la geometria 3D y se apilan
  en el orden en que se anaden al renderer.
* ``vtkTextActor.GetSize`` necesita el viewport: ``GetSize(renderer, [w, h])``.
"""

from __future__ import annotations

import math
import vtk

from . import config


# ---------------------------------------------------------------------------
# Geometria
# ---------------------------------------------------------------------------
def poligono_redondeado(x: float, y: float, w: float, h: float,
                        radio: float = 14.0, resolucion: int = 10) -> vtk.vtkPolyData:
    """Rectangulo de esquinas redondeadas en coordenadas de pantalla."""
    pd = vtk.vtkPolyData()
    celda = vtk.vtkPolygon()

    if radio < 0.5 or w < 2.5 or h < 2.5:
        pts = vtk.vtkPoints()
        for i, (px, py) in enumerate(((x, y), (x + w, y), (x + w, y + h), (x, y + h))):
            pts.InsertNextPoint(px, py, 0.0)
            celda.GetPointIds().InsertNextId(i)
        pd.SetPoints(pts)
        celdas = vtk.vtkCellArray()
        celdas.InsertNextCell(celda)
        pd.SetPolys(celdas)
        return pd

    radio = min(radio, w / 2.0, h / 2.0)
    pts = vtk.vtkPoints()
    esquinas = (
        (x + radio, y + radio, 180.0, 270.0),
        (x + w - radio, y + radio, 270.0, 360.0),
        (x + w - radio, y + h - radio, 0.0, 90.0),
        (x + radio, y + h - radio, 90.0, 180.0),
    )
    indice = 0
    for cx, cy, a0, a1 in esquinas:
        for k in range(resolucion + 1):
            a = math.radians(a0 + (a1 - a0) * k / resolucion)
            pts.InsertNextPoint(cx + radio * math.cos(a), cy + radio * math.sin(a), 0.0)
            celda.GetPointIds().InsertNextId(indice)
            indice += 1
    pd.SetPoints(pts)
    celdas = vtk.vtkCellArray()
    celdas.InsertNextCell(celda)
    pd.SetPolys(celdas)
    return pd


# ---------------------------------------------------------------------------
# Rectangulo 2D en pixeles
# ---------------------------------------------------------------------------
class Rect2D:
    """Rectangulo (con esquinas redondeadas) situado en pixeles de pantalla."""

    def __init__(self, renderer, color, alpha=1.0, radio=14.0, resolucion=10):
        self.renderer = renderer
        self.radio = radio
        self.resolucion = resolucion
        self.rect = (0.0, 0.0, 0.0, 0.0)
        self.mapper = vtk.vtkPolyDataMapper2D()
        self.mapper.ScalarVisibilityOff()
        self.actor = vtk.vtkActor2D()
        self.actor.SetMapper(self.mapper)
        self.actor.PickableOff()
        self.actor.GetProperty().SetColor(*color)
        self.actor.GetProperty().SetOpacity(alpha)
        renderer.AddViewProp(self.actor)

    def colocar(self, x, y, w, h, color=None, alpha=None):
        self.rect = (float(x), float(y), float(w), float(h))
        self.mapper.SetInputData(
            poligono_redondeado(x, y, w, h, self.radio, self.resolucion)
        )
        if color is not None:
            self.actor.GetProperty().SetColor(*color)
        if alpha is not None:
            self.actor.GetProperty().SetOpacity(alpha)

    def color(self, color):
        self.actor.GetProperty().SetColor(*color)

    def opacidad(self, alpha):
        self.actor.GetProperty().SetOpacity(alpha)

    def visibilidad(self, visible):
        self.actor.SetVisibility(bool(visible))

    def contiene(self, px, py):
        x, y, w, h = self.rect
        return x <= px <= x + w and y <= py <= y + h


# ---------------------------------------------------------------------------
# Texto 2D
# ---------------------------------------------------------------------------
class Texto:
    """Etiqueta de texto anclada a pixeles de pantalla."""

    def __init__(self, renderer, texto="", px=18, color=(1.0, 1.0, 1.0),
                 negrita=True, justificar="centro", fondo=None, borde=None,
                 ancho_borde=3, fuente=None, alpha=1.0):
        self.renderer = renderer
        self.propiedad = vtk.vtkTextProperty()
        ruta = fuente if fuente is not None else config.ruta_fuente()
        if ruta:
            self.propiedad.SetFontFile(ruta)
        else:  # pragma: no cover - solo si el sistema no tiene fuentes
            self.propiedad.SetFontFamilyToArial()
        self.propiedad.SetFontSize(px)
        self.propiedad.SetColor(*color)
        self.propiedad.SetBold(negrita)
        self.propiedad.SetOpacity(alpha)
        self._justificar(justificar)
        self.propiedad.SetVerticalJustificationToCentered()
        if fondo is not None:
            self.propiedad.SetBackgroundColor(*fondo)
            self.propiedad.SetBackgroundOpacity(0.98)
            self.propiedad.SetFrame(True)
            self.propiedad.SetFrameColor(*(borde or fondo))
            self.propiedad.SetFrameWidth(ancho_borde)

        self.actor = vtk.vtkTextActor()
        self.actor.SetTextProperty(self.propiedad)
        self.actor.SetInput(texto)
        self.actor.SetTextScaleModeToNone()
        self.actor.PickableOff()
        self.actor.SetPosition(0.0, 0.0)
        renderer.AddViewProp(self.actor)
        self.px = px

    def _justificar(self, modo):
        if modo == "izquierda":
            self.propiedad.SetJustificationToLeft()
        elif modo == "derecha":
            self.propiedad.SetJustificationToRight()
        else:
            self.propiedad.SetJustificationToCentered()

    # -- cambios -----------------------------------------------------------
    def fijar(self, texto=None, px=None, color=None, pos=None, alpha=None,
              negrita=None, justificar=None):
        if texto is not None:
            self.actor.SetInput(texto)
        if px is not None:
            self.px = px
            self.propiedad.SetFontSize(px)
        if color is not None:
            self.propiedad.SetColor(*color)
        if alpha is not None:
            self.propiedad.SetOpacity(alpha)
        if negrita is not None:
            self.propiedad.SetBold(negrita)
        if justificar is not None:
            self._justificar(justificar)
        if pos is not None:
            self.actor.SetPosition(float(pos[0]), float(pos[1]))

    def visibilidad(self, visible):
        self.actor.SetVisibility(bool(visible))

    def medir(self):
        """Tamano del texto en pixeles ``(ancho, alto)``."""
        tam = [0.0, 0.0]
        self.actor.GetSize(self.renderer, tam)
        return (tam[0], tam[1])

    def ajustar_a(self, ancho_max, px_max, px_min=8):
        """Reduce el tamano de fuente hasta que el texto entra en ``ancho_max``."""
        self.propiedad.SetFontSize(px_max)
        self.px = px_max
        actual = px_max
        for _ in range(48):
            ancho, _ = self.medir()
            if ancho <= ancho_max or actual <= px_min:
                break
            actual = max(px_min, int(actual * max(0.5, ancho_max / max(ancho, 1.0)) * 0.99))
            if actual >= px_max:
                actual = px_max - 1
            self.px = actual
            self.propiedad.SetFontSize(actual)
        return self.px

    def envolver_a(self, ancho_max, lineas_max=0):
        """Parte el texto en varias lineas para que no desborde el ancho dado.

        Respeta los saltos de linea explicitos del texto original, y es
        idempotente: volver a envolver un texto ya envuelto no lo degrada.
        """
        original = self.actor.GetInput() or ""
        self.propiedad.SetFontSize(self.px)

        lineas: list[str] = []
        for parrafo in original.split("\n"):
            palabras = parrafo.split()
            if not palabras:
                lineas.append("")
                continue
            actual = ""
            for palabra in palabras:
                tentativa = f"{actual} {palabra}".strip()
                self.actor.SetInput(tentativa)
                ancho_t, _ = self.medir()
                if ancho_t > ancho_max and actual:
                    lineas.append(actual)
                    actual = palabra
                else:
                    actual = tentativa
            lineas.append(actual)

        if lineas_max and len(lineas) > lineas_max:
            lineas = lineas[:lineas_max]
        texto = "\n".join(lineas)
        self.actor.SetInput(texto)
        return texto


# ---------------------------------------------------------------------------
# Boton
# ---------------------------------------------------------------------------
class Boton:
    """Boton rectangular azul con texto centrado, en pixeles de pantalla."""

    def __init__(self, renderer, etiqueta, fuente_px,
                 color, color_hover, color_off, color_texto, color_texto_off,
                 color_borde=None, radio=16, altura=86, color_borde_off=None):
        self.renderer = renderer
        self.altura = altura
        self.fuente_px = fuente_px
        self.color = color
        self.color_hover = color_hover
        self.color_off = color_off
        self.color_texto = color_texto
        self.color_texto_off = color_texto_off
        self.color_borde = color_borde or color
        self.color_borde_off = color_borde_off or (0.34, 0.37, 0.42)
        self.habilitado = True
        self.hover = False
        self.rect = (0.0, 0.0, 0.0, 0.0)

        # El borde se anade antes que el relleno para quedar por debajo.
        self._borde_rect = Rect2D(renderer, self.color_borde, radio=radio)
        self._fondo_rect = Rect2D(renderer, color, radio=radio)
        self._texto = Texto(renderer, etiqueta, fuente_px, color_texto,
                            negrita=True, justificar="centro")

    # -- geometria --------------------------------------------------------
    def colocar(self, x, y, w, h):
        self.rect = (float(x), float(y), float(w), float(h))
        self._borde_rect.colocar(x - 3, y - 3, w + 6, h + 6, color=self._color_borde())
        self._fondo_rect.colocar(x, y, w, h, color=self._color_fondo())
        self._texto.fijar(pos=(x + w / 2.0, y + h / 2.0))
        # La etiqueta se encoge si no cabe en el boton (asi el texto puede
        # crecer sin que se salga de su recuadro).
        self._texto.ajustar_a(max(24.0, w - 26.0), self.fuente_px, px_min=11)

    def _color_fondo(self):
        if not self.habilitado:
            return self.color_off
        return self.color_hover if self.hover else self.color

    def _color_borde(self):
        return self.color_borde if self.habilitado else self.color_borde_off

    def contiene(self, px, py):
        x, y, w, h = self.rect
        return x <= px <= x + w and y <= py <= y + h

    # -- estado -----------------------------------------------------------
    def _refrescar(self):
        self._fondo_rect.color(self._color_fondo())
        self._borde_rect.color(self._color_borde())
        self._texto.fijar(color=self.color_texto if self.habilitado else self.color_texto_off)

    def habilitar(self, valor):
        if self.habilitado != valor:
            self.habilitado = valor
            self._refrescar()

    def pasar_encima(self, valor):
        if self.hover != valor:
            self.hover = valor
            self._refrescar()

    def visibilidad(self, visible):
        visible = bool(visible)
        self._borde_rect.visibilidad(visible)
        self._fondo_rect.visibilidad(visible)
        self._texto.visibilidad(visible)
