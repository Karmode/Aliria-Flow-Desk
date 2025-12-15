import streamlit as st
from datetime import datetime
# Asumo que tu conexión a Mongo está en un archivo en la raíz del proyecto
from db.client import MongoDBConnection
from bson.objectid import ObjectId # Para referenciar al cliente
from streamlit_quill import st_quill

def show():
    """
    Función que muestra el formulario para crear una nueva cotización con un editor de texto enriquecido.
    """
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

    # --- Cargar Clientes para el Selector ---
    try:
        lista_clientes = list(CLIENTES.find({}, {"_id": 1, "nombre": 1}).sort("nombre", 1))
        clientes_dict = {cliente["nombre"]: cliente["_id"] for cliente in lista_clientes}
        if not clientes_dict:
            st.warning("No hay clientes registrados. Por favor, crea un cliente antes de generar una cotización.")
            return
    except Exception as e:
        st.error(f"No se pudieron cargar los clientes: {e}")
        return

    # --- Formulario de Cotización ---
    with st.form("new_quote_form", clear_on_submit=True):
        st.subheader("Datos de la Cotización")

        col1, col2 = st.columns(2)
        with col1:
            nombre_cliente_seleccionado = st.selectbox("Seleccionar Cliente*", options=clientes_dict.keys())
        with col2:
            fecha_cotizacion = st.date_input("Fecha de la Cotización", value=datetime.today())

        st.write("Descripción del Trabajo*")
        descripcion = st_quill(
            placeholder="Detalla aquí los trabajos a realizar, materiales a usar, condiciones, etc.",
            html=True,
            toolbar=[
                [{ 'header': [1, 2, 3, False] }],
                ['bold', 'italic', 'underline'],
                [{ 'list': 'ordered'}, { 'list': 'bullet' }],
                ['clean']
            ]
        )
        
        st.markdown("---")
        # CORRECCIÓN: La sección de costos ahora está al final, dentro del formulario.
        st.subheader("Costos")
        col3, col4 = st.columns(2)
        with col3:
            mano_obra = st.number_input(
                "Valor Mano de Obra ($)",
                min_value=0,
                step=10000,
                help="Ingresa el valor numérico sin puntos ni comas."
            )
        with col4:
            materiales = st.number_input(
                "Valor Materiales ($)",
                min_value=0,
                step=10000,
                help="Ingresa el valor numérico sin puntos ni comas."
            )

        st.markdown("---")
        submitted = st.form_submit_button("✓ Guardar Cotización")

        if submitted:
            if nombre_cliente_seleccionado and descripcion and descripcion != "<p><br></p>":
                id_cliente = clientes_dict[nombre_cliente_seleccionado]

                try:
                    # 🔐 iniciar sesión usando TU conexión
                    with mongo_connection.client.start_session() as session:
                        # 🔁 iniciar transacción
                        with session.start_transaction():

                            contador = CONTADORES.find_one_and_update(
                                {"nombre": "cotizaciones", "año": fecha_cotizacion.year},
                                {
                                    "$inc": {"secuencia": 1},
                                    "$setOnInsert": {
                                        "nombre": "cotizaciones",
                                        "año": fecha_cotizacion.year
                                    }
                                },
                                upsert=True,
                                return_document=True,
                                session=session
                            )

                            secuencia = contador["secuencia"]

                            anio = str(fecha_cotizacion.year)[-2:]
                            secuencia_str = f"{secuencia:04d}"
                            numero_cotizacion = f"{anio}{secuencia_str}"

                            quote_data = {
                                "cliente_id": id_cliente,
                                "nombre_cliente": nombre_cliente_seleccionado,
                                "fecha": datetime.combine(fecha_cotizacion, datetime.min.time()),
                                "descripcion": descripcion,
                                "mano_obra": mano_obra,
                                "materiales": materiales,
                                "estado": "Pendiente",
                                "secuencia": secuencia,
                                "numero_cotizacion": numero_cotizacion,
                                "created_at": datetime.now(),
                            }

                            COTIZACIONES.insert_one(
                                quote_data,
                                session=session
                            )

                    st.success(
                        f"¡Cotización {numero_cotizacion} guardada con éxito!"
                    )

                except Exception as e:
                    # ❌ rollback automático
                    st.error(f"Ocurrió un error al guardar la cotización: {e}")

            else:
                st.warning("El cliente y la descripción son campos obligatorios.")