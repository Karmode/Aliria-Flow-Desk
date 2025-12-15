import streamlit as st

def show():
    """
    Función que crea y muestra todo el contenido de la página de inicio.
    """

    # --- Encabezado ---
    # Usamos st.columns para centrar la imagen del logo o título.
    col1, col2, col3 = st.columns([2, 4, 2])
    with col2:
        # CORRECCIÓN: Se cambió 'use_column_width' por 'use_container_width' para
        # alinearse con las versiones más recientes de Streamlit y evitar la alerta.
        st.image("https://placehold.co/600x200/06B6D4/FFFFFF?text=Aliria+Flow&font=raleway", use_container_width=True)

    st.title("Bienvenida a tu Centro de Mando Digital")
    st.markdown("---")

    # --- Descripción del Proyecto ---
    st.header("Una herramienta para gestionar tu negocio de forma simple y eficiente.")
    st.markdown("""
    Este proyecto nació de la necesidad de simplificar y digitalizar el flujo de trabajo administrativo de mi mamá, Aliria.
    
    El objetivo de **Aliria Flow** es reemplazar los procesos manuales con una herramienta centralizada e intuitiva que te permita enfocarte en lo que mejor sabes hacer: **tu trabajo**.
    """)
    st.markdown("---")

    # --- Dashboard / Resumen ---
    # Un buen dashboard da una vista rápida del estado del negocio.
    st.subheader("Resumen General")
    
    # Creamos columnas para mostrar métricas clave. Por ahora, son valores estáticos.
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric(label="Cotizaciones Activas", value="0")
        
    with metric_col2:
        st.metric(label="Cuentas por Cobrar", value="$0")
        
    with metric_col3:
        st.metric(label="Ingresos del Mes", value="$0")

    # Un mensaje de bienvenida o guía para el usuario.
    st.info("Aquí verás los números más importantes de tu negocio. ¡Todo está listo para empezar a registrar tu primera cotización!")

    # --- Pie de página ---
    st.markdown("---")
    st.markdown("Creado con ❤️ para Aliria.")