#!/usr/bin/env python3
"""Selector de archivos nativo del escritorio (XDG Desktop Portal).

La aplicacion lanza este guion en un subproceso usando un interprete con
PyGObject (``gi``). Al usar ``org.freedesktop.portal.FileChooser`` el cuadro de
dialogo es el del sistema; en KDE es el mismo del gestor de archivos (Dolphin),
de modo que no hace falta dibujar una ventana propia.

Codigos de salida:
    0  el usuario eligio un archivo; su ruta se imprime en stdout
    1  el usuario cancelo
    3  el portal no esta disponible (quien lo llamo probara otro metodo)
"""

from __future__ import annotations

import argparse
import os
import sys
from urllib.parse import unquote, urlparse


def _a_ruta(uri: str) -> str:
    partes = urlparse(uri)
    if partes.scheme in ("", "file"):
        return unquote(partes.path)
    return uri


def _opciones(args):
    from gi.repository import GLib

    opciones = {
        "handle_token": GLib.Variant("s", args.token),
        "multiple": GLib.Variant("b", False),
        "directory": GLib.Variant("b", bool(args.carpeta)),
        "modal": GLib.Variant("b", True),
    }

    filtros = []
    for crudo in args.filtro:
        nombre, _, patrones = crudo.partition("=")
        if nombre and patrones:
            filtros.append((nombre, [(0, patrones)]))
    if filtros and not args.carpeta:
        opciones["filters"] = GLib.Variant("a(sa(us))", filtros)

    if args.etiqueta:
        opciones["accept_label"] = GLib.Variant("s", args.etiqueta)
    if args.inicial and os.path.isdir(args.inicial):
        opciones["current_folder"] = GLib.Variant("ay", os.fsencode(args.inicial))
    return opciones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Selector de archivos del escritorio")
    parser.add_argument("--titulo", default="Elegir archivo")
    parser.add_argument("--filtro", action="append", default=[],
                        help="Etiqueta=patron(es), por ejemplo 'CSV=*.csv'")
    parser.add_argument("--inicial", default=None,
                        help="Carpeta donde abrir el dialogo")
    parser.add_argument("--etiqueta", default="Elegir",
                        help="Texto del boton de aceptar")
    parser.add_argument("--carpeta", action="store_true",
                        help="Elegir una carpeta en vez de un archivo")
    args = parser.parse_args(argv)

    try:
        import gi
        from gi.repository import Gio, GLib
    except Exception:  # noqa: BLE001 - PyGObject es opcional
        return 3

    args.token = f"rifa_{os.getpid()}_{os.urandom(4).hex()}"
    try:
        opciones = _opciones(args)
    except Exception:  # noqa: BLE001
        return 3

    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    except Exception:  # noqa: BLE001
        return 3

    remitente = bus.get_unique_name().lstrip(":").replace(".", "_")
    ruta_peticion = f"/org/freedesktop/portal/desktop/request/{remitente}/{args.token}"

    bucle = GLib.MainLoop()
    salida = {"codigo": 1, "ruta": ""}

    def _responder(_conn, _sender, _path, _iface, _signal, params):
        codigo, resultados = params.unpack()
        if codigo == 0:
            uris = resultados.get("uris") or []
            if uris:
                salida["codigo"] = 0
                salida["ruta"] = _a_ruta(uris[0])
        bucle.quit()

    bus.signal_subscribe(
        "org.freedesktop.portal.Desktop",
        "org.freedesktop.portal.Request",
        "Response",
        ruta_peticion,
        None,
        Gio.DBusSignalFlags.NONE,
        _responder,
    )

    try:
        bus.call_sync(
            "org.freedesktop.portal.Desktop",
            "/org/freedesktop/portal/desktop",
            "org.freedesktop.portal.FileChooser",
            "OpenFile",
            GLib.Variant("(ssa{sv})", ("", args.titulo, opciones)),
            None,
            Gio.DBusCallFlags.NONE,
            30000,
            None,
        )
    except Exception:  # noqa: BLE001
        return 3

    # Si nadie responde en 30 minutos, se cierra para no dejar colgada la app.
    GLib.timeout_add_seconds(1800, lambda: (bucle.quit(), False)[1])
    bucle.run()

    if salida["codigo"] == 0 and salida["ruta"]:
        sys.stdout.write(salida["ruta"])
    return salida["codigo"]


if __name__ == "__main__":
    raise SystemExit(main())
