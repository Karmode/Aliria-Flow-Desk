import streamlit as st
from datetime import datetime
from db.client import MongoDBConnection
from bson import ObjectId


estados_con_iconos = {
    "Aprobada": "✅ Aprobada",
    "Rechazada": "❌ Rechazada",
    "Pendiente": "⏳ Pendiente",
    "Por Cobrar": "💼 Por Cobrar",
    "Pagada": "💰 Pagada",
}

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
    # FILTROS
    # ─────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    with col1:
        estado = st.selectbox(
            "Estado",
            ["Todas", "Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"],
            key="filtro_estado"
        )

    with col2:
        # Usamos el año actual para el valor máximo, pero lo inicializamos con el año actual
        anio = st.number_input(
            "Año",
            min_value=2020,
            max_value=datetime.now().year,
            value=datetime.now().year,
            step=1,
            key="filtro_anio"
        )

    with col3:
        buscar = st.text_input(
            "Buscar cliente o número",
            key="filtro_buscar"
        )


    # ─────────────────────────────────────────────
    # CONSTRUCCIÓN DE LA CONSULTA
    # ─────────────────────────────────────────────
    query = {}

    if estado != "Todas":
        query["estado"] = estado

    # Consulta por rango de fecha para el año
    query["fecha"] = {
        "$gte": datetime(anio, 1, 1),
        "$lte": datetime(anio, 12, 31, 23, 59, 59)
    }

    if buscar:
        # Aseguramos que la búsqueda por número de cotización sea por string/regex
        query["$or"] = [
            {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
            {"numero_cotizacion": {"$regex": buscar, "$options": "i"}} # Búsqueda por número
        ]

    cotizaciones = list(
        COTIZACIONES.find(query).sort("numero_cotizacion", -1)
    )

    if not cotizaciones:
        st.info("No hay cotizaciones para mostrar con los filtros seleccionados.")
        return

    st.markdown("### Resultados")
    
    # ─────────────────────────────────────────────
    # MOSTRAR RESULTADOS
    # ─────────────────────────────────────────────

    for c in cotizaciones:
        # Usamos .get() para evitar errores si falta la clave y forzamos a float para el cálculo
        mano_obra = float(c.get("mano_obra", 0))
        materiales_total = float(c.get("materiales_total", 0))
        total = mano_obra + materiales_total

        # El expander ahora solo muestra los datos clave
        with st.expander(
            f"📄 {c.get('numero_cotizacion', 'N/A')} — {c.get('nombre_cliente', 'N/A')} — {c.get('titulo', 'N/A')} —"
            f"${total:,.0f} — **{estados_con_iconos.get(c.get('estado', 'Desconocido'), c.get('estado', 'Desconocido'))}**",
            expanded=False
        ):
            # 1. BOTONES DE ACCIÓN (Ver Cotización, Crear CC/Ver CC)
            st.markdown("##### Acciones Rápidas")
            
            # Usamos 4 columnas para los botones de acción
            col_acc1, col_acc2, col_acc3, col_acc4 = st.columns([1, 1, 1, 1]) 
            
            # --- BOTÓN 1: VER COTIZACIÓN ---
            with col_acc1:
                if st.button(
                    "🔎 Ver",
                    key=f"ver_cot_{c['_id']}",
                    use_container_width=True
                ):
                    st.session_state.menu_principal = "Cotizaciones"
                    st.session_state.submenu = "Ver Cotización"
                    # Usamos 'cotizacion_id_ver' que definimos en la página 'ver_cotizacion.py'
                    st.session_state.cotizacion_id_ver = str(c["_id"]) 
                    st.rerun()

            # --- BOTÓN 2: EDITAR COTIZACIÓN ---
            with col_acc2:
                if st.button(
                    "✏️ Editar",
                    key=f"editar_cot_{c['_id']}",
                    use_container_width=True
                ):
                    st.session_state.menu_principal = "Cotizaciones"
                    st.session_state.submenu = "Editar Cotización"
                    st.session_state.cotizacion_id_editar = str(c["_id"])
                    st.rerun()

            # --- BOTÓN 3 & 4: CUENTA DE COBRO ---
            tiene_cc = c.get("tiene_cuenta_cobro", False)
            
            if not tiene_cc:
                # CREAR CC
                with col_acc3:
                    if st.button(
                        "🧾 Crear CC",
                        key=f"crear_cc_{c['_id']}",
                        use_container_width=True
                    ):
                        st.session_state.menu_principal = "Cuentas de Cobro"
                        st.session_state.submenu = "Crear Cuenta de Cobro"
                        st.session_state.cotizacion_id = str(c["_id"])
                        st.rerun()
            else:
                # VER CC
                cuenta_cobro_id = c.get("cuenta_cobro_id")
                with col_acc3:
                    if st.button(
                        "📂 Ver CC",
                        key=f"ver_cc_{c['_id']}",
                        use_container_width=True
                    ):
                        st.session_state.menu_principal = "Cuentas de Cobro"
                        st.session_state.submenu = "Ver Cuenta de Cobro"
                        # Usamos 'cuenta_cobro_id_ver' que definimos en la página 'ver_cuenta_cobro.py'
                        st.session_state.cuenta_cobro_id_ver = str(cuenta_cobro_id)
                        st.rerun()

                # EDITAR CC
                with col_acc4:
                    if st.button(
                        "✏️ Editar CC",
                        key=f"editar_cc_{c['_id']}",
                        use_container_width=True
                    ):
                        st.session_state.menu_principal = "Cuentas de Cobro"
                        st.session_state.submenu = "Editar Cuenta de Cobro"
                        st.session_state.cuenta_cobro_id_editar = str(cuenta_cobro_id)
                        st.rerun()
            
            st.markdown("---")
            
            # 2. INFORMACIÓN Y CAMBIO DE ESTADO (MÁS ABAJO)
            st.markdown("##### Actualizar Estado")

            col_info, col_estado = st.columns([1, 1])

            # ───────── Información ─────────
            with col_info:
                st.write("**Título:**", c.get('titulo', 'N/A'))
                st.write("**Fecha de Creación:**", c["fecha"].strftime("%Y-%m-%d"))
                st.write("**Total:**", f'${total:,.0f}')
                st.write("**Estado actual:**", c["estado"])

            # ───────── Cambiar estado ─────────
            with col_estado:                
                nuevo_estado = st.selectbox(
                    "Selecciona el nuevo estado:",
                    ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"],
                    format_func=lambda x: estados_con_iconos[x],
                    index=["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"].index(c["estado"]),
                    key=f"estado_{c['_id']}"
                )

                if st.button(
                    "💾 Guardar estado",
                    key=f"guardar_estado_{c['_id']}",
                    use_container_width=True
                ):
                    try:
                        COTIZACIONES.update_one(
                            {"_id": c["_id"]},
                            {"$set": {"estado": nuevo_estado, "updated_at": datetime.now()}}
                        )
                        st.success(f"Estado de la cotización {c.get('numero_cotizacion')} actualizado a **{nuevo_estado}**.")
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                    st.rerun()
