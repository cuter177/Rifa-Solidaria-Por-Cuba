"""La ruleta en si: disco de sectores, aro, aguja y numeros."""

from __future__ import annotations

import math

import vtk

from . import config
from . import geometria as g
from .widgets import Texto


class Rueda:
    """Disco que gira; los numeros lo acompanan."""

    def __init__(self, renderer):
        self.renderer = renderer
        self.transform = vtk.vtkTransform()
        self.theta = 0.0
        self.restantes: list[int] = []
        self._etiquetas: list[Texto] = []
        self._radios: tuple[float, ...] = (config.RADIO_ETIQUETA,)
        self._piezas: list[vtk.vtkProp] = []          # divisores radiales (rotan)
        self._etiquetas_visibles = True
        self._construir_piezas_fijas()
        # Hasta que no haya participantes la ruleta queda oculta.
        self.visibilidad(False)

    # ------------------------------------------------------------------
    # Construccion estatica
    # ------------------------------------------------------------------
    def _construir_piezas_fijas(self):
        # Aro exterior claro que hace de marco
        disco = vtk.vtkDiskSource()
        disco.SetInnerRadius(0.0)
        disco.SetOuterRadius(config.RADIO_ARO)
        disco.SetCircumferentialResolution(200)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(disco.GetOutputPort())
        self._aro = vtk.vtkActor()
        self._aro.SetMapper(mapper)
        self._aro.GetProperty().SetColor(*config.BLANCO)
        self._aro.GetProperty().LightingOff()
        self._aro.SetPosition(0.0, 0.0, -0.03)
        self.renderer.AddViewProp(self._aro)

        # Buje central
        buje = vtk.vtkDiskSource()
        buje.SetInnerRadius(0.0)
        buje.SetOuterRadius(0.135)
        buje.SetCircumferentialResolution(96)
        mapper_buje = vtk.vtkPolyDataMapper()
        mapper_buje.SetInputConnection(buje.GetOutputPort())
        self._buje = vtk.vtkActor()
        self._buje.SetMapper(mapper_buje)
        self._buje.GetProperty().SetColor(*config.COLOR_HUB)
        self._buje.GetProperty().LightingOff()
        self._buje.SetPosition(0.0, 0.0, 0.05)
        self.renderer.AddViewProp(self._buje)

        anillo = vtk.vtkDiskSource()
        anillo.SetInnerRadius(0.135)
        anillo.SetOuterRadius(0.155)
        anillo.SetCircumferentialResolution(96)
        mapper_anillo = vtk.vtkPolyDataMapper()
        mapper_anillo.SetInputConnection(anillo.GetOutputPort())
        self._anillo = vtk.vtkActor()
        self._anillo.SetMapper(mapper_anillo)
        self._anillo.GetProperty().SetColor(*config.DORADO)
        self._anillo.GetProperty().LightingOff()
        self._anillo.SetPosition(0.0, 0.0, 0.04)
        self.renderer.AddViewProp(self._anillo)

        # Aguja fija arriba, apuntando hacia adentro
        self._aguja = self._crear_aguja(0.30, config.COLOR_AGUJA, 0.085)
        self._aguja_borde = self._crear_aguja(0.28, config.COLOR_AGUJA_BORDE, 0.104)

    def _crear_aguja(self, z, color, semiancho):
        puntos = vtk.vtkPoints()
        puntos.InsertNextPoint(0.0, 0.80, z)
        puntos.InsertNextPoint(-semiancho, 1.14, z)
        puntos.InsertNextPoint(semiancho, 1.14, z)
        triangulo = vtk.vtkTriangle()
        triangulo.GetPointIds().SetId(0, 0)
        triangulo.GetPointIds().SetId(1, 1)
        triangulo.GetPointIds().SetId(2, 2)
        celdas = vtk.vtkCellArray()
        celdas.InsertNextCell(triangulo)
        pd = vtk.vtkPolyData()
        pd.SetPoints(puntos)
        pd.SetPolys(celdas)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*color)
        actor.GetProperty().LightingOff()
        self.renderer.AddViewProp(actor)
        return actor

    # ------------------------------------------------------------------
    # Rueda segun los numeros que siguen en juego
    # ------------------------------------------------------------------
    def establecer_numeros(self, numeros: list[int]):
        """Reconstruye la rueda con los numeros indicados (orden = sectores)."""
        for actor in self._piezas:
            self.renderer.RemoveViewProp(actor)
        for etiqueta in self._etiquetas:
            self.renderer.RemoveViewProp(etiqueta.actor)
        self._piezas.clear()
        self._etiquetas.clear()
        self.restantes = list(numeros)

        n = len(self.restantes)
        if n == 0:
            self._aro.SetVisibility(False)
            self._buje.SetVisibility(False)
            self._anillo.SetVisibility(False)
            self._aguja.SetVisibility(False)
            self._aguja_borde.SetVisibility(False)
            return

        self._aro.SetVisibility(True)
        self._buje.SetVisibility(True)
        self._anillo.SetVisibility(True)
        self._aguja.SetVisibility(True)
        self._aguja_borde.SetVisibility(True)

        self._piezas.append(self._crear_disco(n))
        if n > 1:
            self._piezas.append(self._crear_divisores(n))
        self._crear_etiquetas(n)
        self._todas_las_etiquetas_visibles(self._etiquetas_visibles)

    def _color_sector(self, i: int, n: int):
        paleta = config.PALETA
        if n % len(paleta) != 0 and i == n - 1:
            # Evita que el primer y el ultimo sector compartan color.
            return config.DORADO
        return paleta[i % len(paleta)]

    def _crear_disco(self, n: int) -> vtk.vtkProp:
        """Abanico de sectores de colores.

        Cada sector se dibuja como varios triangulos repartidos a lo largo de
        su arco. Asi el borde exterior es una circunferencia suave y la rueda
        no adquiere aspecto de poligono cuando hay pocos sectores.
        """
        z = 0.0
        pasos = max(1, 160 // max(1, n))      # ~160 segmentos en todo el borde
        puntos = vtk.vtkPoints()
        poligonos = vtk.vtkCellArray()
        colores = vtk.vtkUnsignedCharArray()
        colores.SetNumberOfComponents(3)
        colores.SetName("color")

        for i in range(n):
            a_ini, a_fin = g.rango_sector(i, n)
            color = self._color_sector(i, n)
            rgb = tuple(int(round(c * 255)) for c in color)

            centro = puntos.GetNumberOfPoints()
            puntos.InsertNextPoint(0.0, 0.0, z)
            base = puntos.GetNumberOfPoints()
            for k in range(pasos + 1):
                a = a_ini + (a_fin - a_ini) * k / pasos
                x, y = g.punto(config.RADIO_RUEDA, a)
                puntos.InsertNextPoint(x, y, z)

            for k in range(pasos):
                triangulo = vtk.vtkTriangle()
                triangulo.GetPointIds().SetId(0, centro)
                triangulo.GetPointIds().SetId(1, base + k)
                triangulo.GetPointIds().SetId(2, base + k + 1)
                poligonos.InsertNextCell(triangulo)
                colores.InsertNextTuple3(*rgb)

        pd = vtk.vtkPolyData()
        pd.SetPoints(puntos)
        pd.SetPolys(poligonos)
        pd.GetCellData().SetScalars(colores)

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd)
        mapper.SetScalarModeToUseCellData()
        mapper.SetColorModeToDirectScalars()
        mapper.ScalarVisibilityOn()
        mapper.SetScalarRange(0, 255)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().LightingOff()
        actor.SetUserTransform(self.transform)
        self.renderer.AddViewProp(actor)
        return actor

    def _crear_divisores(self, n: int) -> vtk.vtkProp:
        puntos = vtk.vtkPoints()
        lineas = vtk.vtkCellArray()
        for i in range(n):
            _, a_fin = g.rango_sector(i, n)
            x1, y1 = g.punto(0.148, a_fin)
            x2, y2 = g.punto(config.RADIO_RUEDA, a_fin)
            base = puntos.GetNumberOfPoints()
            puntos.InsertNextPoint(x1, y1, 0.02)
            puntos.InsertNextPoint(x2, y2, 0.02)
            linea = vtk.vtkLine()
            linea.GetPointIds().SetId(0, base)
            linea.GetPointIds().SetId(1, base + 1)
            lineas.InsertNextCell(linea)
        pd = vtk.vtkPolyData()
        pd.SetPoints(puntos)
        pd.SetLines(lineas)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(pd)
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*config.GRIS_DIVISOR)
        actor.GetProperty().SetLineWidth(1.6)
        actor.GetProperty().LightingOff()
        actor.SetUserTransform(self.transform)
        self.renderer.AddViewProp(actor)
        return actor

    def _crear_etiquetas(self, n: int):
        px = config.tamano_etiqueta(n)
        radios = config.radios_etiqueta(n)
        for i in range(n):
            # Sobre las casillas claras (dorado) el numero va oscuro para que
            # se lea bien; sobre azul y rojo, blanco.
            r, g, b = self._color_sector(i, n)
            luminancia = 0.299 * r + 0.587 * g + 0.114 * b
            color = config.COLOR_TEXTO_OSCURO if luminancia > 0.55 else config.BLANCO
            etiqueta = Texto(self.renderer, str(self.restantes[i]), px, color,
                             negrita=True, justificar="centro")
            self._etiquetas.append(etiqueta)
        self._radios = radios

    # ------------------------------------------------------------------
    # Giro
    # ------------------------------------------------------------------
    def fijar_angulo(self, theta: float):
        self.theta = theta
        self.transform.Identity()
        self.transform.RotateZ(theta)
        self.transform.Modified()
        self._colocar_etiquetas()

    def _colocar_etiquetas(self):
        n = len(self._etiquetas)
        if n == 0:
            return
        radios = self._radios or (config.RADIO_ETIQUETA,)
        for i, etiqueta in enumerate(self._etiquetas):
            radio = radios[i % len(radios)]
            angulo = g.centro_sector(i, n) + self.theta
            x, y = g.punto(radio, angulo)
            etiqueta.fijar(pos=self.a_pantalla(x, y, 0.06))

    def a_pantalla(self, x: float, y: float, z: float = 0.0):
        self.renderer.SetWorldPoint(x, y, z, 1.0)
        self.renderer.WorldToDisplay()
        dx, dy, _ = self.renderer.GetDisplayPoint()
        return (dx, dy)

    # ------------------------------------------------------------------
    # Visibilidad
    # ------------------------------------------------------------------
    def _todas_las_etiquetas_visibles(self, visible: bool):
        for etiqueta in self._etiquetas:
            etiqueta.visibilidad(visible)

    def etiquetas_visibles(self, visible: bool):
        self._etiquetas_visibles = visible
        self._todas_las_etiquetas_visibles(visible)

    def visibilidad(self, visible: bool):
        visible = bool(visible)
        for prop in (self._aro, self._buje, self._anillo,
                     self._aguja, self._aguja_borde):
            prop.SetVisibility(visible)
        for pieza in self._piezas:
            pieza.SetVisibility(visible)
        self._todas_las_etiquetas_visibles(visible and self._etiquetas_visibles)

    @property
    def num_sectores(self) -> int:
        return len(self.restantes)
