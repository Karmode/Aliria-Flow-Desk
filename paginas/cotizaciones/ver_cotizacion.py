import streamlit as st
from bson import ObjectId
import pandas as pd
from datetime import datetime

from db.client import MongoDBConnection
from utils.pdf_generator import generate_pdf 

def show():
    st.title("👁️ Ver Cotización")
    st.markdown("---")

    # ───────────────── Validación inicial ─────────────────
    if "cotizacion_id_ver" not in st.session_state:
        st.warning("No hay cotización seleccionada para ver.")
        return

    cotizacion_id = ObjectId(st.session_state.cotizacion_id_ver)

    # ───────────────── Conexión y Carga de Datos ─────────────────
    mongo = MongoDBConnection()
    db = mongo.get_database()
    COTIZACIONES = db["cotizaciones"]

    cotizacion = COTIZACIONES.find_one({"_id": cotizacion_id})

    if not cotizacion:
        st.error("Cotización no encontrada.")
        return

    # ───────────────── GENERACIÓN DE PDF ─────────────────
    pdf_bytes, filename = generate_pdf(cotizacion, doc_type="Cotización")
    
    # ───────────────── VISUALIZACIÓN DE DATOS ─────────────────
    
    # Encabezado
    st.subheader(f"Cotización N° {cotizacion.get('numero_cotizacion', 'N/A')}")
    st.write(f"**Cliente:** {cotizacion.get('nombre_cliente', 'N/A')}")
    st.write(f"**Estado:** **{cotizacion.get('estado', 'Desconocido')}**")
    
    fecha_dt = cotizacion.get('fecha')
    
    if fecha_dt and isinstance(fecha_dt, datetime):
        st.write(f"**Fecha:** {fecha_dt.strftime('%d/%m/%Y')}")
    elif fecha_dt:
        st.write(f"**Fecha:** {fecha_dt}")

    st.markdown("---")

    # Botones de Acción (PDF y Volver)
    col_pdf, col_volver = st.columns([0.4, 0.6])

    with col_pdf:
        st.download_button(
            label="⬇️ Exportar Cotización (PDF)",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True
        )

    with col_volver:
        if st.button("⬅️ Volver al Listado", use_container_width=True):
            st.session_state.menu_principal = "Cotizaciones"
            st.session_state.submenu = "Listar Cotizaciones"
            st.rerun()
            
    st.markdown("---")

    # Detalles
    st.markdown(f"### {cotizacion.get('titulo', 'Sin título')}")
    st.markdown("##### Descripción")
    # Utilizamos st.markdown para renderizar el HTML del quill
    st.markdown(cotizacion.get('descripcion', 'Sin descripción'), unsafe_allow_html=True)
    
    # Costos
    st.markdown("##### Resumen de Costos")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    col_c1.metric("Mano de Obra", f"${cotizacion.get('mano_obra', 0):,.0f}")
    col_c2.metric("Total Materiales", f"${cotizacion.get('materiales_total', 0):,.0f}")
    col_c3.metric("TOTAL GENERAL", f"${cotizacion.get('total_general', 0):,.0f}")

    # Lista de Materiales
    st.markdown("##### Desglose de Materiales")
    materiales_lista = cotizacion.get('materiales_lista', [])
    if materiales_lista:
        df = pd.DataFrame(materiales_lista)
        # Formatear el DataFrame para visualización
        df = df.rename(columns={
            "unidad": "Unidad",
            "material": "Material",
            "cantidad": "Cantidad",
            "valor_unitario": "V. Unitario",
            "total": "Total"
        })
        st.dataframe(
            df.style.format({
                "Cantidad": "{:.2f}", 
                "V. Unitario": "${:,.0f}", 
                "Total": "${:,.0f}"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Esta cotización no tiene desglose de materiales en la lista.")