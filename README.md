# Dashboard de seguimiento de bajas (prototipo)

## Ejecutar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

La aplicación lee el CSV publicado de Google Sheets y refresca su caché cada cinco minutos. En la sidebar se puede cambiar el enlace CSV.

Este prototipo muestra métricas simples y agregaciones de las columnas de registro (fecha, carrera, tipo). No muestra nombres ni DNI. Los indicadores del bloque resumen de la planilla aún no se procesan.
