import streamlit as st
import pandas as pd
import os
import plotly.express as px

# --- CONFIGURACIÓN Y MAPPING ---

# Mapeo de meses (constante)
MESES_MAP = {
    1: "01 Enero", 2: "02 Febrero", 3: "03 Marzo", 4: "04 Abril",
    5: "05 Mayo", 6: "06 Junio", 7: "07 Julio", 8: "08 Agosto",
    9: "09 Septiembre", 10: "10 Octubre", 11: "11 Noviembre", 12: "12 Diciembre"
}

# Configuración de la página
st.set_page_config(page_title="Reporte de Ventas", layout="wide")

# Logos Encabezado
col1, col2, col3 = st.columns([1, 1, 1])
# Nota: Asumo que las imágenes 'assets/logo_vincu.png', 'assets/logo_met.png' y 'assets/logo.png' existen en tu entorno.
try:
    with col1: st.image("assets/logo_vincu.png", width=150)
    with col2: st.image("assets/logo_met.png", width=150)
    with col3: st.image("assets/logo.png", width=100)
except FileNotFoundError:
    with col1: st.subheader("Logo 1")
    with col2: st.subheader("Logo 2")
    with col3: st.subheader("Logo 3")


st.title("📊 Reporte de Eficiencia de Agentes Novatos")

# --- FUNCIONES DE CARGA Y PROCESAMIENTO DE DATOS ---

@st.cache_data
def cargar_y_procesar_ventas(archivo):
    """Carga, valida y procesa el DataFrame de ventas."""
    try:
        if archivo.name.endswith(".csv"):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)
    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        return None

    columnas_requeridas = {"Fecha", "Agente", "Venta ($)", "Asegurado", "Poliza", "Retenedor", "Movimiento"}
    if not columnas_requeridas.issubset(df.columns):
        st.error("❌ El archivo debe contener las columnas requeridas: " + ", ".join(columnas_requeridas))
        return None

    df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')
    df = df.dropna(subset=["Fecha"])

    if df.empty:
        return None

    df = df.assign(
        Mes=df["Fecha"].dt.month,
        Semana=df["Fecha"].dt.isocalendar().week.astype(int),
        **{"Mes Nombre": lambda x: x["Mes"].map(MESES_MAP)},
        Agente=lambda x: x["Agente"].astype(str).str.strip()
    )

    return df

@st.cache_data
def cargar_info_agentes(archivo_info):
    """Carga y limpia el DataFrame de información de agentes."""
    try:
        df_info = pd.read_excel(archivo_info)
        
        columnas_info_requeridas = {"Agente", "Fecha Ingreso", "Agencia", "Estatus", "Motivo"}
        faltantes = columnas_info_requeridas - set(df_info.columns)
        if faltantes:
            st.warning(f"⚠️ El archivo de información de agentes está incompleto. Faltan las columnas: {', '.join(faltantes)}")

        df_info["Agente"] = df_info["Agente"].astype(str).str.strip()
        # Se asegura que la columna de Fecha Ingreso sea datetime
        df_info["Fecha Ingreso"] = pd.to_datetime(df_info["Fecha Ingreso"], errors="coerce")
        
        return df_info
    except Exception as e:
        st.error(f"Error al leer el archivo de información de agentes: {e}")
        return pd.DataFrame()


def obtener_ruta_foto_local(agente):
    """Devuelve la ruta de la foto del agente o la genérica si no existe."""
    # Simulación de limpieza de nombre para la ruta de la foto
    nombre_archivo = agente.lower().replace(" ", "_").replace("ñ", "n").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u") + ".jpg"
    ruta = os.path.join("fotos_agentes", nombre_archivo)
    ruta_generica = os.path.join("fotos_agentes", "generica.jpg")
    return ruta if os.path.exists(ruta) else ruta_generica

# --- FUNCIONES DE VISUALIZACIÓN ---

def mostrar_metricas(df):
    """Muestra la métrica de ventas total."""
    total = df["Venta ($)"].sum()
    st.metric("💰 Total de Ventas", f"${total:,.2f}")

def configurar_grafica(fig, titulo):
    """Aplica el formato común a las gráficas de Plotly."""
    fig.update_layout(
        yaxis_tickformat=",",
        title_font_size=20,
        title=titulo
    )
    return fig

def mostrar_graficas(df):
    """Muestra las gráficas generales de ventas (por agente y por mes)."""
    df_agente = df.groupby("Agente", as_index=False)["Venta ($)"].sum()
    fig_agente = px.bar(df_agente, x="Agente", y="Venta ($)", color="Agente",
                        color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(configurar_grafica(fig_agente, "Ventas por Agente"))

    df_mes = df.groupby("Mes Nombre", as_index=False)["Venta ($)"].sum()
    df_mes["Mes Nombre"] = pd.Categorical(df_mes["Mes Nombre"], categories=MESES_MAP.values(), ordered=True)
    df_mes.sort_values("Mes Nombre", inplace=True)

    fig_mes = px.bar(df_mes, x="Mes Nombre", y="Venta ($)", color="Mes Nombre",
                     color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(configurar_grafica(fig_mes, "Ventas por Mes"))

def mostrar_metricas_por_agencia_mes(df_ventas, df_info):
    st.subheader("📊 Métricas por Agencia Mensual")

    # Unir ventas con agencia
    df_info_temp = df_info[["Agente", "Agencia", "Estatus"]].dropna(subset=["Agencia"])
    df_info_temp["Agente"] = df_info_temp["Agente"].astype(str).str.strip()
    df_ventas["Agente"] = df_ventas["Agente"].astype(str).str.strip()

    df_completo = pd.merge(df_ventas, df_info_temp, on="Agente", how="left")
    df_completo.dropna(subset=["Agencia"], inplace=True) # Solo considerar ventas con agencia conocida

    if df_completo.empty:
        st.info("No hay datos de ventas para agentes con información de agencia para mostrar este reporte.")
        return

    # --- MÉTRICAS DE VENTAS Y PÓLIZAS POR Agencia Y MES ---
    df_agencia_mes = df_completo.groupby(["Agencia", "Mes Nombre"], as_index=False).agg({
        "Venta ($)": "sum",
        "Poliza": "count"
    })
    df_agencia_mes["Mes Nombre"] = pd.Categorical(df_agencia_mes["Mes Nombre"], categories=MESES_MAP.values(), ordered=True)
    df_agencia_mes.sort_values(["Agencia", "Mes Nombre"], inplace=True)

    # Mostrar gráfica
    fig = px.bar(
        df_agencia_mes,
        x="Mes Nombre",
        y="Venta ($)",
        color="Agencia",
        barmode="group",
        category_orders={"Mes Nombre": list(MESES_MAP.values())},
        color_discrete_sequence=px.colors.qualitative.Set2,
        title="Ventas por Agencia Mensual"
        )

    fig.update_layout(yaxis_tickformat=",", title_font_size=20)
    st.plotly_chart(fig)

def mostrar_detalle_agente(df, agente, df_info):
    """Muestra el detalle y las gráficas individuales de un agente."""
    df_agente = df[df["Agente"] == agente].copy()
    df_agente["Fecha"] = df_agente["Fecha"].dt.strftime("%d-%m-%Y")
    total_agente = df_agente["Venta ($)"].sum()

    st.subheader(f"📌 Detalle de ventas de **{agente}**")

    col_img, col_info = st.columns([1, 2])

    with col_img:
        st.image(obtener_ruta_foto_local(agente), width=160, caption=agente)
        st.metric("Total vendido", f"${total_agente:,.2f}")

    with col_info:
        if not df_info.empty:
            fila = df_info[df_info["Agente"] == agente]
            if not fila.empty:
                datos_agente = fila.iloc[0]

                fecha_ingreso = datos_agente["Fecha Ingreso"].strftime("%d-%m-%Y") if pd.notna(datos_agente["Fecha Ingreso"]) else "No disponible"
                agencia = datos_agente.get("Agencia", "No especificada")
                estatus = datos_agente.get("Estatus", "No especificado")

                if isinstance(estatus, str) and estatus.lower() == "activo":
                    estatus_coloreado = f'<span style="color:green">🟢 **{estatus}**</span>'
                elif isinstance(estatus, str) and estatus.lower() == "baja":
                    estatus_coloreado = f'<span style="color:red">🔴 **{estatus}**</span>'
                else:
                    estatus_coloreado = f'<span style="color:gray">⚪ **{estatus}**</span>'

                st.markdown(f"🗓️ **Fecha de ingreso:** {fecha_ingreso}")
                st.markdown(f"👥 **Agencia:** {agencia}")
                st.markdown(f"📌 **Estatus:** {estatus_coloreado}", unsafe_allow_html=True)

                if isinstance(estatus, str) and estatus.lower() == "baja":
                    motivo = datos_agente.get("Motivo", "Motivo no especificado")
                    st.markdown(f"📝 **Motivo de baja:** {motivo}")
            else:
                 st.info("Información del agente no disponible en el archivo de info de agentes.")
        else:
            st.info("Archivo de información de agentes no cargado.")


    df_mes = df_agente.groupby("Mes Nombre", as_index=False)["Venta ($)"].sum()
    fig_mes = px.bar(df_mes, x="Mes Nombre", y="Venta ($)", color="Mes Nombre",
                     color_discrete_sequence=px.colors.qualitative.Plotly)
    st.plotly_chart(configurar_grafica(fig_mes, f"Ventas por Mes de {agente}"))

    with st.expander("Ver todas las ventas de este agente"):
        tabla = df_agente[["Fecha", "Poliza", "Retenedor", "Movimiento", "Asegurado", "Venta ($)"]].reset_index(drop=True)
        tabla.index += 1
        st.dataframe(tabla.style.format({"Venta ($)": "${:,.2f}"}), width="stretch")

# --- FLUJO PRINCIPAL DE LA APLICACIÓN ---

# Carga de archivos en la barra lateral (SIEMPRE VISIBLE)
with st.sidebar:
    st.header("Carga de Archivos 📂")
    archivo_ventas = st.file_uploader("Sube tu archivo de ventas (.xlsx o .csv)", type=["xlsx", "csv"])
    archivo_info = st.file_uploader("Sube el archivo con información de agentes (Opcional, .xlsx)", type=["xlsx"])

# Inicializar DataFrames
df_info = pd.DataFrame()
df = None

if archivo_info:
    df_info = cargar_info_agentes(archivo_info)

if archivo_ventas:
    df = cargar_y_procesar_ventas(archivo_ventas)

if df is None or df.empty:
    if archivo_ventas:
        st.warning("⚠️ No hay datos válidos para mostrar después de la carga y el filtrado inicial.")
    else:
        st.info("⬅️ Por favor, sube tu archivo de ventas para comenzar.")
    st.stop()

# --- NUEVO FILTRO CORREGIDO: Fecha de ingreso del agente ---
df_filtrado_por_ingreso = df.copy() 

if not df_info.empty:
    # EL FILTRO COMPLETO DEBE IR DENTRO DE st.sidebar para que aparezca allí
    with st.sidebar:
        st.subheader("Filtro por Ingreso de Agente 🧑‍💼")
        
        # Obtener las fechas de ingreso disponibles y limpiarlas
        fechas_ingreso = df_info["Fecha Ingreso"].dropna()
        
        if not fechas_ingreso.empty:
            # Convertir a objetos date de Python para que st.date_input funcione correctamente
            min_ingreso = fechas_ingreso.min().to_pydatetime().date()
            max_ingreso = fechas_ingreso.max().to_pydatetime().date()
            
            # Widget de selección de rango de fechas de ingreso
            rango_ingreso = st.date_input(
                "📅 Agentes ingresados entre:",
                [min_ingreso, max_ingreso],
                min_value=min_ingreso,
                max_value=max_ingreso
            )

            if len(rango_ingreso) == 2:
                inicio_ingreso, fin_ingreso = pd.to_datetime(rango_ingreso[0]), pd.to_datetime(rango_ingreso[1])
                
                # Filtrar agentes por fecha de ingreso
                agentes_filtrados = df_info[
                    (df_info["Fecha Ingreso"] >= inicio_ingreso) & 
                    (df_info["Fecha Ingreso"] <= fin_ingreso)
                ]["Agente"].unique()
                
                if agentes_filtrados.size > 0:
                    # Aplicar el filtro a las ventas originales (df)
                    df_filtrado_por_ingreso = df[df["Agente"].isin(agentes_filtrados)].copy()
                else:
                    # Si no hay agentes que cumplan el filtro de fecha de ingreso, vaciamos el DataFrame
                    st.warning("No se encontraron agentes con ese rango de ingreso. Mostrando datos vacíos.")
                    df_filtrado_por_ingreso = pd.DataFrame() 
        else:
            st.info("La columna 'Fecha Ingreso' no tiene datos válidos.")

# El DataFrame principal para las visualizaciones es el filtrado por ingreso
df = df_filtrado_por_ingreso

if df.empty:
    st.warning("⚠️ No hay ventas de agentes que cumplan con los filtros de ingreso seleccionados.")
    st.stop()
# --- FIN NUEVO FILTRO CORREGIDO ---


# Filtro de rango de fechas de VENTA
fecha_min, fecha_max = df["Fecha"].min(), df["Fecha"].max()
rango = st.date_input("📅 Selecciona el rango de fechas de VENTA", [fecha_min, fecha_max])

if len(rango) == 2:
    inicio, fin = pd.to_datetime(rango[0]), pd.to_datetime(rango[1])
    df = df[(df["Fecha"] >= inicio) & (df["Fecha"] <= fin)]

if df.empty:
    st.warning("⚠️ No hay ventas en el rango de fechas seleccionado.")
    st.stop()

# Mostrar resultados generales
mostrar_metricas(df)
mostrar_graficas(df)
if not df_info.empty:
    # Usamos df_info (completo) y df (ventas filtradas)
    mostrar_metricas_por_agencia_mes(df, df_info)


# Selección de agente para detalle
agentes = sorted(df["Agente"].dropna().unique())
opciones = ["-- Selecciona un agente --"] + agentes
seleccionado = st.selectbox("Selecciona un agente para ver su detalle", opciones)

if seleccionado != "-- Selecciona un agente --":
    mostrar_detalle_agente(df, seleccionado, df_info)

st.markdown("---")
st.markdown("Desarrollado por Enrique Zamora 🎯")