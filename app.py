import streamlit as st
from db.client import MongoDBConnection
from paginas import home
from paginas.clientes import listar_clientes, crear_clientes
from paginas.cotizaciones import crear_cotizacion, listar_cotizaciones

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
        "Listar Cotizaciones": listar_cotizaciones,
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

    # ─────────────────────────────────────────────
    # Estados seguros
    # ─────────────────────────────────────────────
    if "menu_principal" not in st.session_state:
        st.session_state.menu_principal = "Inicio"

    if "submenu" not in st.session_state:
        st.session_state.submenu = None

    # ─────────────────────────────────────────────
    # MENÚ PRINCIPAL
    # ─────────────────────────────────────────────
    menu_keys = list(pages.keys())

    # Asegurar valor válido
    if st.session_state.menu_principal not in menu_keys:
        st.session_state.menu_principal = menu_keys[0]

    choice = st.sidebar.radio(
        "Menú",
        menu_keys,
        index=menu_keys.index(st.session_state.menu_principal),
        key="menu_principal_radio"
    )

    # Si cambia menú → reset submenú
    if choice != st.session_state.menu_principal:
        st.session_state.menu_principal = choice
        st.session_state.submenu = None

    # ─────────────────────────────────────────────
    # SUBMENÚ
    # ─────────────────────────────────────────────
    if isinstance(pages[choice], dict):
        submenu_keys = list(pages[choice].keys())

        # Valor seguro
        if st.session_state.submenu not in submenu_keys:
            st.session_state.submenu = submenu_keys[0]

        subpage = st.sidebar.radio(
            f"Submenú de {choice}",
            submenu_keys,
            index=submenu_keys.index(st.session_state.submenu),
            key="submenu_radio"
        )

        st.session_state.submenu = subpage
        selected_page = pages[choice][subpage]

    else:
        selected_page = pages[choice]

    # ─────────────────────────────────────────────
    # MOSTRAR PÁGINA
    # ─────────────────────────────────────────────
    selected_page.show()

if __name__ == "__main__":
    main()