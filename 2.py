import streamlit as st
import pandas as pd

# Insumos estándar (no eléctricos)
INSUMOS = {
        'gas':          {'costo': 12.77, 'rendimiento': 575,   'unidad': 'm'},
        'soldadura':    {'costo': 17.62, 'rendimiento': 150,   'unidad': 'm'},
        'boquillas':    {'costo': 0.84,  'rendimiento': 150,   'unidad': 'm'},
        'teflon':       {'costo': 13.37, 'rendimiento': 900,   'unidad': 'm'},
        'tobera':       {'costo': 4.57,  'rendimiento': 750,   'unidad': 'm'},
        'espiral':      {'costo': 6.73,  'rendimiento': 750,   'unidad': 'm'},
        'difusor':      {'costo': 2.42,  'rendimiento': 750,   'unidad': 'm'},
        'discos_lija':  {'costo': 1.91,  'rendimiento': 75,    'unidad': 'm'},
        'discos_corte': {'costo': 1.06,  'rendimiento': 750,   'unidad': 'm'},
        'esmeril':      {'costo': 37.23, 'rendimiento': 30000, 'unidad': 'm'},
    }


st.file_uploader("paneles.csv")

opcion = st.radio("Seleccione que listado desea detallar", [
"Despiece detallado",
"Materia prima necesaria por perfil (incluye totales)",
"Soldadura necesaria por panel",
"Tiempos por panel",
"Costos por panel (con USD/m² + resumen)",
"Detalle de insumos por pieza y total pedido",
"Área por panel",
"Resumen",
"Todos",
])

RESULTADO_DESPIECE = [
    {
        'panel': "hola",
        'perfil': "wow",
        'numero_piezas': "wow",
        'largo_pieza_mm': "wow",
        'total_mm': "wow",
    },
    {
        'panel': "hola",
        'perfil': "wow2",
        'numero_piezas': "wow2",
        'largo_pieza_mm': "wow2",
        'total_mm': "wow2",
    },
]

generar = st.button("Generar")

msg = '''
## Despiece detallado

Panel | Perfil | Piezas | Largo (mm) | Total (mm)
| -| - | - |- |- |
'''



for item in RESULTADO_DESPIECE:
    msg += f"| {item['panel']:<15} | {item['perfil']:<35} | {item['numero_piezas']:<8} | {item['largo_pieza_mm']:<10} | {item['total_mm']:<10} |\n"

res = st.markdown(msg)

# download = st.download_button("Descargar")


df = pd.DataFrame({
  'first column': [1, 2, 3, 4],
  'second column': [10, 20, 30, 40]
})

# df