import streamlit as st
from datetime import datetime
from bson import ObjectId
import os
import pandas as pd

from db.client import MongoDBConnection
from streamlit_quill import st_quill

UPLOAD_BASE = "uploads/cuentas_cobro"
MATERIALES_COLUMNS = ["Unidad", "Material", "Cantidad", "Valor Unitario"]

def show():
    st.title("✏️ Editar Cuenta de Cobro")
    st.markdown("---")

    # ───────────────── Validación inicial ─────────────────
    if "cuenta_cobro_id_editar" not in st.session_state:
        st.warning("No hay cuenta de cobro seleccionada para editar.")
        return

    cuenta_cobro_id = ObjectId(st.session_state.cuenta_cobro_id_editar)

    # ───────────────── Conexión ─────────────────
    mongo = MongoDBConnection()
    db = mongo.get_database()

    CUENTAS = db["cuentas_cobro"]
    COTIZACIONES = db["cotizaciones"]

    cuenta = CUENTAS.find_one({"_id": cuenta_cobro_id})

    if not cuenta:
        st.error("Cuenta de cobro no encontrada.")
        return

    cotizacion_id = ObjectId(cuenta.get("cotizacion_id"))
    cotizacion = COTIZACIONES.find_one({"_id": cotizacion_id})

    # ───────────────── Preparar datos iniciales ─────────────────
    lista_inicial = cuenta.get("materiales_lista", [])
    df_inicial_data = []
    for item in lista_inicial:
        df_inicial_data.append({
            "Unidad": item.get("unidad", ""),
            "Material": item.get("material", ""),
            "Cantidad": float(item.get("cantidad", 0)),
            "Valor Unitario": int(item.get("valor_unitario", 0)),
        })

    df_inicial = pd.DataFrame(df_inicial_data, columns=MATERIALES_COLUMNS) if df_inicial_data else pd.DataFrame(columns=MATERIALES_COLUMNS)

    if "materiales_df_cc_editar" not in st.session_state or st.session_state.get("last_cc_id_editar") != str(cuenta_cobro_id):
        st.session_state.materiales_df_cc_editar = df_inicial
        st.session_state.last_cc_id_editar = str(cuenta_cobro_id)

    # ───────────────── Encabezado ─────────────────
    st.subheader(f"Cotización {cuenta['numero_cotizacion']}")
    st.write("**Cliente:**", cuenta["nombre_cliente"])

    # ───────────────── Formulario ─────────────────
    with st.form("form_editar_cuenta_cobro"):
        st.subheader("Datos de la Cuenta de Cobro")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Cliente",
                value=cuenta["nombre_cliente"],
                disabled=True
            )

        with col2:
            fecha = st.date_input(
                "Fecha",
                value=cuenta.get("fecha", datetime.today())
            )

        titulo = st.text_input(
            "Título",
            value=cuenta.get("titulo", "")
        )

        st.write("Descripción del trabajo")
        descripcion = st_quill(
            value=cuenta.get("descripcion", ""),
            html=True,
            toolbar=[
                [{"header": [1, 2, 3, False]}],
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["clean"],
            ],
            key="cc_descripcion_editar"
        )

        # ─────────────── Materiales (st.data_editor) ───────────────
        st.markdown("---")
        st.subheader("Listado de Materiales (Editable)")

        edited_df = st.data_editor(
            st.session_state.materiales_df_cc_editar,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Unidad": st.column_config.TextColumn("Unidad", required=True),
                "Material": st.column_config.TextColumn("Material", required=True),
                "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.01, step=0.01, required=True),
                "Valor Unitario": st.column_config.NumberColumn("Valor Unitario ($)", min_value=0, step=100, required=True),
            },
        )

        st.session_state.materiales_df_cc_editar = edited_df

        # Cálculo del total de materiales en la interfaz
        if not edited_df.empty:
            materiales_total_editor = float(
                (edited_df["Cantidad"].fillna(0) * edited_df["Valor Unitario"].fillna(0)).sum()
            )
        else:
            materiales_total_editor = 0.0

        # ─────────────── Costos ───────────────
        st.markdown("---")
        st.subheader("Costos")

        col3, col4 = st.columns(2)

        with col3:
            mano_obra_input = st.number_input(
                "Mano de obra ($)",
                min_value=0,
                value=int(cuenta.get("mano_obra", 0)),
                step=10000
            )

        with col4:
            materiales_manual = st.number_input(
                "Materiales ($)",
                min_value=0,
                value=int(cuenta.get("materiales_total", 0)) if materiales_total_editor == 0.0 else 0,
                step=10000,
                disabled=materiales_total_editor > 0.0,
                help="Se desactiva si usas el listado de materiales."
            )

        # Anticipo (si existe en la cotización)
        anticipo_cotizacion = cotizacion.get('anticipo', 0) if cotizacion else 0
        aplicar_anticipo = False
        if anticipo_cotizacion > 0:
            st.markdown("---")
            st.subheader("⏳ Anticipo")
            st.write(f"**Anticipo en la cotización:** ${anticipo_cotizacion:,.0f}")
            aplicar_anticipo = st.checkbox(
                "Aplicar anticipo (descontar del total)",
                value=cuenta.get('anticipo', 0) > 0,
                help="Si está marcado, el anticipo se descontará del total a cobrar"
            )

        # Descuento (Opcional)
        descuento_cotizacion = cotizacion.get('descuento', 0) if cotizacion else 0
        aplicar_descuento = False
        descuento_adicional = 0.0
        
        st.markdown("---")
        st.subheader("💰 Descuento (opcional)")
        
        if descuento_cotizacion > 0:
            st.write(f"**Descuento en la cotización:** ${descuento_cotizacion:,.0f}")
            aplicar_descuento = st.checkbox(
                "Aplicar descuento de la cotización",
                value=cuenta.get('descuento_cotizacion', 0) > 0,
                help="Si está marcado, el descuento se descontará del total a cobrar"
            )
        
        col_desc1, col_desc2 = st.columns(2)
        with col_desc1:
            descuento_adicional = st.number_input(
                "Descuento adicional ($)",
                min_value=0.0,
                step=10000.0,
                value=float(cuenta.get("descuento_adicional", 0)),
                help="Descuento adicional a aplicar (ej: por pago anticipado)"
            )
        
        with col_desc2:
            st.info(f"ℹ️ Descuento total: ${(descuento_cotizacion if aplicar_descuento else 0) + descuento_adicional:,.0f}")

        guardar = st.form_submit_button("💾 Guardar Cambios", use_container_width=True)

    # ───────────────── Lógica de Guardado ─────────────────
    if guardar:
        if not titulo or not descripcion or descripcion == "<p><br></p>":
            st.warning("Título y descripción son obligatorios.")
            return

        if mano_obra_input <= 0:
            st.warning("La mano de obra debe ser mayor a cero.")
            return

        # 1. Procesamiento del DataFrame
        df_a_guardar = st.session_state.materiales_df_cc_editar.copy()
        materiales_lista_final = []

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

            df_a_guardar["valor_unitario"] = df_a_guardar["valor_unitario"].astype(int)
            df_a_guardar["cantidad"] = df_a_guardar["cantidad"].astype(float)
            df_a_guardar["total"] = (
                df_a_guardar["cantidad"] * df_a_guardar["valor_unitario"]
            ).astype(float)

            materiales_lista_final = df_a_guardar.to_dict(orient="records")

        # 2. Definir valores monetarios finales
        mano_obra_int = int(mano_obra_input)

        if materiales_lista_final:
            materiales_total_double = float(sum(m["total"] for m in materiales_lista_final))
        else:
            materiales_total_double = float(materiales_manual)

        total_sin_anticipo = float(mano_obra_int) + materiales_total_double

        # Aplicar anticipo si está marcado
        anticipo_a_aplicar = 0.0
        if aplicar_anticipo and anticipo_cotizacion > 0:
            anticipo_a_aplicar = float(anticipo_cotizacion)

        # Aplicar descuentos
        descuento_cotizacion_a_aplicar = 0.0
        if aplicar_descuento and descuento_cotizacion > 0:
            descuento_cotizacion_a_aplicar = float(descuento_cotizacion)
        
        descuento_total = descuento_cotizacion_a_aplicar + float(descuento_adicional)

        # Total final (con descuentos y anticipo descontados)
        total_general = total_sin_anticipo - anticipo_a_aplicar - descuento_total

        try:
            # 3. Preparar el documento actualizado
            # Obtener dirección de la cuenta actual o de la cotización
            direccion_cliente = cuenta.get("direccion_cliente", cotizacion.get("direccion_cliente", ""))
            
            cuenta_actualizada = {
                "fecha": datetime.combine(fecha, datetime.min.time()),
                "titulo": titulo,
                "descripcion": descripcion,

                "mano_obra": mano_obra_int,
                "materiales_total": materiales_total_double,
                "materiales_lista": materiales_lista_final,

                "anticipo": anticipo_a_aplicar,
                "anticipo_original": float(anticipo_cotizacion),
                
                "descuento_cotizacion": descuento_cotizacion_a_aplicar,
                "descuento_cotizacion_original": float(descuento_cotizacion),
                "descuento_adicional": float(descuento_adicional),
                "descuento_total": descuento_total,
                
                "total_sin_descuentos": total_sin_anticipo,
                "total": total_general,
                "direccion_cliente": direccion_cliente,
                "updated_at": datetime.now()
            }

            if not materiales_lista_final:
                cuenta_actualizada.pop("materiales_lista", None)

            # 4. Actualizar
            CUENTAS.update_one(
                {"_id": cuenta_cobro_id},
                {"$set": cuenta_actualizada}
            )

            st.success(f"Cuenta de cobro actualizada correctamente por ${total_general:,.0f}")

            st.session_state.menu_principal = "Cuentas de Cobro"
            st.session_state.submenu = "Listar Cuentas"
            st.rerun()

        except Exception as e:
            st.error(f"Error al actualizar: {e}")
