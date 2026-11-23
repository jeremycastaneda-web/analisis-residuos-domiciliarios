import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title="Residuos del Perú", page_icon="♻️", layout="wide")

archivo = "datos/composicion_rrss_2019_2024.csv"

@st.cache_data
def cargar_datos():
    datos = pd.read_csv(archivo, sep=";", encoding="cp1252")
    columnas = [c for c in datos if c.startswith("QRESIDUOS_")]
    datos[columnas] = datos[columnas].apply(pd.to_numeric, errors="coerce")
    datos["PERIODO"] = pd.to_numeric(datos["PERIODO"], errors="coerce")
    return datos, columnas

datos, columnas = cargar_datos()

grupos = {
    "Orgánicos": ["ALIMENTOS", "MALEZA", "OTROS_ORGANICOS"],
    "Papel y cartón": ["PAPEL", "CARTON"],
    "Plásticos": ["TEREFLATO", "POLIETILENO", "POLIPROPILENO",
                  "POLIESTIRENO", "POLICLORURO", "TETRABRICK",
                  "BOLSAS", "TECNOPOR", "ENVOLTURAS"],
    "Vidrio": ["VIDRIO"],
    "Metales": ["LATA", "METALES", "ALUMINIO"]
}

def calcular_composicion(tabla):
    resultado = {}
    pendientes = [c for c in columnas if c != "QRESIDUOS_DOM"]

    for grupo, palabras in grupos.items():
        elegidas = [c for c in pendientes
                    if any(c.replace("QRESIDUOS_", "").startswith(p) for p in palabras)]
        resultado[grupo] = tabla[elegidas].sum().sum()
        pendientes = [c for c in pendientes if c not in elegidas]

    resultado["Otros"] = tabla[pendientes].sum().sum()
    return pd.Series(resultado).clip(lower=0)

st.title("♻️ Composición de residuos sólidos domiciliarios")
st.write("**Análisis de residuos en el Perú (2019–2024)**")
st.caption("Fuente: Ministerio del Ambiente (MINAM). Cantidades en toneladas.")


st.sidebar.header("Filtros")
anios = sorted(datos["PERIODO"].dropna().astype(int).unique(), reverse=True)
anio = st.sidebar.selectbox("Año", anios)

dep = st.sidebar.selectbox("Departamento", ["Todo el Perú"] + sorted(datos["DEPARTAMENTO"].dropna().unique()))

ubicacion = datos.copy()
if dep != "Todo el Perú":
    ubicacion = ubicacion[ubicacion["DEPARTAMENTO"] == dep]

prov = st.sidebar.selectbox("Provincia", ["Todas"] + sorted(ubicacion["PROVINCIA"].dropna().unique()))
if prov != "Todas":
    ubicacion = ubicacion[ubicacion["PROVINCIA"] == prov]

dist = st.sidebar.selectbox("Distrito", ["Todos"] + sorted(ubicacion["DISTRITO"].dropna().unique()))
if dist != "Todos":
    ubicacion = ubicacion[ubicacion["DISTRITO"] == dist]

seleccion = ubicacion[ubicacion["PERIODO"] == anio]

if seleccion.empty:
    st.warning("No hay datos para esta selección.")
    st.stop()

total = seleccion["QRESIDUOS_DOM"].sum()
materiales = [c for c in columnas if c != "QRESIDUOS_DOM"]
detallado = seleccion[materiales].sum().sum()
composicion = calcular_composicion(seleccion)

st.header("1. Resumen del proyecto")
st.write("Analizamos los residuos domiciliarios del Perú mediante gráficos y filtros interactivos.")

c1, c2, c3 = st.columns(3)
c1.metric("Residuos declarados", f"{total:,.2f} t")
c2.metric("Materiales detallados", f"{detallado:,.2f} t")
c3.metric("Registros", len(seleccion))

if total > 0 and abs(total - detallado) / total > 0.05:
    st.warning("Los materiales detallados no coinciden con el total declarado. Los porcentajes corresponden a los materiales informados.")

st.header("2. Composición de residuos")

tabla = composicion.reset_index()
tabla.columns = ["Grupo", "Toneladas"]
tabla = tabla[tabla["Toneladas"] > 0].copy()

if not tabla.empty:
    tabla["Porcentaje"] = (tabla["Toneladas"] / tabla["Toneladas"].sum() * 100).round(2)

    st.vega_lite_chart(tabla, {
        "mark": {"type": "arc", "outerRadius": 150},
        "encoding": {
            "theta": {"field": "Toneladas", "type": "quantitative"},
            "color": {"field": "Grupo", "type": "nominal"},
            "tooltip": [
                {"field": "Grupo", "type": "nominal"},
                {"field": "Toneladas", "type": "quantitative", "format": ",.2f"},
                {"field": "Porcentaje", "type": "quantitative", "format": ".2f"}
            ]
        }
    }, use_container_width=True)

    st.write("**Grupo con mayor cantidad:**", composicion.idxmax())
    st.dataframe(tabla, hide_index=True, use_container_width=True)
else:
    st.info("No hay datos suficientes para el gráfico circular.")

st.caption("Los porcentajes representan únicamente los materiales detallados.")

p1, p2, p3 = st.tabs(["Evolución", "Comparación", "Datos y conclusiones"])

with p1:
    st.subheader("3. Evolución anual")
    evolucion = ubicacion.groupby("PERIODO")["QRESIDUOS_DOM"].sum().sort_index()
    st.line_chart(evolucion)
    st.dataframe(evolucion.rename("Toneladas").reset_index(), hide_index=True)

with p2:
    st.subheader("4. Comparación de categorías")
    st.bar_chart(composicion)

    st.subheader("Comparación territorial")
    if dep == "Todo el Perú":
        nivel = "DEPARTAMENTO"
    elif prov == "Todas":
        nivel = "PROVINCIA"
    else:
        nivel = "DISTRITO"

    comparacion = seleccion.groupby(nivel)["QRESIDUOS_DOM"].sum().nlargest(15)
    st.bar_chart(comparacion, horizontal=True)

with p3:
    st.subheader("5. Análisis estadístico")
    valores = seleccion["QRESIDUOS_DOM"].to_numpy(dtype=float)

    if np.isfinite(valores).any():
        st.write("Promedio:", round(np.nanmean(valores), 2), "toneladas")
        st.write("Mediana:", round(np.nanmedian(valores), 2), "toneladas")
        st.write("Máximo:", round(np.nanmax(valores), 2), "toneladas")
        st.write("Mínimo:", round(np.nanmin(valores), 2), "toneladas")

    st.dataframe(seleccion, hide_index=True)

    st.download_button(
        "Descargar datos",
        seleccion.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="residuos_filtrados.csv",
        mime="text/csv")
    
    st.subheader("Conclusión")
    st.write(
        "Los resultados permiten conocer la composición y evolución "
        "de los residuos domiciliarios. Esta información puede apoyar "
        "la segregación y el reciclaje. Sin embargo, las diferencias "
        "entre los totales y los materiales deben interpretarse con precaución.")
st.divider()
st.caption("Programación Avanzada | Python, Pandas, NumPy y Streamlit")
