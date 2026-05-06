import streamlit as st
from datetime import datetime
from db.client import MongoDBConnection
from bson import ObjectId
import pandas as pd

def show():
    st.title("Listado de Cuentas de Cobro")
    st.markdown("---")

    # --- Conexión ---
    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        CUENTAS = db["cuentas_cobro"]
        COTIZACIONES = db["cotizaciones"]
    except Exception as e:
        st.error(f"Error al conectar con MongoDB: {e}")
        return

    # ─────────────────────────────────────────────
    # FILTROS
    # ─────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        anio = st.number_input(
            "Año",
            min_value=2020,
            max_value=datetime.now().year,
            value=datetime.now().year,
            step=1,
            key="filtro_anio_cc"
        )

    with col2:
        buscar = st.text_input(
            "Buscar cliente o número",
            key="filtro_buscar_cc"
        )

    # ─────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA CONSULTA
    # ─────────────────────────────────────────────
    query = {
        "fecha": {
            "$gte": datetime(anio, 1, 1),
            "$lte": datetime(anio, 12, 31, 23, 59, 59)
        }
    }

    if buscar:
        query["$or"] = [
            {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
            {"numero_cotizacion": {"$regex": buscar, "$options": "i"}}
        ]

    cuentas = list(
        CUENTAS.find(query).sort("numero_cotizacion", -1)
    )

    if not cuentas:
        st.info("No hay cuentas de cobro para mostrar con los filtros seleccionados.")
        return

    st.markdown("### Resultados")

    # ─────────────────────────────────────────────
    # MOSTRAR RESULTADOS
    # ─────────────────────────────────────────────

    for cuenta in cuentas:
        total = cuenta.get("total", 0)
        anticipo = cuenta.get("anticipo", 0)

        with st.expander(
            f"🧾 {cuenta.get('numero_cotizacion', 'N/A')} — {cuenta.get('nombre_cliente', 'N/A')} — "
            f"${total:,.0f}",
            expanded=False
        ):
            st.markdown("##### Acciones Rápidas")

            col_acc1, col_acc2, col_acc3 = st.columns(3)

            # --- BOTÓN 1: VER CUENTA DE COBRO ---
            with col_acc1:
                if st.button(
                    "👁️ Ver Cuenta",
                    key=f"ver_cc_{cuenta['_id']}",
                    use_container_width=True
                ):
                    st.session_state.menu_principal = "Cuentas de Cobro"
                    st.session_state.submenu = "Ver Cuenta de Cobro"
                    st.session_state.cuenta_cobro_id_ver = str(cuenta["_id"])
                    st.rerun()

            # --- BOTÓN 2: EDITAR CUENTA DE COBRO ---
            with col_acc2:
                if st.button(
                    "✏️ Editar Cuenta",
                    key=f"editar_cc_{cuenta['_id']}",
                    use_container_width=True
                ):
                    st.session_state.menu_principal = "Cuentas de Cobro"
                    st.session_state.submenu = "Editar Cuenta de Cobro"
                    st.session_state.cuenta_cobro_id_editar = str(cuenta["_id"])
                    st.rerun()

            # --- BOTÓN 3: VER COTIZACIÓN ORIGINAL ---
            with col_acc3:
                if st.button(
                    "📋 Ver Cotización",
                    key=f"ver_cot_desde_cc_{cuenta['_id']}",
                    use_container_width=True
                ):
                    st.session_state.menu_principal = "Cotizaciones"
                    st.session_state.submenu = "Ver Cotización"
                    st.session_state.cotizacion_id_ver = str(cuenta["cotizacion_id"])
                    st.rerun()

            st.markdown("---")

            # Información de la cuenta
            st.markdown("##### Información")
            col_info1, col_info2 = st.columns(2)

            with col_info1:
                st.write("**Título:**", cuenta.get('titulo', 'N/A'))
                st.write("**Fecha:**", cuenta["fecha"].strftime("%Y-%m-%d"))
                st.write("**Mano de Obra:**", f'${cuenta.get("mano_obra", 0):,.0f}')
                st.write("**Materiales:**", f'${cuenta.get("materiales_total", 0):,.0f}')

            with col_info2:
                st.write("**Total sin Anticipo:**", f'${cuenta.get("total_sin_anticipo", cuenta.get("total", 0) + anticipo):,.0f}')
                if anticipo > 0:
                    st.success(f"✓ Anticipo: ${anticipo:,.0f}")
                st.write("**Total a Cobrar:**", f'${total:,.0f}')
