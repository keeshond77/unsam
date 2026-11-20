import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title='Dashboard de bajas', page_icon='📊', layout='wide')
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSgMux2i_tVLCgcP23RmJR22Y1St0IYpCKa3aZw5tyWCOT0hfJJB6tIsPIOE7BiyOS990dg8dQxlEoG/pub?output=csv'

@st.cache_data(ttl=300)
def load_data(url):
    df = pd.read_csv(url)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data(ttl=300)
def load_excel_history(file):
    sheets = pd.read_excel(file, sheet_name=None, header=0)
    return sheets

st.title('📊 Dashboard de seguimiento de bajas')
st.caption('Datos conectados a la planilla publicada · Actualización automática cada 5 minutos')

with st.sidebar:
    st.header('Configuración')
    url = st.text_input('URL CSV publicado', CSV_URL)
    if st.button('🔄 Actualizar datos ahora', use_container_width=True):
        load_data.clear()
        st.rerun()
    st.divider()
    st.caption('La aplicación utiliza únicamente el CSV publicado. No presenta nombres ni DNI en el dashboard.')

try:
    raw = load_data(url)
except Exception as e:
    st.error('No pude leer el CSV. Verificá que esté publicado y que el enlace sea el CSV directo.')
    st.exception(e)
    st.stop()

# El formato original mezcla registro individual y resumen en columnas distintas.
# Columnas esperadas en el registro: fecha, apellido, nombre, carrera, tipo, DNI.
if len(raw.columns) < 6:
    st.warning('El CSV no parece contener las columnas esperadas (fecha, apellido, nombre, carrera, tipo, DNI).')
    st.dataframe(raw.head(20), use_container_width=True)
    st.stop()

records = raw.iloc[:, :6].copy()
records.columns = ['fecha','apellido','nombre','carrera','tipo','dni']
records['fecha'] = pd.to_datetime(records['fecha'], errors='coerce')
records['carrera'] = records['carrera'].astype('string').str.strip()
records['tipo'] = records['tipo'].astype('string').str.strip().str.upper()
records = records.dropna(subset=['fecha','carrera'])
records = records[records['carrera'].str.lower().ne('nan')]
# Conservamos sólo filas de registros, descartando encabezados o filas auxiliares.
records = records[records['carrera'].str.len() <= 10]
records = records[records['tipo'].isin(['E','T'])]

if records.empty:
    st.info('No encontré registros individuales válidos en las primeras seis columnas del CSV.')
    st.stop()

with st.sidebar:
    st.subheader('Filtros')
    min_date, max_date = records['fecha'].min().date(), records['fecha'].max().date()
    dates = st.date_input('Período', value=(min_date, max_date), min_value=min_date, max_value=max_date)
    careers = sorted(records['carrera'].dropna().unique().tolist())
    selected_careers = st.multiselect('Carrera', careers, default=careers)
    types = sorted(records['tipo'].dropna().unique().tolist())
    selected_types = st.multiselect('Tipo de registro', types, default=types)

if isinstance(dates, tuple) and len(dates) == 2:
    filtered = records[records['fecha'].dt.date.between(dates[0], dates[1])]
else:
    filtered = records.copy()
filtered = filtered[filtered['carrera'].isin(selected_careers) & filtered['tipo'].isin(selected_types)]

# Vista principal: datos agregados, sin datos identificatorios.
col1, col2, col3, col4 = st.columns(4)
col1.metric('Registros en el período', f'{len(filtered):,}'.replace(',', '.'))
col2.metric('Carreras', filtered['carrera'].nunique())
col3.metric('Meses registrados', filtered['fecha'].dt.to_period('M').nunique())
col4.metric('Fecha más reciente', filtered['fecha'].max().strftime('%d/%m/%Y') if not filtered.empty else '—')

st.divider()
left, right = st.columns(2)
with left:
    st.subheader('Registros por carrera')
    career_counts = filtered.groupby('carrera').size().reset_index(name='Registros').sort_values('Registros', ascending=False)
    if not career_counts.empty:
        st.plotly_chart(px.bar(career_counts, x='carrera', y='Registros', text='Registros', labels={'carrera':'Carrera'}, color='carrera'), use_container_width=True)
with right:
    st.subheader('Evolución mensual')
    monthly = filtered.assign(mes=filtered['fecha'].dt.to_period('M').dt.to_timestamp()).groupby('mes').size().reset_index(name='Registros')
    if not monthly.empty:
        st.plotly_chart(px.line(monthly, x='mes', y='Registros', markers=True, labels={'mes':'Mes','Registros':'Cantidad'}), use_container_width=True)

st.subheader('Distribución por tipo de registro')
by_type = filtered.groupby('tipo').size().reset_index(name='Cantidad')
if not by_type.empty:
    st.plotly_chart(px.pie(by_type, names='tipo', values='Cantidad', hole=.45), use_container_width=True)

st.subheader('Detalle agregado por carrera y tipo')
summary = filtered.groupby(['carrera','tipo']).size().reset_index(name='Cantidad').pivot(index='carrera', columns='tipo', values='Cantidad').fillna(0).reset_index()
st.dataframe(summary, use_container_width=True, hide_index=True)

st.caption('Este prototipo cuenta registros que aparecen en la sección individual de la planilla. Los indicadores oficiales de bajas, porcentajes y montos del resumen lateral de la planilla aún no se integran en esta versión.')
