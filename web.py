import streamlit as st
from backend import (
    DESIRED_ORDER,
    calcular_despiece_desde_agrupado,
    calcular_materia_prima_por_perfil,
    calcular_totales_perfiles,
    calcular_soldadura_por_panel,
    calcular_tiempos_por_panel,
    cargar_pedido_agrupado,
    exportar_todo,
    menu_exportacion,
    parse_panel_code,
    calcular_area,
    calcular_detalle_insumos,
    calcular_areas_por_base,
    resumen_totales_pedido,
)
import tests


csv_file = st.file_uploader(
    "paneles.csv",
    type="csv",
)
dolar = st.number_input("Valor del dólar CLP→USD", min_value=0, value=970)

if csv_file:
    cantidades_por_base, df_pedido = cargar_pedido_agrupado(csv_file)

elif False:  # for dev, I don't want to load a huge csv every time I test something
    cantidades_por_base, df_pedido = tests.CANTIDADES_POR_BASE, tests.DF_PEDIDO

else:
    st.stop()


resultado_despiece = calcular_despiece_desde_agrupado(cantidades_por_base)
costos_por_panel, total_general_usd, detalle_costos, detalle_unidades = (
    menu_exportacion(resultado_despiece, dolar)
)

tiempos_panel, tiempo_total_general = calcular_tiempos_por_panel(resultado_despiece)
detalle_por_pieza, total_insumos_pedido = calcular_detalle_insumos(
    detalle_costos, detalle_unidades
)
resumen = resumen_totales_pedido(
    resultado_despiece=resultado_despiece,
    tiempos_panel=tiempos_panel,
    tiempo_total_general=tiempo_total_general,
    costos_por_panel=costos_por_panel,
    total_general_usd=total_general_usd,
    cantidades_por_base=cantidades_por_base,
)


if False:  # hidden cause it is too big
    # Mostrar la “tabla dinámica”
    msg = """
    ### Pedido agrupado por BASE

    | Panel (base) | Cantidad |
    | - | - |
    """

    for _, row in df_pedido.iterrows():
        msg += f"| {row['Panel (base)']} | {int(row['Cantidad'])} | \n"
    st.markdown(msg)


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

msg = ""

if opcion == "Todos":
    export_file = exportar_todo(
        resultado_despiece,
        cantidades_por_base,
        df_pedido,
        costos_por_panel,
        tiempos_panel,
        detalle_por_pieza,
        dolar,
        resumen,
    )

    download = st.download_button(
        "Descargar todo en excel",
        file_name="reporte_completo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        data=export_file.getvalue(),
    )

if opcion == "Despiece detallado" or opcion == "Todos":
    msg += """
### Despiece detallado

Panel | Perfil | Piezas | Largo (mm) | Total (mm) |
| -| - | - |- |- |
"""

    for item in resultado_despiece:
        msg += f"| {item['panel']} | {item['perfil']} | {item['numero_piezas']} | {item['largo_pieza_mm']} | {item['total_mm']} |\n"

# 4) Materia prima por perfil (unificado con totales de perfiles)
if (
    opcion == "Materia prima necesaria por perfil (incluye totales)"
    or opcion == "Todos"
):
    totales = calcular_totales_perfiles(
        resultado_despiece
    )  # {perfil: {numero_piezas, total_mm}}
    materia_prima = calcular_materia_prima_por_perfil(
        resultado_despiece, longitud_perfil=5850
    )
    msg += """
### Materia prima necesaria por perfil (incluye totales)

Perfil | Piezas totales | Total (mm) | Perfiles necesarios | Waste (mm) |
| -| - | - |- |- |
"""

    # primero en el orden deseado
    for perfil in DESIRED_ORDER:
        d_tot = totales.get(perfil, {"numero_piezas": 0, "total_mm": 0})
        d_mp = materia_prima.get(perfil, {"num_perfiles": 0, "waste_mm": 0})
        msg += f"{perfil} | {d_tot['numero_piezas']} | {d_tot['total_mm']} | {d_mp['num_perfiles']} | {d_mp['waste_mm']}\n"

    # luego los que no están en DESIRED_ORDER (orden alfabético)
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

if opcion == "Soldadura necesaria por panel" or opcion == "Todos":
    soldadura = calcular_soldadura_por_panel(resultado_despiece)
    msg += """
### Soldadura necesaria por panel

| Panel | Soldadura (mm) |
| - | - |
"""
    for panel in sorted(soldadura.keys(), key=lambda x: x.lower()):
        msg += f"| {panel} | {soldadura[panel]} |\n"

if opcion == "Tiempos por panel" or opcion == "Todos":
    msg += """
### Tiempos por panel

| Panel | Corte | Sold. | Perf. | Total |
| - | - | - | - | - |
"""
    for panel, d in tiempos_panel.items():
        msg += f"| {panel} | {d['tiempo_corte_min']:.2f} | {d['tiempo_soldadura_min']:.2f} | {d['tiempo_perforacion_min']:.2f} | {d['tiempo_total_min']:.2f} |\n"
    msg += f"\n**Tiempo TOTAL fabricación:** {tiempo_total_general / 60:.2f} horas"

if opcion == "Costos por panel (con USD/m² + resumen)" or opcion == "Todos":
    msg += """
### Costos por panel (con USD/m² + resumen)

| Panel (base) | Cant. | Área panel (m²) | Costo unit (USD) | USD/m² unit | MP (USD) | MO (USD) | Insumos (USD) | Energía (USD) | Total (USD) |
| - | - | - | - | - | - | - | - | - | - |
"""
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
        cantidades_por_base.items(), key=lambda x: x[0].lower()
    ):
        if cant_total <= 0:
            continue
        info = parse_panel_code(base)
        _, _, area_unit = calcular_area(info["nums"])
        if area_unit <= 0:
            continue

        dcost = costos_por_panel.get(base, {})
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
        msg += f"| {base} | {cant} | {area_unit:.3f} | {costo_unit:.2f} | {usd_m2_unit:.2f} | {mp_total:.2f} | {mo_total:.2f} | {ins_total:.2f} | {energia_total:.2f} | {total_base:.2f} |"

    precio_medio = (total_costo / total_area) if total_area > 0 else 0.0
    msg += f"""
---
**Resumen del pedido**
- Unidades totales: {total_unidades}
- Área total del pedido (m²): {total_area:.3f}
- Costo TOTAL pedido (USD): {total_costo:.2f}
- Precio medio (USD/m²): {precio_medio:.2f}
"""

if opcion == "Detalle de insumos por pieza y total pedido" or opcion == "Todos":
    msg += """
### Detalle de insumos por pieza y total pedido

| Panel | Insumo | Cantidad | Costo USD |
| - | - | - | - |
"""
    for panel, insumos in detalle_por_pieza.items():
        for nombre, datos in insumos.items():
            cantidad = datos["cantidad"]
            costo_usd = datos["costo_usd"]
            msg += f"| {panel} | {nombre} | {cantidad:.3f} | {costo_usd:.2f} |\n"

    msg += """
#### Total insumos TODO PEDIDO
| Insumo | Cant. Total | Costo Total USD |
| - | - | - |
"""
    for nombre, tot in total_insumos_pedido.items():
        msg += f"| {nombre} | {tot['cantidad_total']:.3f} | {tot['costo_total_usd']:.2f} |\n"

if opcion == "Área por panel" or opcion == "Todos":
    filas_area, total_area_pedido = calcular_areas_por_base(cantidades_por_base)
    msg += """
| Panel (base) | Cant. | Área panel (m²) | Área total (m²) |
| - | - | - | - |
"""
    for r in filas_area:
        msg += f"| {r['Panel (base)']} | {r['Cantidad']} | {r['Área panel (m²)']:.3f} | {r['Área total (m²)']:.3f} |\n"
    msg += f"\n**Área TOTAL del pedido (m²):** {total_area_pedido:.3f}"

if opcion == "Resumen" or opcion == "Todos":
    msg += f"""
### Resumen
- **Total piezas (despiece):** {resumen["total_piezas_despiece"]}
- **Total paneles (CSV):** {resumen["total_paneles"]}
- **Área total (m²):** {resumen["total_area_m2"]:.3f}
- **Costo total (USD):** {resumen["total_costo_usd"]:.2f}
- **Costo promedio (USD/m²):** {resumen["costo_promedio_usd_m2"]:.2f}
- **Tiempo total (min):** {resumen["total_tiempo_min"]:.2f}
- **Tiempo total (horas):** {resumen["total_tiempo_horas"]:.2f}
- **Tiempo total (días, 8h):** {resumen["total_tiempo_dias"]:.2f}
"""

res = st.markdown(msg)
