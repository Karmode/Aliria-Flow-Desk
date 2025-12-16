import streamlit as st
from datetime import datetime
from db.client import MongoDBConnection
from streamlit_quill import st_quill
from paginas.cotizaciones import listar_cotizaciones


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

    # --- Estado para materiales ---
    if "materiales_lista" not in st.session_state:
        st.session_state.materiales_lista = []

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

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            unidad = st.text_input("Unidad", key="unidad_mat")
        with col_b:
            material = st.text_input("Material", key="material_mat")
        with col_c:
            cantidad = st.number_input(
                "Cantidad", min_value=1.0, step=1.0, key="cantidad_mat"
            )
        with col_d:
            valor_unitario = st.number_input(
                "Valor unitario ($)", min_value=0, step=100, key="valor_unitario_mat"
            )

        if st.form_submit_button("➕ Agregar material"):
            if unidad and material:
                total = cantidad * valor_unitario
                st.session_state.materiales_lista.append(
                    {
                        "unidad": unidad,
                        "material": material,
                        "cantidad": cantidad,
                        "valor_unitario": valor_unitario,
                        "total": total,
                    }
                )
            else:
                st.warning("Unidad y material son obligatorios.")

        if st.session_state.materiales_lista:
            st.markdown("### Materiales agregados")
            st.table(st.session_state.materiales_lista)

        # ---------------- COSTOS ----------------
        st.markdown("---")
        st.subheader("Costos")

        col3, col4 = st.columns(2)
        with col3:
            mano_obra = st.number_input(
                "Valor Mano de Obra ($)",
                min_value=0,
                step=10000,
            )

        with col4:
            materiales_manual = st.number_input(
                "Valor Materiales ($)",
                min_value=0,
                step=10000,
                disabled=bool(st.session_state.materiales_lista),
                help="Se desactiva si usas el listado de materiales.",
            )

        # ---------------- SUBMIT FINAL ----------------
        submitted = st.form_submit_button("✓ Guardar Cotización")

        if submitted:
            if not nombre_cliente_seleccionado or not descripcion or descripcion == "<p><br></p>" or not titulo:
                st.warning("El cliente, el título y la descripción son obligatorios.")
                return

            id_cliente = clientes_dict[nombre_cliente_seleccionado]

            # Total materiales
            if st.session_state.materiales_lista:
                materiales_total = sum(
                    m["total"] for m in st.session_state.materiales_lista
                )
            else:
                materiales_total = materiales_manual

            try:
                with mongo_connection.client.start_session() as session:
                    with session.start_transaction():

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
                        numero_cotizacion = f"{anio}{secuencia:04d}"

                        quote_data = {
                            "cliente_id": id_cliente,
                            "nombre_cliente": nombre_cliente_seleccionado,
                            "fecha": datetime.combine(
                                fecha_cotizacion, datetime.min.time()
                            ),
                            "titulo": titulo,
                            "descripcion": descripcion,
                            "mano_obra": mano_obra,
                            "materiales_total": materiales_total,
                            "materiales_lista": st.session_state.materiales_lista,
                            "estado": "Pendiente",
                            "secuencia": secuencia,
                            "numero_cotizacion": numero_cotizacion,
                            "created_at": datetime.now(),
                        }
                        
                        if not st.session_state.materiales_lista:
                            quote_data.pop("materiales_lista", None)

                        COTIZACIONES.insert_one(quote_data, session=session)

                st.success(
                    f"¡Cotización {numero_cotizacion} guardada con éxito!"
                )

                # limpiar materiales
                st.session_state.materiales_lista = []
                
                st.session_state.menu_principal = "Cotizaciones"
                st.session_state.submenu = "Listar Cotizaciones"

                st.rerun()

            except Exception as e:
                st.error(f"Ocurrió un error al guardar la cotización: {e}")