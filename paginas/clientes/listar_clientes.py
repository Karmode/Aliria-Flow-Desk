import streamlit as st
import pandas as pd
from db.client import MongoDBConnection

def show():
    """
    Función que crea y muestra la página con la lista de clientes en una tabla.
    """
    st.title("Lista de Clientes Registrados")
    st.markdown("---")

    # --- Conexión a MongoDB ---
    try:
        mongo_connection = MongoDBConnection()
        db = mongo_connection.get_database()
        CLIENTES = db["clientes"]
    except Exception as e:
        st.error(f"Error al conectar con MongoDB: {e}")
        st.warning("Asegúrate de haber configurado el `MONGO_URL` en tus secretos o en tu archivo .env")
        return

    # --- Lógica de Listado en Tabla ---
    try:
        # CORRECCIÓN: Buscamos el campo 'direccion' en lugar de 'direcciones'
        all_clients = list(CLIENTES.find({}, {"_id": 0, "nombre": 1, "telefono": 1, "direccion": 1}).sort("nombre", 1))

        if not all_clients:
            st.info("Aún no hay clientes registrados.")
        else:
            # Convertimos los datos a un DataFrame de Pandas
            df = pd.DataFrame(all_clients)
            
            # CORRECCIÓN: Renombramos la columna 'direccion' a 'Dirección'
            df.rename(columns={
                'nombre': 'Nombre',
                'telefono': 'Teléfono',
                'direccion': 'Dirección'
            }, inplace=True)
            
            # Usamos st.dataframe para mostrar la tabla interactiva
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"No se pudo cargar la lista de clientes: {e}")