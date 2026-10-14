"""Genera los archivos de ejemplo (CSV y Excel).

    .venv/bin/python ejemplos/generar.py
"""

from __future__ import annotations

import csv
import os
import random

AQUI = os.path.dirname(os.path.abspath(__file__))

NOMBRES = [
    "Ana Lucía Fernández", "José Ramón Muñiz", "Dayana Rodríguez",
    "Carlos Manuel Pérez", "Yamilé González", "Ernesto Valdés",
    "María Teresa Guerra", "Alejandro Sosa", "Lisandra Betancourt",
    "Rafael Antonio Cruz", "Yordanka Hernández", "Miguel Ángel Castellanos",
    "Ileana Cárdenas", "Osmany Delgado", "Yusimí Herrera", "Lázaro Mirabal",
    "Dalianis Núñez", "Yoel Rivas", "Marlene Iglesias", "Reinier Zaldívar",
    "Odalis Cabrera", "Yordanis Peña", "Mayelín Quintero", "Arnaldo Espinosa",
    "Damaris Toledo", "Rogelio Benítez", "Yisel Aponte", "Néstor Zambrano",
    "Aracelys Montero", "Wilfredo Salgado", "Yanet Cisneros", "Orlando Fajardo",
    "Elián Bermúdez", "Zulema Aranguren", "Noelvis Martiatu", "Misleidis Padrón",
    "Franklin Ocaña", "Gretel Villalón", "Julián Ricardo", "Saily Estrada",
    "Evelio Barrera", "Anisley Correa", "Tomás Regalado", "Nereida Fonseca",
    "Yassel Ibarra", "Belkis Almaguer", "Diosnel Calzadilla", "Roxana Trujillo",
    "Edelmiro Lorenzo", "Yunia Santos", "Jorge Luis Delgado", "Marisol Terrero",
    "Alberto Nápoles", "Cira Montalvo", "Fidel Águila", "Yamila Pacheco",
    "Antonio Recio", "Dunia Cardoso", "Rancel Quevedo", "Mercedes Bécquer",
]


def escribir_csv(ruta: str, participantes: list[tuple[int, str]]):
    with open(ruta, "w", newline="", encoding="utf-8") as fh:
        escritor = csv.writer(fh)
        escritor.writerow(["numero", "nombre"])
        escritor.writerows(participantes)


def escribir_xlsx(ruta: str, participantes: list[tuple[int, str]]):
    try:
        import openpyxl
    except ImportError:
        print("openpyxl no esta instalado: se omite", ruta)
        return
    libro = openpyxl.Workbook()
    hoja = libro.active
    hoja.title = "Participantes"
    hoja.append(["numero", "nombre"])
    for numero, nombre in participantes:
        hoja.append([numero, nombre])
    hoja.column_dimensions["A"].width = 10
    hoja.column_dimensions["B"].width = 32
    libro.save(ruta)


def main():
    pequenos = [(i + 1, n) for i, n in enumerate(NOMBRES[:12])]
    escribir_csv(os.path.join(AQUI, "participantes.csv"), pequenos)
    escribir_xlsx(os.path.join(AQUI, "participantes.xlsx"), pequenos)

    # Ejemplo grande para probar con muchos sectores, numeros no consecutivos
    rng = random.Random(7)
    numeros = sorted(rng.sample(range(1, 500), 60))
    grandes = [(n, NOMBRES[i % len(NOMBRES)]) for i, n in enumerate(numeros)]
    escribir_csv(os.path.join(AQUI, "rifa_grande.csv"), grandes)
    escribir_xlsx(os.path.join(AQUI, "rifa_grande.xlsx"), grandes)

    print("Ejemplos generados en", AQUI)


if __name__ == "__main__":
    main()
