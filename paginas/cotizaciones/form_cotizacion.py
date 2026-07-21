from datetime import datetime

import streamlit as st
from streamlit_quill import st_quill

from utils.materiales import df_desde_lista, procesar_editor
from utils.calculos import total_cotizacion
from paginas.cotizaciones._ui import QUILL_TOOLBAR

_COLCONFIG = {
    "Unidad": st.column_config.TextColumn("Unidad"),
    "Material": st.column_config.TextColumn("Material"),
    "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
    "Valor Unitario": st.column_config.NumberColumn(
        "Valor Unitario ($)", min_value=0, step=100
    ),
}


def render_form(prefix, clientes_dict, cot=None):
    """Campos de una cotización. Fuera de st.form para recalcular en vivo."""
    nombres = list(clientes_dict.keys())

    col1, col2 = st.columns(2)
    with col1:
        if cot:
            actual = cot.get("nombre_cliente")
            idx = nombres.index(actual) if actual in nombres else 0
            cliente = st.selectbox("Cliente*", nombres, index=idx, key=f"{prefix}_cliente")
        else:
            cliente = st.selectbox("Cliente*", nombres, key=f"{prefix}_cliente")
    with col2:
        fecha = st.date_input(
            "Fecha",
            value=cot.get("fecha", datetime.today()) if cot else datetime.today(),
            key=f"{prefix}_fecha",
        )

    titulo = st.text_input(
        "Título*", value=cot.get("titulo", "") if cot else "", key=f"{prefix}_titulo"
    )

    st.write("Descripción del trabajo*")
    descripcion = st_quill(
        value=cot.get("descripcion", "") if cot else "",
        html=True,
        toolbar=QUILL_TOOLBAR,
        key=f"{prefix}_desc",
    )

    st.markdown("**Materiales (opcional)**")
    df_init = df_desde_lista(cot.get("materiales_lista", []) if cot else [])
    edited = st.data_editor(
        df_init,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{prefix}_mat",
        column_config=_COLCONFIG,
    )
    materiales_lista, mat_total_editor = procesar_editor(edited)

    col3, col4 = st.columns(2)
    with col3:
        mano_obra = st.number_input(
            "Mano de obra ($)",
            min_value=0.0,
            step=10000.0,
            value=float(cot.get("mano_obra", 0)) if cot else 0.0,
            key=f"{prefix}_mo",
        )
    with col4:
        base_mat = float(cot.get("materiales_total", 0)) if cot else 0.0
        matman_key = f"{prefix}_matman"
        # Sembramos el valor vía session_state (sin `value=`) para que el campo
        # muestre el total del editor cuando hay materiales, sin advertencias de
        # Streamlit por combinar value= con una key ya existente.
        if matman_key not in st.session_state:
            st.session_state[matman_key] = base_mat
        if mat_total_editor > 0:
            st.session_state[matman_key] = float(mat_total_editor)
        materiales_manual = st.number_input(
            "Materiales ($)",
            min_value=0.0,
            step=10000.0,
            disabled=mat_total_editor > 0,
            key=matman_key,
            help="Se desactiva si usas el listado de materiales.",
        )

    col5, col6 = st.columns(2)
    with col5:
        anticipo = st.number_input(
            "Anticipo ($) - opcional",
            min_value=0.0,
            step=10000.0,
            value=float(cot.get("anticipo", 0)) if cot else 0.0,
            key=f"{prefix}_ant",
        )
    with col6:
        descuento = st.number_input(
            "Descuento ($) - opcional",
            min_value=0.0,
            step=10000.0,
            value=float(cot.get("descuento", 0)) if cot else 0.0,
            key=f"{prefix}_descval",
        )

    materiales_total = mat_total_editor if mat_total_editor > 0 else float(materiales_manual)
    tot = total_cotizacion(mano_obra, materiales_total, descuento)

    m1, m2, m3 = st.columns(3)
    m1.metric("Subtotal", f"${tot['subtotal']:,.0f}")
    m2.metric("Descuento", f"-${tot['descuento']:,.0f}")
    m3.metric("Total", f"${tot['total_general']:,.0f}")

    return {
        "cliente_id": clientes_dict.get(cliente),
        "nombre_cliente": cliente,
        "fecha": datetime.combine(fecha, datetime.min.time()),
        "titulo": titulo,
        "descripcion": descripcion,
        "mano_obra": float(mano_obra),
        "materiales_total": float(materiales_total),
        "materiales_lista": materiales_lista,
        "descuento": float(descuento),
        "anticipo": float(anticipo),
    }


def validar(datos):
    if not datos.get("nombre_cliente") or not datos.get("titulo"):
        return "El cliente y el título son obligatorios."
    desc = datos.get("descripcion")
    if not desc or desc == "<p><br></p>":
        return "La descripción es obligatoria."
    if datos.get("mano_obra", 0) <= 0:
        return "La mano de obra debe ser mayor a cero."
    return None
