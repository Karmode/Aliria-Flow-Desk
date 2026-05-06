import streamlit as st
from datetime import datetime
from bson import ObjectId
import pandas as pd

from db.client import MongoDBConnection
from streamlit_quill import st_quill

def show():
    st.title("✏️ Editar Cotización")
    st.markdown("---")

    # ───────────────── Validación inicial ─────────────────
    if "cotizacion_id_editar" not in st.session_state:
        st.warning("No hay cotización seleccionada para editar.")
        return

    cotizacion_id = ObjectId(st.session_state.cotizacion_id_editar)

    # ───────────────── Conexión ─────────────────
    mongo = MongoDBConnection()
    db = mongo.get_database()

    COTIZACIONES = db["cotizaciones"]
    CLIENTES = db["clientes"]

    cotizacion = COTIZACIONES.find_one({"_id": cotizacion_id})

    if not cotizacion:
        st.error("Cotización no encontrada.")
        return

    if cotizacion.get("tiene_cuenta_cobro"):
        st.warning("⚠️ Esta cotización ya tiene cuenta de cobro. Solo puedes editar algunos campos.")
        editable = False
    else:
        editable = True

    # ───────────────── Cargar Clientes ─────────────────
    try:
        lista_clientes = list(
            CLIENTES.find({}, {"_id": 1, "nombre": 1}).sort("nombre", 1)
        )
        clientes_dict = {c["nombre"]: c["_id"] for c in lista_clientes}
    except Exception as e:
        st.error(f"Error al cargar clientes: {e}")
        return

    # ───────────────── Preparar datos iniciales ─────────────────
    lista_inicial = cotizacion.get("materiales_lista", [])
    df_inicial_data = []
    for item in lista_inicial:
        df_inicial_data.append({
            "Unidad": item.get("unidad", ""),
            "Material": item.get("material", ""),
            "Cantidad": float(item.get("cantidad", 0)),
            "Valor Unitario": int(item.get("valor_unitario", 0)),
        })

    df_inicial = pd.DataFrame(df_inicial_data, columns=["Unidad", "Material", "Cantidad", "Valor Unitario"]) if df_inicial_data else pd.DataFrame(columns=["Unidad", "Material", "Cantidad", "Valor Unitario"])

    if "materiales_df_editar" not in st.session_state or st.session_state.get("last_cot_id_editar") != str(cotizacion_id):
        st.session_state.materiales_df_editar = df_inicial
        st.session_state.last_cot_id_editar = str(cotizacion_id)

    # ───────────────── Formulario ─────────────────
    with st.form("edit_quote_form"):
        st.subheader("Datos de la Cotización")

        col1, col2 = st.columns(2)
        with col1:
            nombre_cliente_actual = cotizacion["nombre_cliente"]
            if editable:
                nombre_cliente_seleccionado = st.selectbox(
                    "Seleccionar Cliente*",
                    options=clientes_dict.keys(),
                    index=list(clientes_dict.keys()).index(nombre_cliente_actual) if nombre_cliente_actual in clientes_dict.keys() else 0
                )
            else:
                st.text_input("Cliente", value=nombre_cliente_actual, disabled=True)
                nombre_cliente_seleccionado = nombre_cliente_actual

        with col2:
            fecha_cotizacion = st.date_input(
                "Fecha de la Cotización",
                value=cotizacion.get("fecha", datetime.today()),
                disabled=not editable
            )

        titulo = st.text_input(
            "Título de la Cotización*",
            value=cotizacion.get("titulo", ""),
            disabled=not editable
        )

        st.write("Descripción del Trabajo*")
        descripcion = st_quill(
            value=cotizacion.get("descripcion", ""),
            placeholder="Detalla aquí los trabajos a realizar...",
            html=True,
            toolbar=[
                [{"header": [1, 2, 3, False]}],
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["clean"],
            ],
            readonly=not editable
        )

        # ───────────────── MATERIALES ─────────────────
        st.markdown("---")
        st.subheader("Listado de Materiales (opcional)")

        edited_df = st.data_editor(
            st.session_state.materiales_df_editar,
            num_rows="dynamic",
            use_container_width=True,
            disabled=not editable,
            column_config={
                "Unidad": st.column_config.TextColumn("Unidad", required=True),
                "Material": st.column_config.TextColumn("Material", required=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=1, step=1, required=True),
                "Valor Unitario": st.column_config.NumberColumn("Valor Unitario ($)", min_value=0, step=100, required=True),
            },
        )

        st.session_state.materiales_df_editar = edited_df

        # ───────────────── COSTOS ─────────────────
        st.markdown("---")
        st.subheader("Costos")

        if not edited_df.empty:
            materiales_total_editor = float(
                (edited_df["Cantidad"].fillna(0) * edited_df["Valor Unitario"].fillna(0)).sum()
            )
        else:
            materiales_total_editor = 0.0

        col3, col4 = st.columns(2)
        with col3:
            mano_obra = st.number_input(
                "Valor Mano de Obra ($)",
                min_value=0.0,
                step=10000.0,
                value=float(cotizacion.get("mano_obra", 0)),
            )

        with col4:
            materiales_manual = st.number_input(
                "Valor Materiales ($)",
                min_value=0.0,
                step=10000.0,
                disabled=materiales_total_editor > 0.0,
                value=materiales_total_editor if materiales_total_editor > 0 else float(cotizacion.get("materiales_total", 0)),
                help="Se desactiva si usas el listado de materiales.",
            )

        # ───────────────── ANTICIPO ─────────────────
        col5, col6 = st.columns(2)
        with col5:
            anticipo = st.number_input(
                "Anticipo ($) - OPCIONAL",
                min_value=0.0,
                step=10000.0,
                value=float(cotizacion.get("anticipo", 0)),
                help="Monto del anticipo para esta cotización (opcional)",
            )

        with col6:
            st.info(f"ℹ️ Anticipo ingresado: ${anticipo:,.0f}")

        # ───────────────── DESCUENTO ─────────────────
        col7, col8 = st.columns(2)
        with col7:
            descuento = st.number_input(
                "Descuento ($) - OPCIONAL",
                min_value=0.0,
                step=10000.0,
                value=float(cotizacion.get("descuento", 0)),
                help="Monto de descuento a aplicar (opcional)",
            )

        with col8:
            st.info(f"ℹ️ Descuento ingresado: ${descuento:,.0f}")

        # ───────────────── ESTADO ─────────────────
        st.markdown("---")
        st.subheader("Estado")

        estados = ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]
        estado_actual = cotizacion.get("estado", "Pendiente")
        nuevo_estado = st.selectbox(
            "Estado de la Cotización",
            options=estados,
            index=estados.index(estado_actual) if estado_actual in estados else 0
        )

        # ───────────────── BOTÓN ─────────────────
        submitted = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)

        if submitted:
            if not nombre_cliente_seleccionado or not descripcion or descripcion == "<p><br></p>" or not titulo:
                st.warning("El cliente, el título y la descripción son obligatorios.")
                return

            if mano_obra <= 0:
                st.warning("El valor de mano de obra debe ser mayor a cero.")
                return

            id_cliente = clientes_dict[nombre_cliente_seleccionado]

            # ───────────────── PROCESAMIENTO DE MATERIALES ─────────────────
            df_a_guardar = st.session_state.materiales_df_editar.copy()
            materiales_lista = []

            if not df_a_guardar.empty:
                df_a_guardar = df_a_guardar.dropna(
                    subset=["Material", "Cantidad", "Valor Unitario"],
                    how="any"
                ).reset_index(drop=True)

                df_a_guardar = df_a_guardar[
                    (df_a_guardar["Cantidad"] > 0)
                ].reset_index(drop=True)

            if not df_a_guardar.empty:
                df_a_guardar.rename(
                    columns={
                        "Unidad": "unidad",
                        "Material": "material",
                        "Cantidad": "cantidad",
                        "Valor Unitario": "valor_unitario",
                    },
                    inplace=True,
                )

                df_a_guardar["valor_unitario"] = df_a_guardar["valor_unitario"].astype(float)
                df_a_guardar["cantidad"] = df_a_guardar["cantidad"].astype(float)
                df_a_guardar["total"] = (
                    df_a_guardar["cantidad"] * df_a_guardar["valor_unitario"]
                ).astype(float)

                materiales_lista = df_a_guardar.to_dict(orient="records")

            # ───────────────── CÁLCULOS FINALES ─────────────────
            materiales_total_calculado = (
                sum(m["total"] for m in materiales_lista)
                if materiales_lista
                else materiales_manual
            )

            materiales_total_double = float(materiales_total_calculado)
            mano_obra_entero = int(mano_obra)
            
            # Subtotal antes de descuentos
            subtotal = mano_obra_entero + materiales_total_double
            
            # Descuento
            descuento_float = float(descuento) if descuento > 0 else 0.0
            
            # Cálculo del total general (subtotal - descuento)
            total_general = subtotal - descuento_float

            try:
                # ───────────────── OBTENER DIRECCIÓN DEL CLIENTE ─────────────────
                id_cliente = clientes_dict[nombre_cliente_seleccionado]
                cliente_doc = CLIENTES.find_one({"_id": id_cliente})
                direccion_cliente = cliente_doc.get("direccion", "") if cliente_doc else ""
                
                # ───────────────── ACTUALIZAR ─────────────────
                update_data = {
                    "cliente_id": id_cliente,
                    "nombre_cliente": nombre_cliente_seleccionado,
                    "direccion_cliente": direccion_cliente,
                    "fecha": datetime.combine(fecha_cotizacion, datetime.min.time()),
                    "titulo": titulo,
                    "descripcion": descripcion,
                    "mano_obra": float(mano_obra_entero),
                    "materiales_total": materiales_total_double,
                    "subtotal": subtotal,
                    "descuento": descuento_float,
                    "total_general": total_general,
                    "anticipo": float(anticipo) if anticipo > 0 else 0.0,
                    "estado": nuevo_estado,
                    "updated_at": datetime.now(),
                }

                if materiales_lista:
                    update_data["materiales_lista"] = materiales_lista
                else:
                    update_data["materiales_lista"] = None

                COTIZACIONES.update_one(
                    {"_id": cotizacion_id},
                    {"$set": update_data}
                )

                st.success(
                    f"¡Cotización {cotizacion['numero_cotizacion']} actualizada exitosamente! Total General: ${total_general:,.0f}"
                )

                st.session_state.menu_principal = "Cotizaciones"
                st.session_state.submenu = "Listar Cotizaciones"
                st.rerun()

            except Exception as e:
                st.error(f"Ocurrió un error al guardar: {e}")
