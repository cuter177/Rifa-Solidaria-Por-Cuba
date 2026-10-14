"""Configuracion central de la Rifa Solidaria por Cuba.

Todos los parametros visuales y de tiempos se pueden ajustar desde aqui.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# Ventana
# --------------------------------------------------------------------------
TITULO = "Rifa Solidaria por Cuba"
ANCHO_INICIAL = 1600
ALTO_INICIAL = 900
ANCHO_MINIMO = 1000
ALTO_MINIMO = 640

# --------------------------------------------------------------------------
# Escena / camara (la rueda vive en coordenadas de mundo, radio 1.0)
# --------------------------------------------------------------------------
RADIO_RUEDA = 1.0
RADIO_ARO = 1.075
RADIO_ETIQUETA = 0.62
CAMARA_FOCO_X = 0.58          # desplaza la rueda hacia la izquierda de la pantalla
ESCALA_PARALELA = 1.36        # media altura visible, en unidades de mundo

# --------------------------------------------------------------------------
# Colores (R, G, B en 0..1)
# --------------------------------------------------------------------------
COLOR_FONDO_ARRIBA = (0.055, 0.125, 0.235)
COLOR_FONDO_ABAJO = (0.012, 0.035, 0.075)
COLOR_SOMBRA = (0.008, 0.024, 0.055)
ALFA_SOMBRA = 0.68            # opacidad final del "sombreado" de fondo
DURACION_SOMBRA = 0.45        # segundos

AZUL = (0.000, 0.165, 0.561)
ROJO = (0.812, 0.078, 0.169)
BLANCO = (0.965, 0.972, 0.985)
DORADO = (0.945, 0.780, 0.361)
NEGRO = (0.000, 0.000, 0.000)
COLOR_TEXTO_OSCURO = (0.075, 0.125, 0.205)
GRIS_DIVISOR = (0.98, 0.98, 0.98)
COLOR_HUB = (0.020, 0.055, 0.115)
COLOR_AGUJA = (0.965, 0.800, 0.330)
COLOR_AGUJA_BORDE = (0.145, 0.090, 0.020)

# Paleta que se repite por toda la rueda (estilo bandera de Cuba)
PALETA = [AZUL, ROJO]

# --------------------------------------------------------------------------
# Botones
# --------------------------------------------------------------------------
AZUL_BOTON = (0.043, 0.325, 0.741)
AZUL_BOTON_HOVER = (0.098, 0.451, 0.894)
AZUL_BOTON_OFF = (0.215, 0.235, 0.265)
AZUL_BOTON_BORDE = (0.478, 0.694, 0.980)
COLOR_TEXTO_BOTON = (1.0, 1.0, 1.0)
COLOR_TEXTO_BOTON_OFF = (0.62, 0.65, 0.70)

FUENTE_BOTON = 38
FUENTE_BOTON_SEC = 27
ANCHO_BOTON_BASE = 300
ALTO_BOTON_BASE = 108
ALTO_BOTON_SEC = 80

# --------------------------------------------------------------------------
# Titulo de la esquina superior izquierda
# --------------------------------------------------------------------------
FUENTE_TITULO = 60
FUENTE_SUBTITULO = 29

# --------------------------------------------------------------------------
# Etiquetas de la rueda
# --------------------------------------------------------------------------
FUENTE_ETIQUETA_MAX = 38
FUENTE_ETIQUETA_MIN = 11

# --------------------------------------------------------------------------
# Animacion del giro
# --------------------------------------------------------------------------
DURACION_GIRO = 6.2           # segundos
VUELTAS_MIN = 6
VUELTAS_MAX = 9
FPS = 60

# --------------------------------------------------------------------------
# Animacion del reveal (sombreado + nombre del ganador)
# --------------------------------------------------------------------------
INICIO_REVEAL = 0.28          # segundos tras empezar el sombreado
DURACION_REVEAL = 0.85
FUENTE_GANADOR_NUM = 176
FUENTE_GANADOR_NOMBRE = 64
FUENTE_GANADOR_TITULO = 32
FUENTE_GANADOR_PIE = 23
COLOR_TARJETA = (0.016, 0.043, 0.086)
COLOR_TARJETA_BORDE = (0.945, 0.780, 0.361)

# --------------------------------------------------------------------------
# Confeti (opcional)
# --------------------------------------------------------------------------
CONFETI = True
CONFETI_PIEZAS = 130
CONFETI_DURACION = 4.5
PALETA_CONFETI = [
    (0.945, 0.780, 0.361),
    (0.965, 0.972, 0.985),
    (0.098, 0.451, 0.894),
    (0.902, 0.192, 0.267),
    (0.290, 0.800, 0.702),
]

# --------------------------------------------------------------------------
# HUD / textos de pantalla
# --------------------------------------------------------------------------
FUENTE_HUD = 21
FUENTE_AVISO = 19
FUENTE_AYUDA = 18
COLOR_HUD = (0.760, 0.815, 0.880)
COLOR_ERROR = (0.988, 0.549, 0.549)

# --------------------------------------------------------------------------
# Panel de resultados (lista de ganadores, pensado para proyectar)
# --------------------------------------------------------------------------
FUENTE_HIST_TITULO = 44
FUENTE_HIST_SUBTITULO = 25
FUENTE_HIST_FILA = 30
FUENTE_HIST_PIE = 20
COLOR_HIST_FILA = (0.945, 0.780, 0.361)   # numero de cada ganador
ALFA_VELO_HIST = 0.88                      # oscurecimiento del fondo

# --------------------------------------------------------------------------
# Adornos: bandera de Cuba, silueta del Che y logos de las organizaciones
# --------------------------------------------------------------------------
MOSTRAR_ADORNOS = True

# Silueta del Che: se usa como marca de agua grande de fondo. La imagen puede
# ser un PNG/JPG/SVG; el fondo claro se vuelve transparente automaticamente.
_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUTA_CHE = os.path.join(_RAIZ, "doc", "che.svg")
COLOR_CHE = (0.72, 0.80, 0.94)   # tono claro para que quede de fondo
OPACIDAD_CHE = 0.16

# Logos de las organizaciones (etiqueta, ruta). Se dibujan como insignias.
LOGOS = [
    ("BREP", os.path.join(_RAIZ, "doc", "breplogo.jpeg")),
    ("FADEP", os.path.join(_RAIZ, "doc", "FadepLOGO.jpg")),
]

# --------------------------------------------------------------------------
# Fuentes del sistema (necesarias para acentos y "n con virgulilla")
# --------------------------------------------------------------------------
FUENTES_CANDIDATAS = (
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
)


def ruta_fuente() -> str | None:
    """Devuelve la primera fuente TrueType disponible en el sistema."""
    for candidata in FUENTES_CANDIDATAS:
        if os.path.exists(candidata):
            return candidata
    return None


def radios_etiqueta(n: int) -> tuple[float, ...]:
    """Radios (en anillos alternos) donde se colocan los numeros.

    Con muchos sectores un solo anillo amontona las etiquetas en el centro;
    repartirlas en 2 o 3 anillos da el triple de espacio angular.
    """
    if n <= 22:
        return (RADIO_ETIQUETA,)
    if n <= 44:
        return (0.50, 0.79)
    return (0.42, 0.645, 0.87)


def tamano_etiqueta(n: int) -> int:
    """Tamano de fuente de los numeros segun cuantos participantes haya."""
    if n <= 0:
        return FUENTE_ETIQUETA_MIN
    escala = (12.0 / n) ** 0.5
    return int(max(FUENTE_ETIQUETA_MIN, min(FUENTE_ETIQUETA_MAX, FUENTE_ETIQUETA_MAX * escala)))
