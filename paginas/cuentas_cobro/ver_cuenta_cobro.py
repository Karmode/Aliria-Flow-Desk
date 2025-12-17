import streamlit as st
from bson import ObjectId
import pandas as pd
from datetime import datetime
import os

from db.client import MongoDBConnection
from utils.pdf_generator import generate_pdf 

def show():
    st.title("👁️ Ver Cuenta de Cobro")
    st.markdown("---")

    # ───────────────── Validación inicial ─────────────────
    if "cuenta_cobro_id_ver" not in st.session_state:
        st.warning("No hay cuenta de cobro seleccionada para ver.")
        return

    cuenta_cobro_id = ObjectId(st.session_state.cuenta_cobro_id_ver)

    # ───────────────── Conexión y Carga de Datos ─────────────────
    mongo = MongoDBConnection()
    db = mongo.get_database()
    CUENTAS = db["cuentas_cobro"]

    cuenta = CUENTAS.find_one({"_id": cuenta_cobro_id})

    if not cuenta:
        st.error("Cuenta de cobro no encontrada.")
        return

    # ───────────────── GENERACIÓN DE PDF ─────────────────
    pdf_bytes, filename = generate_pdf(cuenta, doc_type="Cuenta de Cobro")
    
    # ───────────────── VISUALIZACIÓN DE DATOS ─────────────────
    
    # Encabezado
    st.subheader(f"Cuenta de Cobro de la Cotización N° {cuenta.get('numero_cotizacion', 'N/A')}")
    st.write(f"**Cliente:** {cuenta.get('nombre_cliente', 'N/A')}")
    
    fecha_dt = cuenta.get('fecha')
    
    if fecha_dt and isinstance(fecha_dt, datetime):
        st.write(f"**Fecha:** {fecha_dt.strftime('%d/%m/%Y')}")
    elif fecha_dt:
        st.write(f"**Fecha:** {fecha_dt}")

    st.markdown("---")

    # Botones de Acción (PDF y Volver)
    col_pdf, col_volver = st.columns([0.4, 0.6])

    with col_pdf:
        st.download_button(
            label="⬇️ Exportar Cuenta de Cobro (PDF)",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            use_container_width=True
        )

    with col_volver:
        if st.button("⬅️ Volver al Listado", use_container_width=True):
            st.session_state.menu_principal = "Cuentas de Cobro"
            st.session_state.submenu = "Listar Cuentas"
            st.rerun()
            
    st.markdown("---")

    # Detalles
    st.markdown(f"### {cuenta.get('titulo', 'Sin título')}")
    st.markdown("##### Descripción")
    st.markdown(cuenta.get('descripcion', 'Sin descripción'), unsafe_allow_html=True)
    
    # Costos
    st.markdown("##### Resumen de Costos Final")
    col_c1, col_c2, col_c3 = st.columns(3)
    
    col_c1.metric("Mano de Obra", f"${cuenta.get('mano_obra', 0):,.0f}")
    col_c2.metric("Total Materiales", f"${cuenta.get('materiales_total', 0):,.0f}")
    col_c3.metric("TOTAL FINAL", f"${cuenta.get('total', 0):,.0f}") # Usamos 'total'
    
    # Lista de Materiales
    st.markdown("##### Desglose de Materiales")
    materiales_lista = cuenta.get('materiales_lista', [])
    if materiales_lista:
        df = pd.DataFrame(materiales_lista)
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
        st.info("Esta cuenta de cobro no tiene desglose de materiales en la lista (se usó el valor manual).")
        
    # Soportes
    st.markdown("##### Soportes Adjuntos")
    soportes = cuenta.get('soportes', [])
    if soportes:
        for i, ruta in enumerate(soportes):
            nombre_archivo = os.path.basename(ruta)
            st.success(f"✔️ Soporte {i+1}: **{nombre_archivo}**")
            # Podrías añadir un botón de descarga para el soporte aquí si fuera necesario.
    else:
        st.info("No se adjuntaron soportes a esta cuenta de cobro.")