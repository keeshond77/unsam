import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

st.set_page_config(page_title='Dashboard de bajas', page_icon='📊', layout='wide')
CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vSgMux2i_tVLCgcP23RmJR22Y1St0IYpCKa3aZw5tyWCOT0hfJJB6tIsPIOE7BiyOS990dg8dQxlEoG/pub?output=csv'
# La hoja ACTUAL del Excel comienza el 05/08/2026. El CSV publicado debe apuntar a esa hoja.
FECHA_CORTE = pd.Timestamp('2026-08-01')
TIPOS = {'T': 'Temporal', 'E': 'Egreso', 'O': 'Oficio'}

@st.cache_data(ttl=300)
def load_data(url):
    return pd.read_csv(url)

st.title('📊 Dashboard de seguimiento de bajas')
st.caption('Fuente: Google Sheets · Actualización automática cada 5 minutos · Datos identificatorios excluidos')

with st.sidebar:
    st.header('Configuración')
    url = st.text_input('URL CSV publicado', CSV_URL)
    if st.button('🔄 Actualizar datos ahora', use_container_width=True):
        load_data.clear()
        st.rerun()
    st.divider()
    st.subheader('Filtros')

try:
    raw = load_data(url)
except Exception as e:
    st.error('No pude leer el CSV. Verificá que esté publicado y que el enlace sea el CSV directo.')
    st.exception(e)
    st.stop()

if len(raw.columns) < 6:
    st.error('El CSV no contiene las seis columnas esperadas: fecha, apellido, nombre, carrera, tipo y DNI.')
    st.dataframe(raw.head(20), use_container_width=True)
    st.stop()

# El CSV de la pestaña ACTUAL tiene los registros individuales en sus primeras seis columnas.
records = raw.iloc[:, :6].copy()
records.columns = ['fecha', 'apellido', 'nombre', 'carrera', 'tipo', 'dni']
records['fecha'] = pd.to_datetime(records['fecha'], errors='coerce', dayfirst=True)
records['carrera'] = records['carrera'].astype('string').str.strip().str.upper()
records['tipo'] = records['tipo'].astype('string').str.strip().str.upper()
records = records.dropna(subset=['fecha', 'carrera', 'tipo'])
records = records[records['tipo'].isin(TIPOS)]
records = records[records['carrera'].str.len().between(2, 10)]

# No mezclar la pestaña histórica 2026 (febrero-julio) con la pestaña ACTUAL (agosto en adelante).
antes_corte = len(records[records['fecha'] < FECHA_CORTE])
records = records[records['fecha'] >= FECHA_CORTE].copy()
records['tipo_nombre'] = records['tipo'].map(TIPOS)

if records.empty:
    st.error('No hay registros desde agosto de 2026 en el CSV recibido. Revisá que la publicación de Google Sheets corresponda a la pestaña ACTUAL y no a la pestaña histórica 2026.')
    if antes_corte:
        st.warning(f'El CSV contiene {antes_corte} registros anteriores al 01/08/2026; se excluyeron porque pertenecen al período histórico previo.')
    st.stop()

with st.sidebar:
    min_date, max_date = records['fecha'].min().date(), records['fecha'].max().date()
    dates = st.date_input('Período', value=(min_date, max_date), min_value=min_date, max_value=max_date)
    careers = sorted(records['carrera'].dropna().unique().tolist())
    selected_careers = st.multiselect('Carrera', careers, default=careers)
    type_codes = ['T', 'E', 'O']
    selected_types = st.multiselect('Tipo de baja', type_codes, default=type_codes, format_func=lambda x: f'{x} — {TIPOS[x]}')

if isinstance(dates, tuple) and len(dates) == 2:
    filtered = records[records['fecha'].dt.date.between(dates[0], dates[1])]
else:
    filtered = records.copy()
filtered = filtered[filtered['carrera'].isin(selected_careers) & filtered['tipo'].isin(selected_types)]

c1, c2, c3, c4 = st.columns(4)
c1.metric('Bajas en el período', f'{len(filtered):,}'.replace(',', '.'))
c2.metric('Carreras', filtered['carrera'].nunique())
c3.metric('Meses con registros', filtered['fecha'].dt.to_period('M').nunique())
c4.metric('Última fecha', filtered['fecha'].max().strftime('%d/%m/%Y') if not filtered.empty else '—')

st.divider()
left, right = st.columns(2)
with left:
    st.subheader('Bajas por carrera y tipo')
    st.caption('Barras apiladas: Temporal, Egreso y Oficio.')
    if not filtered.empty:
        career_type = (filtered.groupby(['carrera', 'tipo_nombre']).size().reset_index(name='Bajas'))
        order = (career_type.groupby('carrera')['Bajas'].sum().sort_values(ascending=False).index.tolist())
        fig = px.bar(career_type, x='carrera', y='Bajas', color='tipo_nombre',
                     category_orders={'carrera': order, 'tipo_nombre': ['Temporal', 'Egreso', 'Oficio']},
                     color_discrete_map={'Temporal': '#3977A8', 'Egreso': '#36A47A', 'Oficio': '#E39A3B'},
                     text_auto=True, labels={'carrera': 'Carrera', 'tipo_nombre': 'Tipo de baja'})
        fig.update_layout(barmode='stack', legend_title_text='Tipo de baja', xaxis_title='', yaxis_title='Cantidad de bajas')
        st.plotly_chart(fig, use_container_width=True)
with right:
    st.subheader('Bajas por mes')
    st.caption('Cantidad de registros por mes, desglosada por tipo.')
    if not filtered.empty:
        monthly = filtered.assign(mes=filtered['fecha'].dt.to_period('M').dt.to_timestamp()).groupby(['mes', 'tipo_nombre']).size().reset_index(name='Bajas')
        fig = px.bar(monthly, x='mes', y='Bajas', color='tipo_nombre',
                     category_orders={'tipo_nombre': ['Temporal', 'Egreso', 'Oficio']},
                     color_discrete_map={'Temporal': '#3977A8', 'Egreso': '#36A47A', 'Oficio': '#E39A3B'},
                     barmode='stack', text_auto=True,
                     labels={'mes': 'Mes', 'tipo_nombre': 'Tipo de baja'})
        fig.update_layout(legend_title_text='Tipo de baja', xaxis_title='', yaxis_title='Cantidad de bajas')
        st.plotly_chart(fig, use_container_width=True)

st.subheader('Distribución de tipos de baja')
if not filtered.empty:
    by_type = filtered.groupby('tipo_nombre').size().reindex(['Temporal', 'Egreso', 'Oficio'], fill_value=0).reset_index(name='Cantidad')
    fig = px.pie(by_type, names='tipo_nombre', values='Cantidad', hole=.48,
                 color='tipo_nombre', color_discrete_map={'Temporal': '#3977A8', 'Egreso': '#36A47A', 'Oficio': '#E39A3B'})
    st.plotly_chart(fig, use_container_width=True)

st.subheader('Detalle agregado por carrera y tipo')
if not filtered.empty:
    summary = filtered.groupby(['carrera', 'tipo_nombre']).size().unstack(fill_value=0).reindex(columns=['Temporal', 'Egreso', 'Oficio'], fill_value=0)
    summary['Total'] = summary.sum(axis=1)
    summary = summary.sort_values('Total', ascending=False).reset_index()
    st.dataframe(summary, use_container_width=True, hide_index=True)
    csv = summary.to_csv(index=False).encode('utf-8-sig')
    st.download_button('⬇️ Descargar resumen CSV', csv, 'resumen_bajas_por_carrera.csv', 'text/csv')

if antes_corte:
    with st.expander('Control de calidad de fechas'):
        st.info(f'Se excluyeron {antes_corte} registros anteriores al 01/08/2026. La hoja ACTUAL del Excel compartido comienza el 05/08/2026; si esperabas ver esos registros, verificá que el CSV publicado esté apuntando a ACTUAL.')

st.caption('Códigos de la fuente: T = Temporal · E = Egreso · O = Oficio. Los nombres y DNI no se muestran ni se exportan.')
