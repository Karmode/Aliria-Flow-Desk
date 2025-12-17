import streamlit as st
from db.client import MongoDBConnection
from bson import ObjectId
from pathlib import Path
from datetime import datetime

def show():
    st.title("Exportar Cotización / Cuenta de Cobro")
    st.markdown("---")

    # ─────────────────────────────────────────────
    # Validar cotización seleccionada
    # ─────────────────────────────────────────────
    if "cotizacion_id" not in st.session_state:
        st.warning("No hay cotización seleccionada.")
        return

    cotizacion_id = st.session_state.cotizacion_id

    # ─────────────────────────────────────────────
    # Conexión
    # ─────────────────────────────────────────────
    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        COTIZACIONES = db["cotizaciones"]
    except Exception as e:
        st.error(f"Error MongoDB: {e}")
        return

    cotizacion = COTIZACIONES.find_one({"_id": ObjectId(cotizacion_id)})

    if not cotizacion:
        st.error("Cotización no encontrada.")
        return

    # ─────────────────────────────────────────────
    # Info básica
    # ─────────────────────────────────────────────
    st.subheader(f"Cotización {cotizacion['numero_cotizacion']}")
    st.write("**Cliente:**", cotizacion["nombre_cliente"])
    st.write("**Fecha:**", cotizacion["fecha"].strftime("%Y-%m-%d"))
    st.write("**Estado:**", cotizacion["estado"])

    st.markdown("---")

    # ─────────────────────────────────────────────
    # Tipo de documento
    # ─────────────────────────────────────────────
    tipo = st.radio(
        "Tipo de documento a generar",
        ["Cotización", "Cuenta de Cobro"]
    )

    soportes = []

    # ─────────────────────────────────────────────
    # Soportes (solo cuenta de cobro)
    # ─────────────────────────────────────────────
    if tipo == "Cuenta de Cobro":
        st.subheader("Soportes de Facturas")

        soportes = st.file_uploader(
            "Sube fotos o escaneos de facturas",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True
        )

    st.markdown("---")

    # ─────────────────────────────────────────────
    # Generar PDF
    # ─────────────────────────────────────────────
    if st.button("📥 Generar PDF"):
        try:
            ruta_soportes = None

            if tipo == "Cuenta de Cobro" and soportes:
                ruta_soportes = guardar_soportes(
                    cotizacion["numero_cotizacion"],
                    soportes
                )

            pdf_path = generar_pdf(
                cotizacion,
                tipo,
                ruta_soportes
            )

            with open(pdf_path, "rb") as f:
                st.download_button(
                    "⬇️ Descargar PDF",
                    data=f,
                    file_name=Path(pdf_path).name,
                    mime="application/pdf"
                )

        except Exception as e:
            st.error(f"Error al generar PDF: {e}")
