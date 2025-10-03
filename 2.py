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

RESULTADO_DESPIECE = [
    {
        "panel": "hola",
        "perfil": "wow",
        "numero_piezas": "wow",
        "largo_pieza_mm": "wow",
        "total_mm": "wow",
    },
    {
        "panel": "hola",
        "perfil": "wow2",
        "numero_piezas": "wow2",
        "largo_pieza_mm": "wow2",
        "total_mm": "wow2",
    },
]


if opcion == "Despiece detallado":
    msg = """
## Despiece detallado

Panel | Perfil | Piezas | Largo (mm) | Total (mm) |
| -| - | - |- |- |
"""

    for item in RESULTADO_DESPIECE:
        msg += f"| {item['panel']} | {item['perfil']} | {item['numero_piezas']} | {item['largo_pieza_mm']} | {item['total_mm']} |\n"

    res = st.markdown(msg)

# 4) Materia prima por perfil (unificado con totales de perfiles)
elif opcion == "Materia prima necesaria por perfil (incluye totales)":
    # totales = calcular_totales_perfiles(resultado_despiece)  # {perfil: {numero_piezas, total_mm}}
    # materia_prima = calcular_materia_prima_por_perfil(resultado_despiece, longitud_perfil=5850)
    msg = """
## Materia Prima necesaria por perfil (incluye totales) 

Perfil | Piezas totales | Total (mm) | Perfiles necesarios | Waste (mm) |
| -| - | - |- |- |
"""

    # primero en el orden deseado
    for perfil in desired_order:
        d_tot = totales.get(perfil, {"numero_piezas": 0, "total_mm": 0})
        d_mp = materia_prima.get(perfil, {"num_perfiles": 0, "waste_mm": 0})
        msg += f"{perfil} {d_tot['numero_piezas']} {d_tot['total_mm']} {d_mp['num_perfiles']} {d_mp['waste_mm']}\n"

    # luego los que no están en desired_order (orden alfabético)
    otros = sorted(
        [
            p
            for p in set(list(totales.keys()) + list(materia_prima.keys()))
            if p not in desired_order
        ]
    )
    for p in otros:
        d_tot = totales.get(p, {"numero_piezas": 0, "total_mm": 0})
        d_mp = materia_prima.get(p, {"num_perfiles": 0, "waste_mm": 0})
        msg += f"{p} {d_tot['numero_piezas']} {d_tot['total_mm']} {d_mp['num_perfiles']} {d_mp['waste_mm']}\n"

# download = st.download_button("Descargar")


df = pd.DataFrame({"first column": [1, 2, 3, 4], "second column": [10, 20, 30, 40]})

# df
