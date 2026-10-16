"""Pruebas del nucleo sin VTK: geometria de la ruleta y carga de archivos.

    .venv/bin/python -m tests.test_core

No necesita pytest: son aserciones puras.
"""

from __future__ import annotations

import os
import random
import shutil
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from rifa import config, datos, geometria as g  # noqa: E402

fallos: list[str] = []


def comprobar(condicion, mensaje):
    if not condicion:
        fallos.append(mensaje)
        print(f"  FALLO  {mensaje}")


def seccion(nombre):
    print(f"\n== {nombre} ==")


# ---------------------------------------------------------------------------
def test_geometria():
    seccion("geometria")

    for n in (1, 2, 3, 7, 12, 60, 200):
        comprobar(abs(g.paso(n) * n - 360.0) < 1e-9, f"paso({n})")

    # El sector 0 esta centrado en la aguja sin girar
    for n in (1, 2, 5, 12, 37):
        comprobar(g.indice_bajo_aguja(0.0, n) == 0, f"theta=0 -> sector 0 (n={n})")
        ini, fin = g.rango_sector(0, n)
        comprobar(ini < fin, f"rango sector 0 ordenado (n={n})")
        comprobar(abs(g.centro_sector(0, n) - g.ANGULO_AGUJA) < 1e-9,
                  f"centro del sector 0 en la aguja (n={n})")
        comprobar(abs(g.centro_sector(0, n) - (ini + fin) / 2.0) < 1e-9,
                  f"el centro cae dentro del rango (n={n})")
        comprobar(abs((fin - ini) - g.paso(n)) < 1e-9, f"ancho del sector (n={n})")

    # Girar exactamente un sector deja el siguiente bajo la aguja
    for n in (3, 8, 12, 25):
        for k in range(n):
            comprobar(g.indice_bajo_aguja(k * g.paso(n), n) == k,
                      f"theta={k}*paso -> sector {k} (n={n})")
            comprobar(g.indice_bajo_aguja(-k * g.paso(n), n) == (n - k) % n,
                      f"theta=-{k}*paso -> sector {(n - k) % n} (n={n})")

    # theta_para_ganador acierta siempre y da al menos las vueltas pedidas
    rng = random.Random(1234)
    for n in (1, 2, 4, 9, 16, 60, 150):
        for _ in range(200):
            theta_ini = rng.uniform(0, 360)
            objetivo = rng.randrange(n)
            vueltas = rng.randint(6, 9)
            destino = g.theta_para_ganador(objetivo, n, theta_ini, vueltas, rng)
            obtenido = g.indice_bajo_aguja(destino, n)
            comprobar(obtenido == objetivo,
                      f"ganador pedido {objetivo} pero salio {obtenido} (n={n})")
            giro = theta_ini - destino
            comprobar(giro >= vueltas * 360 - 1e-6,
                      f"giro insuficiente: {giro} < {vueltas * 360} (n={n})")
            comprobar(giro < (vueltas + 1) * 360 + 1e-6,
                      f"giro excesivo: {giro} (n={n})")

    # El desvio aleatorio nunca cae en el borde exacto del sector: la aguja
    # siempre queda apuntando al interior de la casilla ganadora.
    rng = random.Random(99)
    for _ in range(500):
        n = rng.randint(2, 90)
        i = rng.randrange(n)
        destino = g.theta_para_ganador(i, n, 0.0, 6, rng)
        p = g.paso(n)
        inicio, fin = g.ventana_theta(i, n)
        dentro = ((destino - inicio) % p) / p
        comprobar(0.2 < dentro < 0.8, f"desvio fuera de rango: {dentro} (n={n})")
        # La aguja nunca queda pegada a una frontera de la casilla ganadora.
        distancia = ((destino - i * p + p / 2.0) % p) - p / 2.0
        comprobar(abs(distancia) < 0.3 * p,
                  f"aguja demasiado cerca de la frontera: {distancia} (n={n})")

    # Puntos sobre la circunferencia
    for angulo in (0, 45, 90, 180, 270):
        x, y = g.punto(2.0, angulo)
        comprobar(abs((x * x + y * y) ** 0.5 - 2.0) < 1e-9, f"radio en {angulo} grados")
    x, y = g.punto(1.0, 90)
    comprobar(abs(x) < 1e-9 and abs(y - 1.0) < 1e-9, "punto(1, 90) es el norte")

    # El reparto de ganadores debe ser razonablemente uniforme
    rng = random.Random(5)
    n = 10
    cuenta = [0] * n
    for _ in range(6000):
        w = rng.randrange(n)
        destino = g.theta_para_ganador(w, n, 0.0, 6, rng)
        cuenta[g.indice_bajo_aguja(destino, n)] += 1
    comprobar(sum(cuenta) == 6000, "todos los giros atribuidos")
    comprobar(min(cuenta) > 6000 / n * 0.7, f"reparto desequilibrado: {cuenta}")


# ---------------------------------------------------------------------------
def _escribir(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(contenido)


def test_datos():
    seccion("carga de datos")
    tmp = tempfile.mkdtemp(prefix="rifa_test_")

    # CSV con cabecera numero,nombre
    a = os.path.join(tmp, "a.csv")
    _escribir(a, "numero,nombre\n1,Ana\n2,José Muñiz\n3,María\n")
    lista = datos.cargar(a)
    comprobar([p.numero for p in lista] == [1, 2, 3], "csv cabecera: numeros")
    comprobar(lista[1].nombre == "José Muñiz", "csv cabecera: acentos")

    # CSV con punto y coma (formato espanol) y cabeceras acentuadas
    b = os.path.join(tmp, "b.csv")
    _escribir(b, "Número;Nombre\n10;Luis\n20;Elena\n")
    lista = datos.cargar(b)
    comprobar([p.numero for p in lista] == [10, 20], "csv ';' y cabecera acentuada")

    # CSV sin cabecera: dos columnas, numero y nombre
    c = os.path.join(tmp, "c.csv")
    _escribir(c, "1,Ana\n2,Bea\n")
    lista = datos.cargar(c)
    comprobar([p.numero for p in lista] == [1, 2], "csv sin cabecera")

    # CSV de una sola columna: se numera por orden de fila
    d = os.path.join(tmp, "d.csv")
    _escribir(d, "nombre\nAna\nBea\nCarlos\n")
    lista = datos.cargar(d)
    comprobar([p.numero for p in lista] == [1, 2, 3], "csv una columna se autonumera")
    comprobar([p.nombre for p in lista] == ["Ana", "Bea", "Carlos"], "csv una columna nombres")

    # Filas vacias y numeros desordenados
    e = os.path.join(tmp, "e.csv")
    _escribir(e, "numero,nombre\n5,Eva\n\n,,\n2,Ana\n")
    lista = datos.cargar(e)
    comprobar([p.numero for p in lista] == [2, 5], "orden ascendente y filas vacias ignoradas")

    # Numeros con ruido ("Nº 12")
    f = os.path.join(tmp, "f.csv")
    _escribir(f, "numero,nombre\nNº 12,Pedro\n7,Julia\n")
    lista = datos.cargar(f)
    comprobar([p.numero for p in lista] == [7, 12], "numeros con prefijo")

    # Duplicados -> error legible
    dd = os.path.join(tmp, "dup.csv")
    _escribir(dd, "numero,nombre\n1,Ana\n1,Otra Ana\n")
    try:
        datos.cargar(dd)
        comprobar(False, "los duplicados deberian dar error")
    except datos.ErrorDatos as exc:
        comprobar("repetidos" in str(exc), "mensaje de duplicados")

    # Excel
    try:
        import openpyxl

        x = os.path.join(tmp, "x.xlsx")
        libro = openpyxl.Workbook()
        hoja = libro.active
        hoja.append(["numero", "nombre"])
        hoja.append([3, "Nélida"])
        hoja.append([1, "Oscar"])
        libro.save(x)
        lista = datos.cargar(x)
        comprobar([p.numero for p in lista] == [1, 3], "xlsx ordenado")
        comprobar(lista[0].nombre == "Oscar", "xlsx nombres")
    except ImportError:
        print("  (openpyxl no disponible: se omite la prueba de Excel)")

    # Registro de ganadores
    lista = datos.cargar(a)
    reg = datos.ruta_registro(a)
    comprobar(reg.endswith("a_resultados.csv"), f"nombre del registro: {reg}")
    if os.path.exists(reg):
        os.remove(reg)
    datos.registrar_ganador(a, "sesion-1", 1, lista[0])
    datos.registrar_ganador(a, "sesion-1", 2, lista[1])
    datos.registrar_ganador(a, "sesion-2", 1, lista[2])
    with open(reg, encoding="utf-8") as fh:
        lineas = fh.read().strip().splitlines()
    comprobar(len(lineas) == 4, f"registro con cabecera + 3 lineas, hay {len(lineas)}")
    comprobar(lineas[0].startswith("sesion,orden,numero,nombre"), "cabecera del registro")
    comprobar("Ana" in lineas[1], "primera linea del registro")
    comprobar("sesion-2" in lineas[3], "el registro distingue las sesiones")
    os.remove(reg)

    # Archivo inexistente y formato raro
    try:
        datos.cargar(os.path.join(tmp, "nada.csv"))
        comprobar(False, "un archivo inexistente deberia fallar")
    except datos.ErrorDatos:
        pass
    raro = os.path.join(tmp, "raro.pdf")
    _escribir(raro, "x")
    try:
        datos.cargar(raro)
        comprobar(False, "un formato no soportado deberia fallar")
    except datos.ErrorDatos:
        pass


# ---------------------------------------------------------------------------
def test_resultados():
    seccion("lectura del registro de resultados")
    tmp = tempfile.mkdtemp(prefix="rifa_res_")

    # Archivo tal como lo escribe la rifa
    r = os.path.join(tmp, "lista_resultados.csv")
    _escribir(
        r,
        "sesion,orden,numero,nombre,fecha_hora\n"
        "2026-01-01 10:00:00,1,5,Pedro,2026-01-01 10:00:01\n"
        "2026-01-01 10:00:00,2,9,Ana,2026-01-01 10:00:05\n"
        "2026-01-02 11:00:00,1,3,José,2026-01-02 11:00:00\n",
    )
    ganadores = datos.cargar_resultados(r)
    comprobar(len(ganadores) == 3, f"3 ganadores, hay {len(ganadores)}")
    comprobar(ganadores[0].numero == 5 and ganadores[0].nombre == "Pedro",
              "primer ganador leido")
    comprobar(ganadores[2].nombre == "José", "acentos en resultados")
    grupos = datos.agrupar_por_sesion(ganadores)
    comprobar(len(grupos) == 2, f"dos sesiones, hay {len(grupos)}")
    comprobar([g.numero for g in grupos[0][1]] == [5, 9], "sesion 1 ordenada")
    comprobar([g.numero for g in grupos[1][1]] == [3], "sesion 2")

    # Sin cabecera: se asume el orden que escribe la rifa
    s = os.path.join(tmp, "sin_cabecera.csv")
    _escribir(s, "s1,1,7,Luis\ns1,2,2,Marta\n")
    ganadores = datos.cargar_resultados(s)
    comprobar([g.numero for g in ganadores] == [7, 2], "resultados sin cabecera")
    comprobar(ganadores[1].nombre == "Marta", "nombres sin cabecera")

    # Solo numero y nombre (sin cabecera reconocible)
    t = os.path.join(tmp, "solo_dos.csv")
    _escribir(t, "4,Carmen\n8,Raúl\n")
    ganadores = datos.cargar_resultados(t)
    comprobar(len(ganadores) == 2, "dos columnas dan dos ganadores")

    # Vacio -> error legible
    v = os.path.join(tmp, "vacio.csv")
    _escribir(v, "sesion,orden,numero,nombre,fecha_hora\n")
    try:
        datos.cargar_resultados(v)
        comprobar(False, "un archivo sin ganadores deberia fallar")
    except datos.ErrorDatos:
        pass


# ---------------------------------------------------------------------------
def test_integracion_ejemplos():
    seccion("ejemplos del repositorio")
    carpeta = os.path.join(RAIZ, "ejemplos")
    if not os.path.isdir(carpeta):
        print("  (no hay carpeta de ejemplos: se omite)")
        return
    for nombre in ("participantes.csv", "participantes.xlsx",
                   "rifa_grande.csv", "rifa_grande.xlsx"):
        ruta = os.path.join(carpeta, nombre)
        if not os.path.exists(ruta):
            print(f"  (falta {nombre}: se omite)")
            continue
        lista = datos.cargar(ruta)
        comprobar(len(lista) > 0, f"{nombre} tiene participantes")
        numeros = [p.numero for p in lista]
        comprobar(numeros == sorted(numeros), f"{nombre} viene ordenado")
        comprobar(len(set(numeros)) == len(numeros), f"{nombre} sin duplicados")

        # Simulacion completa de un sorteo sin reposicion
        rng = random.Random(11)
        restantes = list(lista)
        theta = 0.0
        ganados = []
        while restantes:
            n = len(restantes)
            w = rng.randrange(n)
            theta = g.theta_para_ganador(w, n, theta % 360, rng.randint(6, 9), rng)
            comprobar(g.indice_bajo_aguja(theta, n) == w, f"{nombre}: giro coherente")
            ganados.append(restantes.pop(w).numero)
        comprobar(sorted(ganados) == sorted(numeros), f"{nombre}: todos ganan una vez")


# ---------------------------------------------------------------------------
def test_pila_guardado_y_continuidad():
    seccion("pila, guardado y continuacion")
    tmp = tempfile.mkdtemp(prefix="rifa_pila_")

    def fila(sesion, orden, numero, nombre, resultado="gana"):
        return datos.Ganador(sesion, orden, numero, nombre, "", resultado)

    # -- forma de pila: lo mas reciente arriba dentro de cada sesion --------
    filas = [fila("s1", 1, 5, "Pedro"), fila("s1", 2, 9, "Ana"),
             fila("s2", 1, 3, "José")]
    grupos = datos.agrupar_por_sesion(filas, pila=True)
    comprobar(len(grupos) == 2, "dos sesiones al agrupar")
    comprobar([g.numero for g in grupos[0][1]] == [9, 5], "s1 en forma de pila")
    comprobar([g.numero for g in grupos[1][1]] == [3], "s2 en forma de pila")
    cronologico = datos.agrupar_por_sesion(filas)
    comprobar([g.numero for g in cronologico[0][1]] == [5, 9],
              "por defecto sigue en orden cronologico")
    comprobar(grupos[-1][0] == "s2", "la sesion mas reciente sigue al final")

    # -- el archivo se escribe con el orden que se le da -------------------
    lista = [datos.Participante(n, f"Persona {n}") for n in (1, 2, 3)]
    entrada = os.path.join(tmp, "lista.csv")
    _escribir(entrada, "numero,nombre\n1,Persona 1\n2,Persona 2\n3,Persona 3\n")
    destino = datos.guardar_ganadores(entrada, list(reversed(lista)))
    comprobar(destino == datos.ruta_ganadores(entrada),
              "guardar_ganadores usa <lista>_ganadores.csv")
    with open(destino, encoding="utf-8") as fh:
        lineas = fh.read().strip().splitlines()
    comprobar(lineas[0] == "Número,Nombre", f"cabecera, hay {lineas[0]!r}")
    comprobar(lineas[1].startswith("3,"), f"el mas reciente primero: {lineas[1]!r}")
    comprobar(len(lineas) == 4, "cabecera + 3 ganadores")

    # El mismo archivo sirve como lista de participantes y como resultados.
    recargada = datos.cargar(destino)
    comprobar([p.numero for p in recargada] == [1, 2, 3],
              "se puede recargar como lista de participantes")
    como_resultados = datos.cargar_resultados(destino)
    comprobar([g.numero for g in como_resultados] == [3, 2, 1],
              "y se puede abrir en la pantalla de resultados (pila)")

    # -- leer el registro incluyendo los giros que no ganan ----------------
    reg = os.path.join(tmp, "r_resultados.csv")
    _escribir(
        reg,
        "sesion,orden,numero,nombre,fecha_hora,resultado\n"
        "s1,1,5,Pedro,t,gana\n"
        "s1,2,9,Ana,t,no_gana\n",
    )
    todos = datos.cargar_resultados(reg, solo_ganadores=False)
    comprobar(len(todos) == 2, f"solo_ganadores=False devuelve 2, hay {len(todos)}")
    comprobar(todos[1].resultado == "no_gana", "conserva el campo resultado")
    comprobar(len(datos.cargar_resultados(reg)) == 1, "por defecto solo ganadores")

    # -- inferencia del modo "cada cuantos giros gana uno" -----------------
    def secuencia(patrones):
        return [fila("s", i + 1, i + 1, f"p{i + 1}", resultado)
                for i, resultado in enumerate(patrones)]

    comprobar(datos.inferir_cada_cuantos(secuencia(["gana"])) == 1, "modo 1")
    comprobar(datos.inferir_cada_cuantos(
        secuencia(["no_gana", "gana"])) == 2, "modo 2")
    comprobar(datos.inferir_cada_cuantos(
        secuencia(["no_gana", "no_gana", "gana"])) == 3, "modo 3")
    comprobar(datos.inferir_cada_cuantos(
        secuencia(["no_gana"] * 3 + ["gana"] + ["no_gana"] * 3 + ["gana"])) == 4,
        "modo 4 con dos ciclos")
    comprobar(datos.inferir_cada_cuantos(secuencia(["no_gana", "no_gana"])) is None,
              "patron incompleto -> ambiguo (None)")
    comprobar(datos.inferir_cada_cuantos([]) is None, "sin giros -> None")

    # -- continuacion de una sesion interrumpida ---------------------------
    lista2 = os.path.join(tmp, "continuar.csv")
    _escribir(lista2, "numero,nombre\n1,Ana\n2,Bea\n3,Caro\n4,Dana\n")
    comprobar(datos.leer_continuidad(lista2) is None,
              "sin archivo de ganadores no hay nada que continuar")

    # Sin registro, el archivo en pila se devuelve en orden cronologico.
    gente = datos.cargar(lista2)
    datos.guardar_ganadores(lista2, [gente[3], gente[1]])   # pila: 4, 2
    solo_archivo = datos.leer_continuidad(lista2)
    comprobar([g.numero for g in solo_archivo.ganadores] == [2, 4],
              "pila del archivo -> cronologico en memoria")
    comprobar(solo_archivo.sesion == "", "sin registro no hay sesion")

    datos.registrar_resultado(lista2, "S-1", 1, gente[0], "no_gana")
    datos.registrar_resultado(lista2, "S-1", 2, gente[1], "gana")
    datos.registrar_resultado(lista2, "S-1", 3, gente[2], "no_gana")
    datos.registrar_resultado(lista2, "S-1", 4, gente[3], "gana")
    datos.guardar_ganadores(lista2, [gente[3], gente[1]])   # ya en pila

    c = datos.leer_continuidad(lista2)
    comprobar(c is not None, "hay continuidad con registro")
    comprobar([g.numero for g in c.ganadores] == [2, 4],
              "ganadores en orden cronologico (el registro manda)")
    comprobar([g.numero for g in c.eliminados] == [1, 3],
              "eliminados recuperados del registro")
    comprobar(c.sesion == "S-1", f"sesion recuperada: {c.sesion!r}")
    comprobar(c.giros == 4 and c.contador_modo == 4, "contador de giros")
    comprobar(c.cada_cuantos == 2, f"modo inferido: {c.cada_cuantos}")

    # Ganadores que no coinciden con el registro: no se inventa nada.
    datos.guardar_ganadores(lista2, [gente[0]])
    c2 = datos.leer_continuidad(lista2)
    comprobar(c2 is not None, "sigue habiendo continuidad")
    comprobar(c2.sesion == "", "sin coincidencia no se recupera la sesion")
    comprobar(c2.eliminados == [], "sin coincidencia no hay eliminados")
    comprobar(c2.cada_cuantos is None, "sin coincidencia el modo es desconocido")
    comprobar(c2.ganadores[0].numero == 1, "pero los ganadores se conservan")


# ---------------------------------------------------------------------------
def test_dialogos_guardado():
    seccion("dialogo de guardado (sin abrir ventanas)")
    from rifa import archivos

    llamadas: list[list[str]] = []
    respuestas: list[str] = []      # rutas que "elige" el usuario

    class _Resultado:
        returncode = 0
        stdout = ""
        stderr = ""

    def _falso_run(argumentos, **kwargs):
        argumentos = [str(a) for a in argumentos]
        llamadas.append(argumentos)
        res = _Resultado()
        res.stdout = respuestas[-1] if respuestas else ""
        if any("_portal_chooser.py" in a for a in argumentos):
            res.returncode = 3          # el portal no esta disponible
        if kwargs.get("check") and res.returncode != 0:
            raise subprocess.CalledProcessError(res.returncode, argumentos)
        return res

    original_which, original_run = shutil.which, subprocess.run
    original_preguntar = archivos.preguntar
    respaldo_preguntar: list[bool | None] = []
    try:
        shutil.which = lambda n: "/usr/bin/zenity" if n == "zenity" else original_which(n)
        subprocess.run = _falso_run
        archivos.preguntar = lambda t, m: respaldo_preguntar.append(True) or True

        ruta = archivos.guardar_archivo(
            "Guardar ganadores", "/tmp/ganadores.csv",
            archivos.FILTRO_GANADORES, "/tmp",
        )
        comprobar(ruta == "", "cancelar el dialogo devuelve cadena vacia")
        comprobar(not respaldo_preguntar, "sin archivo no se pregunta por sobrescribir")

        # El portal se invoca con el metodo de guardado y el nombre propuesto.
        portal = [c for c in llamadas
                  if any("_portal_chooser.py" in a for a in c)]
        comprobar(len(portal) == 1, "se prueba primero el portal de escritorio")
        if portal:
            comprobar("--guardar" in portal[0],
                      f"el portal usa SaveFile: {portal[0]}")
            comprobar("--nombre" in portal[0] and "ganadores.csv" in portal[0],
                      "el portal lleva el nombre propuesto")

        zenity = [c for c in llamadas if c and "zenity" in c[0]]
        comprobar(len(zenity) == 1, f"se usa zenity como backend: {llamadas}")
        comando = zenity[0]
        comprobar("--save" in comando, f"es un dialogo de guardado: {comando}")
        comprobar("--confirm-overwrite" not in comando,
                  "no pasa la opcion obsoleta de zenity")
        comprobar("--filename=/tmp/ganadores.csv" in comando,
                  f"sugiere el nombre de archivo: {comando}")
        comprobar("--title=Guardar ganadores" in comando, "lleva el titulo")

        # Si el archivo elegido ya existe, se pregunta antes de pisarlo.
        destino = os.path.join(tempfile.mkdtemp(prefix="rifa_guard_"), "y.csv")
        _escribir(destino, "Número,Nombre\n1,Ana\n")
        respuestas.append(destino)
        respaldo_preguntar.clear()
        archivos.preguntar = lambda t, m: respaldo_preguntar.append(False) or False
        ruta = archivos.guardar_archivo("Guardar ganadores", destino, None, None)
        comprobar(ruta == "", "responder no a sobrescribir cancela el guardado")
        comprobar(len(respaldo_preguntar) == 1, "se pregunta si el archivo existe")

        archivos.preguntar = lambda t, m: respaldo_preguntar.append(True) or True
        ruta = archivos.guardar_archivo("Guardar ganadores", destino, None, None)
        comprobar(ruta == destino, "responder si deja guardar")
    finally:
        shutil.which = original_which
        subprocess.run = original_run
        archivos.preguntar = original_preguntar


# ---------------------------------------------------------------------------
def test_total_boletos():
    seccion("total de boletos de la rifa")
    tmp = tempfile.mkdtemp(prefix="rifa_total_")
    comprobar(config.TOTAL_NUMEROS is None or config.TOTAL_NUMEROS > 0,
              "TOTAL_NUMEROS es None o un entero positivo")

    # Se usan 10 boletos para la prueba, al margen del valor real de config.
    original = config.TOTAL_NUMEROS
    config.TOTAL_NUMEROS = 10
    try:
        # Archivo tipico: tres vendidos, dos filas sin nombre y sin mas.
        a = os.path.join(tmp, "a.csv")
        _escribir(a, "numero,nombre\n1,Ana\n2,Bea\n3,Caro\n4,\n5,\n")
        lista, total = datos.cargar_con_total(a)
        comprobar([p.numero for p in lista] == [1, 2, 3],
                  "los boletos sin nombre quedan fuera de la lista")
        comprobar(total == 10, f"el minimo de config marca el total: {total}")
        comprobar(datos.resumen(lista, total) ==
                  "3 participantes · numeros 1 a 10 (7 sin vender)",
                  "resumen cuenta tambien los no vendidos del final")
        comprobar(datos.resumen(lista) ==
                  "3 participantes · numeros 1 a 10 (7 sin vender)",
                  "resumen sin total explicito aplica el minimo")

        # Si se anaden boletos nuevos (11, 12...) el rango se amplia solo.
        c = os.path.join(tmp, "c.csv")
        filas = "numero,nombre\n"
        filas += "".join(f"{n},Persona {n}\n" for n in range(1, 6))
        filas += "".join(f"{n},\n" for n in range(6, 13))
        _escribir(c, filas)
        lista, total = datos.cargar_con_total(c)
        comprobar(total == 12, f"el archivo amplia el rango: {total}")
        comprobar(datos.resumen(lista, total) ==
                  "5 participantes · numeros 1 a 12 (7 sin vender)",
                  "resumen del rango ampliado")

        # Sin columna de numeros se autonumera: el total son las filas.
        d = os.path.join(tmp, "d.csv")
        _escribir(d, "nombre\nAna\nBea\nCarlos\n")
        lista, total = datos.cargar_con_total(d)
        comprobar([p.numero for p in lista] == [1, 2, 3], "autonumerado: numeros")
        comprobar(total == 10, f"autonumerado usa el minimo: {total}")

        # Sin el minimo, el rango sale exactamente del archivo.
        config.TOTAL_NUMEROS = None
        lista, total = datos.cargar_con_total(a)
        comprobar(total == 5, f"sin minimo el total es el del archivo: {total}")
        comprobar(datos.resumen(lista, total) ==
                  "3 participantes · numeros 1 a 5 (2 sin vender)",
                  "resumen sin minimo")
        config.TOTAL_NUMEROS = 10
    finally:
        config.TOTAL_NUMEROS = original

    comprobar(datos.resumen([]) == "Sin participantes cargados",
              "resumen de lista vacia")


# ---------------------------------------------------------------------------
def main() -> int:
    test_geometria()
    test_datos()
    test_total_boletos()
    test_resultados()
    test_pila_guardado_y_continuidad()
    test_dialogos_guardado()
    test_integracion_ejemplos()
    print()
    if fallos:
        print(f"FALLOS: {len(fallos)}")
        for f in fallos[:40]:
            print("  -", f)
        return 1
    print("TODO OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
