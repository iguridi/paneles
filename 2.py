import streamlit as st
import pandas as pd

# Insumos estándar (no eléctricos)
INSUMOS = {
    "gas": {"costo": 12.77, "rendimiento": 575, "unidad": "m"},
    "soldadura": {"costo": 17.62, "rendimiento": 150, "unidad": "m"},
    "boquillas": {"costo": 0.84, "rendimiento": 150, "unidad": "m"},
    "teflon": {"costo": 13.37, "rendimiento": 900, "unidad": "m"},
    "tobera": {"costo": 4.57, "rendimiento": 750, "unidad": "m"},
    "espiral": {"costo": 6.73, "rendimiento": 750, "unidad": "m"},
    "difusor": {"costo": 2.42, "rendimiento": 750, "unidad": "m"},
    "discos_lija": {"costo": 1.91, "rendimiento": 75, "unidad": "m"},
    "discos_corte": {"costo": 1.06, "rendimiento": 750, "unidad": "m"},
    "esmeril": {"costo": 37.23, "rendimiento": 30000, "unidad": "m"},
}

DESIRED_ORDER = [
    "ALA_LOSA",
    "ALA_MURO",
    "BASTIDOR_LOSA_50",
    "BASTIDOR_LOSA_54",
    "BASTIDOR_MURO_50",
    "BASTIDOR_MURO_54",
    "BCPN",
    "BH120",
    "BH150",
    "CLN50",
    "CLN70",
    "CLN100",
    "ICN",
    "OCN",
    "REFUERZOCHICO",
    "REFUERZOGRANDE",
    "TUBO",
]

RESULTADO_DESPIECE = [
    {
        "panel": "hola",
        "perfil": "ALA_LOSA",
        "numero_piezas": 1,
        "largo_pieza_mm": 3,
        "total_mm": 6,
    },
    {
        "panel": "hola",
        "perfil": "ALA_MURO",
        "numero_piezas": 2,
        "largo_pieza_mm": 4,
        "total_mm": 6,
    },
]

def calcular_totales_perfiles(despiece):
    """
    Agrupa el despiece por perfil y suma el total de piezas y milímetros.
    Retorna un diccionario en el que cada clave es el perfil.
    """
    totales = {}
    for item in despiece:
        perfil = item["perfil"]
        if perfil not in totales:
            totales[perfil] = {"numero_piezas": 0, "total_mm": 0}
        totales[perfil]["numero_piezas"] += item["numero_piezas"]
        totales[perfil]["total_mm"] += item["total_mm"]
    return totales

def calcular_materia_prima_por_perfil(despiece, longitud_perfil=5850):
    """
    Para cada perfil del despiece, calcula cuántos perfiles de materia prima
    (de longitud fija, por defecto 5850 mm) se necesitan para cortar todas las piezas,
    utilizando first-fit decreasing para optimizar la utilización.
    Retorna un diccionario con:
      - num_perfiles: cantidad de perfiles necesarios
      - waste_mm: desperdicio total en mm.
    """
    piezas_por_perfil = {}
    for item in despiece:
        perfil = item["perfil"]
        largo = item["largo_pieza_mm"]
        if largo <= 0:
            continue
        count = item["numero_piezas"]
        piezas_por_perfil.setdefault(perfil, [])
        piezas_por_perfil[perfil].extend([largo] * count)

    resultados = {}
    for perfil, piezas in piezas_por_perfil.items():
        piezas.sort(reverse=True)
        bins = []
        for pieza in piezas:
            placed = False
            for i in range(len(bins)):
                if bins[i] >= pieza:
                    bins[i] -= pieza
                    placed = True
                    break
            if not placed:
                bins.append(longitud_perfil - pieza)
        num_perfiles = len(bins)
        waste = sum(bins)
        resultados[perfil] = {"num_perfiles": num_perfiles, "waste_mm": waste}
    return resultados


########################

st.file_uploader("paneles.csv")

opcion = st.radio(
    "Seleccione que listado desea detallar",
    [
        "Despiece detallado",
        "Materia prima necesaria por perfil (incluye totales)",
        "Soldadura necesaria por panel",
        "Tiempos por panel",
        "Costos por panel (con USD/m² + resumen)",
        "Detalle de insumos por pieza y total pedido",
        "Área por panel",
        "Resumen",
        "Todos",
    ],
)



st.markdown(opcion)

if opcion == "Despiece detallado":
    msg = """
### Despiece detallado

Panel | Perfil | Piezas | Largo (mm) | Total (mm) |
| -| - | - |- |- |
"""

    for item in RESULTADO_DESPIECE:
        msg += f"| {item['panel']} | {item['perfil']} | {item['numero_piezas']} | {item['largo_pieza_mm']} | {item['total_mm']} |\n"

# 4) Materia prima por perfil (unificado con totales de perfiles)
elif opcion == "Materia prima necesaria por perfil (incluye totales)":
    totales = calcular_totales_perfiles(RESULTADO_DESPIECE)  # {perfil: {numero_piezas, total_mm}}
    materia_prima = calcular_materia_prima_por_perfil(RESULTADO_DESPIECE, longitud_perfil=5850)
    msg = """
### Materia Prima necesaria por perfil (incluye totales) 

Perfil | Piezas totales | Total (mm) | Perfiles necesarios | Waste (mm) |
| -| - | - |- |- |
"""

    # primero en el orden deseado
    for perfil in DESIRED_ORDER:
        d_tot = totales.get(perfil, {"numero_piezas": 0, "total_mm": 0})
        d_mp = materia_prima.get(perfil, {"num_perfiles": 0, "waste_mm": 0})
        msg += f"{perfil} | {d_tot['numero_piezas']} | {d_tot['total_mm']} | {d_mp['num_perfiles']} | {d_mp['waste_mm']}\n"

    # luego los que no están en desired_order (orden alfabético)
    otros = sorted(
        [
            p
            for p in set(list(totales.keys()) + list(materia_prima.keys()))
            if p not in DESIRED_ORDER
        ]
    )
    for p in otros:
        d_tot = totales.get(p, {"numero_piezas": 0, "total_mm": 0})
        d_mp = materia_prima.get(p, {"num_perfiles": 0, "waste_mm": 0})
        msg += f"{p} | {d_tot['numero_piezas']} | {d_tot['total_mm']} | {d_mp['num_perfiles']} | {d_mp['waste_mm']}\n"

res = st.markdown(msg)

# download = st.download_button("Descargar")


df = pd.DataFrame({"first column": [1, 2, 3, 4], "second column": [10, 20, 30, 40]})

# df
