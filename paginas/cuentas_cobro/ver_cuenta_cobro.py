import streamlit as st
from bson import ObjectId
import pandas as pd
from datetime import datetime
import os
import base64

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

    # ───────────────── Obtener dirección del cliente ─────────────────
    CLIENTES = db["clientes"]
    cliente_id = cuenta.get("cliente_id")
    cliente = CLIENTES.find_one({"_id": cliente_id}) if cliente_id else None
    direccion_cliente = cliente.get("direccion", "") if cliente else ""
    
    # Agregar dirección al documento para el PDF
    cuenta["direccion_cliente"] = direccion_cliente

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
    
    # Previsualización del PDF
    st.subheader("📄 Previsualización")
    pdf_base64 = base64.b64encode(pdf_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="700" style="border:1px solid #ddd;"></iframe>',
        unsafe_allow_html=True
    )

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
    
    # Desglose de descuentos y anticipo
    st.markdown("---")
    total_sin_descuentos = cuenta.get('total_sin_descuentos', 0)
    anticipo_aplicado = cuenta.get('anticipo', 0)
    descuento_total = cuenta.get('descuento_total', 0)
    
    st.write(f"**Subtotal:** ${total_sin_descuentos:,.0f}")
    
    # Anticipo
    anticipo_original = cuenta.get('anticipo_original', 0)
    if anticipo_original > 0:
        if anticipo_aplicado > 0:
            st.write(f"**Anticipo:** -${anticipo_aplicado:,.0f}")
        else:
            st.write(f"**Anticipo:** (no aplicado)")
    
    # Descuentos
    descuento_cotizacion = cuenta.get('descuento_cotizacion', 0)
    descuento_adicional = cuenta.get('descuento_adicional', 0)
    if descuento_total > 0:
        if descuento_cotizacion > 0:
            st.write(f"  • Descuento cotización: -${descuento_cotizacion:,.0f}")
        if descuento_adicional > 0:
            st.write(f"  • Descuento adicional: -${descuento_adicional:,.0f}")
        st.write(f"**Descuento total:** -${descuento_total:,.0f}")
    
    st.markdown("---")
    col_c3.metric("TOTAL A COBRAR", f"${cuenta.get('total', 0):,.0f}")
    
    # Anticipo (si fue aplicado)
    anticipo_aplicado = cuenta.get('anticipo', 0)
    anticipo_original = cuenta.get('anticipo_original', 0)
    if anticipo_original > 0:
        st.markdown("---")
        st.markdown("##### ⏳ Anticipo")
        col_ant1, col_ant2 = st.columns(2)
        with col_ant1:
            st.metric("Anticipo Original", f"${anticipo_original:,.0f}")
        with col_ant2:
            if anticipo_aplicado > 0:
                st.success(f"✓ Anticipo Aplicado: ${anticipo_aplicado:,.0f}")
            else:
                st.warning(f"✗ Anticipo No Aplicado (no pagado)")
        
        total_sin_anticipo = cuenta.get('total_sin_descuentos', cuenta.get('total', 0) + anticipo_aplicado)
        st.write(f"**Total sin anticipo:** ${total_sin_anticipo:,.0f}")
        st.write(f"**Menos anticipo:** -${anticipo_aplicado:,.0f}")
        st.write(f"**Total a cobrar:** ${cuenta.get('total', 0):,.0f}")
    
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