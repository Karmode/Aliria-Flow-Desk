import streamlit as st
from db.client import MongoDBConnection
from paginas import home
from paginas.clientes import listar_clientes, crear_clientes
from paginas.cotizaciones import crear_cotizacion

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Aliria Flow Desk",
    page_icon="🌊",
    layout="wide"
)

mongo_connection = MongoDBConnection()
db = mongo_connection.get_database()

pages = {
    "Inicio": home,
    "Clientes": {
        "Listar Clientes": listar_clientes,
        "Crear Clientes": crear_clientes,
    },
    "Cotizaciones": {
        "Crear Cotización": crear_cotizacion,
    },
}

titulo_color = '''
    <style>
    h1 {
        color: #ff7700; /* Naranja llamativo */
        font-family: 'Futura', sans-serif; /* Tipo de letra Futura */
    }
    </style>
'''

def main():
    st.sidebar.title("Navegación")
    st.markdown(titulo_color, unsafe_allow_html=True)
    
    # Navegación principal
    choice = st.sidebar.radio("Menú", list(pages.keys()))

    # Si la opción seleccionada es un diccionario (una categoría), mostramos un submenú
    if isinstance(pages[choice], dict):
        subpage = st.sidebar.radio(f"Submenú de {choice}", list(pages[choice].keys()))
        selected_page = pages[choice][subpage]
    else:
        selected_page = pages[choice]

    # Llamada a la página seleccionada
    selected_page.show()

if __name__ == "__main__":
    main()