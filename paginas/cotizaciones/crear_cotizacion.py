import streamlit as st
from datetime import datetime
from db.client import MongoDBConnection # Asumiendo que esta importación es correcta
from streamlit_quill import st_quill
import pandas as pd

def show():
    st.title("Generar Nueva Cotización")
    st.markdown("---")

    # --- Conexión a MongoDB ---
    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        CLIENTES = db["clientes"]
        COTIZACIONES = db["cotizaciones"]
        CONTADORES = db["contadores"]
    except Exception as e:
        st.error(f"Error al conectar con MongoDB: {e}")
        return

    # --- Cargar Clientes ---
    try:
        lista_clientes = list(
            CLIENTES.find({}, {"_id": 1, "nombre": 1}).sort("nombre", 1)
        )
        clientes_dict = {c["nombre"]: c["_id"] for c in lista_clientes}
        if not clientes_dict:
            st.warning("No hay clientes registrados.")
            return
    except Exception as e:
        st.error(f"No se pudieron cargar los clientes: {e}")
        return
    
    # MODIFICACIÓN 1: Eliminar la columna "Total" del DataFrame inicial
    if "materiales_df" not in st.session_state:
        st.session_state.materiales_df = pd.DataFrame(
            columns=["Unidad", "Material", "Cantidad", "Valor Unitario"] # "Total" eliminado
        )

    # --- Formulario ---
    with st.form("new_quote_form", clear_on_submit=True):
        st.subheader("Datos de la Cotización")

        col1, col2 = st.columns(2)
        with col1:
            nombre_cliente_seleccionado = st.selectbox(
                "Seleccionar Cliente*", options=clientes_dict.keys()
            )
        with col2:
            fecha_cotizacion = st.date_input(
                "Fecha de la Cotización", value=datetime.today()
            )
            
        titulo = st.text_input("Título de la Cotización*")

        st.write("Descripción del Trabajo*")
        descripcion = st_quill(
            placeholder="Detalla aquí los trabajos a realizar...",
            html=True,
            toolbar=[
                [{"header": [1, 2, 3, False]}],
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["clean"],
            ],
        )

# ---------------- MATERIALES ----------------
        st.markdown("---")
        st.subheader("Listado de Materiales (opcional)")

        edited_df = st.data_editor(
            st.session_state.materiales_df,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Unidad": st.column_config.TextColumn(
                    "Unidad", required=True
                ),
                "Material": st.column_config.TextColumn(
                    "Material", required=True
                ),
                "Cantidad": st.column_config.NumberColumn(
                    "Cantidad", min_value=1, step=1, required=True
                ),
                "Valor Unitario": st.column_config.NumberColumn(
                    "Valor Unitario ($)", min_value=0, step=100, required=True
                ),
            },
        )

        st.session_state.materiales_df = edited_df

        # ---------------- COSTOS ----------------
        st.markdown("---")
        st.subheader("Costos")
        
        # CÁLCULO DE TOTAL DE MATERIALES EN LA INTERFAZ (CORREGIDO)
        if not edited_df.empty:
            # Aseguramos que el resultado sea un float nativo de Python
            materiales_total_editor = float(
                (edited_df["Cantidad"].fillna(0) * edited_df["Valor Unitario"].fillna(0)).sum()
            )
        else:
            materiales_total_editor = 0.0 # Usamos float para consistencia

        col3, col4 = st.columns(2)
        with col3:
            mano_obra = st.number_input(
                "Valor Mano de Obra ($)",
                min_value=0.0, # Usamos float
                step=10000.0,
            )

        with col4:
            # CORRECCIÓN DEL ERROR DE TIPO EN value
            materiales_manual = st.number_input(
                "Valor Materiales ($)",
                min_value=0.0,
                step=10000.0,
                disabled=materiales_total_editor > 0.0,
                value=materiales_total_editor, # Pasamos el valor directamente
                help="Se desactiva si usas el listado de materiales.",
            )

        # Anticipo (Opcional)
        col5, col6 = st.columns(2)
        with col5:
            anticipo = st.number_input(
                "Anticipo ($) - OPCIONAL",
                min_value=0.0,
                step=10000.0,
                help="Monto del anticipo para esta cotización (opcional)",
            )

        with col6:
            st.info(f"ℹ️ Anticipo ingresado: ${anticipo:,.0f}")

        # Descuento (Opcional)
        col7, col8 = st.columns(2)
        with col7:
            descuento = st.number_input(
                "Descuento ($) - OPCIONAL",
                min_value=0.0,
                step=10000.0,
                help="Monto de descuento a aplicar (opcional)",
            )

        with col8:
            st.info(f"ℹ️ Descuento ingresado: ${descuento:,.0f}")

        # ---------------- SUBMIT FINAL ----------------
        submitted = st.form_submit_button("✓ Guardar Cotización") # Aquí está el botón

        if submitted:
            if not nombre_cliente_seleccionado or not descripcion or descripcion == "<p><br></p>" or not titulo:
                st.warning("El cliente, el título y la descripción son obligatorios.")
                return
            
            # Se permite mano_obra > 0
            if mano_obra <= 0:
                st.warning("El valor de mano de obra debe ser mayor a cero.")
                return
            
            id_cliente = clientes_dict[nombre_cliente_seleccionado]

            # ---------------- INICIO DE PROCESAMIENTO DE MATERIALES ----------------

            df_a_guardar = st.session_state.materiales_df.copy()
            
            materiales_lista = []
            
            if not df_a_guardar.empty:
                
                # 1. FILTRAR FILAS INVÁLIDAS Y VACÍAS (Las que no tienen datos esenciales)
                df_a_guardar = df_a_guardar.dropna(
                    subset=["Material", "Cantidad", "Valor Unitario"],
                    how="any"
                ).reset_index(drop=True)
                
                # Asegurar que los valores numéricos sean válidos para el cálculo
                df_a_guardar = df_a_guardar[
                    (df_a_guardar["Cantidad"] > 0)
                ].reset_index(drop=True)

            # Si después de filtrar, el DataFrame tiene datos válidos:
            if not df_a_guardar.empty:
                
                # 2. RENOMBRAR COLUMNAS
                df_a_guardar.rename(
                    columns={
                        "Unidad": "unidad",
                        "Material": "material",
                        "Cantidad": "cantidad",
                        "Valor Unitario": "valor_unitario",
                    },
                    inplace=True,
                )
                
                # 3. FORZAR TIPOS DE DATOS PARA CADA CAMPO (Según tu JSON Schema)
                # 'valor_unitario' debe ser INT
                df_a_guardar["valor_unitario"] = df_a_guardar["valor_unitario"].astype(float)
                # 'cantidad' debe ser DOUBLE/FLOAT
                df_a_guardar["cantidad"] = df_a_guardar["cantidad"].astype(float)

                # 4. Calcular la columna "total" (debe ser DOUBLE/FLOAT)
                df_a_guardar["total"] = (
                    df_a_guardar["cantidad"] *
                    df_a_guardar["valor_unitario"]
                ).astype(float)
                
                # 5. Convertir a lista de diccionarios
                materiales_lista = df_a_guardar.to_dict(orient="records")

            # Cálculo final del total de materiales
            materiales_total_calculado = (
                sum(m["total"] for m in materiales_lista)
                if materiales_lista
                else materiales_manual
            )
            
            # SOLUCIÓN AL PROBLEMA: Aseguramos que materiales_total sea float (double)
            materiales_total_double = float(materiales_total_calculado) 
            
            # Aseguramos que mano_obra sea un entero
            mano_obra_entero = int(mano_obra)
            
            # Subtotal antes de descuentos
            subtotal = mano_obra_entero + materiales_total_double
            
            # Descuento
            descuento_float = float(descuento) if descuento > 0 else 0.0
            
            # Cálculo del total general (subtotal - descuento)
            total_general = subtotal - descuento_float

            try:
                with mongo_connection.client.start_session() as session:
                    with session.start_transaction():

                        # Obtener datos del cliente incluyendo dirección
                        cliente_doc = CLIENTES.find_one({"_id": id_cliente}, session=session)
                        direccion_cliente = cliente_doc.get("direccion", "") if cliente_doc else ""

                        contador = CONTADORES.find_one_and_update(
                            {"nombre": "cotizaciones", "año": fecha_cotizacion.year},
                            {
                                "$inc": {"secuencia": 1},
                                "$setOnInsert": {
                                    "nombre": "cotizaciones",
                                    "año": fecha_cotizacion.year,
                                },
                            },
                            upsert=True,
                            return_document=True,
                            session=session,
                        )

                        secuencia = contador["secuencia"]
                        anio = str(fecha_cotizacion.year)[-2:]
                        numero_cotizacion = f"{anio}{secuencia:03d}"

                        quote_data = {
                            "cliente_id": id_cliente,
                            "nombre_cliente": nombre_cliente_seleccionado,
                            "direccion_cliente": direccion_cliente,
                            "fecha": datetime.combine(
                                fecha_cotizacion, datetime.min.time()
                            ),
                            "titulo": titulo,
                            "descripcion": descripcion,
                            "mano_obra": float(mano_obra_entero),
                            "materiales_lista": materiales_lista,
                            "materiales_total": materiales_total_double, # Usamos el valor DOUBLE
                            "subtotal": subtotal,
                            "descuento": descuento_float,
                            "total_general": total_general,
                            "anticipo": float(anticipo) if anticipo > 0 else 0.0,
                            "estado": "Pendiente",
                            "secuencia": secuencia,
                            "numero_cotizacion": numero_cotizacion,
                            "created_at": datetime.now(),
                        }
                        
                        if not materiales_lista:
                            quote_data.pop("materiales_lista", None)

                        COTIZACIONES.insert_one(quote_data, session=session)

                st.success(
                    f"¡Cotización {numero_cotizacion} guardada con éxito! Total General: ${total_general:,.0f}"
                )

                # limpiar materiales (tabla tipo Excel)
                st.session_state.materiales_df = pd.DataFrame(
                    columns=["Unidad", "Material", "Cantidad", "Valor Unitario"]
                )

                st.session_state.menu_principal = "Cotizaciones"
                st.session_state.submenu = "Listar Cotizaciones"

                st.rerun()
                
            except Exception as e:
                st.error(f"Ocurrió un error al guardar la cotización: {e}")