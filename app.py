import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title="Dashboard de bajas y recaudación", page_icon="📊", layout="wide")

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSgMux2i_tVLCgcP23RmJR22Y1St0IYpCKa3aZw5tyWCOT0hfJJB6tIsPIOE7BiyOS990dg8dQxlEoG/pub?output=csv"
FECHA_CORTE = pd.Timestamp("2026-08-01")
TIPOS = {"T": "Temporal", "E": "Egreso", "O": "Oficio"}
COLORS = {"Temporal": "#3977A8", "Egreso": "#36A47A", "Oficio": "#E39A3B"}

st.title("📊 Seguimiento de bajas y recaudación")
#st.caption("Fuente: Google Sheets · Actualización automática cada 5 minutos · Datos identificatorios excluidos")

def numero(valor):
    """Convierte números con formato argentino (1.234,56), moneda o porcentaje."""
    if pd.isna(valor):
        return float("nan")
    if isinstance(valor, (int, float)):
        return float(valor)
    s = str(valor).strip().replace("$", "").replace("%", "").replace(" ", "")
    if not s or s in {"-", "—"}:
        return float("nan")
    # Si hay coma, se interpreta como separador decimal y el punto como miles.
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return float("nan")

def dinero(v):
    return "—" if pd.isna(v) else "$ " + f"{v:,.0f}".replace(",", ".")

def entero(v):
    return "—" if pd.isna(v) else f"{v:,.0f}".replace(",", ".")

@st.cache_data(ttl=300)
def load_data(url):
    return pd.read_csv(url, dtype=str, keep_default_na=False)

with st.sidebar:
    st.header("Configuración")
    url = st.text_input("URL CSV publicado", CSV_URL)
    if st.button("🔄 Actualizar datos ahora", use_container_width=True):
        load_data.clear()
        st.rerun()

try:
    raw = load_data(url)
except Exception as e:
    st.error("No pude leer el CSV. Verificá que esté publicado y que el enlace sea directo al CSV.")
    st.exception(e)
    st.stop()

if raw.shape[1] < 14 or len(raw) < 13:
    st.error("El CSV no parece incluir toda la pestaña ACTUAL (se necesitan al menos 14 columnas y 13 filas). Publicá la pestaña ACTUAL completa.")
    st.stop()

# Registros individuales: columnas A:F.
records = raw.iloc[:, :6].copy()
records.columns = ["fecha", "apellido", "nombre", "carrera", "tipo", "dni"]
records["fecha"] = pd.to_datetime(records["fecha"], errors="coerce", dayfirst=True)
records["carrera"] = records["carrera"].astype(str).str.strip().str.upper()
records["tipo"] = records["tipo"].astype(str).str.strip().str.upper()
records = records.dropna(subset=["fecha"])
records = records[records["tipo"].isin(TIPOS) & records["carrera"].str.len().between(2, 10)].copy()
antes_corte = int((records["fecha"] < FECHA_CORTE).sum())
records = records[records["fecha"] >= FECHA_CORTE].copy()
records["tipo_nombre"] = records["tipo"].map(TIPOS)

# Bloque G2:N13 (índices desde cero: filas 1:13, columnas 6:14).
# G/H: indicadores; J:N: bajas por carrera y montos.
bloque = raw.iloc[1:13, 6:14].copy()
bloque.columns = ["indicador", "valor", "vacia", "bajas_carrera", "carrera", "caida_pct", "al_inicio", "cuatrimestral"]
indicadores = bloque.iloc[1:8][["indicador", "valor"]].copy()
indicadores["indicador"] = indicadores["indicador"].astype(str).str.strip()
indicadores["valor_num"] = indicadores["valor"].map(numero)
indicadores = indicadores[indicadores["indicador"].ne("") & indicadores["indicador"].ne("nan")]

carreras = bloque.iloc[1:9][["bajas_carrera", "carrera", "caida_pct", "al_inicio", "cuatrimestral"]].copy()
for c in ["bajas_carrera", "caida_pct", "al_inicio", "cuatrimestral"]:
    carreras[c] = carreras[c].map(numero)
carreras["carrera"] = carreras["carrera"].astype(str).str.strip()
carreras = carreras[carreras["carrera"].ne("") & carreras["carrera"].ne("nan")].copy()
carreras["caida_pct"] = carreras["caida_pct"].round(2)

# Filas 11:13 del bloque original: M contiene concepto y N el importe.
financieros = raw.iloc[10:13, 12:14].copy()
financieros.columns = ["concepto", "importe"]
financieros["concepto"] = financieros["concepto"].astype(str).str.strip()
financieros["importe"] = financieros["importe"].map(numero)
financieros = financieros[financieros["concepto"].ne("") & financieros["concepto"].ne("nan")]

# La tabla de recaudación por carrera usa importes calculados en la propia hoja.
recaudacion_carrera = carreras[["carrera", "bajas_carrera", "al_inicio", "cuatrimestral"]].copy()
recaudacion_carrera.columns = ["Carrera", "Bajas", "Al inicio", "Cuatrimestral"]
recaudacion_carrera["Cuatrimestral"] = pd.to_numeric(recaudacion_carrera["Cuatrimestral"], errors="coerce")

tab_bajas, tab_recaudacion = st.tabs(["📉 Bajas", "💰 Recaudación"])

with tab_bajas:
    st.subheader("Indicadores generales")
    cols = st.columns(4)
    for col, label in zip(cols, ["ingresantes", "reinscriptos", "TOTAL activos", "bajas egreso"]):
        row = indicadores[indicadores["indicador"].str.casefold() == label.casefold()]
        val = row.iloc[0]["valor_num"] if not row.empty else float("nan")
        col.metric(label.title(), entero(val))
    cols2 = st.columns(3)
    for col, label in zip(cols2, ["bajas", "bajas oficio", "% bajas"]):
        row = indicadores[indicadores["indicador"].str.casefold() == label.casefold()]
        val = row.iloc[0]["valor_num"] if not row.empty else float("nan")
        col.metric(label.title(), f"{val:.2f}%" if label == "% bajas" and pd.notna(val) else entero(val))

    st.divider()
    with st.sidebar:
        st.subheader("Filtros de bajas")
        if records.empty:
            st.info("No hay registros individuales desde agosto de 2026.")
            min_date = max_date = None
        else:
            min_date, max_date = records["fecha"].min().date(), records["fecha"].max().date()
            dates = st.date_input("Período", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            careers_filter = sorted(records["carrera"].unique().tolist())
            selected_careers = st.multiselect("Carrera", careers_filter, default=careers_filter)
            selected_types = st.multiselect("Tipo de baja", list(TIPOS), default=list(TIPOS),
                                            format_func=lambda x: f"{x} — {TIPOS[x]}")

    if not records.empty:
        if isinstance(dates, tuple) and len(dates) == 2:
            filtered = records[records["fecha"].dt.date.between(dates[0], dates[1])]
        else:
            filtered = records.copy()
        filtered = filtered[filtered["carrera"].isin(selected_careers) & filtered["tipo"].isin(selected_types)]
    else:
        filtered = records.copy()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Bajas registradas en el filtro", entero(len(filtered)))
    k2.metric("Carreras", entero(filtered["carrera"].nunique()))
    k3.metric("Meses con registros", entero(filtered["fecha"].dt.to_period("M").nunique()))
    k4.metric("Última fecha", filtered["fecha"].max().strftime("%d/%m/%Y") if not filtered.empty else "—")

    left, right = st.columns(2)
    with left:
        st.subheader("Bajas por carrera y tipo")
        st.caption("Barras apiladas por carrera.")
        if not filtered.empty:
            agg = filtered.groupby(["carrera", "tipo_nombre"]).size().reset_index(name="Bajas")
            order = agg.groupby("carrera")["Bajas"].sum().sort_values(ascending=False).index.tolist()
            fig = px.bar(agg, x="carrera", y="Bajas", color="tipo_nombre", barmode="stack",
                         category_orders={"carrera": order, "tipo_nombre": ["Temporal", "Egreso", "Oficio"]},
                         color_discrete_map=COLORS, text_auto=True,
                         labels={"carrera": "Carrera", "tipo_nombre": "Tipo"})
            fig.update_layout(xaxis_title="", yaxis_title="Cantidad", legend_title="Tipo de baja")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay bajas para los filtros seleccionados.")
    with right:
        st.subheader("Bajas por mes")
        st.caption("Barras mensuales apiladas por tipo.")
        if not filtered.empty:
            monthly = (filtered.assign(mes=filtered["fecha"].dt.to_period("M").dt.to_timestamp())
                       .groupby(["mes", "tipo_nombre"]).size().reset_index(name="Bajas"))
            fig = px.bar(monthly, x="mes", y="Bajas", color="tipo_nombre", barmode="stack",
                         category_orders={"tipo_nombre": ["Temporal", "Egreso", "Oficio"]},
                         color_discrete_map=COLORS, text_auto=True,
                         labels={"mes": "Mes", "tipo_nombre": "Tipo"})
            fig.update_layout(xaxis_title="", yaxis_title="Cantidad", legend_title="Tipo de baja")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay bajas para los filtros seleccionados.")

    st.subheader("Detalle por carrera (resumen de la planilla)")
    #st.caption("Estos porcentajes y cantidades provienen del bloque de gestión de Google Sheets, no del recuento del filtro.")
    view = carreras.rename(columns={"bajas_carrera": "Bajas", "carrera": "Carrera",
                                    "caida_pct": "Caída (%)", "al_inicio": "Al inicio",
                                    "cuatrimestral": "Cuatrimestral"}).copy()
    view["Caída (%)"] = view["Caída (%)"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    for c in ["Bajas", "Al inicio"]:
        view[c] = view[c].map(entero)
    view["Cuatrimestral"] = view["Cuatrimestral"].map(dinero)
    st.dataframe(view, use_container_width=True, hide_index=True)

    if antes_corte:
        st.caption(f"Control: se excluyeron {antes_corte} registros anteriores al 01/08/2026 del análisis individual. Los indicadores generales siguen mostrando los valores publicados en la planilla.")

with tab_recaudacion:
    st.subheader("Indicadores económicos")
    #st.caption("Importes tomados del bloque M11:N13 de Google Sheets; se actualizan con la misma lectura del CSV.")
    if not financieros.empty:
        metric_cols = st.columns(len(financieros))
        for col, (_, row) in zip(metric_cols, financieros.iterrows()):
            col.metric(str(row["concepto"]).title(), dinero(row["importe"]))
    else:
        st.warning("No se encontraron los tres indicadores económicos. Verificá que el CSV incluya las columnas M:N y las filas 11:13.")

    st.divider()
    st.subheader("Recaudación / importe cuatrimestral por carrera")
    #st.caption("Se conserva el valor calculado en la planilla para cada carrera.")
    rc = recaudacion_carrera.copy()
    rc = rc.rename(columns={"Cuatrimestral": "Importe cuatrimestral"})
    rc["Bajas"] = rc["Bajas"].map(entero)
    rc["Al inicio"] = rc["Al inicio"].map(entero)
    rc["Importe cuatrimestral"] = rc["Importe cuatrimestral"].map(dinero)
    st.dataframe(rc, use_container_width=True, hide_index=True)

    if not recaudacion_carrera.empty:
        chart_data = recaudacion_carrera.sort_values("cuatrimestral" if "cuatrimestral" in recaudacion_carrera.columns else "Cuatrimestral", ascending=True)
        # La tabla de carrera conserva los valores de la hoja; el gráfico usa importes numéricos.
        plot_data = carreras[["carrera", "cuatrimestral"]].dropna().sort_values("cuatrimestral")
        fig = px.bar(plot_data, x="cuatrimestral", y="carrera", orientation="h",
                     labels={"cuatrimestral": "Importe cuatrimestral", "carrera": "Carrera"},
                     text=plot_data["cuatrimestral"].map(dinero))
        fig.update_layout(xaxis_title="Importe ($)", yaxis_title="", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

st.caption("Códigos de la fuente: T = Temporal · E = Egreso · O = Oficio.")
