import streamlit as st
from datetime import datetime
import pandas as pd

from db.client import MongoDBConnection

def show():
    """
    Función que crea y muestra todo el contenido de la página de inicio.
    """

    # --- Encabezado ---
    # Usamos st.columns para centrar la imagen del logo o título.
    col1, col2, col3 = st.columns([2, 4, 2])
    with col2:
        # CORRECCIÓN: Se cambió 'use_column_width' por 'use_container_width' para
        # alinearse con las versiones más recientes de Streamlit y evitar la alerta.
        st.image("https://placehold.co/600x200/06B6D4/FFFFFF?text=Aliria+Flow&font=raleway", use_container_width=True)

    st.title("Bienvenida a tu Centro de Mando Digital")
    st.markdown("---")

    # --- Descripción del Proyecto ---
    st.header("Una herramienta para gestionar tu negocio de forma simple y eficiente.")
    st.markdown("""
    Este proyecto nació de la necesidad de simplificar y digitalizar el flujo de trabajo administrativo de mi mamá, Aliria.
    
    El objetivo de **Aliria Flow** es reemplazar los procesos manuales con una herramienta centralizada e intuitiva que te permita enfocarte en lo que mejor sabes hacer: **tu trabajo**.
    """)
    st.markdown("---")

    # --- Dashboard / Resumen ---
    st.subheader("Resumen General")

    # Conectamos a la base de datos y calculamos métricas
    try:
        mongo = MongoDBConnection()
        db = mongo.get_database()
        COTIZACIONES = db["cotizaciones"]
        CUENTAS = db["cuentas_cobro"]
    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")
        return

    # Fechas para cálculos mensuales
    hoy = datetime.now()
    inicio_mes = datetime(hoy.year, hoy.month, 1)

    # Cotizaciones
    total_cotizaciones = COTIZACIONES.count_documents({})
    estados = ["Pendiente", "Por Cobrar", "Aprobada", "Pagada", "Rechazada"]
    cot_por_estado = {e: COTIZACIONES.count_documents({"estado": e}) for e in estados}
    cot_activas = cot_por_estado.get("Pendiente", 0) + cot_por_estado.get("Por Cobrar", 0)

    # Cuentas de cobro
    total_cuentas = CUENTAS.count_documents({})
    suma_cuentas_total = 0.0
    try:
        pipeline = [{"$group": {"_id": None, "total": {"$sum": "$total"}}}]
        agg = list(CUENTAS.aggregate(pipeline))
        suma_cuentas_total = float(agg[0]["total"]) if agg else 0.0
    except Exception:
        # Fallback: iterar manualmente (más lento pero seguro)
        suma_cuentas_total = sum((c.get("total", 0) or 0) for c in CUENTAS.find({}, {"total": 1}))

    # Ingresos del mes (sumar 'total' de cuentas con fecha en el mes actual)
    pipeline_mes = [
        {"$match": {"fecha": {"$gte": inicio_mes, "$lte": hoy}}},
        {"$group": {"_id": None, "mes_total": {"$sum": "$total"}}}
    ]
    agg_mes = list(CUENTAS.aggregate(pipeline_mes))
    ingresos_mes = float(agg_mes[0]["mes_total"]) if agg_mes else 0.0

    # Mostrar métricas
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    metric_col1.metric(label="Cotizaciones Activas", value=f"{cot_activas}")
    metric_col2.metric(label="Cuentas Registradas", value=f"{total_cuentas}")
    metric_col3.metric(label="Cuentas - Total ($)", value=f"${suma_cuentas_total:,.0f}")

    col_ing1, col_ing2 = st.columns([2, 3])
    with col_ing1:
        st.metric(label="Ingresos del Mes", value=f"${ingresos_mes:,.0f}")
    with col_ing2:
        # Mostrar desglose breve por estado
        st.markdown("**Cotizaciones por estado**")
        st.write(", ".join([f"{k}: {v}" for k, v in cot_por_estado.items()]))

    st.markdown("---")

    # Tablas recientes
    st.subheader("Últimas Cotizaciones")
    ult_cot = list(COTIZACIONES.find({}).sort("created_at", -1).limit(5))
    if ult_cot:
        df_cot = pd.DataFrame([{
            "Número": c.get("numero_cotizacion", "N/A"),
            "Cliente": c.get("nombre_cliente", "N/A"),
            "Fecha": c.get("fecha"),
            "Estado": c.get("estado", "N/A"),
            "Total": c.get("total_general", c.get("mano_obra", 0) + c.get("materiales_total", 0))
        } for c in ult_cot])
        st.dataframe(df_cot, use_container_width=True)
    else:
        st.info("No hay cotizaciones registradas aún.")

    st.subheader("Últimas Cuentas de Cobro")
    ult_cc = list(CUENTAS.find({}).sort("created_at", -1).limit(5))
    if ult_cc:
        df_cc = pd.DataFrame([{
            "Número Cotización": c.get("numero_cotizacion", "N/A"),
            "Cliente": c.get("nombre_cliente", "N/A"),
            "Fecha": c.get("fecha"),
            "Total": c.get("total", 0)
        } for c in ult_cc])
        st.dataframe(df_cc, use_container_width=True)
    else:
        st.info("No hay cuentas de cobro registradas aún.")

    st.markdown("---")
    st.info("Aquí verás los números más importantes de tu negocio. Haz clic en 'Cotizaciones' o 'Cuentas de Cobro' para detalles.")

    # --- Pie de página ---
    st.markdown("---")
    st.markdown("Creado con ❤️ para Aliria.")