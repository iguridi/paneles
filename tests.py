import pandas as pd

from backend import (
    calcular_area,
    calcular_areas_por_base,
    calcular_costos_por_panel,
    calcular_despiece_desde_agrupado,
    calcular_materia_prima_por_perfil,
    calcular_soldadura_por_panel,
    calcular_tiempos_por_panel,
    calcular_totales_perfiles,
    parse_panel_code,
)


CANTIDADES_POR_BASE = {"WF600X2250": 10, "SF400X2000": 5}
DF_PEDIDO = pd.DataFrame(
    [
        {"Panel (base)": "WF600X2250", "Cantidad": 10},
        {"Panel (base)": "SF400X2000", "Cantidad": 5},
    ]
)
resultado_despiece = calcular_despiece_desde_agrupado(CANTIDADES_POR_BASE)
tiempos_panel, _ = calcular_tiempos_por_panel(resultado_despiece)



def assert_equals(x, y):
    assert x == y, f"{x} != {y}"


assert_equals(
    calcular_materia_prima_por_perfil(resultado_despiece, longitud_perfil=5850),
    {
        "ALA_MURO": {"num_perfiles": 15, "waste_mm": 22750},
        "REFUERZOGRANDE": {"num_perfiles": 10, "waste_mm": 6320},
        "REFUERZOCHICO": {"num_perfiles": 2, "waste_mm": 4410},
        "BASTIDOR_MURO_50": {"num_perfiles": 3, "waste_mm": 1550},
    },
)

assert_equals(
    calcular_totales_perfiles(resultado_despiece),
    {
        "ALA_MURO": {"numero_piezas": 30, "total_mm": 65000},
        "REFUERZOGRANDE": {"numero_piezas": 110, "total_mm": 52180},
        "REFUERZOCHICO": {"numero_piezas": 15, "total_mm": 7290},
        "BASTIDOR_MURO_50": {"numero_piezas": 30, "total_mm": 16000},
    },
)

assert_equals(
    calcular_soldadura_por_panel(resultado_despiece),
    {"WF600X2250": 90950, "SF400X2000": 33700},
)

assert_equals(
    calcular_tiempos_por_panel(resultado_despiece),
    (
        {
            "WF600X2250": {
                "tiempo_corte_min": 130.0,
                "tiempo_soldadura_min": 1819.0,
                "tiempo_perforacion_min": 0,
                "tiempo_total_min": 1949.0,
            },
            "SF400X2000": {
                "tiempo_corte_min": 55.0,
                "tiempo_soldadura_min": 674.0,
                "tiempo_perforacion_min": 0,
                "tiempo_total_min": 729.0,
            },
        },
        2678.0,
    ),
)

assert_equals(
    parse_panel_code(list(CANTIDADES_POR_BASE.keys())[0]),
    {
        "tipo": "WF",
        "base": "WF600X2250",
        "nums": [600, 2250],
        "partes": ["WF600", "2250"],
    },
)

assert_equals(
    calcular_area([600, 2250]),
    (600, 2250, 1.35),
)

assert_equals(
    calcular_areas_por_base(CANTIDADES_POR_BASE),
    (
        [
            {
                "Panel (base)": "SF400X2000",
                "Cantidad": 5,
                "Área panel (m²)": 0.8,
                "Área total (m²)": 4.0,
            },
            {
                "Panel (base)": "WF600X2250",
                "Cantidad": 10,
                "Área panel (m²)": 1.35,
                "Área total (m²)": 13.5,
            },
        ],
        17.5,
    ),
)

assert_equals(
    calcular_costos_por_panel(
        resultado_despiece,
        {
            "WF600X2250": {
                "tiempo_corte_min": 130.0,
                "tiempo_soldadura_min": 1819.0,
                "tiempo_perforacion_min": 0,
                "tiempo_total_min": 1949.0,
            }
        },
        970,
        True,
    ),
    (
        {
            "WF600X2250": {
                "costo_mp_usd": 1058.07956496,
                "costo_mo_corte_usd": 11.293470790378006,
                "costo_mo_sold_usd": 206.62214776632302,
                "costo_mo_perf_usd": 0.0,
                "costo_insumos_usd": 35.543290597343,
                "costo_energia_usd": 28.84533333333334,
                "costo_total_usd": 1340.3838074473774,
            },
            "SF400X2000": {
                "costo_mp_usd": 428.383824,
                "costo_mo_corte_usd": 0.0,
                "costo_mo_sold_usd": 0.0,
                "costo_mo_perf_usd": 0.0,
                "costo_insumos_usd": 6.960574965700483,
                "costo_energia_usd": 0.0,
                "costo_total_usd": 435.34439896570046,
            },
        },
        1775.728206413078,
        {
            "WF600X2250": {
                "gas": 2.0198808695652177,
                "soldadura": 10.683593333333334,
                "boquillas": 0.50932,
                "teflon": 1.3511127777777778,
                "tobera": 0.5541886666666668,
                "espiral": 0.8161246666666668,
                "difusor": 0.29346533333333336,
                "discos_lija": 2.3161933333333335,
                "discos_corte": 0.1285426666666667,
                "esmeril": 0.11286895,
                "ojales": 12.978000000000002,
                "remaches": 3.7800000000000002,
                "energia_usd": 28.84533333333334,
            },
            "SF400X2000": {
                "gas": 0.7484330434782609,
                "soldadura": 3.958626666666667,
                "boquillas": 0.18872,
                "teflon": 0.5006322222222223,
                "tobera": 0.20534533333333338,
                "espiral": 0.3024013333333334,
                "difusor": 0.10873866666666668,
                "discos_lija": 0.8582266666666667,
                "discos_corte": 0.04762933333333334,
                "esmeril": 0.041821699999999996,
                "energia_usd": 0.0,
            },
        },
        {
            "WF600X2250": {
                "gas": 0.158,
                "soldadura": 0.606,
                "boquillas": 0.606,
                "teflon": 0.101,
                "tobera": 0.121,
                "espiral": 0.121,
                "difusor": 0.121,
                "discos_lija": 1.213,
                "discos_corte": 0.121,
                "esmeril": 0.003,
                "ojales": 14,
                "remaches": 28,
                "energia_kwh": 144.2267,
            },
            "SF400X2000": {
                "gas": 0.059,
                "soldadura": 0.225,
                "boquillas": 0.225,
                "teflon": 0.037,
                "tobera": 0.045,
                "espiral": 0.045,
                "difusor": 0.045,
                "discos_lija": 0.449,
                "discos_corte": 0.045,
                "esmeril": 0.001,
                "energia_kwh": 0.0,
            },
        },
    ),
)

print("All tests passed!")
