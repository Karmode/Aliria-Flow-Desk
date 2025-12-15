import streamlit as st
import re
from db.client import MongoDBConnection

def show():
    """
    Función que muestra un formulario simple y directo para crear un nuevo cliente.
    """
    st.title("Registrar un Nuevo Cliente")
    st.write("Completa los datos para añadir un nuevo cliente a la lista.")
    st.markdown("---")

    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        CLIENTES = db["clientes"]
    except Exception as e:
        st.error(f"Error al conectar con MongoDB: {e}")
        return

    # Usamos un formulario para agrupar los campos y el botón de envío
    with st.form("new_client_form", clear_on_submit=True):
        
        # Usamos columnas para un diseño más limpio
        col1, col2 = st.columns(2)
        with col1:
            nombre_cliente = st.text_input("Nombre del Cliente*")
        with col2:
            telefono_cliente = st.text_input("Teléfono (Opcional)")
        
        # Campo para la dirección única
        direccion_cliente = st.text_input("Dirección*", placeholder="Ej: Carrera 5 # 10-20, Apto 301")
        
        st.markdown("---")
        submitted = st.form_submit_button("✓ Guardar Cliente")
        
        if submitted:
            # Validaciones al momento de guardar
            if nombre_cliente and direccion_cliente:
                client_data = {
                    "nombre": nombre_cliente,
                    "telefono": telefono_cliente,
                    "direccion": direccion_cliente, # Guardamos la dirección como un string
                }
                try:
                    CLIENTES.insert_one(client_data)
                    st.success(f"¡Cliente '{nombre_cliente}' guardado con éxito!")
                except Exception as e:
                    st.error(f"Ocurrió un error al guardar en la base de datos: {e}")
            else:
                st.warning("Los campos con * son obligatorios.")