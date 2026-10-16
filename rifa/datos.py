"""Carga de participantes desde CSV o Excel, y registro de ganadores.

Sin dependencias obligatorias de VTK. ``openpyxl`` solo se importa cuando
realmente se abre un ``.xlsx``.
"""

from __future__ import annotations

import csv
import datetime as _dt
import os
import re
from dataclasses import dataclass

# Cabeceras reconocidas (normalizadas: minusculas, espacios -> guion bajo)
CAB_NUMERO = {
    "numero", "número", "num", "num_", "n", "no", "nº", "n°", "nro",
    "id", "bolo", "ficha", "boleto", "numero_boleto", "numero_de_boleto", "#",
}
CAB_NOMBRE = {
    "nombre", "nombres", "nombre_completo", "nombre_y_apellidos",
    "name", "full_name", "participante", "persona", "titular",
    "apellido", "apellidos", "beneficiario", "alumno", "socio",
}

# Cabeceras del archivo de resultados (``<lista>_resultados.csv``)
CAB_RES_SESION = {"sesion", "sesión", "session", "ronda", "sorteo"}
CAB_RES_ORDEN = {"orden", "order", "puesto", "posicion", "posición", "turno"}
CAB_RES_FECHA = {"fecha_hora", "fecha", "hora", "date", "timestamp", "cuando", "momento"}
CAB_RES_RESULTADO = {"resultado", "result", "estado", "status"}

EXTENSIONES_CSV = {".csv", ".txt", ".tsv"}
EXTENSIONES_EXCEL = {".xlsx", ".xlsm", ".xltx", ".xltm"}


class ErrorDatos(Exception):
    """Error legible para mostrar al usuario."""


@dataclass(frozen=True)
class Participante:
    numero: int
    nombre: str

    def __str__(self) -> str:  # pragma: no cover - solo depuracion
        return f"{self.numero}: {self.nombre}"


@dataclass(frozen=True)
class Ganador:
    """Una linea del registro de resultados."""

    sesion: str
    orden: int
    numero: int
    nombre: str
    fecha_hora: str = ""
    resultado: str = "gana"

    def __str__(self) -> str:  # pragma: no cover - solo depuracion
        return f"{self.orden}. Nº {self.numero} {self.nombre}"


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and valor == int(valor):
        return str(int(valor))
    return str(valor).strip()


def _normalizar_cabecera(valor) -> str:
    return re.sub(r"\s+", "_", _texto(valor).lower())


def _a_entero(valor) -> int | None:
    """Extrae un entero de una celda, o ``None`` si no parece un numero."""
    if valor is None or isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        if valor != valor:  # NaN
            return None
        return int(round(valor))
    coincidencia = re.search(r"\d+", str(valor))
    return int(coincidencia.group()) if coincidencia else None


def _leer_lineas_csv(ruta: str) -> list[list[str]]:
    with open(ruta, "rb") as fh:
        crudo = fh.read()
    texto = None
    for codificacion in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            texto = crudo.decode(codificacion)
            break
        except UnicodeDecodeError:
            continue
    if texto is None:  # pragma: no cover - latin-1 nunca falla
        raise ErrorDatos("No se pudo leer el archivo: codificacion desconocida.")

    primera = next((l for l in texto.splitlines() if l.strip()), "")
    dialéctica = {",": primera.count(","), ";": primera.count(";"), "\t": primera.count("\t"), "|": primera.count("|")}
    delimitador = max(dialéctica, key=lambda k: dialéctica[k])
    if dialéctica[delimitador] == 0:
        delimitador = ","

    lector = csv.reader(texto.splitlines(), delimiter=delimitador)
    return [fila for fila in lector]


def _leer_lineas_excel(ruta: str) -> list[list]:
    try:
        import openpyxl
    except ImportError as exc:  # pragma: no cover
        raise ErrorDatos(
            "Para leer archivos de Excel hace falta 'openpyxl'.\n"
            "Instalalo con:  .venv/bin/pip install openpyxl"
        ) from exc
    try:
        libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ErrorDatos(f"No se pudo abrir el Excel: {exc}") from exc
    hoja = libro.active
    filas = [list(fila) for fila in hoja.iter_rows(values_only=True)]
    libro.close()
    return filas


# ---------------------------------------------------------------------------
# Deteccion de la estructura
# ---------------------------------------------------------------------------
def _parece_numerica(datos: list[list], columna: int) -> float:
    """Proporcion de filas (de las primeras 50) cuya celda es un numero."""
    total = 0
    numericas = 0
    for fila in datos[:50]:
        if columna >= len(fila) or not _texto(fila[columna]):
            continue
        total += 1
        if _a_entero(fila[columna]) is not None:
            numericas += 1
    return (numericas / total) if total else 0.0


def _detectar_columnas(filas: list[list]) -> tuple[int | None, int | None, list[list]]:
    """Devuelve ``(columna_numero, columna_nombre, filas_de_datos)``."""
    primera = filas[0]
    hay_cabecera = _a_entero(primera[0]) is None if primera else False

    idx_numero: int | None = None
    idx_nombre: int | None = None

    if hay_cabecera:
        for posicion, celda in enumerate(primera):
            clave = _normalizar_cabecera(celda)
            if idx_numero is None and clave in CAB_NUMERO:
                idx_numero = posicion
            elif idx_nombre is None and clave in CAB_NOMBRE:
                idx_nombre = posicion
        datos = filas[1:]
    else:
        datos = filas

    n_columnas = max((len(f) for f in datos), default=len(primera))

    if idx_numero is None and idx_nombre is None:
        # Sin ninguna pista: se deduce el orden mirando los propios datos.
        if n_columnas >= 2:
            if _parece_numerica(datos, 0) >= 0.6:
                idx_numero, idx_nombre = 0, 1
            else:
                idx_nombre, idx_numero = 0, 1
        else:
            idx_nombre, idx_numero = 0, None
    elif idx_numero is None:
        # Se conoce el nombre: se busca una columna que parezca numerica.
        for posicion in range(n_columnas):
            if posicion == idx_nombre:
                continue
            if _parece_numerica(datos, posicion) >= 0.6:
                idx_numero = posicion
                break
    elif idx_nombre is None:
        idx_nombre = 1 if idx_numero == 0 else 0

    if idx_numero is not None and idx_numero == idx_nombre:
        idx_numero = None

    return idx_numero, idx_nombre, datos


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------
def cargar(ruta: str) -> list[Participante]:
    """Lee ``ruta`` (CSV o Excel) y devuelve los participantes ordenados."""
    if not os.path.exists(ruta):
        raise ErrorDatos(f"No existe el archivo:\n{ruta}")

    extension = os.path.splitext(ruta)[1].lower()
    if extension in EXTENSIONES_EXCEL:
        filas = _leer_lineas_excel(ruta)
    elif extension in EXTENSIONES_CSV or extension == "":
        filas = _leer_lineas_csv(ruta)
    else:
        raise ErrorDatos(
            f"Formato no soportado: '{extension}'.\n"
            "Usa un archivo .csv, .xlsx o .xlsm."
        )

    filas = [
        list(fila)
        for fila in filas
        if any(_texto(celda) for celda in (fila or []))
    ]
    if not filas:
        raise ErrorDatos("El archivo no contiene ninguna fila con datos.")

    idx_numero, idx_nombre, datos = _detectar_columnas(filas)
    if not datos:
        raise ErrorDatos(
            "El archivo solo contiene la fila de cabecera, sin participantes."
        )

    def celda(fila: list, indice: int | None):
        if indice is None or indice >= len(fila):
            return None
        return fila[indice]

    participantes: list[Participante] = []
    vistos: dict[int, str] = {}
    duplicados: list[str] = []
    descartadas = 0

    for posicion, fila in enumerate(datos, start=1):
        nombre = _texto(celda(fila, idx_nombre))
        if not nombre:
            descartadas += 1
            continue

        if idx_numero is None:
            numero = posicion
        else:
            numero = _a_entero(celda(fila, idx_numero))
            if numero is None:
                descartadas += 1
                continue

        if numero in vistos:
            duplicados.append(f"{numero} ({vistos[numero]} / {nombre})")
            continue
        vistos[numero] = nombre
        participantes.append(Participante(numero, nombre))

    if not participantes:
        raise ErrorDatos(
            "No se reconoce ninguna columna de nombres con contenido.\n"
            "El archivo debe tener dos columnas: numero y nombre."
        )
    if duplicados:
        raise ErrorDatos(
            "Hay numeros repetidos en el archivo:\n  "
            + "\n  ".join(duplicados[:12])
            + ("\n  ..." if len(duplicados) > 12 else "")
        )

    participantes.sort(key=lambda p: p.numero)
    return participantes


def resumen(participantes: list[Participante]) -> str:
    if not participantes:
        return "Sin participantes cargados"
    numeros = [p.numero for p in participantes]
    faltantes = set(range(min(numeros), max(numeros) + 1)) - set(numeros)
    aviso = f" ({len(faltantes)} sin vender)" if faltantes else ""
    return (
        f"{len(participantes)} participantes · "
        f"numeros {min(numeros)} a {max(numeros)}{aviso}"
    )


def ruta_registro(ruta_entrada: str) -> str:
    """Archivo ``<nombre>_resultados.csv`` que acompana al listado de entrada."""
    ruta_abs = os.path.abspath(ruta_entrada)
    carpeta = os.path.dirname(ruta_abs) or os.getcwd()
    base = os.path.splitext(os.path.basename(ruta_abs))[0] or "rifa"
    return os.path.join(carpeta, f"{base}_resultados.csv")


def ruta_ganadores(ruta_entrada: str) -> str:
    """Archivo de ganadores de la sesion actual, en formato de participantes."""
    ruta_abs = os.path.abspath(ruta_entrada)
    carpeta = os.path.dirname(ruta_abs) or os.getcwd()
    base = os.path.splitext(os.path.basename(ruta_abs))[0] or "rifa"
    return os.path.join(carpeta, f"{base}_ganadores.csv")


def guardar_ganadores_en(ruta_destino: str, ganadores) -> str:
    """Escribe ``ganadores`` en ``ruta_destino`` con el formato de una lista.

    Se conserva **el orden recibido**: quien apila (pantalla, auto-guardado)
    pasa la lista del mas reciente al mas antiguo y asi queda en el archivo.
    Funciona tanto con ``Participante`` como con ``Ganador``.
    """
    with open(ruta_destino, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.writer(fh)
        escritor.writerow(["Número", "Nombre"])
        escritor.writerows((p.numero, p.nombre) for p in ganadores)
    return ruta_destino


def guardar_ganadores(ruta_entrada: str, ganadores) -> str:
    """Reescribe los ganadores actuales como una lista de participantes."""
    return guardar_ganadores_en(ruta_ganadores(ruta_entrada), ganadores)


def _migrar_registro_resultados(destino: str):
    """Completa registros antiguos con la columna ``resultado``."""
    if not os.path.exists(destino) or os.path.getsize(destino) == 0:
        return
    with open(destino, "r", newline="", encoding="utf-8-sig") as fh:
        filas = list(csv.reader(fh))
    if not filas:
        return
    cabeceras = {_normalizar_cabecera(celda) for celda in filas[0]}
    if "resultado" in cabeceras or "result" in cabeceras:
        return
    filas[0].append("resultado")
    for fila in filas[1:]:
        fila.append("gana")
    with open(destino, "w", newline="", encoding="utf-8") as fh:
        csv.writer(fh).writerows(filas)


def registrar_resultado(ruta_entrada: str, sesion: str, orden: int,
                        participante: Participante,
                        resultado: str = "gana") -> str:
    """Anade un giro al registro acumulado y devuelve la ruta usada."""
    resultado = "no_gana" if resultado == "no_gana" else "gana"
    destino = ruta_registro(ruta_entrada)
    _migrar_registro_resultados(destino)
    nuevo = not os.path.exists(destino) or os.path.getsize(destino) == 0
    with open(destino, "a", newline="", encoding="utf-8") as fh:
        escritor = csv.writer(fh)
        if nuevo:
            escritor.writerow([
                "sesion", "orden", "numero", "nombre", "fecha_hora", "resultado",
            ])
        escritor.writerow(
            [
                sesion,
                orden,
                participante.numero,
                participante.nombre,
                _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                resultado,
            ]
        )
    return destino


def registrar_ganador(ruta_entrada: str, sesion: str, orden: int,
                      participante: Participante) -> str:
    """Compatibilidad: registra un ganador con el formato nuevo."""
    return registrar_resultado(ruta_entrada, sesion, orden, participante, "gana")


# ---------------------------------------------------------------------------
# Lectura del registro de resultados (para proyectar la lista de ganadores)
# ---------------------------------------------------------------------------
def _celda(fila: list, indice: int | None):
    if indice is None or indice >= len(fila):
        return None
    return fila[indice]


def _filas_de_archivo(ruta: str) -> list[list]:
    extension = os.path.splitext(ruta)[1].lower()
    if extension in EXTENSIONES_EXCEL:
        return _leer_lineas_excel(ruta)
    if extension in EXTENSIONES_CSV or extension == "":
        return _leer_lineas_csv(ruta)
    raise ErrorDatos(
        f"Formato no soportado: '{extension}'.\n"
        "Usa el archivo .csv de resultados (o un .xlsx)."
    )


def cargar_resultados(ruta: str, solo_ganadores: bool = True) -> list[Ganador]:
    """Lee un archivo de resultados y devuelve sus ganadores en orden.

    Acepta el archivo que genera la propia rifa
    (``sesion,orden,numero,nombre,fecha_hora,resultado``) y es flexible con
    las cabeceras y el orden de las columnas. Los giros ``no_gana`` se
    conservan en el registro, pero no se muestran como ganadores: con
    ``solo_ganadores=False`` se devuelven tambien (campo ``resultado``).
    """
    if not os.path.exists(ruta):
        raise ErrorDatos(f"No existe el archivo:\n{ruta}")

    filas = [
        list(fila)
        for fila in _filas_de_archivo(ruta)
        if any(_texto(celda) for celda in (fila or []))
    ]
    if not filas:
        raise ErrorDatos("El archivo de resultados no contiene ninguna linea.")

    indices: dict[str, int | None] = {
        "sesion": None, "orden": None, "numero": None, "nombre": None,
        "fecha": None, "resultado": None,
    }
    conocidas = 0
    for posicion, celda in enumerate(filas[0]):
        clave = _normalizar_cabecera(celda)
        for campo, cabeceras in (
            ("sesion", CAB_RES_SESION),
            ("orden", CAB_RES_ORDEN),
            ("numero", CAB_NUMERO),
            ("nombre", CAB_NOMBRE),
            ("fecha", CAB_RES_FECHA),
            ("resultado", CAB_RES_RESULTADO),
        ):
            if indices[campo] is None and clave in cabeceras:
                indices[campo] = posicion
                conocidas += 1
                break

    hay_cabecera = (indices["numero"] is not None and indices["nombre"] is not None) \
        or conocidas >= 2
    if not hay_cabecera:
        n_columnas = max((len(fila) for fila in filas), default=0)
        if n_columnas <= 2 and _parece_numerica(filas, 0) >= 0.6:
            # Un simple "numero,nombre" sin cabecera.
            indices = {"sesion": None, "orden": None, "numero": 0,
                       "nombre": 1, "fecha": None, "resultado": None}
        else:
            # Se asume el orden que escribe la rifa.
            indices = {"sesion": 0, "orden": 1, "numero": 2, "nombre": 3,
                       "fecha": 4, "resultado": 5}

    ganadores: list[Ganador] = []
    for fila in (filas[1:] if hay_cabecera else filas):
        nombre = _texto(_celda(fila, indices["nombre"]))
        numero = _a_entero(_celda(fila, indices["numero"]))
        if not nombre and numero is None:
            continue
        orden = _a_entero(_celda(fila, indices["orden"]))
        resultado = _texto(_celda(fila, indices["resultado"])).lower()
        no_gana = resultado in {"no_gana", "no gana", "no-gana", "eliminado"}
        if solo_ganadores and no_gana:
            continue
        ganadores.append(
            Ganador(
                sesion=_texto(_celda(fila, indices["sesion"])),
                orden=orden if orden is not None else len(ganadores) + 1,
                numero=numero if numero is not None else 0,
                nombre=nombre,
                fecha_hora=_texto(_celda(fila, indices["fecha"])),
                resultado="no_gana" if no_gana else "gana",
            )
        )

    if not ganadores:
        raise ErrorDatos(
            "No se reconoce ningun ganador en el archivo.\n"
            "Se esperaba el archivo de resultados de la rifa."
        )
    return ganadores


def agrupar_por_sesion(ganadores: list[Ganador],
                       pila: bool = False) -> list[tuple[str, list[Ganador]]]:
    """Agrupa los ganadores por sesion, respetando el orden de aparicion.

    Con ``pila=True`` cada sesion se invierte: queda el **mas reciente
    arriba** (forma de pila), que es como se rifa de peor premio a mejor.
    """
    grupos: list[tuple[str, list[Ganador]]] = []
    for ganador in ganadores:
        clave = ganador.sesion or "Resultados"
        if not grupos or grupos[-1][0] != clave:
            grupos.append((clave, []))
        grupos[-1][1].append(ganador)
    for _, lista in grupos:
        lista.sort(key=lambda g: g.orden)
        if pila:
            lista.reverse()
    return grupos


# ---------------------------------------------------------------------------
# Continuacion de una sesion interrumpida
# ---------------------------------------------------------------------------
@dataclass
class Continuidad:
    """Estado de una sesion anterior guardado en los archivos de la rifa."""

    ganadores: list[Participante]
    eliminados: list[Participante]
    sesion: str = ""
    giros: int = 0
    contador_modo: int = 0
    cada_cuantos: int | None = None


def candidatos_cada_cuantos(filas: list[Ganador]) -> list[int]:
    """Valores de "cada cuantos giros gana uno" compatibles con ``filas``.

    Un giro ``s`` (1-based) gana si y solo si ``s % cada == 0``; se devuelven
    todos los ``cada`` de 1 a 99 que explican toda la secuencia observada.
    """
    observados = [(g.orden, g.resultado != "no_gana")
                  for g in filas if g.orden and g.orden > 0]
    if not observados:
        return []
    return [
        cada for cada in range(1, 100)
        if all((orden % cada == 0) == gana for orden, gana in observados)
    ]


def inferir_cada_cuantos(filas: list[Ganador]) -> int | None:
    """El unico valor compatible con la sesion, o ``None`` si es ambiguo."""
    candidatos = candidatos_cada_cuantos(filas)
    return candidatos[0] if len(candidatos) == 1 else None


def leer_continuidad(ruta_lista: str) -> Continuidad | None:
    """Lee el estado pendiente de ``ruta_lista`` para poder continuarla.

    Cruza ``<lista>_ganadores.csv`` (guardado en **pila**, mas reciente
    arriba) con la ultima sesion de ``<lista>_resultados.csv``: si los
    numeros coinciden se recuperan tambien los eliminados (``no_gana``),
    la sesion y el contador de giros. Los ganadores y eliminados se
    devuelven en **orden cronologico**, que es como los guarda la app en
    memoria. Devuelve ``None`` si no hay nada que continuar.
    """
    destino = ruta_ganadores(ruta_lista)
    if not os.path.exists(destino) or os.path.getsize(destino) == 0:
        return None
    try:
        filas = cargar_resultados(destino)
    except (ErrorDatos, OSError):
        return None
    archivo = [Participante(g.numero, g.nombre) for g in filas if g.nombre]
    if not archivo:
        return None

    sesion = ""
    ganadores = list(reversed(archivo))     # pila -> cronologico
    eliminados: list[Participante] = []
    giros = len(archivo)
    cada: int | None = None

    registro = ruta_registro(ruta_lista)
    if os.path.exists(registro):
        try:
            todas = cargar_resultados(registro, solo_ganadores=False)
        except (ErrorDatos, OSError):
            todas = []
        grupos = agrupar_por_sesion(todas)
        if grupos:
            _, ultima = grupos[-1]
            gana = [g for g in ultima if g.resultado != "no_gana"]
            if {g.numero for g in gana} == {g.numero for g in archivo}:
                # El registro manda: orden cronologico de verdad.
                ganadores = [Participante(g.numero, g.nombre) for g in gana]
                sesion = ultima[0].sesion
                eliminados = [
                    Participante(g.numero, g.nombre)
                    for g in ultima if g.resultado == "no_gana"
                ]
                giros = max(len(ultima), max((g.orden for g in ultima), default=0))
                cada = inferir_cada_cuantos(ultima)

    return Continuidad(
        ganadores=ganadores,
        eliminados=eliminados,
        sesion=sesion,
        giros=giros,
        contador_modo=giros,
        cada_cuantos=cada,
    )
