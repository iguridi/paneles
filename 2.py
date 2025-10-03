import streamlit as st
import pandas as pd


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

generar = st.button("Generar")


df = pd.DataFrame({
  'first column': [1, 2, 3, 4],
  'second column': [10, 20, 30, 40]
})

# df