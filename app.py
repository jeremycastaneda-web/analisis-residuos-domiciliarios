"""Proyecto final de Programación Avanzada: residuos domiciliarios en Perú."""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(page_title="Residuos domiciliarios", page_icon="♻️", layout="wide")

# El archivo CSV debe permanecer dentro de la carpeta datos.
archivo = Path(__file__).parent / "datos" / "composicion_rrss_2019_2024.csv"

# Estos grupos reúnen materiales del dataset que tienen características similares.
grupos_residuos = {
    "Orgánicos": ["ALIMENTOS", "MALEZA", "OTROS_ORGANICOS"],
    "Papel y cartón": ["PAPEL_BLANCO", "PAPEL_PERIODICO", "PAPEL_MIXTO",
                       "CARTON_BLANCO", "CARTON_MARRON", "CARTON_MIXTO"],
    "Plásticos y envases": ["TEREFLATO_POLIETILENO", "POLIETILENO_ALTA_DENSIDAD",
                            "POLIETILENO_BAJA_DENSIDAD", "POLIPROPILENO",
                            "POLIESTIRENO", "POLICLORURO_VINILO", "TETRABRICK",
                            "BOLSAS_PLASTICAS", "TECNOPOR", "ENVOLTURAS_SNAKCS_OTROS"],
    "Vidrio": ["VIDRIO_TRANSPARENTE", "VIDRIO_OTROS_COLORES", "VIDRIOS_OTROS"],
    "Metales": ["LATA", "METALES_FERROSOS", "ALUMINIO", "OTROS_METALES"],
    "Otros": ["SANITARIOS", "PILAS", "INERTES", "TEXTILES", "CAUCHO_CUERO",
              "MEDICAMENTOS", "OTROS_NO_CATEGORIZADOS"],
}


@st.cache_data
def cargar_datos():
    # El archivo original del MINAM está separado por punto y coma.
    datos = pd.read_csv(archivo, sep=";", encoding="cp1252", dtype={"UBIGEO": str})

    columnas_residuos = [col for col in datos.columns
                         if col.startswith("QRESIDUOS_") and col != "QRESIDUOS_DOM"]
    columnas_numericas = ["QRESIDUOS_DOM", "GPC_DOM"] + columnas_residuos

    for columna in columnas_numericas:
        datos[columna] = pd.to_numeric(datos[columna], errors="coerce")

    datos["PERIODO"] = pd.to_numeric(datos["PERIODO"], errors="coerce")
    datos["UBIGEO"] = datos["UBIGEO"].str.zfill(6)

    # NumPy suma las cantidades registradas de los diferentes materiales.
    matriz = datos[columnas_residuos].to_numpy(dtype=float)
    datos["SUMA_MATERIALES"] = np.nansum(matriz, axis=1)
    datos["DIFERENCIA"] = datos["SUMA_MATERIALES"] - datos["QRESIDUOS_DOM"]

    return datos, columnas_residuos


def mostrar_numero(valor):
    """Muestra los valores con separador de miles y dos decimales."""
    return f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def obtener_composicion(datos_filtrados):
    """Calcula cuántas toneladas hay de cada grupo de materiales."""
    resultado = {}
    for grupo, materiales in grupos_residuos.items():
        columnas = ["QRESIDUOS_" + material for material in materiales]
        resultado[grupo] = datos_filtrados[columnas].sum().sum()
    return pd.Series(resultado, name="Toneladas")


st.title("♻️ Composición de residuos sólidos domiciliarios")
st.write("**Perú, 2019–2024 | Proyecto de Programación Avanzada**")
st.caption("Fuente de los datos: Ministerio del Ambiente (MINAM). Las cantidades están en toneladas por año.")

try:
    datos, columnas_materiales = cargar_datos()
except (FileNotFoundError, UnicodeError, pd.errors.ParserError, KeyError) as error:
    st.error("No se pudo abrir el dataset. Revisa que el CSV esté dentro de la carpeta datos.")
    st.code(str(error))
    st.stop()

# Los selectores permiten explorar departamentos, provincias y distritos.
st.sidebar.header("Filtros")
anios = sorted(datos["PERIODO"].dropna().astype(int).unique().tolist())
anio = st.sidebar.selectbox("Año", anios, index=len(anios) - 1)

departamentos = sorted(datos["DEPARTAMENTO"].dropna().unique().tolist())
departamento = st.sidebar.selectbox("Departamento", ["Todo el Perú"] + departamentos)

ubicacion = datos.copy()
if departamento != "Todo el Perú":
    ubicacion = ubicacion[ubicacion["DEPARTAMENTO"] == departamento]

provincias = sorted(ubicacion["PROVINCIA"].dropna().unique().tolist())
provincia = st.sidebar.selectbox("Provincia", ["Todas"] + provincias)
if provincia != "Todas":
    ubicacion = ubicacion[ubicacion["PROVINCIA"] == provincia]

distritos = sorted(ubicacion["DISTRITO"].dropna().unique().tolist())
distrito = st.sidebar.selectbox("Distrito", ["Todos"] + distritos)
if distrito != "Todos":
    ubicacion = ubicacion[ubicacion["DISTRITO"] == distrito]

seleccion = ubicacion[ubicacion["PERIODO"] == anio].copy()

if seleccion.empty:
    st.warning("No hay datos para esta ubicación y año. Prueba con otros filtros.")
    st.stop()

st.header("1. Resumen del proyecto")
st.write(
    "En este trabajo analizamos los residuos que se generan en las viviendas del Perú. "
    "La página permite revisar los cambios por año y conocer qué materiales aparecen "
    "en los registros del MINAM. También podemos comparar departamentos, provincias y distritos."
)

total_residuos = seleccion["QRESIDUOS_DOM"].sum()
total_materiales = seleccion["SUMA_MATERIALES"].sum()
relacion = total_materiales / total_residuos * 100 if total_residuos > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Residuos declarados", mostrar_numero(total_residuos) + " t")
col2.metric("Materiales detallados", mostrar_numero(total_materiales) + " t")
col3.metric("Registros", len(seleccion))

if not 95 <= relacion <= 105:
    st.warning(
        "Importante: la suma de los materiales detallados no coincide con el total declarado. "
        "Por eso, los porcentajes de composición se calculan sobre los materiales informados, "
        "no sobre el total de residuos."
    )

pestana1, pestana2, pestana3, pestana4 = st.tabs([
    "Evolución anual", "Tipos de residuos", "Comparación", "Datos y conclusiones"
])

with pestana1:
    st.subheader("2. ¿Cómo cambió la cantidad de residuos?")
    evolucion = ubicacion.groupby("PERIODO")["QRESIDUOS_DOM"].sum().sort_index()
    st.line_chart(evolucion, x_label="Año", y_label="Toneladas por año")
    st.dataframe(evolucion.rename("Toneladas").reset_index(), hide_index=True)

    # Estadística descriptiva con funciones básicas de Pandas.
    valores = seleccion["QRESIDUOS_DOM"].dropna()
    if not valores.empty:
        st.write("**Estadísticas de los registros seleccionados**")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Promedio", mostrar_numero(valores.mean()) + " t")
        c2.metric("Mediana", mostrar_numero(valores.median()) + " t")
        c3.metric("Mínimo", mostrar_numero(valores.min()) + " t")
        c4.metric("Máximo", mostrar_numero(valores.max()) + " t")

with pestana2:
    st.subheader("3. Composición de los residuos")
    composicion = obtener_composicion(seleccion).sort_values(ascending=False)
    st.bar_chart(composicion, x_label="Tipo de residuo", y_label="Toneladas")

    tabla = composicion.reset_index()
    tabla.columns = ["Grupo", "Toneladas"]
    tabla["Porcentaje informado"] = (
        tabla["Toneladas"] / total_materiales * 100 if total_materiales > 0 else 0
    )
    st.dataframe(tabla, hide_index=True, use_container_width=True)
    st.caption("Los grupos fueron creados para facilitar el análisis de las 33 clases de residuos.")

    st.write("**Materiales individuales con mayor cantidad registrada**")
    materiales = seleccion[columnas_materiales].sum().sort_values(ascending=False).head(10)
    materiales.index = materiales.index.str.replace("QRESIDUOS_", "", regex=False).str.replace("_", " ")
    st.bar_chart(materiales, horizontal=True, x_label="Toneladas")

with pestana3:
    st.subheader("4. Comparación entre territorios")
    if departamento == "Todo el Perú":
        nivel = "DEPARTAMENTO"
    elif provincia == "Todas":
        nivel = "PROVINCIA"
    else:
        nivel = "DISTRITO"

    comparacion = (seleccion.groupby(nivel)["QRESIDUOS_DOM"]
                   .sum().sort_values(ascending=False).head(15))
    st.bar_chart(comparacion, horizontal=True, x_label="Toneladas")
    st.caption("Una mayor cantidad total puede deberse a que el lugar tiene más habitantes.")

with pestana4:
    st.subheader("5. Revisión de los datos")
    st.write("Comparamos el total declarado con la suma de los tipos de residuos registrados.")
    diferencias = seleccion["DIFERENCIA"].abs()
    porcentaje_diferencia = diferencias / seleccion["QRESIDUOS_DOM"].replace(0, np.nan)
    alertas = (diferencias > 1) & (porcentaje_diferencia > 0.05)
    st.metric("Registros con diferencias relevantes", int(alertas.sum()))
    st.caption("Criterio utilizado: diferencia mayor de 1 tonelada y mayor del 5 % del total.")

    columnas = ["PERIODO", "DEPARTAMENTO", "PROVINCIA", "DISTRITO",
                "QRESIDUOS_DOM", "SUMA_MATERIALES", "DIFERENCIA"]
    st.dataframe(seleccion[columnas], hide_index=True, use_container_width=True)
    st.download_button("Descargar datos filtrados", seleccion.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       file_name="residuos_filtrados.csv", mime="text/csv")

    st.subheader("Conclusión")
    st.write(
        "Los resultados permiten conocer cómo se distribuye la generación de residuos "
        "en el país y qué materiales aparecen con mayor frecuencia en los registros. "
        "La información puede apoyar la planificación de segregación y aprovechamiento. "
        "Sin embargo, las diferencias entre los totales y los componentes deben "
        "revisarse antes de sacar conclusiones definitivas sobre los porcentajes."
    )

st.divider()
st.caption("Herramientas utilizadas: Python, NumPy, Pandas y Streamlit. Dataset: MINAM (2019–2024).")
