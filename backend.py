import re
import math

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
