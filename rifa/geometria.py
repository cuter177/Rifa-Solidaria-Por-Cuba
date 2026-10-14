"""Calculos geometricos puros de la ruleta.

Este modulo NO depende de VTK a proposito, para poder probarlo con tests.

Convenio de angulos
-------------------
* Grados, sentido antihorario (el mismo que ``vtkTransform.RotateZ``).
* La aguja ganadora esta fija en ``ANGULO_AGUJA`` (arriba, 12 en punto).
* El sector ``i`` esta **centrado** en ``ANGULO_AGUJA - i*paso``, de modo que
  sin girar la aguja apunta al centro del sector 0 y nunca a una frontera.
  Los sectores avanzan en sentido horario.
* Si la rueda se gira ``theta`` grados, el angulo local ``a`` se convierte
  en el angulo de mundo ``a + theta``.
"""

from __future__ import annotations

import math

ANGULO_AGUJA = 90.0


def paso(n: int) -> float:
    """Ancho angular de cada casilla, en grados."""
    if n <= 0:
        raise ValueError("se necesita al menos un participante")
    return 360.0 / n


def rango_sector(i: int, n: int) -> tuple[float, float]:
    """Arco ``(inicio, fin)`` del sector ``i`` en el sistema local (inicio < fin)."""
    centro = centro_sector(i, n)
    semiancho = paso(n) / 2.0
    return (centro - semiancho, centro + semiancho)


def centro_sector(i: int, n: int) -> float:
    """Angulo local del centro del sector ``i``."""
    return ANGULO_AGUJA - i * paso(n)


def ventana_theta(i: int, n: int) -> tuple[float, float]:
    """Rango de giro ``theta`` para el que el sector ``i`` queda bajo la aguja.

    Ojo: vive en el espacio de ``theta`` (giro de la rueda), no en el de los
    angulos locales de los sectores.
    """
    p = paso(n)
    return (i * p - p / 2.0, i * p + p / 2.0)


def indice_bajo_aguja(theta: float, n: int) -> int:
    """Indice del sector que queda bajo la aguja tras girar ``theta`` grados.

    Con el convenio de arriba la cuenta es directa::

        indice = floor(((theta + paso/2) mod 360) / paso)

    El epsilon evita que un giro que cae justo en la frontera de un sector
    caiga en el sector anterior por error de coma flotante.
    """
    p = paso(n)
    x = ((theta + p / 2.0) % 360.0) + 1e-9
    return min(int(x // p), n - 1)


def theta_para_ganador(
    i: int,
    n: int,
    theta_ini: float,
    vueltas: int,
    rng,
) -> float:
    """Angulo final de giro que deja al sector ``i`` justo bajo la aguja.

    Gira en sentido horario (``theta`` decrece) al menos ``vueltas`` vueltas
    completas y anade un pequeno desvio aleatorio **simetrico respecto al
    centro del sector**, para que la parada no parezca calculada y la aguja
    nunca quede pegada a una frontera.
    """
    p = paso(n)
    desvio = rng.uniform(-0.25, 0.25) * p
    objetivo = i * p + desvio
    delta = vueltas * 360.0 + ((theta_ini - objetivo) % 360.0)
    return theta_ini - delta


def punto(radio: float, angulo: float) -> tuple[float, float]:
    """Punto del plano a ``radio`` distancia y ``angulo`` grados."""
    a = math.radians(angulo)
    return (radio * math.cos(a), radio * math.sin(a))
