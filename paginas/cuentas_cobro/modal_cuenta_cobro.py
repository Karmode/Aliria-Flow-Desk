from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_quill import st_quill

from services.cuenta_cobro_service import CuentaCobroService
from utils.materiales import df_desde_lista, procesar_editor
from utils.calculos import total_cuenta_cobro
from utils.pdf_generator import generate_pdf
from paginas.cotizaciones._ui import QUILL_TOOLBAR, preview_pdf

_COLCONFIG = {
    "Unidad": st.column_config.TextColumn("Unidad"),
    "Material": st.column_config.TextColumn("Material"),
    "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
    "Valor Unitario": st.column_config.NumberColumn(
        "Valor Unitario ($)", min_value=0, step=100
    ),
}


@st.dialog("Cuenta de Cobro", width="large")
def abrir_modal_cuenta(cc):
    id_str = str(cc["_id"])
    svc = CuentaCobroService()
    if st.session_state.get(f"cc_edit_{id_str}"):
        _editar(cc, svc, id_str)
    else:
        _detalle(cc, id_str)


def _tabla_materiales(materiales):
    if not materiales:
        return
    dfm = pd.DataFrame(materiales).rename(columns={
        "unidad": "Unidad", "material": "Material", "cantidad": "Cantidad",
        "valor_unitario": "V. Unitario", "total": "Total",
    })
    columnas = [c for c in ["Unidad", "Material", "Cantidad", "V. Unitario", "Total"] if c in dfm.columns]
    st.dataframe(
        dfm[columnas].style.format(
            {"Cantidad": "{:.2f}", "V. Unitario": "${:,.0f}", "Total": "${:,.0f}"}
        ),
        use_container_width=True, hide_index=True,
    )


def _detalle(cc, id_str):
    total = float(cc.get("total", 0))
    st.markdown(f"### 🧾 Cuenta de Cobro {cc.get('numero_cotizacion', '')}")
    c1, c2 = st.columns(2)
    c1.metric("Total a cobrar", f"${total:,.0f}")
    fecha = cc.get("fecha")
    c2.metric("Fecha", fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else str(fecha))
    st.write("**Cliente:**", cc.get("nombre_cliente", ""))

    st.divider()
    st.markdown(f"#### {cc.get('titulo', '')}")
    st.markdown(cc.get("descripcion") or "_Sin descripción_", unsafe_allow_html=True)
    _tabla_materiales(cc.get("materiales_lista", []))
    st.write(
        f"**Mano de obra:** ${cc.get('mano_obra', 0):,.0f}   |   "
        f"**Materiales:** ${cc.get('materiales_total', 0):,.0f}"
    )
    if cc.get("anticipo", 0):
        st.write(f"**Anticipo:** -${cc.get('anticipo', 0):,.0f}")
    if cc.get("descuento_total", 0):
        st.write(f"**Descuento:** -${cc.get('descuento_total', 0):,.0f}")
    soportes = cc.get("soportes", [])
    if soportes:
        st.write(f"**Soportes adjuntos:** {len(soportes)}")

    pdf_bytes, filename = generate_pdf(dict(cc), doc_type="Cuenta de Cobro")

    st.divider()
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("✏️ Editar", key=f"cce_{id_str}", use_container_width=True):
            st.session_state[f"cc_edit_{id_str}"] = True
            st.rerun()
    with a2:
        st.download_button(
            "⬇️ Exportar PDF", data=pdf_bytes, file_name=filename,
            mime="application/pdf", key=f"ccpdf_{id_str}", use_container_width=True,
        )
    with a3:
        if st.button("📋 Ver Cotización original", key=f"ccvcot_{id_str}", use_container_width=True):
            st.session_state["menu_principal"] = "Cotizaciones"
            st.session_state["cot_buscar"] = cc.get("numero_cotizacion", "")
            st.rerun()

    st.divider()
    st.caption("📄 Previsualización del PDF")
    preview_pdf(pdf_bytes)


def _editar(cc, svc, id_str):
    st.markdown(f"### ✏️ Editar Cuenta de Cobro {cc.get('numero_cotizacion', '')}")

    titulo = st.text_input("Título", value=cc.get("titulo", ""), key=f"cced_tit_{id_str}")
    st.write("Descripción")
    descripcion = st_quill(
        value=cc.get("descripcion", ""), html=True, toolbar=QUILL_TOOLBAR,
        key=f"cced_desc_{id_str}",
    )
    fecha = st.date_input("Fecha", value=cc.get("fecha", datetime.today()), key=f"cced_fecha_{id_str}")

    df_init = df_desde_lista(cc.get("materiales_lista", []))
    edited = st.data_editor(
        df_init, num_rows="dynamic", use_container_width=True,
        key=f"cced_mat_{id_str}", column_config=_COLCONFIG,
    )
    materiales_lista, mat_total_editor = procesar_editor(edited)

    col1, col2 = st.columns(2)
    with col1:
        mano_obra = st.number_input(
            "Mano de obra ($)", min_value=0, value=int(cc.get("mano_obra", 0)),
            step=10000, key=f"cced_mo_{id_str}",
        )
    with col2:
        base_mat = int(cc.get("materiales_total", 0)) if mat_total_editor == 0 else 0
        matman_key = f"cced_matman_{id_str}"
        if matman_key not in st.session_state:
            st.session_state[matman_key] = base_mat
        if mat_total_editor > 0:
            st.session_state[matman_key] = int(mat_total_editor)
        mat_manual = st.number_input(
            "Materiales ($)", min_value=0, step=10000,
            disabled=mat_total_editor > 0, key=matman_key,
        )
    materiales_total = mat_total_editor if mat_total_editor > 0 else float(mat_manual)

    descuento_adicional = st.number_input(
        "Descuento adicional ($)", min_value=0.0, step=10000.0,
        value=float(cc.get("descuento_adicional", 0)), key=f"cced_descad_{id_str}",
    )

    anticipo = float(cc.get("anticipo", 0) or 0)
    descuento_cot = float(cc.get("descuento_cotizacion", 0) or 0)
    tot = total_cuenta_cobro(
        mano_obra, materiales_total, anticipo=anticipo,
        descuento_cotizacion=descuento_cot, descuento_adicional=descuento_adicional,
    )
    st.metric("Total a cobrar", f"${tot['total']:,.0f}")

    col_g, col_c = st.columns(2)
    with col_g:
        if st.button("💾 Guardar", type="primary", use_container_width=True, key=f"cced_save_{id_str}"):
            if not titulo or not descripcion or descripcion == "<p><br></p>":
                st.warning("Título y descripción son obligatorios.")
                return
            datos = {
                "fecha": datetime.combine(fecha, datetime.min.time()),
                "titulo": titulo,
                "descripcion": descripcion,
                "mano_obra": mano_obra,
                "materiales_total": materiales_total,
                "materiales_lista": materiales_lista,
                "anticipo": anticipo,
                "descuento_cotizacion": descuento_cot,
                "descuento_adicional": descuento_adicional,
            }
            svc.actualizar(id_str, datos)
            st.session_state.pop(f"cc_edit_{id_str}", None)
            st.session_state["cc_msg"] = "Cuenta de cobro actualizada."
            st.rerun()
    with col_c:
        if st.button("↩️ Cancelar", use_container_width=True, key=f"cced_cancel_{id_str}"):
            st.session_state.pop(f"cc_edit_{id_str}", None)
            st.rerun()
