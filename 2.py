import streamlit as st
import pandas as pd
from backend import (
    RESULTADO_DESPIECE,
    DESIRED_ORDER,
    calcular_materia_prima_por_perfil,
    calcular_totales_perfiles,
    calcular_soldadura_por_panel,
    calcular_tiempos_por_panel,
    CANTIDADES_POR_BASE,
    COSTOS_POR_PANEL,
    parse_panel_code,
    calcular_area,
    DETALLE_COSTOS,
    DETALLE_UNIDADES,
    calcular_detalle_insumos,
)





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

msg = f'### {opcion}\n\n'


if opcion == "Despiece detallado":
    msg += """
Panel | Perfil | Piezas | Largo (mm) | Total (mm) |
| -| - | - |- |- |
"""

    for item in RESULTADO_DESPIECE:
        msg += f"| {item['panel']} | {item['perfil']} | {item['numero_piezas']} | {item['largo_pieza_mm']} | {item['total_mm']} |\n"

# 4) Materia prima por perfil (unificado con totales de perfiles)
elif opcion == "Materia prima necesaria por perfil (incluye totales)":
    totales = calcular_totales_perfiles(RESULTADO_DESPIECE)  # {perfil: {numero_piezas, total_mm}}
    materia_prima = calcular_materia_prima_por_perfil(RESULTADO_DESPIECE, longitud_perfil=5850)
    msg += """
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
    msg += """
| Panel | Soldadura (mm) |
| - | - |
"""
    for panel in sorted(soldadura.keys(), key=lambda x: x.lower()):
        msg += f"| {panel} | {soldadura[panel]} |\n"

elif opcion == "Tiempos por panel":
    tiempos_panel, tiempo_total_general = calcular_tiempos_por_panel(RESULTADO_DESPIECE)
    msg += """
| Panel | Corte | Sold. | Perf. | Total |
| - | - | - | - | - |
"""
    for panel, d in tiempos_panel.items():
        msg += f"| {panel} | {d['tiempo_corte_min']:.2f} | {d['tiempo_soldadura_min']:.2f} | {d['tiempo_perforacion_min']:.2f} | {d['tiempo_total_min']:.2f} |\n"
    msg += f"\n**Tiempo TOTAL fabricación:** {tiempo_total_general / 60:.2f} horas"

elif opcion == "Costos por panel (con USD/m² + resumen)":
    msg += '''
| Panel (base) | Cant. | Área panel (m²) | Costo unit (USD) | USD/m² unit | MP (USD) | MO (USD) | Insumos (USD) | Energía (USD) | Total (USD) |
| - | - | - | - | - | - | - | - | - | - |
'''
    total_area = 0.0
    total_costo = 0.0
    total_unidades = 0

    def _mo_total(d):
        return (
            d.get("costo_mo_corte_usd", 0.0)
            + d.get("costo_mo_sold_usd", 0.0)
            + d.get("costo_mo_perf_usd", 0.0)
        )

    filas = []
    for base, cant_total in sorted(
        CANTIDADES_POR_BASE.items(), key=lambda x: x[0].lower()
    ):
        if cant_total <= 0:
            continue
        info = parse_panel_code(base)
        _, _, area_unit = calcular_area(info["nums"])
        if area_unit <= 0:
            continue

        dcost = COSTOS_POR_PANEL.get(base, {})
        total_base = dcost.get("costo_total_usd", 0.0) or 0.0
        mp_total = dcost.get("costo_mp_usd", 0.0) or 0.0
        mo_total = _mo_total(dcost)
        ins_total = dcost.get("costo_insumos_usd", 0.0) or 0.0
        energia_total = dcost.get("costo_energia_usd", 0.0) or 0.0  # ← NUEVO

        costo_unit = total_base / cant_total
        usd_m2_unit = costo_unit / area_unit

        total_unidades += cant_total
        total_area += area_unit * cant_total
        total_costo += total_base

        filas.append(
            (
                base,
                cant_total,
                area_unit,
                costo_unit,
                usd_m2_unit,
                mp_total,
                mo_total,
                ins_total,
                energia_total,
                total_base,
            )
        )

    for (
        base,
        cant,
        area_unit,
        costo_unit,
        usd_m2_unit,
        mp_total,
        mo_total,
        ins_total,
        energia_total,
        total_base,
    ) in filas:
        msg += f'| {base} | {cant} | {area_unit:.3f} | {costo_unit:.2f} | {usd_m2_unit:.2f} | {mp_total:.2f} | {mo_total:.2f} | {ins_total:.2f} | {energia_total:.2f} | {total_base:.2f} |'

    precio_medio = (total_costo / total_area) if total_area > 0 else 0.0
    msg += f"""
---
**Resumen del pedido**
- Unidades totales: {total_unidades}
- Área total del pedido (m²): {total_area:.3f}
- Costo TOTAL pedido (USD): {total_costo:.2f}
- Precio medio (USD/m²): {precio_medio:.2f}
"""

elif opcion == "Detalle de insumos por pieza y total pedido":
    detalle_por_pieza, total_insumos_pedido = calcular_detalle_insumos(
        DETALLE_COSTOS, DETALLE_UNIDADES
    )
    msg += """
| Panel | Insumo | Cantidad | Costo USD |
| - | - | - | - |
"""
    for panel, insumos in detalle_por_pieza.items():
        for nombre, datos in insumos.items():
            cantidad = datos["cantidad"]
            costo_usd = datos["costo_usd"]
            msg += f"| {panel} | {nombre} | {cantidad:.3f} | {costo_usd:.2f} |\n"

    msg += """
### Total insumos TODO PEDIDO
| Insumo | Cant. Total | Costo Total USD |
| - | - | - |
"""
    for nombre, tot in total_insumos_pedido.items():
        msg += f"| {nombre} | {tot['cantidad_total']:.3f} | {tot['costo_total_usd']:.2f} |\n"



res = st.markdown(msg)

# download = st.download_button("Descargar")

