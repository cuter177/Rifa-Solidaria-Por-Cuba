"""Elementos del momento del reveal: sombreado de fondo, tarjeta y confeti."""

from __future__ import annotations

import math
import random

import vtk

from . import config
from .widgets import Rect2D, Texto


# ---------------------------------------------------------------------------
# Sombreado de fondo
# ---------------------------------------------------------------------------
class Sombra:
    """Quad gigante semitransparente delante de la rueda.

    Es geometria 3D a proposito: los actores 2D (textos y botones) se dibujan
    siempre despues, asi que el nombre del ganador y la tarjeta quedan nitidos
    mientras la rueda se oscurece.
    """

    def __init__(self, renderer):
        plano = vtk.vtkPlaneSource()
        plano.SetXResolution(1)
        plano.SetYResolution(1)
        plano.SetOrigin(-200.0, -200.0, 1.0)
        plano.SetPoint1(200.0, -200.0, 1.0)
        plano.SetPoint2(-200.0, 200.0, 1.0)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(plano.GetOutputPort())
        self.actor = vtk.vtkActor()
        self.actor.SetMapper(mapper)
        self.actor.GetProperty().SetColor(*config.COLOR_SOMBRA)
        self.actor.GetProperty().LightingOff()
        self.actor.GetProperty().SetOpacity(0.0)
        self.actor.SetVisibility(False)
        self.actor.PickableOff()
        renderer.AddViewProp(self.actor)
        self.opacidad = 0.0

    def fijar(self, alpha: float):
        self.opacidad = alpha
        self.actor.GetProperty().SetOpacity(alpha)
        self.actor.SetVisibility(alpha > 0.001)


# ---------------------------------------------------------------------------
# Tarjeta del ganador
# ---------------------------------------------------------------------------
class Tarjeta:
    """Tarjeta central con el numero y el nombre de la persona ganadora."""

    def __init__(self, renderer):
        self.renderer = renderer
        self.ancho = 800.0
        self.alto = 360.0
        self.centro = (0.0, 0.0)

        self._borde = Rect2D(renderer, config.COLOR_TARJETA_BORDE, radio=30)
        self._fondo = Rect2D(renderer, config.COLOR_TARJETA, radio=26)
        self._separador = Rect2D(renderer, config.COLOR_TARJETA_BORDE, radio=0)
        self._titulo = Texto(renderer, "¡HA SALIDO!", config.FUENTE_GANADOR_TITULO,
                             config.DORADO, negrita=True)
        self._numero = Texto(renderer, "Nº 0", config.FUENTE_GANADOR_NUM,
                             config.DORADO, negrita=True)
        self._nombre = Texto(renderer, "", config.FUENTE_GANADOR_NOMBRE,
                             config.BLANCO, negrita=True)
        self._pie = Texto(renderer, "Clic para continuar", config.FUENTE_GANADOR_PIE,
                          config.COLOR_HUD, negrita=False)
        # tamanos de fuente ya ajustados al ancho de la tarjeta (escala 1.0)
        self._px_titulo = config.FUENTE_GANADOR_TITULO
        self._px_numero = config.FUENTE_GANADOR_NUM
        self._px_nombre = config.FUENTE_GANADOR_NOMBRE
        self._px_pie = config.FUENTE_GANADOR_PIE
        self.visible(False)

    # ------------------------------------------------------------------
    def repartir(self, ancho_pantalla: int, alto_pantalla: int):
        """Calcula el tamano y el centro de la tarjeta segun la ventana."""
        self.ancho = max(420.0, min(ancho_pantalla * 0.60, 860.0))
        self.alto = max(230.0, min(alto_pantalla * 0.46, 370.0))
        self.centro = (ancho_pantalla / 2.0, alto_pantalla * 0.5)
        self.colocar(1.0)

    def preparar(self, numero: int, nombre: str):
        """Fija el contenido y calcula los tamanos de fuente definitivos."""
        ancho_util = self.ancho * 0.82
        self._titulo.fijar("¡HA SALIDO EL NÚMERO!")
        self._numero.fijar(f"Nº {numero}")
        self._nombre.fijar(nombre, px=int(self.alto * 0.132))
        self._nombre.envolver_a(self.ancho * 0.80, lineas_max=2)

        self._px_titulo = self._titulo.ajustar_a(ancho_util, int(self.alto * 0.082), px_min=8)
        self._px_numero = self._numero.ajustar_a(ancho_util, int(self.alto * 0.300), px_min=10)
        self._px_nombre = self._nombre.ajustar_a(self.ancho * 0.80, int(self.alto * 0.126), px_min=17)
        self._px_pie = max(14, int(self.alto * 0.055))
        self.colocar(1.0)

    def colocar(self, escala: float = 1.0):
        """Dibuja la tarjeta con zoom ``escala`` desde su centro."""
        escala = max(0.02, escala)
        cx, cy = self.centro
        w = self.ancho * escala
        h = self.alto * escala
        x = cx - w / 2.0
        y = cy - h / 2.0

        alfa = min(1.0, max(0.0, (escala - 0.12) / 0.5))
        self._borde.colocar(x - 4, y - 4, w + 8, h + 8)
        self._fondo.colocar(x, y, w, h)
        self._fondo.opacidad(alfa)
        self._borde.opacidad(alfa)

        def py(frac):
            return cy + frac * h

        def pxf(base):
            return max(4, int(base * escala))

        self._titulo.fijar(px=pxf(self._px_titulo), pos=(cx, py(0.320)))
        self._numero.fijar(px=pxf(self._px_numero), pos=(cx, py(0.035)))
        self._separador.colocar(cx - w * 0.27, py(-0.150) - 1.5, w * 0.54, 3.0)
        self._separador.opacidad(alfa)
        self._nombre.fijar(px=pxf(self._px_nombre), pos=(cx, py(-0.278)))
        self._pie.fijar(px=pxf(self._px_pie), pos=(cx, py(-0.428)))

    def opacidad(self, alfa: float):
        alfa = min(1.0, max(0.0, alfa))
        for texto in (self._titulo, self._numero, self._nombre, self._pie):
            texto.fijar(alpha=alfa)

    def visible(self, valor: bool):
        valor = bool(valor)
        for pieza in (self._borde, self._fondo, self._separador):
            pieza.visibilidad(valor)
        for texto in (self._titulo, self._numero, self._nombre, self._pie):
            texto.visibilidad(valor)


# ---------------------------------------------------------------------------
# Confeti
# ---------------------------------------------------------------------------
class _Pieza:
    __slots__ = ("actor", "transformacion", "x0", "y0", "z0", "vx", "vy",
                 "giro", "vel_giro", "voltereta", "fase", "onda", "retardo",
                 "activa")

    def __init__(self):
        self.activa = False


class Confeti:
    """Pequenas piezas de colores que caen girando sobre el sombreado."""

    GRAVEDAD = 0.72

    def __init__(self, renderer, cantidad=None):
        self.renderer = renderer
        self.cantidad = cantidad or config.CONFETI_PIEZAS
        self.piezas: list[_Pieza] = []
        self.rng = random.Random()
        self._alto_mundo = 2.8
        self._construir()

    def _construir(self):
        for i in range(self.cantidad):
            w = self.rng.uniform(0.016, 0.032)
            h = self.rng.uniform(0.030, 0.062)
            pd = vtk.vtkPolyData()
            puntos = vtk.vtkPoints()
            for px, py in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
                puntos.InsertNextPoint(px, py, 0.0)
            celda = vtk.vtkPolygon()
            for k in range(4):
                celda.GetPointIds().InsertNextId(k)
            celdas = vtk.vtkCellArray()
            celdas.InsertNextCell(celda)
            pd.SetPoints(puntos)
            pd.SetPolys(celdas)

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(pd)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(*self.rng.choice(config.PALETA_CONFETI))
            actor.GetProperty().LightingOff()
            actor.GetProperty().SetOpacity(0.96)
            actor.SetVisibility(False)
            actor.PickableOff()
            transformacion = vtk.vtkTransform()
            actor.SetUserTransform(transformacion)
            self.renderer.AddViewProp(actor)

            pieza = _Pieza()
            pieza.actor = actor
            pieza.transformacion = transformacion
            self.piezas.append(pieza)

    def lanzar(self, ancho_mundo: float = 4.5, alto_mundo: float = 2.8):
        self._alto_mundo = alto_mundo
        centro_x = ancho_mundo * 0.13  # la camara esta desplazada a la derecha
        for pieza in self.piezas:
            pieza.x0 = self.rng.uniform(-ancho_mundo / 2, ancho_mundo / 2) + centro_x
            pieza.y0 = alto_mundo * 0.62 + self.rng.uniform(0.0, 0.5)
            pieza.z0 = self.rng.uniform(2.0, 3.4)
            pieza.vx = self.rng.uniform(-0.20, 0.20)
            pieza.vy = self.rng.uniform(-0.30, -0.05)
            pieza.giro = self.rng.uniform(0, 360)
            pieza.vel_giro = self.rng.uniform(-220, 220)
            pieza.voltereta = self.rng.uniform(-2.2, 2.2)
            pieza.fase = self.rng.uniform(0, 6.283)
            pieza.onda = self.rng.uniform(0.05, 0.22)
            pieza.retardo = self.rng.uniform(0.0, 0.6)
            pieza.activa = True
            pieza.actor.SetVisibility(False)

    def actualizar(self, t: float):
        if t > config.CONFETI_DURACION:
            self.ocultar()
            return
        limite = -self._alto_mundo * 0.5 - 0.25
        for pieza in self.piezas:
            if not pieza.activa:
                continue
            tt = t - pieza.retardo
            if tt < 0.0:
                continue
            pieza.actor.SetVisibility(True)
            y = pieza.y0 + pieza.vy * tt - 0.5 * self.GRAVEDAD * tt * tt
            x = pieza.x0 + pieza.vx * tt + pieza.onda * math.sin(2.1 * tt + pieza.fase)
            pieza.transformacion.Identity()
            pieza.transformacion.Translate(x, y, pieza.z0)
            pieza.transformacion.RotateZ(pieza.giro + pieza.vel_giro * tt)
            pieza.transformacion.RotateY(pieza.voltereta * tt * 360.0)
            pieza.transformacion.Modified()
            if y < limite:
                pieza.activa = False
                pieza.actor.SetVisibility(False)

    def ocultar(self):
        for pieza in self.piezas:
            pieza.activa = False
            pieza.actor.SetVisibility(False)


# ---------------------------------------------------------------------------
# Panel de resultados (lista de ganadores, pensado para proyectar)
# ---------------------------------------------------------------------------
class Historial:
    """Panel a pantalla completa con la lista de ganadores.

    Se dibuja por encima de la rueda con un velo oscuro y una tarjeta grande,
    con texto de buen tamano para que se lea en una proyeccion o retransmision.
    El reparto decide cuantas filas caben; quien lo usa pagina la lista.
    """

    MARGEN_X = 0.06
    MARGEN_Y = 0.06
    MAX_FILAS = 40

    def __init__(self, renderer):
        self.renderer = renderer
        self.max_filas = 1
        self.px_fila = config.FUENTE_HIST_FILA
        self._x_card = self._w_card = 0.0
        self._x_num = self._x_nombre = 0.0
        self._y_centro = 0.0
        self._paso = 1.0

        self._velo = Rect2D(renderer, config.COLOR_SOMBRA, radio=0)
        self._borde = Rect2D(renderer, config.COLOR_TARJETA_BORDE, radio=36)
        self._fondo = Rect2D(renderer, config.COLOR_TARJETA, radio=32)
        self._titulo = Texto(renderer, "GANADORES", config.FUENTE_HIST_TITULO,
                             config.DORADO, negrita=True)
        self._subtitulo = Texto(renderer, "", config.FUENTE_HIST_SUBTITULO,
                                config.COLOR_HUD, negrita=True)
        self._numeros = [
            Texto(renderer, "", self.px_fila, config.COLOR_HIST_FILA,
                  negrita=True, justificar="derecha")
            for _ in range(self.MAX_FILAS)
        ]
        self._nombres = [
            Texto(renderer, "", self.px_fila, config.BLANCO,
                  negrita=False, justificar="izquierda")
            for _ in range(self.MAX_FILAS)
        ]
        self._pie = Texto(renderer, "", config.FUENTE_HIST_PIE,
                          config.COLOR_HUD, negrita=False)
        self.visible(False)

    # ------------------------------------------------------------------
    def repartir(self, ancho: int, alto: int):
        ancho, alto = float(ancho), float(alto)
        self._velo.colocar(0, 0, ancho, alto)
        self._velo.opacidad(config.ALFA_VELO_HIST)

        w = min(ancho * (1.0 - 2.0 * self.MARGEN_X), 1240.0)
        h = min(alto * (1.0 - 2.0 * self.MARGEN_Y), 820.0)
        x = (ancho - w) / 2.0
        y = (alto - h) / 2.0
        self._x_card, self._w_card = x, w
        self._borde.colocar(x - 4, y - 4, w + 8, h + 8)
        self._fondo.colocar(x, y, w, h)

        self._titulo.fijar(px=int(max(20, min(config.FUENTE_HIST_TITULO, h * 0.085))),
                           pos=(ancho / 2.0, y + h * 0.925))
        self._subtitulo.fijar(
            px=int(max(14, min(config.FUENTE_HIST_SUBTITULO, h * 0.052))),
            pos=(ancho / 2.0, y + h * 0.855),
        )
        self._pie.fijar(px=int(max(12, min(config.FUENTE_HIST_PIE, h * 0.044))),
                        pos=(ancho / 2.0, y + h * 0.055))

        # Zona de filas: tantas como quepan con comodidad.
        arriba = y + h * 0.795
        abajo = y + h * 0.135
        self.px_fila = int(max(16, min(config.FUENTE_HIST_FILA, h * 0.046)))
        self._paso = self.px_fila * 1.72
        self.max_filas = max(1, min(self.MAX_FILAS,
                                    int(max(1.0, arriba - abajo) // self._paso)))
        self._y_centro = (arriba + abajo) / 2.0
        self._x_num = x + w * 0.19
        self._x_nombre = x + w * 0.225
        for numero, nombre in zip(self._numeros, self._nombres):
            numero.fijar(px=self.px_fila)
            nombre.fijar(px=self.px_fila)

    # ------------------------------------------------------------------
    def mostrar(self, titulo: str, subtitulo: str, filas, pie: str):
        self._titulo.fijar(titulo)
        self._subtitulo.fijar(subtitulo)
        self._pie.fijar(pie)

        limite = self._x_card + self._w_card * 0.95
        ancho_nombre = max(80.0, limite - self._x_nombre)
        ancho_numero = max(60.0, self._x_num - self._x_card - 0.04 * self._w_card)

        # El bloque de filas se centra verticalmente en su banda.
        y_inicio = self._y_centro + max(0, len(filas) - 1) * self._paso * 0.5
        for i, (numero, nombre) in enumerate(zip(self._numeros, self._nombres)):
            if i < len(filas):
                etiqueta, texto = filas[i]
                y = y_inicio - i * self._paso
                numero.fijar(texto=str(etiqueta), pos=(self._x_num, y))
                nombre.fijar(texto=str(texto), pos=(self._x_nombre, y))
                numero.ajustar_a(ancho_numero, self.px_fila, px_min=13)
                nombre.ajustar_a(ancho_nombre, self.px_fila, px_min=13)
                numero.visibilidad(True)
                nombre.visibilidad(True)
            else:
                numero.visibilidad(False)
                nombre.visibilidad(False)

    # ------------------------------------------------------------------
    def visible(self, valor: bool):
        valor = bool(valor)
        for pieza in (self._velo, self._borde, self._fondo):
            pieza.visibilidad(valor)
        for texto in (self._titulo, self._subtitulo, self._pie):
            texto.visibilidad(valor)
        for numero, nombre in zip(self._numeros, self._nombres):
            numero.visibilidad(valor)
            nombre.visibilidad(valor)
