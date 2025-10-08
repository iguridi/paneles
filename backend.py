from collections import defaultdict
import csv
import io
import streamlit as st

from io import StringIO
import math
import re
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

# --- Parámetros base ---
COSTO_ALUMINIO_USD_POR_KG = 3.828
PESO_POR_PERFIL = {
    "ALA_LOSA": 4.316,
    "ALA_MURO": 4.480,
    "BASTIDOR_LOSA_50": 1.064,
    "BASTIDOR_LOSA_54": 1.129,
    "BASTIDOR_MURO_50": 1.368,
    "BASTIDOR_MURO_54": 1.284,
    "BCPN": 3.754,
    "BH120": 4.615,
    "BH150": 5.034,
    "CLN100": 5.072,
    "CLN50": 5.023,
    "CLN70": 5.294,
    "ICN": 6.838,
    "OCN": 2.745,
    "REFUERZOCHICO": 1.200,
    "REFUERZOGRANDE": 1.274,
    "TUBO": 1.923,
}
MATERIA_PRIMA_POR_MM = {
    p: (w / 1000.0) * COSTO_ALUMINIO_USD_POR_KG for p, w in PESO_POR_PERFIL.items()
}
MANO_OBRA = {
    "corte": 5056.0 / 60.0,
    "soldadura": 6611.0 / 60.0,
    "perforacion": 3889.0 / 60.0,
}
# ---

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


## File stuff
def exportar_todo(
    resultado_despiece,
    cantidades_por_base,
    df_pedido,
    costos_por_panel,
    tiempos_panel,
    detalle_por_pieza,
    dolar,
    resumen,
):
    # Reconstruimos estructuras que usamos arriba
    totales = calcular_totales_perfiles(resultado_despiece)
    materia_prima = calcular_materia_prima_por_perfil(
        resultado_despiece, longitud_perfil=5850
    )
    soldadura = calcular_soldadura_por_panel(resultado_despiece)

    # Áreas por BASE (misma lógica que opción 9 y resumen)
    filas_area_base, total_area_base = calcular_areas_por_base(
        cantidades_por_base
    )

    export_file = io.BytesIO
    with pd.ExcelWriter(export_file, engine="openpyxl") as writer:
        # 0) Pedido agrupado
        df_pedido.to_excel(writer, sheet_name="Pedido_agrupado", index=False)

        # 1) Despiece detallado
        pd.DataFrame(resultado_despiece).to_excel(
            writer, sheet_name="Despiece", index=False
        )

        # 2) Materia prima (unificada con totales)
        filas_mp = []
        # primero DESIRED_ORDER
        for perfil in DESIRED_ORDER:
            t = totales.get(perfil, {"numero_piezas": 0, "total_mm": 0})
            m = materia_prima.get(perfil, {"num_perfiles": 0, "waste_mm": 0})
            filas_mp.append(
                {
                    "Perfil": perfil,
                    "Piezas totales": t["numero_piezas"],
                    "Total(mm)": t["total_mm"],
                    "Perfiles necesarios (5850mm)": m["num_perfiles"],
                    "Waste (mm)": m["waste_mm"],
                }
            )
        # luego otros perfiles
        otros = sorted(
            [
                p
                for p in set(list(totales.keys()) + list(materia_prima.keys()))
                if p not in DESIRED_ORDER
            ]
        )
        for p in otros:
            t = totales.get(p, {"numero_piezas": 0, "total_mm": 0})
            m = materia_prima.get(p, {"num_perfiles": 0, "waste_mm": 0})
            filas_mp.append(
                {
                    "Perfil": p,
                    "Piezas totales": t["numero_piezas"],
                    "Total(mm)": t["total_mm"],
                    "Perfiles necesarios (5850mm)": m["num_perfiles"],
                    "Waste (mm)": m["waste_mm"],
                }
            )
        pd.DataFrame(filas_mp).to_excel(
            writer, sheet_name="Materia prima", index=False
        )

        # 3) Soldadura
        pd.DataFrame(
            [{"Panel": k, "Soldadura(mm)": v} for k, v in soldadura.items()]
        ).to_excel(writer, sheet_name="Soldadura", index=False)

        # 4) Tiempos por panel
        df_tiempos = pd.DataFrame.from_dict(
            tiempos_panel, orient="index"
        ).reset_index()
        df_tiempos.rename(columns={"index": "Panel"}, inplace=True)
        df_tiempos.to_excel(writer, sheet_name="Tiempos", index=False)

        # 5) Costos por panel (agrupado por BASE) — usa cantidades_por_base ya existente
        filas_costos = []

        def _mo_total(d):
            return (
                (d.get("costo_mo_corte_usd", 0.0) or 0.0)
                + (d.get("costo_mo_sold_usd", 0.0) or 0.0)
                + (d.get("costo_mo_perf_usd", 0.0) or 0.0)
            )

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
            mp_total = dcost.get("costo_mp_usd", 0.0) or 0.0
            mo_total = _mo_total(dcost)
            insumos_total = dcost.get("costo_insumos_usd", 0.0) or 0.0
            total_base = dcost.get("costo_total_usd", 0.0) or 0.0

            energia_total = (
                dcost.get("costo_energia_usd", 0.0) or 0.0
            )  # ← NUEVO

            costo_unit = total_base / cant_total if cant_total else 0.0
            usd_m2_unit = (costo_unit / area_unit) if area_unit > 0 else 0.0

            filas_costos.append(
                {
                    "Panel (base)": base,
                    "Cantidad": cant_total,
                    "Área panel (m²)": round(area_unit, 3),
                    "Costo unit (USD)": round(costo_unit, 2),
                    "USD/m² unit": round(usd_m2_unit, 2),
                    "MP (USD)": round(mp_total, 2),
                    "MO (USD)": round(mo_total, 2),
                    "Insumos (USD)": round(insumos_total, 2),
                    "Energía (USD)": round(energia_total, 2),  # ← NUEVO
                    "Total (USD)": round(total_base, 2),
                }
            )

        pd.DataFrame(filas_costos).to_excel(
            writer, sheet_name="Costos", index=False
        )

        # 6) Detalle de insumos por pieza
        filas_insumos = []
        for panel, ins in detalle_por_pieza.items():
            for nombre, datos in ins.items():
                filas_insumos.append(
                    {
                        "Panel": panel,
                        "Insumo": nombre,
                        "Cantidad": datos["cantidad"],
                        "Costo USD": datos["costo_usd"],
                    }
                )
        pd.DataFrame(filas_insumos).to_excel(
            writer, sheet_name="Insumos", index=False
        )

        # 7) Áreas (por BASE)
        pd.DataFrame(filas_area_base).to_excel(
            writer, sheet_name="Áreas_BASE", index=False
        )

        # 8) Resumen (mismas métricas que 'resumen' ya calculado)
        df_resumen = pd.DataFrame(
            [
                {
                    "Total piezas (despiece)": resumen["total_piezas_despiece"],
                    "Total paneles (CSV)": resumen["total_paneles"],
                    "Área total (m²)": round(
                        resumen["total_area_m2"], 3
                    ),  # viene de calcular_areas_por_base
                    "Costo total (USD)": round(resumen["total_costo_usd"], 2),
                    "Costo promedio (USD/m²)": round(
                        resumen["costo_promedio_usd_m2"], 2
                    ),
                    "Tiempo total (horas)": round(
                        resumen["total_tiempo_horas"], 2
                    ),
                    "Tiempo total (días, 8h)": round(
                        resumen["total_tiempo_dias"], 2
                    ),
                    "Tasa CLP→USD usada": dolar,
                }
            ]
        )
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)

    return export_file



def cargar_pedido_agrupado(csv_file):
    """
    Lee el CSV original y devuelve:
      - cantidades_por_base: dict {BASE: cantidad_total}
      - df_pedido: DataFrame con columnas ['Panel (base)', 'Cantidad'] (ordenado)
    Normaliza el código eliminando todo lo que siga al primer '-'.
    """
    cantidades_por_base = defaultdict(int)

    reader = csv.reader(StringIO(csv_file.getvalue().decode("utf-8")))
    next(reader, None)  # saltar encabezado
    for row in reader:
        if not row:
            continue
        panel_raw = row[0]
        raw = row[1] if len(row) > 1 else "0"
        cant = int(re.sub(r"\D", "", raw)) if re.search(r"\d", raw or "") else 0
        if cant <= 0:
            continue
        base = parse_panel_code(panel_raw)["base"]  # ← quita sufijo después de '-'
        cantidades_por_base[base] += cant

    df_pedido = pd.DataFrame(
        [
            {"Panel (base)": k, "Cantidad": v}
            for k, v in sorted(cantidades_por_base.items())
        ]
    )
    return dict(cantidades_por_base), df_pedido

def menu_exportacion(
    resultado_despiece, tasa
):
    # Valores por defecto y tiempos predefinidos
    tiempo_por_corte = 1.25
    velocidad_sold = 200.0
    entrada = (
        "WF:2,SF:2,MF:2,CL:0.2,CLI:1.5,CLE:1.5,IC:4,OC:1,BH:5,BCP:1,CP:0.9,CE:0.6,CS:1"
    )
    tiempos_perforacion_por_tipo = {}
    for parte in entrada.split(","):
        tipo, val = parte.split(":", 1)
        try:
            tiempos_perforacion_por_tipo[tipo] = float(val)
        except ValueError:
            tiempos_perforacion_por_tipo[tipo] = 0.0

    # Pre-cálculos (una sola vez)
    tiempos_panel, tiempo_total_general = calcular_tiempos_por_panel(
        resultado_despiece,
        tiempo_por_corte_min=tiempo_por_corte,
        velocidad_soldadura_mm_por_min=velocidad_sold,
        tiempos_perforacion_por_tipo=tiempos_perforacion_por_tipo,
    )

    costos_por_panel, total_general_usd, detalle_costos, detalle_unidades = (
        calcular_costos_por_panel(resultado_despiece, tiempos_panel, tasa, True)
    )

    return costos_por_panel, total_general_usd, detalle_costos, detalle_unidades

###

def _agregar_despiece_de_panel(panel_base, cantidad, despiece):
    """
    Reusa la lógica que hoy tienes adentro del for del CSV,
    pero recibiendo directamente (panel_base, cantidad).
    panel_base debe venir SIN sufijos (ej. WF600X2250).
    """
    panel_raw = panel_base  # compat
    info = parse_panel_code(panel_raw)
    tipo = info["tipo"]
    panel = info["base"]
    nums = info["nums"]
    partes = info["partes"]

    # --- Panel WF ---
    if tipo == "WF":
        try:
            ANCHO, ALTO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel WF:", panel_raw)
            return

        if 100 <= ANCHO <= 300:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_MURO_54",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": cantidad * ALTO,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": cantidad * ALTO,
                }
            )
        elif 301 <= ANCHO <= 399:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * cantidad * ALTO,
                }
            )
        elif 400 <= ANCHO <= 579:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * cantidad * ALTO,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOCHICO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 175,
                    "total_mm": 175 * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOCHICO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 258,
                    "total_mm": 258 * cantidad,
                }
            )
        elif 580 <= ANCHO <= 600:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * cantidad * ALTO,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 160,
                    "total_mm": 160 * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 258,
                    "total_mm": 258 * cantidad,
                }
            )
        else:
            print("Pieza WF no corresponde al catálogo:", panel)
            return

        # Elementos base para WF
        despiece.append(
            {
                "panel": panel,
                "perfil": "REFUERZOCHICO",
                "numero_piezas": cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": cantidad * ANCHO,
            }
        )
        despiece.append(
            {
                "panel": panel,
                "perfil": "REFUERZOGRANDE",
                "numero_piezas": 6 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 6 * cantidad * ANCHO,
            }
        )
        despiece.append(
            {
                "panel": panel,
                "perfil": "BASTIDOR_MURO_50",
                "numero_piezas": 2 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 2 * cantidad * ANCHO,
            }
        )

    # --- Panel SF ---
    elif tipo == "SF":
        try:
            ANCHO, ALTO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel SF:", panel_raw)
            return

        if 100 <= ANCHO <= 399:
            pass
        elif 400 <= ANCHO <= 579:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOCHICO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 258,
                    "total_mm": 258 * cantidad,
                }
            )
        elif 580 <= ANCHO <= 600:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": 258,
                    "total_mm": 258 * cantidad,
                }
            )
        else:
            print("ANCHO no corresponde en panel SF:", panel)
            return

        if 100 <= ALTO <= 2249:
            a = 280
            l = 1
            rg = 0
            rch = 0
            while a < ALTO:
                if l == 1 and a == 280:
                    a += 79
                elif l == 1:
                    rg += 1
                    rch -= 1
                    a += 160
                else:
                    rch += 1
                    a += 140
                l *= -1
            if rg != 0:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOGRANDE",
                        "numero_piezas": rg * cantidad,
                        "largo_pieza_mm": ANCHO,
                        "total_mm": rg * ANCHO * cantidad,
                    }
                )  # FIX
            if rch != 0:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": rch * cantidad,
                        "largo_pieza_mm": ANCHO,
                        "total_mm": rch * ANCHO * cantidad,
                    }
                )
        else:
            print("ALTO no permitido en panel SF:", panel)
            return

        despiece.append(
            {
                "panel": panel,
                "perfil": "BASTIDOR_MURO_50",
                "numero_piezas": 2 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 2 * cantidad * ANCHO,
            }
        )
        if 100 <= ANCHO <= 300:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_MURO_54",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
        else:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * cantidad * ALTO,
                }
            )

    # --- Panel MF ---
    elif tipo == "MF":
        try:
            ANCHO, ALTO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel MF:", panel_raw)
            return

        a = 200
        b = 0
        c = 0
        rg = 0
        rch = 0
        if 100 <= ALTO <= 2100:
            a += 100
            b = ALTO
            while a < ALTO:
                if a == 300:
                    rch += 1
                    a += 300
                else:
                    rg += 1
                    a += 300
                    c += 1
            if c != 0:
                b = ALTO - 275 - 300 * (c - 1)
            if rg != 0:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOGRANDE",
                        "numero_piezas": rg * cantidad,
                        "largo_pieza_mm": ANCHO,
                        "total_mm": rg * ANCHO * cantidad,
                    }
                )  # FIX
            if rch != 0:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": rch * cantidad,
                        "largo_pieza_mm": ANCHO,
                        "total_mm": rch * ANCHO * cantidad,
                    }
                )
        else:
            print("ALTO no permitido en panel MF:", panel)
            return

        if 100 <= ANCHO <= 399:
            pass
        elif 400 <= ANCHO <= 579:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOCHICO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": b,
                    "total_mm": b * cantidad,
                }
            )
        else:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": b,
                    "total_mm": b * cantidad,
                }
            )

        despiece.append(
            {
                "panel": panel,
                "perfil": "BASTIDOR_MURO_50",
                "numero_piezas": 2 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 2 * cantidad * ANCHO,
            }
        )
        if 100 <= ANCHO <= 300:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_MURO_54",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
        else:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_MURO",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * cantidad * ALTO,
                }
            )

    # --- Panel CL / CLI / CLE ---
    elif tipo in ("CL", "CLI", "CLE"):
        try:
            if tipo == "CL":
                # CL<ALTO>X<ANCHO>X<LARGO>
                ALTO = int(partes[0][2:])
                ANCHO = int(partes[1])
                LARGO = int(partes[2])
                ie = False
                A = B = 0
            else:
                # CLI/CLE: CL?E<ALTO>X<ANCHO>X<A>X<B>
                ALTO = int(partes[0][3:])
                ANCHO = int(partes[1])
                A = int(partes[2])
                B = int(partes[3])
                LARGO = 600
                ie = True
        except Exception:
            print("Error extrayendo dimensiones en panel CL/CLE/CLI:", panel_raw)
            return

        if ALTO == 50:
            if not ie:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN50",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": LARGO,
                        "total_mm": LARGO * cantidad,
                    }
                )
            else:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN50",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": A,
                        "total_mm": A * cantidad,
                    }
                )
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN50",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": B,
                        "total_mm": B * cantidad,
                    }
                )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZO_CL50",
                    "numero_piezas": cantidad
                    * (2 + (LARGO // 600 - 1) + (A // 600) + (B // 600)),
                    "largo_pieza_mm": 0,
                    "total_mm": 0,
                }
            )

        elif ALTO == 70:
            if not ie:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN70",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": LARGO,
                        "total_mm": LARGO * cantidad,
                    }
                )
            else:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN70",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": A,
                        "total_mm": A * cantidad,
                    }
                )
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN70",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": B,
                        "total_mm": B * cantidad,
                    }
                )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZO_CL70",
                    "numero_piezas": cantidad
                    * (2 + (LARGO // 600 - 1) + (A // 600) + (B // 600)),
                    "largo_pieza_mm": 0,
                    "total_mm": 0,
                }
            )

        elif ALTO == 100:
            if not ie:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN100",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": LARGO,
                        "total_mm": LARGO * cantidad,
                    }
                )
            else:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN100",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": A,
                        "total_mm": A * cantidad,
                    }
                )
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "CLN100",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": B,
                        "total_mm": B * cantidad,
                    }
                )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZO_CL100",
                    "numero_piezas": cantidad
                    * (2 + (LARGO // 600 - 1) + (A // 600) + (B // 600)),
                    "largo_pieza_mm": 0,
                    "total_mm": 0,
                }
            )
        else:
            # Caso especial 70x150
            if ANCHO == 70 and ALTO == 150:
                if not ie:
                    despiece.append(
                        {
                            "panel": panel,
                            "perfil": "CLN70",
                            "numero_piezas": cantidad,
                            "largo_pieza_mm": LARGO,
                            "total_mm": LARGO * cantidad,
                        }
                    )
                else:
                    despiece.append(
                        {
                            "panel": panel,
                            "perfil": "CLN70",
                            "numero_piezas": cantidad,
                            "largo_pieza_mm": A,
                            "total_mm": A * cantidad,
                        }
                    )
                    despiece.append(
                        {
                            "panel": panel,
                            "perfil": "CLN70",
                            "numero_piezas": cantidad,
                            "largo_pieza_mm": B,
                            "total_mm": B * cantidad,
                        }
                    )
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZO_CL70",
                        "numero_piezas": cantidad
                        * (2 + (LARGO // 600 - 1) + (A // 600) + (B // 600)),
                        "largo_pieza_mm": 0,
                        "total_mm": 0,
                    }
                )
            else:
                print("ALTO no reconocido para panel CL:", panel)
                return

    # --- Panel IC ---
    elif tipo == "IC":
        try:
            ANCHO, ALTO, LARGO = nums[0], nums[1], nums[2]
        except Exception:
            print("Error extrayendo dimensiones en panel IC:", panel_raw)
            return

        if 100 <= LARGO <= 2400:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZO_IC",
                    "numero_piezas": 2 * cantidad + (LARGO // 300 - 1) * cantidad,
                    "largo_pieza_mm": 0,
                    "total_mm": 0,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ICN",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": LARGO,
                    "total_mm": LARGO * cantidad,
                }
            )
        else:
            print("LARGO no permitido en panel IC:", panel)
            return

    # --- Panel OC ---
    elif tipo == "OC":
        try:
            LARGO = nums[0]
        except Exception:
            print("Error extrayendo LARGO en panel OC:", panel_raw)
            return
        despiece.append(
            {
                "panel": panel,
                "perfil": "OCN",
                "numero_piezas": cantidad,
                "largo_pieza_mm": LARGO,
                "total_mm": LARGO * cantidad,
            }
        )

    # --- Panel BH ---
    elif tipo == "BH":
        try:
            ANCHO, LARGO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel BH:", panel_raw)
            return
        if ANCHO in [100, 110, 120]:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BH120",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": LARGO,
                    "total_mm": LARGO * cantidad,
                }
            )
        else:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BH150",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": LARGO,
                    "total_mm": LARGO * cantidad,
                }
            )

    # --- Panel BCP ---
    elif tipo == "BCP":
        try:
            ALTO, ANCHO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel BCP:", panel_raw)
            return
        if 100 <= ALTO <= 300 and 100 <= ANCHO <= 1800:
            if 600 <= ANCHO <= 1349:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": ALTO,
                        "total_mm": ALTO * cantidad,
                    }
                )
            elif 1350 <= ANCHO <= 1800:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": 2 * cantidad,
                        "largo_pieza_mm": ALTO,
                        "total_mm": 2 * ALTO * cantidad,
                    }
                )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BCPN",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ANCHO,
                    "total_mm": ANCHO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_LOSA_50",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * ALTO * cantidad,
                }
            )
        else:
            print("⚠️⚠️Pieza BCP no corresponde a ninguna del catálogo⚠️⚠️:", panel)
            return

    # --- Panel CP ---
    elif tipo == "CP":
        try:
            ALTO, ANCHO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel CP:", panel_raw)
            return
        if 100 <= ALTO <= 300 and 100 <= ANCHO <= 1800:
            if 600 <= ANCHO <= 1349:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": cantidad,
                        "largo_pieza_mm": ALTO,
                        "total_mm": ALTO * cantidad,
                    }
                )
            elif 1350 <= ANCHO <= 1800:
                despiece.append(
                    {
                        "panel": panel,
                        "perfil": "REFUERZOCHICO",
                        "numero_piezas": 2 * cantidad,
                        "largo_pieza_mm": ALTO,
                        "total_mm": 2 * ALTO * cantidad,
                    }
                )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BCPN",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ANCHO,
                    "total_mm": ANCHO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_LOSA_50",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * ALTO * cantidad,
                }
            )
        else:
            print("⚠️⚠️Pieza CP no corresponde a ninguna del catálogo⚠️⚠️:", panel)
            return

    # --- Panel CE ---
    elif tipo == "CE":
        try:
            ANCHO, ALTO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel CE:", panel_raw)
            return
        if 100 <= ALTO <= 499:
            LARGO = ALTO
            C = 1
        elif 500 <= ALTO <= 899:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ANCHO,
                    "total_mm": ANCHO * cantidad,
                }
            )
            LARGO = ALTO // 2
            C = 2
        elif 900 <= ALTO <= 1199:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ANCHO,
                    "total_mm": 2 * ANCHO * cantidad,
                }
            )
            LARGO = (300 + (ALTO - 300) / 2) // 2  # tu regla de negocio
            C = 2
        elif ALTO == 1200:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": 3 * cantidad,
                    "largo_pieza_mm": ANCHO,
                    "total_mm": 3 * ANCHO * cantidad,
                }
            )
            LARGO = 300
            C = 2
        else:
            print("Error en panel CE:", panel)
            return

        despiece.append(
            {
                "panel": panel,
                "perfil": "BASTIDOR_LOSA_50",
                "numero_piezas": 2 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 2 * ANCHO * cantidad,
            }
        )
        if 100 <= ANCHO < 300:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_LOSA",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "BASTIDOR_LOSA_54",
                    "numero_piezas": cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": ALTO * cantidad,
                }
            )
        elif 300 <= ANCHO <= 399:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_LOSA",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * ALTO * cantidad,
                }
            )
        elif 400 <= ANCHO <= 499:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_LOSA",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * ALTO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOCHICO",
                    "numero_piezas": C * cantidad,
                    "largo_pieza_mm": LARGO,
                    "total_mm": C * LARGO * cantidad,
                }
            )
        else:
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "REFUERZOGRANDE",
                    "numero_piezas": C * cantidad,
                    "largo_pieza_mm": LARGO,
                    "total_mm": C * LARGO * cantidad,
                }
            )
            despiece.append(
                {
                    "panel": panel,
                    "perfil": "ALA_LOSA",
                    "numero_piezas": 2 * cantidad,
                    "largo_pieza_mm": ALTO,
                    "total_mm": 2 * ALTO * cantidad,
                }
            )

    # --- Panel CS ---
    elif tipo == "CS":
        try:
            ANCHO, LARGO = nums[0], nums[1]
        except Exception:
            print("Error extrayendo dimensiones en panel CS:", panel_raw)
            return
        despiece.append(
            {
                "panel": panel,
                "perfil": "BCPN",
                "numero_piezas": cantidad,
                "largo_pieza_mm": LARGO,
                "total_mm": LARGO * cantidad,
            }
        )
        a = 100
        c = 0
        while a <= LARGO:
            if a == 100:
                a += 400
            elif a == 500:
                a += 400
                c += 1
            else:
                a += 300
                c += 1
        despiece.append(
            {
                "panel": panel,
                "perfil": "REFUERZOGRANDE",
                "numero_piezas": c * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": ANCHO * c * cantidad,
            }
        )
        despiece.append(
            {
                "panel": panel,
                "perfil": "TUBO",
                "numero_piezas": c * cantidad,
                "largo_pieza_mm": 47,
                "total_mm": 47 * c * cantidad,
            }
        )
        despiece.append(
            {
                "panel": panel,
                "perfil": "BASTIDOR_LOSA_50",
                "numero_piezas": 2 * cantidad,
                "largo_pieza_mm": ANCHO,
                "total_mm": 2 * ANCHO * cantidad,
            }
        )

    else:
        print("Tipo de panel no reconocido:", panel_raw)
        return


def calcular_despiece_desde_agrupado(cantidades_por_base):
    despiece = []
    for base, cantidad in cantidades_por_base.items():
        if cantidad <= 0:
            continue
        _agregar_despiece_de_panel(base, cantidad, despiece)
    return despiece


def parse_panel_code(code):
    """
    Normaliza y extrae partes del código de panel.
    Retorna:
      - tipo: prefijo alfabético (ej. WF, SF, MF, CL, CLE, CLI, CE, IC, OC, BH, BCP, CP, CS)
      - base: código sin sufijo después de '-' (ej. WF600X2250-ABC -> WF600X2250)
      - nums: lista de enteros en orden de aparición
      - partes: lista de strings separadas por 'X'
    """
    base = code.split("-", 1)[0]  # quita sufijos después de "-"
    m = re.match(r"([A-Za-z_]+)", base)  # soporta letras y guiones bajos
    tipo = m.group(1) if m else ""
    nums = list(map(int, re.findall(r"\d+", base)))
    partes = re.split(r"[xX]", base)

    # --- Normalización de tipos equivalentes ---
    if tipo in ("ICC", "IC_Chico"):
        tipo = "IC"
    elif tipo in ("OCC", "OC_Chico", "OCH"):
        tipo = "OC"

    return {"tipo": tipo, "base": base, "nums": nums, "partes": partes}


@st.cache_data
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


@st.cache_data
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


def calcular_totales_por_medida(despiece):
    """
    Agrupa el despiece por (perfil, largo_pieza_mm) y suma las cantidades y totales.
    Retorna un diccionario cuyas llaves son tuplas (perfil, largo_pieza_mm).
    """
    totales_medida = {}
    for item in despiece:
        key = (item["perfil"], item["largo_pieza_mm"])
        if key not in totales_medida:
            totales_medida[key] = {"numero_piezas": 0, "total_mm": 0}
        totales_medida[key]["numero_piezas"] += item["numero_piezas"]
        totales_medida[key]["total_mm"] += item["total_mm"]
    return totales_medida


def calcular_tiempos_por_panel(
    despiece,
    tiempo_por_corte_min=1.0,
    velocidad_soldadura_mm_por_min=50.0,
    tiempos_perforacion_por_tipo=None,
):
    if tiempos_perforacion_por_tipo is None:
        tiempos_perforacion_por_tipo = {}

    cortes_por_panel = {}
    for item in despiece:
        panel = item["panel"]
        cortes_por_panel.setdefault(panel, 0)
        cortes_por_panel[panel] += item["numero_piezas"]

    soldadura_mm_por_panel = calcular_soldadura_por_panel(despiece)

    tiempos_panel = {}
    tiempo_total_general = 0.0

    for panel, cortes in cortes_por_panel.items():
        t_corte = cortes * tiempo_por_corte_min
        mm_sold = soldadura_mm_por_panel.get(panel, 0)
        t_sold = (
            mm_sold / velocidad_soldadura_mm_por_min
            if velocidad_soldadura_mm_por_min > 0
            else 0
        )

        m = re.match(r"([A-Za-z]+)", panel)
        tipo = m.group(1) if m else panel
        t_perfor = cortes * tiempos_perforacion_por_tipo.get(tipo, 0)
        t_total = t_corte + t_sold + t_perfor

        tiempos_panel[panel] = {
            "tiempo_corte_min": t_corte,
            "tiempo_soldadura_min": t_sold,
            "tiempo_perforacion_min": t_perfor,
            "tiempo_total_min": t_total,
        }
        tiempo_total_general += t_total

    return tiempos_panel, tiempo_total_general


def calcular_costos_por_panel(
    despiece,
    tiempos_por_panel,
    tasa_clp_usd,
    detalle_insumos=True,
    # --- NUEVO: costo de la energía y potencias de máquinas (puedes ajustar)
    costo_kwh_usd=0.20,
    potencias_kw=None,
):
    """
    Calcula costos por panel e incluye detalle de insumos (cantidad y costo),
    incluyendo ojales/remaches y AHORA energía eléctrica (kWh).

    Retorna:
      1) costos_por_panel: dict con MP, MO, insumos, energía y total por panel
      2) total_general_usd: suma de todos los paneles en USD
      3) detalle_costos: dict panel → {insumo/energia_usd: costo_usd, …}
      4) detalle_unidades: dict panel → {insumo/energia_kwh: cantidad, …}
    """

    # --- NUEVO: potencias (kW) por proceso; ajusta a tus equipos reales
    # Ejemplo: sierra tronzadora 2.2 kW, soldadura MIG 5.0 kW, taladro/esmeril 1.5 kW
    if potencias_kw is None:
        potencias_kw = {"corte": 5.0, "soldadura": 4.4, "perforacion": 25.0}

    # --- Agrupación preliminar (versión segura) ---
    materia_prima_por_panel = {}
    cortes_por_panel = {}
    for it in despiece:
        p = it["panel"]
        d = materia_prima_por_panel.setdefault(p, {})
        d[it["perfil"]] = d.get(it["perfil"], 0) + it["total_mm"]
        cortes_por_panel[p] = cortes_por_panel.get(p, 0) + it["numero_piezas"]

    # --- Longitud de soldadura por panel ---
    soldadura_mm_por_panel = calcular_soldadura_por_panel(despiece)

    costos_por_panel = {}
    detalle_costos = {}
    detalle_unidades = {}
    total_general_usd = 0.0

    # --- Cálculo por panel ---
    for panel, perfiles_mm in materia_prima_por_panel.items():
        # Materia prima
        costo_mp = sum(
            mm * MATERIA_PRIMA_POR_MM.get(perfil, 0)
            for perfil, mm in perfiles_mm.items()
        )

        # Mano de obra
        t = tiempos_por_panel.get(panel, {})
        t_corte_min = t.get("tiempo_corte_min", 0.0)
        t_sold_min = t.get("tiempo_soldadura_min", 0.0)
        t_perf_min = t.get("tiempo_perforacion_min", 0.0)

        costo_mo_c = t_corte_min * MANO_OBRA["corte"] / tasa_clp_usd
        costo_mo_s = t_sold_min * MANO_OBRA["soldadura"] / tasa_clp_usd
        costo_mo_p = t_perf_min * MANO_OBRA["perforacion"] / tasa_clp_usd

        # Insumos estándar
        soldadura_length = soldadura_mm_por_panel.get(panel, 0)
        num_cortes = cortes_por_panel.get(panel, 0)

        detalle_costos[panel] = {}
        detalle_unidades[panel] = {}
        costo_insumos = 0.0

        sold_mm = soldadura_length
        sold_m = sold_mm / 1000.0
        t_sold = t_sold_min
        cortes = num_cortes

        for nombre, cfg in INSUMOS.items():
            rend = cfg.get("rendimiento", 0) or 0
            unidad = cfg.get("unidad", "m")

            if rend <= 0:
                uds = 0.0
            elif unidad == "m":
                uds = sold_m / rend
            elif unidad == "mm":
                uds = sold_mm / rend
            elif unidad == "min":
                uds = t_sold / rend
            elif unidad == "corte":
                uds = cortes / rend
            else:
                uds = sold_m / rend

            costo = uds * cfg["costo"]
            detalle_unidades[panel][nombre] = round(uds, 3)
            detalle_costos[panel][nombre] = costo
            costo_insumos += costo

        # --- Ojales y remaches (WF siempre; SF/MF solo si ANCHO=600) ---
        info_panel = parse_panel_code(panel)
        tipo_p = info_panel["tipo"]
        nums_p = info_panel["nums"]

        def _agregar_ojales_remaches(alto_mm):
            ojal_count = (alto_mm // 300) * 2
            remache_count = ojal_count * 2
            detalle_unidades[panel]["ojales"] = ojal_count
            cost_ojal = ojal_count * 0.927
            detalle_costos[panel]["ojales"] = cost_ojal
            detalle_unidades[panel]["remaches"] = remache_count
            cost_rem = remache_count * 0.135
            detalle_costos[panel]["remaches"] = cost_rem
            return cost_ojal + cost_rem

        if tipo_p == "WF":
            alto_mm = nums_p[1] if len(nums_p) > 1 else 0
            costo_insumos += _agregar_ojales_remaches(alto_mm)
        elif tipo_p in ("SF", "MF"):
            if len(nums_p) >= 2:
                ancho_mm, alto_mm = nums_p[0], nums_p[1]
                if ancho_mm == 600:
                    costo_insumos += _agregar_ojales_remaches(alto_mm)

        # --- NUEVO: Energía eléctrica (kWh y costo) ---
        kwh_corte = (t_corte_min / 60.0) * (potencias_kw.get("corte", 0.0) or 0.0)
        kwh_sold = (t_sold_min / 60.0) * (potencias_kw.get("soldadura", 0.0) or 0.0)
        kwh_perf = (t_perf_min / 60.0) * (potencias_kw.get("perforacion", 0.0) or 0.0)
        energia_kwh = kwh_corte + kwh_sold + kwh_perf
        costo_energia = energia_kwh * costo_kwh_usd

        # Guardar en detalle
        detalle_unidades[panel]["energia_kwh"] = round(energia_kwh, 4)
        detalle_costos[panel]["energia_usd"] = costo_energia

        # Total por panel
        total_panel = (
            costo_mp
            + costo_mo_c
            + costo_mo_s
            + costo_mo_p
            + costo_insumos
            + costo_energia
        )
        costos_por_panel[panel] = {
            "costo_mp_usd": costo_mp,
            "costo_mo_corte_usd": costo_mo_c,
            "costo_mo_sold_usd": costo_mo_s,
            "costo_mo_perf_usd": costo_mo_p,
            "costo_insumos_usd": costo_insumos,
            "costo_energia_usd": costo_energia,  # ← NUEVO
            "costo_total_usd": total_panel,
        }
        total_general_usd += total_panel

    return costos_por_panel, total_general_usd, detalle_costos, detalle_unidades


def calcular_detalle_insumos(detalle_costos, detalle_unidades):
    detalle_por_pieza = {}
    total_pedido = {}

    for panel, costos in detalle_costos.items():
        detalle_por_pieza[panel] = {}
        for insumo, costo in costos.items():  # << ahora usa 'costos'
            uds = detalle_unidades.get(panel, {}).get(insumo, 0)
            detalle_por_pieza[panel][insumo] = {"cantidad": uds, "costo_usd": costo}
            if insumo not in total_pedido:
                total_pedido[insumo] = {"cantidad_total": 0, "costo_total_usd": 0.0}
            total_pedido[insumo]["cantidad_total"] += uds
            total_pedido[insumo]["costo_total_usd"] += costo

    return detalle_por_pieza, total_pedido


@st.cache_data
def calcular_soldadura_por_panel(despiece):
    # Agrupar items por panel
    paneles = {}
    for item in despiece:
        panel_code = item["panel"]
        paneles.setdefault(panel_code, []).append(item)

    soldadura_por_panel = {}

    for panel, items in paneles.items():
        soldadura_total = 0
        ala_muro_contado = (
            False  # ALA_MURO / ALA_LOSA se cuentan una sola vez (tu regla actual)
        )

        # Info base del código (tipo, números, etc.)
        info = parse_panel_code(panel)
        tipo = info["tipo"]
        nums = info["nums"]

        # 1) Aportes por perfil de cada ítem
        for it in items:
            perfil = it["perfil"]
            largo = it["largo_pieza_mm"]
            piezas = it["numero_piezas"]

            if perfil in ("ALA_MURO", "ALA_LOSA"):
                # regla actual: contar una sola vez por panel
                if not ala_muro_contado:
                    soldadura_total += largo
                    ala_muro_contado = True

            elif perfil in ("BASTIDOR_MURO_50", "BASTIDOR_LOSA_50"):
                soldadura_total += (largo + 100) * piezas

            elif perfil == "REFUERZOCHICO":
                soldadura_total += (math.ceil(largo / 120) * 100 + 240) * piezas

            elif perfil == "REFUERZOGRANDE":
                soldadura_total += (math.ceil(largo / 120) * 100 + 400) * piezas

            elif perfil == "REFUERZO_CL70":
                soldadura_total += 270 * piezas

            elif perfil in ("REFUERZO_CL100", "REFUERZO_CL50"):
                soldadura_total += 250 * piezas

            elif perfil == "REFUERZO_IC":
                soldadura_total += 300 * piezas

            elif perfil == "TUBO":
                soldadura_total += 157 * piezas

            # Otros perfiles: sin aporte de soldadura

        # 2) Extras por tipo de panel (manteniendo tu lógica original)

        # CLI / CLE: extra fijo
        if "CLI" in panel or "CLE" in panel:
            soldadura_total += 270 + 200

        # CS / CP / BCP: usar helper para ALTO/ANCHO y sumar extras
        if tipo in ("CS", "CP", "BCP"):
            try:
                # Para BCP/CP definimos antes ALTO, ANCHO (en ese orden)
                # Para CS definimos ANCHO, LARGO, pero aquí sólo necesitamos ANCHO y ALTO.
                # En tu lógica original, ALTO se lee del prefijo (CL/BCP/CP), para CS no está explícito.
                # Conservamos tu criterio: en BCP/CP, ALTO es nums[0], ANCHO es nums[1].
                if tipo in ("BCP", "CP"):
                    ALTO, ANCHO = nums[0], nums[1]
                    if tipo == "BCP":
                        soldadura_total += 200  # extra cuando empieza con 'B' (BCP)
                else:
                    # CS: en tu cálculo original no se usó ALTO directamente aquí,
                    # sólo después para condiciones en BCP/CP. Así que no hacemos nada especial.
                    # Si alguna vez necesitas ALTO para CS, ajusta la regla aquí.
                    ANCHO = nums[0]  # primera cifra es ANCHO en CS
                    ALTO = None

                if ALTO is not None:
                    if ALTO > 150:
                        soldadura_total += ANCHO * 2
                    if ALTO < 150:
                        soldadura_total += ANCHO
            except Exception:
                # Si falla el parse, no sumamos extras (mantenemos robustez)
                pass

        # IC: usar helper para ANCHO/ALTO/LARGO y sumar extras
        if tipo == "IC":
            try:
                ANCHO, ALTO, LARGO = nums[0], nums[1], nums[2]
                if ANCHO > 150 or ALTO > 150:
                    soldadura_total += LARGO * 2
                if ANCHO < 150 or ALTO < 150:
                    soldadura_total += LARGO
            except Exception:
                pass

        # WF: extra fijo
        if tipo == "WF":
            soldadura_total += 300

        # CE: si ANCHO == 600, sumar 600
        if tipo == "CE":
            try:
                ANCHO = nums[0]
                if ANCHO == 600:
                    soldadura_total += 600
            except Exception:
                pass

        soldadura_por_panel[panel] = soldadura_total

    return soldadura_por_panel


def resumen_totales_pedido(
    resultado_despiece,
    tiempos_panel,
    tiempo_total_general,
    costos_por_panel,
    total_general_usd,
    cantidades_por_base,
    input_csv="paneles.csv",
):
    """
    Resumen global del pedido ALINEADO con el cálculo por BASE:
      - total_piezas_despiece
      - total_paneles
      - total_area_m2
      - total_costo_usd
      - total_tiempo_min / horas / días
      - costo_promedio_usd_m2
    """
    # 1) Total piezas del despiece
    total_piezas_despiece = sum(it.get("numero_piezas", 0) for it in resultado_despiece)

    # 3) Totales
    total_paneles = sum(cantidades_por_base.values())

    # 4) Área TOTAL por BASE (una sola vez, usando el agrupado)
    _, total_area_m2 = calcular_areas_por_base(cantidades_por_base)

    # 5) Costos y tiempos
    total_costo_usd = float(total_general_usd or 0.0)
    total_tiempo_min = float(tiempo_total_general or 0.0)
    total_tiempo_horas = total_tiempo_min / 60.0 if total_tiempo_min > 0 else 0.0
    total_tiempo_dias = total_tiempo_horas / 8.0 if total_tiempo_horas > 0 else 0.0

    # 6) Promedio USD/m²
    costo_promedio_usd_m2 = (
        (total_costo_usd / total_area_m2) if total_area_m2 > 0 else 0.0
    )

    return {
        "total_piezas_despiece": total_piezas_despiece,
        "total_paneles": total_paneles,
        "total_area_m2": total_area_m2,
        "total_costo_usd": total_costo_usd,
        "total_tiempo_min": total_tiempo_min,
        "total_tiempo_horas": total_tiempo_horas,
        "total_tiempo_dias": total_tiempo_dias,
        "costo_promedio_usd_m2": costo_promedio_usd_m2,
    }


# === Función para calcular área ===
def calcular_area(dimensiones):
    """
    A partir de una lista de dimensiones (X-separadas), devuelve:
      - ancho (mm)
      - largo (mm)
      - área en m²
    """
    if len(dimensiones) == 1:
        ancho = 108
        largo = dimensiones[0]
    elif len(dimensiones) == 2:
        ancho, largo = dimensiones
    elif len(dimensiones) == 3:
        ancho = dimensiones[0] + dimensiones[1]
        largo = dimensiones[2]
    elif len(dimensiones) == 4:
        ancho = dimensiones[0] + dimensiones[1]
        largo = dimensiones[2] + dimensiones[3]
    else:
        return 0, 0, 0
    area = ancho * largo / 1_000_000
    return ancho, largo, area

@st.cache_data
def calcular_areas_por_base(cantidades_por_base):
    filas = []
    total_area = 0.0
    for base, cant in sorted(cantidades_por_base.items(), key=lambda x: x[0].lower()):
        _, _, area_unit = calcular_area(parse_panel_code(base)["nums"])
        if area_unit <= 0:
            continue
        area_total = area_unit * cant
        filas.append(
            {
                "Panel (base)": base,
                "Cantidad": cant,
                "Área panel (m²)": round(area_unit, 3),
                "Área total (m²)": round(area_total, 3),
            }
        )
        total_area += area_total
    return filas, total_area


