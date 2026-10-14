"""Aplicacion: ventana, estado del sorteo, botones y animaciones."""

from __future__ import annotations

import os
import random
import time
from enum import Enum

import vtk

from . import archivos
from . import config
from . import datos
from . import geometria as g
from .adornos import Adornos
from .reveal import Confeti, Historial, Sombra, Tarjeta
from .ruleta import Rueda
from .widgets import Boton, Texto


class Estado(Enum):
    SIN_DATOS = "sin_datos"
    LISTO = "listo"
    GIRANDO = "girando"
    REVELADO = "revelado"
    HISTORIAL = "historial"
    FIN = "fin"


def ease_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return 1.0 - (1.0 - t) ** 4.4


def ease_out_back(t: float, s: float = 1.35) -> float:
    t = min(1.0, max(0.0, t))
    c3 = s + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + s * (t - 1.0) ** 2


class RifaApp:
    def __init__(self, ruta_inicial: str | None = None):
        self.rng = random.Random()
        self.intervalo = max(1, int(1000 / config.FPS))

        self.estado = Estado.SIN_DATOS
        self.ruta: str | None = None
        self.sesion = ""
        self.participantes: list[datos.Participante] = []
        self.restantes: list[datos.Participante] = []
        self.ganadores: list[datos.Participante] = []
        self.eliminados: list[datos.Participante] = []
        self.ultimo: datos.Participante | None = None
        self.ultimo_fue_ganador = True
        self.cada_cuantos_gana = 1
        self.giros = 0
        self.contador_modo = 0
        self._giro_es_ganador = True

        self.theta = 0.0
        self.indice_ganador: int | None = None
        self.anim: dict | None = None
        self.reveal_t0 = 0.0
        self.timer_encendido = False
        self.aviso_activo = False
        self._ocultos = False

        # Panel de resultados
        self._hist_ruta: str | None = None
        self._hist_sesiones: list[tuple[str, list[datos.Ganador]]] = []
        self._hist_sesion = 0
        self._hist_pagina = 0
        self._hist_paginas: list[list[datos.Ganador]] = []

        self._crear_ventana()
        self._crear_escena()
        self._crear_interfaz()
        self._conectar_eventos()
        self._repartir()

        if ruta_inicial:
            self.cargar(ruta_inicial)
        else:
            self._actualizar_hud()
            self._repartir()

    # ==================================================================
    # Construccion
    # ==================================================================
    def _crear_ventana(self):
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.SetWindowName(config.TITULO)
        self.render_window.SetSize(config.ANCHO_INICIAL, config.ALTO_INICIAL)
        self.render_window.SetMultiSamples(0)

        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(*config.COLOR_FONDO_ABAJO)
        self.renderer.SetBackground2(*config.COLOR_FONDO_ARRIBA)
        self.renderer.GradientBackgroundOn()
        self.renderer.SetUseFXAA(True)
        self.render_window.AddRenderer(self.renderer)

        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)
        # Sin estilo interactivo: no queremos que los clics muevan la camara.
        self.interactor.SetInteractorStyle(vtk.vtkInteractorStyleUser())

    def _crear_escena(self):
        self.camara = self.renderer.GetActiveCamera()
        self.camara.ParallelProjectionOn()
        self.camara.SetViewUp(0.0, 1.0, 0.0)
        self.camara.SetClippingRange(0.1, 600.0)
        self.camara.SetPosition(config.CAMARA_FOCO_X, 0.0, 8.0)
        self.camara.SetFocalPoint(config.CAMARA_FOCO_X, 0.0, 0.0)

    def _crear_interfaz(self):
        # --- primero la rueda (para que quede por debajo de todo lo 2D) ---
        self.rueda = Rueda(self.renderer)
        self.sombra = Sombra(self.renderer)
        self.confeti = Confeti(self.renderer)
        self.adornos = Adornos(self.renderer)

        # --- botones azules a la derecha ---
        self.btn_girar = Boton(
            self.renderer, "GIRAR", config.FUENTE_BOTON,
            config.AZUL_BOTON, config.AZUL_BOTON_HOVER,
            config.AZUL_BOTON_OFF, config.COLOR_TEXTO_BOTON,
            config.COLOR_TEXTO_BOTON_OFF, config.AZUL_BOTON_BORDE,
            radio=18, altura=config.ALTO_BOTON_BASE,
        )
        self.btn_cargar = Boton(
            self.renderer, "CARGAR LISTA", config.FUENTE_BOTON_SEC,
            config.AZUL_BOTON, config.AZUL_BOTON_HOVER,
            config.AZUL_BOTON_OFF, config.COLOR_TEXTO_BOTON,
            config.COLOR_TEXTO_BOTON_OFF, config.AZUL_BOTON_BORDE,
            radio=16, altura=config.ALTO_BOTON_SEC,
        )
        self.btn_resultados = Boton(
            self.renderer, "RESULTADOS", config.FUENTE_BOTON_SEC,
            config.AZUL_BOTON, config.AZUL_BOTON_HOVER,
            config.AZUL_BOTON_OFF, config.COLOR_TEXTO_BOTON,
            config.COLOR_TEXTO_BOTON_OFF, config.AZUL_BOTON_BORDE,
            radio=16, altura=config.ALTO_BOTON_SEC,
        )
        self.btn_modo = Boton(
            self.renderer, "MODO: CADA GIRO", config.FUENTE_BOTON_SEC,
            config.AZUL_BOTON, config.AZUL_BOTON_HOVER,
            config.AZUL_BOTON_OFF, config.COLOR_TEXTO_BOTON,
            config.COLOR_TEXTO_BOTON_OFF, config.AZUL_BOTON_BORDE,
            radio=16, altura=config.ALTO_BOTON_SEC,
        )
        self.botones = (self.btn_girar, self.btn_cargar, self.btn_resultados,
                        self.btn_modo)

        self.titulo = Texto(self.renderer, "RIFA SOLIDARIA", config.FUENTE_TITULO,
                            config.DORADO, negrita=True, justificar="izquierda")
        self.subtitulo = Texto(self.renderer, "POR CUBA", config.FUENTE_SUBTITULO,
                               config.COLOR_HUD, negrita=True, justificar="izquierda")
        self.estado_txt = Texto(self.renderer, "", config.FUENTE_HUD, config.COLOR_HUD,
                                negrita=False, justificar="centro")
        self.aviso_txt = Texto(self.renderer, "", config.FUENTE_AVISO, config.COLOR_ERROR,
                               negrita=False, justificar="izquierda")
        self.ayuda_txt = Texto(
            self.renderer,
            "ESPACIO gira · C carga · R resultados · M modo · ESC sale",
            config.FUENTE_AYUDA, (0.52, 0.58, 0.66), negrita=False,
            justificar="izquierda",
        )

        # --- tarjeta del ganador y panel de resultados (van al final: se
        #     dibujan por encima de todo lo demas) ---
        self.tarjeta = Tarjeta(self.renderer)
        self.historial = Historial(self.renderer)

    # ==================================================================
    # Reparto de pantalla
    # ==================================================================
    def _ajustar_camara(self):
        ancho, alto = self.render_window.GetSize()
        ancho = max(320, ancho)
        alto = max(240, alto)
        aspecto = ancho / float(alto)
        escala = max(config.ESCALA_PARALELA, 1.83 / aspecto)
        self.camara.SetParallelScale(escala)
        self.camara.SetPosition(config.CAMARA_FOCO_X, 0.0, 8.0)
        self.camara.SetFocalPoint(config.CAMARA_FOCO_X, 0.0, 0.0)
        self.camara.SetClippingRange(0.1, 600.0)

    def _repartir(self):
        self._ajustar_camara()
        ancho, alto = self.render_window.GetSize()
        ancho = max(320, ancho)
        alto = max(240, alto)

        # Los adornos informan donde termina el bloque de arriba a la derecha
        # (bandera y logos) para no solapar los botones con ellos.
        techo = self.adornos.repartir(ancho, alto)
        self.rueda._colocar_etiquetas()

        # Panel derecho: botones apilados verticalmente.
        escala = max(0.72, min(1.0, alto / 900.0))
        ancho_b = int(max(230.0, min(ancho * 0.24, 350.0)))
        x_b = ancho - ancho_b - int(max(26.0, ancho * 0.028))
        alto_g = int(config.ALTO_BOTON_BASE * escala)
        alto_c = int(config.ALTO_BOTON_SEC * escala)
        hueco = int(max(16.0, alto * 0.026))
        total = alto_g + alto_c + 2 * hueco

        tope = int(alto * 0.56)
        if techo is not None:
            tope = min(tope, int(techo) - 14)
        tope = max(tope, 96 + total)

        y_girar = tope - alto_g
        y_sec = y_girar - hueco - alto_c
        ancho_sec = (ancho_b - hueco) // 2
        self.btn_girar.colocar(x_b, y_girar, ancho_b, alto_g)
        self.btn_cargar.colocar(x_b, y_sec, ancho_sec, alto_c)
        self.btn_resultados.colocar(
            x_b + ancho_sec + hueco, y_sec, ancho_b - ancho_sec - hueco, alto_c,
        )

        ancho_hud = max(360.0, min(ancho * 0.42, 600.0))
        self.estado_txt.fijar(px=config.FUENTE_HUD)
        self.estado_txt.envolver_a(ancho_hud)
        _, alto_hud = self.estado_txt.medir()
        espacio_hud = max(80.0, y_sec - config.HUD_HUECO - 24.0)
        if alto_hud > espacio_hud:
            px_hud = max(24, int(self.estado_txt.px * espacio_hud / alto_hud * 0.96))
            self.estado_txt.fijar(px=px_hud)
            self.estado_txt.envolver_a(ancho_hud)
            _, alto_hud = self.estado_txt.medir()
        self.estado_txt.fijar(pos=(x_b + ancho_b / 2.0,
                                   y_sec - config.HUD_HUECO - alto_hud / 2.0))

        # Titulos arriba a la izquierda (crecen con la ventana).
        px_titulo = int(max(30, min(config.FUENTE_TITULO, ancho * 0.05)))
        px_sub = int(max(16, px_titulo * 0.46))
        self.titulo.fijar(px=px_titulo, pos=(34, alto - int(px_titulo * 1.05)))
        self.subtitulo.fijar(
            px=px_sub,
            pos=(34, alto - int(px_titulo * 1.05) - int(px_sub * 1.5)),
        )
        self._actualizar_modo_boton()
        y_sub = alto - int(px_titulo * 1.05) - int(px_sub * 1.5)
        alto_modo = int(config.ALTO_BOTON_SEC * max(0.72, min(1.0, alto / 900.0)))
        ancho_modo = int(max(250.0, min(ancho * 0.30, 390.0)))
        y_modo = int(max(90.0, y_sub - px_sub / 2.0 - 18.0 - alto_modo))
        self.btn_modo.colocar(34, y_modo, ancho_modo, alto_modo)
        self.aviso_txt.fijar(pos=(34, int(max(70.0, alto * 0.10))))
        self.aviso_txt.envolver_a(max(200.0, ancho * 0.6))
        self.ayuda_txt.fijar(pos=(34, 22))

        if self.estado == Estado.REVELADO:
            self.tarjeta.repartir(ancho, alto)
        elif self.estado == Estado.HISTORIAL:
            self.historial.repartir(ancho, alto)
            self._pintar_historial()

    def _actualizar_modo_boton(self):
        if self.cada_cuantos_gana == 1:
            etiqueta = "MODO: CADA GIRO"
        else:
            etiqueta = f"MODO: CADA {self.cada_cuantos_gana} GIROS"
        self.btn_modo.etiqueta(etiqueta)

    def _ancho_mundo(self) -> float:
        ancho, alto = self.render_window.GetSize()
        aspecto = max(0.4, ancho / float(max(1, alto)))
        return 2.0 * self.camara.GetParallelScale() * aspecto

    def _alto_mundo(self) -> float:
        return 2.0 * self.camara.GetParallelScale()

    # ==================================================================
    # Eventos
    # ==================================================================
    def _conectar_eventos(self):
        self.interactor.AddObserver("TimerEvent", self._on_timer)
        self.interactor.AddObserver("LeftButtonPressEvent", self._on_click)
        self.interactor.AddObserver("MouseMoveEvent", self._on_movimiento)
        self.interactor.AddObserver("KeyPressEvent", self._on_tecla)
        self.render_window.AddObserver("WindowResizeEvent", self._on_resize)

    def _on_resize(self, _obj, _evento):
        self._repartir()
        self.render_window.Render()

    def _on_timer(self, _obj, _evento):
        ahora = time.perf_counter()
        seguir = False
        if self.estado == Estado.GIRANDO:
            seguir = self._paso_giro(ahora)
        elif self.estado == Estado.REVELADO:
            seguir = self._paso_reveal(ahora)
        self.render_window.Render()
        if seguir:
            self.interactor.CreateOneShotTimer(self.intervalo)
        else:
            self.timer_encendido = False

    def _on_movimiento(self, _obj, _evento):
        if self.estado in (Estado.REVELADO, Estado.GIRANDO, Estado.HISTORIAL):
            return
        x, y = self.interactor.GetEventPosition()
        cambio = False
        for boton in self.botones:
            antes = boton.hover
            boton.pasar_encima(boton.habilitado and boton.contiene(x, y))
            cambio = cambio or (antes != boton.hover)
        if cambio:
            self.render_window.Render()

    def _on_click(self, _obj, _evento):
        if self.estado == Estado.REVELADO:
            self._terminar_reveal()
            return
        if self.estado == Estado.HISTORIAL:
            self._avanzar_historial()
            return
        if self.estado == Estado.GIRANDO:
            return
        x, y = self.interactor.GetEventPosition()
        if self.btn_cargar.habilitado and self.btn_cargar.contiene(x, y):
            self._elegir_archivo()
        elif self.btn_resultados.habilitado and self.btn_resultados.contiene(x, y):
            self._elegir_resultados()
        elif self.btn_modo.habilitado and self.btn_modo.contiene(x, y):
            self._elegir_modo()
        elif self.btn_girar.habilitado and self.btn_girar.contiene(x, y):
            self.girar()

    def _on_tecla(self, _obj, _evento):
        tecla = self.interactor.GetKeySym()
        if tecla in ("Escape", "q", "Q"):
            if self.estado == Estado.HISTORIAL:
                self._cerrar_historial()
            else:
                self.interactor.TerminateApp()
        elif tecla in ("space", "Return", "KP_Enter"):
            if self.estado == Estado.REVELADO:
                self._terminar_reveal()
            elif self.estado == Estado.HISTORIAL:
                self._avanzar_historial()
            elif self.estado == Estado.LISTO:
                self.girar()
        elif tecla in ("Left", "Right", "a", "d", "Prior", "Next"):
            if self.estado == Estado.HISTORIAL:
                self._cambiar_sesion(-1 if tecla in ("Left", "a", "Prior") else 1)
        elif tecla in ("r", "R"):
            if self.estado in (Estado.LISTO, Estado.SIN_DATOS, Estado.FIN):
                self._elegir_resultados()
        elif tecla in ("o", "O"):
            if self.estado == Estado.HISTORIAL and self._hist_ruta:
                archivos.revelar_archivo(self._hist_ruta)
        elif tecla in ("c", "C"):
            if self.estado in (Estado.LISTO, Estado.SIN_DATOS, Estado.FIN):
                self._elegir_archivo()
        elif tecla in ("m", "M"):
            if self.estado in (Estado.LISTO, Estado.SIN_DATOS, Estado.FIN):
                self._elegir_modo()

    # ==================================================================
    # Timers
    # ==================================================================
    def _asegurar_timer(self):
        if not self.timer_encendido:
            self.timer_encendido = True
            self.interactor.CreateOneShotTimer(self.intervalo)

    # ==================================================================
    # Giro
    # ==================================================================
    def girar(self):
        if self.estado != Estado.LISTO or not self.restantes:
            return
        n = len(self.restantes)
        self.theta %= 360.0
        indice = self.rng.randrange(n)
        vueltas = self.rng.randint(config.VUELTAS_MIN, config.VUELTAS_MAX)
        destino = g.theta_para_ganador(indice, n, self.theta, vueltas, self.rng)
        self._giro_es_ganador = (
            (self.contador_modo + 1) % self.cada_cuantos_gana == 0
        )

        self.indice_ganador = indice
        self.anim = {
            "t0": time.perf_counter(),
            "duracion": config.DURACION_GIRO,
            "origen": self.theta,
            "destino": destino,
        }
        self.estado = Estado.GIRANDO
        self.btn_girar.habilitar(False)
        self.btn_cargar.habilitar(False)
        self.btn_resultados.habilitar(False)
        self.btn_modo.habilitar(False)
        self._avisar(None)
        self._asegurar_timer()

    def _paso_giro(self, ahora: float) -> bool:
        anim = self.anim
        t = (ahora - anim["t0"]) / anim["duracion"]
        progreso = ease_out(min(1.0, t))
        theta = anim["origen"] + (anim["destino"] - anim["origen"]) * progreso
        self.theta = theta
        self.rueda.fijar_angulo(theta)
        if t >= 1.0:
            self._iniciar_reveal(ahora)
        return True

    # ==================================================================
    # Reveal
    # ==================================================================
    def _iniciar_reveal(self, ahora: float):
        ganador = self.restantes[self.indice_ganador]
        ancho, alto = self.render_window.GetSize()
        self.tarjeta.repartir(ancho, alto)
        self.tarjeta.preparar(ganador.numero, ganador.nombre, self._giro_es_ganador)
        self.tarjeta.visible(True)
        self.tarjeta.colocar(0.10)
        self.tarjeta.opacidad(0.0)

        # Los numeros y los botones se ocultan un poco despues, cuando empieza
        # a entrar la tarjeta: asi la aguja se ve sobre el numero ganador.
        self.sombra.fijar(0.0)
        if config.CONFETI and self._giro_es_ganador:
            self.confeti.lanzar(self._ancho_mundo(), self._alto_mundo())

        self.estado = Estado.REVELADO
        self.reveal_t0 = ahora
        self._ocultos = False
        self.timer_encendido = True

    def _paso_reveal(self, ahora: float) -> bool:
        t = ahora - self.reveal_t0

        progreso_sombra = 1.0
        if config.DURACION_SOMBRA > 0:
            progreso_sombra = min(1.0, t / config.DURACION_SOMBRA)
        self.sombra.fijar(config.ALFA_SOMBRA * ease_out(progreso_sombra))

        t_tarjeta = (t - config.INICIO_REVEAL) / max(0.01, config.DURACION_REVEAL)
        if t_tarjeta > 0.0 and not self._ocultos:
            self._ocultar_interfaz_reveal()
        escala = 0.10 + 0.90 * ease_out_back(t_tarjeta)
        self.tarjeta.colocar(escala)
        self.tarjeta.opacidad(min(1.0, max(0.0, t_tarjeta * 2.2)))

        t_confeti = t - config.INICIO_REVEAL
        if config.CONFETI and self._giro_es_ganador:
            self.confeti.actualizar(max(0.0, t_confeti))

        sigue_animando = t_tarjeta < 1.0
        if config.CONFETI and self._giro_es_ganador:
            sigue_animando = sigue_animando or t_confeti < config.CONFETI_DURACION
        return sigue_animando

    def _ocultar_interfaz_reveal(self):
        self._ocultos = True
        self.rueda.etiquetas_visibles(False)
        self.btn_girar.visibilidad(False)
        self.btn_cargar.visibilidad(False)
        self.btn_resultados.visibilidad(False)
        self.btn_modo.visibilidad(False)
        self.estado_txt.visibilidad(False)
        self.aviso_txt.visibilidad(False)
        self.ayuda_txt.visibilidad(False)

    def _terminar_reveal(self):
        if self.indice_ganador is None or self.indice_ganador >= len(self.restantes):
            self.estado = Estado.LISTO
            return
        ganador = self.restantes.pop(self.indice_ganador)
        es_ganador = self._giro_es_ganador
        self.ultimo = ganador
        self.ultimo_fue_ganador = es_ganador
        if es_ganador:
            self.ganadores.append(ganador)
        else:
            self.eliminados.append(ganador)
        self.giros += 1
        self.contador_modo += 1
        self.indice_ganador = None

        if self.ruta:
            try:
                orden = self.giros
                destino = datos.registrar_resultado(
                    self.ruta, self.sesion, orden, ganador,
                    "gana" if es_ganador else "no_gana",
                )
                if es_ganador:
                    datos.guardar_ganadores(self.ruta, self.ganadores)
                etiqueta = "Ganador" if es_ganador else "No gana"
                print(f"{etiqueta} {ganador.numero:>3}: {ganador.nombre}  ->  {destino}",
                      flush=True)
            except OSError as exc:
                self._avisar(f"No se pudo guardar el registro de ganadores:\n{exc}")

        self.tarjeta.visible(False)
        self.sombra.fijar(0.0)
        self.confeti.ocultar()
        self.btn_girar.visibilidad(True)
        self.btn_cargar.visibilidad(True)
        self.btn_resultados.visibilidad(True)
        self.btn_modo.visibilidad(True)
        self.estado_txt.visibilidad(True)
        self.ayuda_txt.visibilidad(True)
        self.aviso_txt.visibilidad(self.aviso_activo)
        self.rueda.etiquetas_visibles(True)

        self.theta %= 360.0
        self.rueda.establecer_numeros([p.numero for p in self.restantes])
        self.rueda.fijar_angulo(self.theta)
        self.estado = Estado.FIN if not self.restantes else Estado.LISTO
        self._actualizar_hud()
        self._repartir()
        self.render_window.Render()

    # ==================================================================
    # Carga de datos
    # ==================================================================
    def _elegir_archivo(self):
        carpeta = os.path.dirname(os.path.abspath(self.ruta)) if self.ruta else None
        ruta = archivos.elegir_archivo(
            "Selecciona la lista de participantes",
            filtros=archivos.FILTRO_PARTICIPANTES,
            carpeta=carpeta,
        )
        if ruta:
            self.cargar(ruta)

    def cargar(self, ruta: str) -> bool:
        try:
            lista = datos.cargar(ruta)
        except datos.ErrorDatos as exc:
            self._avisar(str(exc))
            return False
        except Exception as exc:  # noqa: BLE001
            self._avisar(f"Error inesperado al leer el archivo:\n{exc}")
            return False

        self.ruta = ruta
        self.sesion = time.strftime("%Y-%m-%d %H:%M:%S")
        self.participantes = lista
        self.restantes = list(lista)
        self.ganadores = []
        self.eliminados = []
        self.ultimo = None
        self.ultimo_fue_ganador = True
        self.giros = 0
        self.contador_modo = 0
        self._giro_es_ganador = True
        self.theta = 0.0
        self.indice_ganador = None
        self.estado = Estado.LISTO

        # Si el panel de resultados estaba abierto, se cierra.
        self.historial.visible(False)
        self._hist_paginas = []
        self._ocultar_ui_historial(False)

        self.rueda.establecer_numeros([p.numero for p in self.restantes])
        self.rueda.etiquetas_visibles(True)
        self.rueda.fijar_angulo(0.0)

        self._avisar(None)
        try:
            datos.guardar_ganadores(self.ruta, self.ganadores)
        except OSError as exc:
            self._avisar(f"No se pudo preparar el archivo de ganadores:\n{exc}")

        self._actualizar_hud()
        self._repartir()
        self.render_window.Render()
        return True

    # ==================================================================
    # Modo del sorteo
    # ==================================================================
    def _elegir_modo(self):
        respuesta = archivos.pedir_texto(
            "Modo del sorteo",
            "Cada cuantos giros gana uno? (1 = gana el que sale)",
            str(self.cada_cuantos_gana),
        )
        if not respuesta:
            return
        try:
            frecuencia = int(respuesta)
        except ValueError:
            self._avisar("Escribe un numero entero entre 1 y 99.")
            return
        if not 1 <= frecuencia <= 99:
            self._avisar("La frecuencia debe estar entre 1 y 99.")
            return
        self.cada_cuantos_gana = frecuencia
        self.contador_modo = 0
        self._avisar(None)
        self._actualizar_hud()
        self._repartir()
        self.render_window.Render()

    # ==================================================================
    # Resultados (lista de ganadores)
    # ==================================================================
    def _elegir_resultados(self):
        carpeta = os.path.dirname(os.path.abspath(self.ruta)) if self.ruta else None
        ruta = archivos.elegir_archivo(
            "Selecciona el archivo de resultados",
            filtros=archivos.FILTRO_RESULTADOS,
            carpeta=carpeta,
        )
        if not ruta:
            return
        try:
            ganadores = datos.cargar_resultados(ruta)
        except datos.ErrorDatos as exc:
            self._avisar(str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            self._avisar(f"No se pudo leer el archivo de resultados:\n{exc}")
            return
        self._abrir_historial(ruta, ganadores)

    def _abrir_historial(self, ruta: str, ganadores: list[datos.Ganador]):
        self._hist_ruta = ruta
        self._hist_sesiones = datos.agrupar_por_sesion(ganadores)
        self._hist_sesion = len(self._hist_sesiones) - 1
        self._hist_pagina = 0

        self._avisar(None)
        self.estado = Estado.HISTORIAL
        self._ocultar_ui_historial(True)

        ancho, alto = self.render_window.GetSize()
        self.historial.repartir(ancho, alto)
        self.historial.visible(True)
        self._pintar_historial()
        self.render_window.Render()

    def _pintar_historial(self):
        if not self._hist_sesiones:
            return
        self._hist_sesion = max(0, min(self._hist_sesion, len(self._hist_sesiones) - 1))
        sesion, ganadores = self._hist_sesiones[self._hist_sesion]

        por_pagina = max(1, self.historial.max_filas)
        self._hist_paginas = [
            ganadores[i:i + por_pagina]
            for i in range(0, len(ganadores), por_pagina)
        ] or [[]]
        self._hist_pagina = max(0, min(self._hist_pagina, len(self._hist_paginas) - 1))
        pagina = self._hist_paginas[self._hist_pagina]

        subtitulo = f"{sesion}  ·  {len(ganadores)} ganadores"
        if len(self._hist_sesiones) > 1:
            subtitulo += f"   (sesión {self._hist_sesion + 1}/{len(self._hist_sesiones)})"
        if len(self._hist_paginas) > 1:
            subtitulo += f"   ·   página {self._hist_pagina + 1}/{len(self._hist_paginas)}"

        filas = [(f"Nº {g.numero}", g.nombre) for g in pagina]
        ultima = self._hist_pagina >= len(self._hist_paginas) - 1
        if ultima:
            pie = "CLIC o ESPACIO: cerrar  ·  A/D: otra sesión  ·  O: abrir carpeta  ·  ESC: cerrar"
        else:
            pie = "CLIC o ESPACIO: siguiente página  ·  A/D: otra sesión  ·  O: abrir carpeta"

        self.historial.mostrar("GANADORES", subtitulo, filas, pie)

    def _avanzar_historial(self):
        if self._hist_pagina < len(self._hist_paginas) - 1:
            self._hist_pagina += 1
            self._pintar_historial()
            self.render_window.Render()
        else:
            self._cerrar_historial()

    def _cambiar_sesion(self, delta: int):
        if len(self._hist_sesiones) < 2:
            return
        self._hist_sesion = (self._hist_sesion + delta) % len(self._hist_sesiones)
        self._hist_pagina = 0
        self._pintar_historial()
        self.render_window.Render()

    def _cerrar_historial(self):
        self.historial.visible(False)
        self._hist_paginas = []
        self._ocultar_ui_historial(False)
        if not self.participantes:
            self.estado = Estado.SIN_DATOS
        elif self.restantes:
            self.estado = Estado.LISTO
        else:
            self.estado = Estado.FIN
        self._actualizar_hud()
        self._repartir()
        self.render_window.Render()

    def _ocultar_ui_historial(self, ocultar: bool):
        visible = not ocultar
        self.rueda.etiquetas_visibles(visible)
        for boton in self.botones:
            boton.visibilidad(visible)
        self.titulo.visibilidad(visible)
        self.subtitulo.visibilidad(visible)
        self.estado_txt.visibilidad(visible)
        self.ayuda_txt.visibilidad(visible)
        self.aviso_txt.visibilidad(visible and self.aviso_activo)

    # ==================================================================
    # HUD
    # ==================================================================
    def _actualizar_hud(self):
        total = len(self.participantes)
        restantes = len(self.restantes)
        ganados = len(self.ganadores)
        eliminados = len(self.eliminados)

        if total == 0:
            texto = "Sin participantes\n\nPulsa CARGAR LISTA"
        elif restantes == 0:
            texto = (
                f"{total} participantes\n"
                f"Ganados: {ganados} · No ganan: {eliminados}\n\n"
                "Sorteo finalizado"
            )
        else:
            proximo = "GANA" if (
                (self.contador_modo + 1) % self.cada_cuantos_gana == 0
            ) else "NO GANA"
            ultimo = "—"
            if self.ultimo is not None:
                estado_ultimo = "gana" if self.ultimo_fue_ganador else "no gana"
                ultimo = f"Nº {self.ultimo.numero} · {estado_ultimo}"
            texto = (
                f"Participantes: {total}\n"
                f"Restantes: {restantes}\n"
                f"Ganados: {ganados} · Eliminados: {eliminados}\n"
                f"Proximo: {proximo} · Ultimo: {ultimo}"
            )
            faltan_para_ganar = self.cada_cuantos_gana - (
                self.contador_modo % self.cada_cuantos_gana
            )
            if restantes < faltan_para_ganar:
                texto += "\nSin suficientes giros para otro ganador"
        self.estado_txt.fijar(texto)
        self.estado_txt.envolver_a(max(360.0, min(
            self.render_window.GetSize()[0] * 0.42, 600.0,
        )))
        self._actualizar_modo_boton()
        self.btn_girar.habilitar(restantes > 0 and self.estado == Estado.LISTO)
        self.btn_cargar.habilitar(True)
        self.btn_resultados.habilitar(self.estado != Estado.HISTORIAL)
        self.btn_modo.habilitar(self.estado not in
                                (Estado.GIRANDO, Estado.REVELADO, Estado.HISTORIAL))

    def _avisar(self, mensaje: str | None):
        if mensaje:
            self.aviso_activo = True
            self.aviso_txt.fijar(mensaje)
            self.aviso_txt.envolver_a(max(220.0, self.render_window.GetSize()[0] * 0.6))
            self.aviso_txt.visibilidad(True)
        else:
            self.aviso_activo = False
            self.aviso_txt.visibilidad(False)

    # ==================================================================
    # Arranque
    # ==================================================================
    def run(self):
        self.render_window.Render()
        self.interactor.Initialize()
        self._repartir()
        self.render_window.Render()
        self.interactor.Start()
