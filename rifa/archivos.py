"""Seleccion de archivos y apertura en el gestor de archivos del sistema.

Para elegir un archivo se usa el **selector nativo del escritorio** (XDG
Desktop Portal); en un escritorio KDE es literalmente el cuadro de dialogo del
gestor de archivos (Dolphin), no una ventana propia de la aplicacion. Si el
portal no esta disponible se recurre a ``zenity`` y, como ultimo recurso, a
``tkinter``.

Tambien hay ayudantes para abrir una carpeta o revelar un archivo en el gestor
de archivos por defecto (``xdg-open``, ``dolphin``), pensados para "subir" o
compartir el archivo de resultados.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys

_AQUI = os.path.dirname(os.path.abspath(__file__))
_PORTAL = os.path.join(_AQUI, "_portal_chooser.py")

# Filtros reutilizables: (etiqueta, patrones). El portal y zenity separan los
# patrones con espacios.
FILTRO_PARTICIPANTES = [
    ("Excel o CSV", "*.xlsx *.xlsm *.csv"),
    ("CSV", "*.csv *.txt *.tsv"),
    ("Excel", "*.xlsx *.xlsm"),
    ("Todos los archivos", "*"),
]
FILTRO_RESULTADOS = [
    ("Resultados (CSV)", "*.csv *.txt *.tsv"),
    ("Resultados (Excel)", "*.xlsx *.xlsm"),
    ("Todos los archivos", "*"),
]
FILTRO_GANADORES = [
    ("Ganadores (CSV)", "*.csv *.txt *.tsv"),
    ("Todos los archivos", "*"),
]


# ---------------------------------------------------------------------------
# Interpretes con PyGObject (para el portal)
# ---------------------------------------------------------------------------
_INTERPRETE_GI: str | None = None
_INTERPRETE_BUSCADO = False


def _interprete_con_gi() -> str | None:
    """Primer interprete disponible que pueda ``import gi`` (o ``None``)."""
    global _INTERPRETE_GI, _INTERPRETE_BUSCADO
    if _INTERPRETE_BUSCADO:
        return _INTERPRETE_GI
    _INTERPRETE_BUSCADO = True

    vistos: set[str] = set()
    for candidato in (sys.executable, shutil.which("python3"), "/usr/bin/python3"):
        if not candidato:
            continue
        # Ojo: en un entorno virtual ``.venv/bin/python`` suele ser un enlace
        # al interprete del sistema. Hay que distinguirlos por su ruta literal
        # (el mismo binario con pyvenv.cfg no ve ``gi``, pero el del sistema si).
        clave = os.path.abspath(candidato)
        if clave in vistos or not os.path.exists(candidato):
            continue
        vistos.add(clave)
        try:
            subprocess.run(
                [candidato, "-c", "import gi"],
                check=True, timeout=20,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            _INTERPRETE_GI = candidato
            break
        except Exception:  # noqa: BLE001
            continue
    return _INTERPRETE_GI


# ---------------------------------------------------------------------------
# Dialogos
# ---------------------------------------------------------------------------
def _por_portal(titulo, filtros, carpeta, guardar=False, nombre="", etiqueta=None):
    interprete = _interprete_con_gi()
    if not interprete:
        return False, ""

    argumentos = [interprete, _PORTAL, "--titulo", titulo]
    if guardar:
        argumentos.append("--guardar")
        if etiqueta:
            argumentos += ["--etiqueta", etiqueta]
        if nombre:
            argumentos += ["--nombre", nombre]
    for etiqueta_f, patrones in filtros or []:
        argumentos += ["--filtro", f"{etiqueta_f}={patrones}"]
    if carpeta:
        argumentos += ["--inicial", carpeta]

    try:
        resultado = subprocess.run(
            argumentos, capture_output=True, text=True, timeout=1800,
        )
    except Exception:  # noqa: BLE001
        return False, ""

    if resultado.returncode == 0:
        return True, resultado.stdout.strip()
    if resultado.returncode == 1:
        return True, ""          # cancelado por el usuario
    return False, ""             # portal no disponible: se prueba otro metodo


def _por_zenity(titulo, filtros, carpeta, guardar=False, nombre="", etiqueta=None):
    ejecutable = shutil.which("zenity")
    if not ejecutable:
        return False, ""

    if guardar:
        argumentos = [ejecutable, "--file-selection", f"--title={titulo}", "--save"]
        inicial = os.path.join(carpeta or "", nombre or "")
        if inicial:
            argumentos.append(f"--filename={inicial}")
    else:
        argumentos = [ejecutable, "--file-selection", f"--title={titulo}"]
        for etiqueta_f, patrones in filtros or []:
            argumentos.append(f"--file-filter={etiqueta_f} | {patrones}")
        if carpeta and os.path.isdir(carpeta):
            argumentos.append(f"--filename={os.path.join(carpeta, '')}")

    try:
        resultado = subprocess.run(argumentos, capture_output=True, text=True)
    except Exception:  # noqa: BLE001
        return False, ""

    ruta = resultado.stdout.strip()
    # zenity ya no confirma la sobrescritura (--confirm-overwrite esta
    # obsoleto): se pregunta aqui para no pisar un archivo sin avisar.
    if guardar and ruta and os.path.exists(ruta):
        if preguntar("Sobrescribir archivo",
                     f"Ya existe el archivo:\n{ruta}\n\n¿Quieres reemplazarlo?") is False:
            return True, ""
    return True, ruta


def _por_tkinter(titulo, filtros, carpeta, guardar=False, nombre="", etiqueta=None):
    try:
        import tkinter
        from tkinter import filedialog
    except Exception:  # noqa: BLE001
        return False, ""

    raiz = tkinter.Tk()
    raiz.withdraw()
    try:
        raiz.attributes("-topmost", True)
    except Exception:  # noqa: BLE001
        pass

    tipos = [
        (etiqueta_f, " ".join(patrones.split()))
        for etiqueta_f, patrones in (filtros or [])
    ] or [("Todos los archivos", "*.*")]
    try:
        if guardar:
            ruta = filedialog.asksaveasfilename(
                title=titulo,
                initialdir=carpeta if carpeta and os.path.isdir(carpeta) else None,
                initialfile=nombre or None,
                defaultextension=".csv",
                filetypes=tipos,
            )
        else:
            ruta = filedialog.askopenfilename(
                title=titulo,
                initialdir=carpeta if carpeta and os.path.isdir(carpeta) else None,
                filetypes=tipos,
            )
    finally:
        raiz.destroy()
    return True, ruta or ""


def elegir_archivo(titulo: str, filtros=None, carpeta: str | None = None) -> str:
    """Devuelve la ruta elegida, o ``""`` si el usuario cancela.

    Se intenta primero el selector nativo del escritorio; si no esta
    disponible, zenity y, por ultimo, tkinter.
    """
    for intento in (_por_portal, _por_zenity, _por_tkinter):
        disponible, ruta = intento(titulo, filtros, carpeta)
        if disponible:
            return ruta
    return ""


def guardar_archivo(titulo: str, nombre_sugerido: str = "",
                    filtros=None, carpeta: str | None = None) -> str:
    """Dialogo de **guardado** (no el de carga): devuelve la ruta elegida.

    ``nombre_sugerido`` es la ruta completa que se propone (carpeta + nombre);
    si el usuario cancela devuelve ``""``. El aviso de sobrescritura lo da el
    dialogo nativo (portal y tkinter) y, en zenity, la propia aplicacion.
    """
    nombre = os.path.basename(nombre_sugerido or "")
    carpeta = carpeta or (os.path.dirname(nombre_sugerido) if nombre_sugerido else None)
    for intento in (_por_portal, _por_zenity, _por_tkinter):
        disponible, ruta = intento(titulo, filtros, carpeta, guardar=True,
                                   nombre=nombre, etiqueta="Guardar")
        if disponible:
            return ruta
    return ""


def preguntar(titulo: str, mensaje: str) -> bool | None:
    """Pregunta de si/no con el dialogo nativo.

    Devuelve ``True``/``False`` segun la respuesta y ``None`` si no hay
    ningun dialogo disponible (quien llama decide que hacer sin preguntar).
    """
    zenity = shutil.which("zenity")
    if zenity:
        try:
            resultado = subprocess.run(
                [zenity, "--question", f"--title={titulo}", f"--text={mensaje}"],
                capture_output=True, text=True,
            )
            if resultado.returncode == 0:
                return True
            if resultado.returncode == 1:
                return False
        except Exception:  # noqa: BLE001
            pass

    try:
        import tkinter
        from tkinter import messagebox
    except Exception:  # noqa: BLE001
        return None

    raiz = tkinter.Tk()
    raiz.withdraw()
    try:
        raiz.attributes("-topmost", True)
    except Exception:  # noqa: BLE001
        pass
    try:
        return bool(messagebox.askyesno(titulo, mensaje, parent=raiz))
    except Exception:  # noqa: BLE001
        return None
    finally:
        raiz.destroy()


def pedir_texto(titulo: str, mensaje: str, valor_inicial: str = "") -> str:
    """Pide una linea de texto usando el dialogo nativo disponible."""
    zenity = shutil.which("zenity")
    if zenity:
        try:
            resultado = subprocess.run(
                [zenity, "--entry", f"--title={titulo}", f"--text={mensaje}",
                 f"--entry-text={valor_inicial}"],
                capture_output=True, text=True,
            )
            if resultado.returncode == 0:
                return resultado.stdout.strip()
            return ""
        except Exception:  # noqa: BLE001
            pass

    try:
        import tkinter
        from tkinter import simpledialog
    except Exception:  # noqa: BLE001
        return ""

    raiz = tkinter.Tk()
    raiz.withdraw()
    try:
        try:
            raiz.attributes("-topmost", True)
        except Exception:  # noqa: BLE001
            pass
        respuesta = simpledialog.askstring(
            titulo, mensaje, initialvalue=valor_inicial, parent=raiz,
        )
    finally:
        raiz.destroy()
    return (respuesta or "").strip()


# ---------------------------------------------------------------------------
# Gestor de archivos del sistema
# ---------------------------------------------------------------------------
def _lanzar(comando: list[str]) -> bool:
    try:
        subprocess.Popen(
            comando,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:  # noqa: BLE001
        return False


def abrir_carpeta(carpeta: str) -> bool:
    """Abre ``carpeta`` en el gestor de archivos por defecto del sistema."""
    if not os.path.isdir(carpeta):
        return False
    for comando in (["xdg-open", carpeta], ["dolphin", carpeta],
                    ["nautilus", carpeta], ["thunar", carpeta]):
        if shutil.which(comando[0]):
            if _lanzar(comando):
                return True
    return False


def revelar_archivo(ruta: str) -> bool:
    """Muestra ``ruta`` seleccionada en el gestor de archivos (si se puede)."""
    if not os.path.exists(ruta):
        return abrir_carpeta(os.getcwd())
    dolphin = shutil.which("dolphin")
    if dolphin:
        # Dolphin es el unico que permite dejar el archivo ya seleccionado.
        if _lanzar([dolphin, "--select", ruta]):
            return True
    return abrir_carpeta(os.path.dirname(os.path.abspath(ruta)))
