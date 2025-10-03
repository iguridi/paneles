import streamlit as st
import pandas as pd
from backend import RESULTADO_DESPIECE, DESIRED_ORDER, calcular_materia_prima_por_perfil, calcular_totales_perfiles, calcular_soldadura_por_panel, calcular_tiempos_por_panel



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

elif opcion == "Soldadura necesaria por panel":
    soldadura = calcular_soldadura_por_panel(RESULTADO_DESPIECE)
    msg = """
### Soldadura necesaria por panel

| Panel | Soldadura (mm) |
| - | - |
"""
    for panel in sorted(soldadura.keys(), key=lambda x: x.lower()):
        msg += f"| {panel} | {soldadura[panel]} |\n"

elif opcion == "Tiempos por panel":
    tiempos_panel, tiempo_total_general = calcular_tiempos_por_panel(RESULTADO_DESPIECE)
    msg = """
### Tiempos por PANEL (min)

| Panel | Corte | Sold. | Perf. | Total |
| - | - | - | - | - |
"""
    for panel, d in tiempos_panel.items():
        msg += f"| {panel} | {d['tiempo_corte_min']:.2f} | {d['tiempo_soldadura_min']:.2f} | {d['tiempo_perforacion_min']:.2f} | {d['tiempo_total_min']:.2f} |\n"
    msg += f"\n**Tiempo TOTAL fabricación:** {tiempo_total_general / 60:.2f} horas"

res = st.markdown(msg)

# download = st.download_button("Descargar")

