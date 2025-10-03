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
