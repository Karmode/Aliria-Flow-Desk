import streamlit as st
from datetime import datetime
from db.client import MongoDBConnection
from bson import ObjectId

def show():
    st.title("Listado de Cotizaciones")
    st.markdown("---")

    # --- Conexión ---
    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        COTIZACIONES = db["cotizaciones"]
    except Exception as e:
        st.error(f"Error al conectar con MongoDB: {e}")
        return

    # ─────────────────────────────────────────────
    # Filtros
    # ─────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        estado = st.selectbox(
            "Estado",
            ["Todas", "Pendiente", "Aprobada", "Rechazada"],
            key="filtro_estado"
        )

    with col2:
        anio = st.number_input(
            "Año",
            min_value=2020,
            max_value=datetime.now().year,
            value=datetime.now().year,
            key="filtro_anio"
        )

    with col3:
        buscar = st.text_input(
            "Buscar cliente o número",
            key="filtro_buscar"
        )

    # ─────────────────────────────────────────────
    # Query
    # ─────────────────────────────────────────────
    query = {}

    if estado != "Todas":
        query["estado"] = estado

    query["fecha"] = {
        "$gte": datetime(anio, 1, 1),
        "$lte": datetime(anio, 12, 31, 23, 59, 59)
    }

    if buscar:
        query["$or"] = [
            {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
            {"numero_cotizacion": {"$regex": buscar}}
        ]

    cotizaciones = list(
        COTIZACIONES.find(query).sort("fecha", -1)
    )

    if not cotizaciones:
        st.info("No hay cotizaciones para mostrar.")
        return

    st.markdown("### Resultados")

    # ─────────────────────────────────────────────
    # Listado interactivo
    # ─────────────────────────────────────────────
    for c in cotizaciones:
        total = c.get("mano_obra", 0) + c.get("materiales_total", 0)

        with st.expander(
            f"📄 {c['numero_cotizacion']} — {c['nombre_cliente']} — {c.get('titulo', '')} — ${total:,.0f} — {c['estado']}",
            expanded=False
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.write("**Fecha:**", c["fecha"].strftime("%Y-%m-%d"))
                st.write("**Estado actual:**", c["estado"])

            with col2:
                nuevo_estado = st.selectbox(
                    "Cambiar estado",
                    ["Pendiente", "Aprobada", "Rechazada"],
                    index=["Pendiente", "Aprobada", "Rechazada"].index(c["estado"]),
                    key=f"estado_{c['_id']}"
                )

            # ───────── Guardar estado ─────────
            if st.button(
                "💾 Guardar cambios",
                key=f"guardar_{c['_id']}"
            ):
                try:
                    COTIZACIONES.update_one(
                        {"_id": ObjectId(c["_id"])},
                        {"$set": {"estado": nuevo_estado}}
                    )
                    st.success("Estado actualizado correctamente")
                    st.rerun()

                except Exception as e:
                    st.error(f"Error al actualizar estado: {e}")
