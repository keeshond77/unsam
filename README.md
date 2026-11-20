# Dashboard de seguimiento de bajas

Aplicación Streamlit conectada a la publicación CSV de Google Sheets.

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Publicar en Streamlit Community Cloud

Subir `app.py` y `requirements.txt` a un repositorio GitHub y desplegar `app.py`.

## Consideraciones

- La publicación CSV debe corresponder a la pestaña `ACTUAL`.
- La app excluye registros anteriores al 01/08/2026 para no mezclar la hoja histórica `2026` (febrero-julio) con la hoja vigente `ACTUAL` (agosto en adelante).
- Tipos: T = Temporal, E = Egreso, O = Oficio.
- Los nombres y DNI no se muestran ni se exportan.
- La caché se actualiza cada 5 minutos.
