from datetime import datetime

import pandas as pd
import streamlit as st
from streamlit_quill import st_quill

from services.cotizacion_service import CotizacionService
from services.cuenta_cobro_service import CuentaCobroService
from utils.materiales import df_desde_lista, procesar_editor
from utils.calculos import total_cuenta_cobro
from utils.pdf_generator import generate_pdf
from paginas.cotizaciones._ui import (
    ESTADOS, ESTADOS_ICONOS, QUILL_TOOLBAR, preview_pdf,
)
from paginas.cotizaciones.form_cotizacion import render_form, validar

_COLCONFIG = {
    "Unidad": st.column_config.TextColumn("Unidad"),
    "Material": st.column_config.TextColumn("Material"),
    "Cantidad": st.column_config.NumberColumn("Cantidad", min_value=0.0, step=1.0),
    "Valor Unitario": st.column_config.NumberColumn(
        "Valor Unitario ($)", min_value=0, step=100
    ),
}


@st.dialog("Gestión de Cotización", width="large")
def abrir_modal_cotizacion(cot):
    id_str = str(cot["_id"])
    svc = CotizacionService()
    if st.session_state.get(f"cot_edit_{id_str}"):
        _vista_editar(cot, svc, id_str)
    else:
        _vista_detalle(cot, svc, id_str)


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
        use_container_width=True,
        hide_index=True,
    )


def _vista_detalle(cot, svc, id_str):
    estado = cot.get("estado", "Pendiente")
    total = float(cot.get("total_general", cot.get("mano_obra", 0) + cot.get("materiales_total", 0)))

    st.markdown(f"### 📄 Cotización {cot.get('numero_cotizacion', 'N/A')}")
    c1, c2, c3 = st.columns(3)
    c1.metric("Estado", ESTADOS_ICONOS.get(estado, estado))
    c2.metric("Total", f"${total:,.0f}")
    fecha = cot.get("fecha")
    c3.metric("Fecha", fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else str(fecha))
    st.write("**Cliente:**", cot.get("nombre_cliente", "N/A"))

    st.divider()
    st.markdown(f"#### {cot.get('titulo', 'Sin título')}")
    st.markdown(cot.get("descripcion") or "_Sin descripción_", unsafe_allow_html=True)
    _tabla_materiales(cot.get("materiales_lista", []))
    st.write(
        f"**Mano de obra:** ${cot.get('mano_obra', 0):,.0f}   |   "
        f"**Materiales:** ${cot.get('materiales_total', 0):,.0f}"
    )
    if cot.get("descuento", 0):
        st.write(f"**Descuento:** -${cot.get('descuento', 0):,.0f}")
    if cot.get("anticipo", 0):
        st.write(f"**Anticipo:** ${cot.get('anticipo', 0):,.0f}")

    pdf_bytes, filename = generate_pdf(dict(cot), doc_type="Cotización")

    st.divider()
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("✏️ Editar", key=f"e_{id_str}", use_container_width=True):
            st.session_state[f"cot_edit_{id_str}"] = True
            st.rerun()
    with a2:
        st.download_button(
            "⬇️ Exportar PDF", data=pdf_bytes, file_name=filename,
            mime="application/pdf", key=f"pdf_{id_str}", use_container_width=True,
        )
    with a3:
        with st.popover("🔄 Estado", use_container_width=True):
            nuevo = st.selectbox(
                "Nuevo estado", ESTADOS,
                index=ESTADOS.index(estado) if estado in ESTADOS else 0,
                format_func=lambda x: ESTADOS_ICONOS[x], key=f"es_{id_str}",
            )
            if st.button("Guardar", key=f"esb_{id_str}", type="primary"):
                svc.cambiar_estado(id_str, nuevo)
                st.rerun()

    st.divider()
    if cot.get("tiene_cuenta_cobro"):
        st.success("✅ Esta cotización ya tiene cuenta de cobro.")
        cc_svc = CuentaCobroService()
        cc = cc_svc.buscar_por_id(str(cot["cuenta_cobro_id"])) if cot.get("cuenta_cobro_id") else None
        if cc:
            cc_pdf, cc_name = generate_pdf(dict(cc), doc_type="Cuenta de Cobro")
            st.download_button(
                "⬇️ Exportar Cuenta de Cobro (PDF)", data=cc_pdf, file_name=cc_name,
                mime="application/pdf", key=f"ccpdf_{id_str}", use_container_width=True,
            )
    else:
        with st.expander("🧾 Generar Cuenta de Cobro"):
            _form_generar_cc(cot)

    st.divider()
    st.caption("📄 Previsualización del PDF")
    preview_pdf(pdf_bytes)


def _vista_editar(cot, svc, id_str):
    st.markdown(f"### ✏️ Editar Cotización {cot.get('numero_cotizacion', '')}")
    clientes_dict = svc.clientes_dict()
    datos = render_form(f"edit_{id_str}", clientes_dict, cot=cot)
    estado_actual = cot.get("estado", "Pendiente")
    estado = st.selectbox(
        "Estado", ESTADOS,
        index=ESTADOS.index(estado_actual) if estado_actual in ESTADOS else 0,
        format_func=lambda x: ESTADOS_ICONOS[x], key=f"edest_{id_str}",
    )

    col_g, col_c = st.columns(2)
    with col_g:
        if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key=f"save_{id_str}"):
            err = validar(datos)
            if err:
                st.warning(err)
                return
            datos["estado"] = estado
            svc.actualizar(id_str, datos)
            st.session_state.pop(f"cot_edit_{id_str}", None)
            st.session_state["cot_msg"] = "Cotización actualizada."
            st.rerun()
    with col_c:
        if st.button("↩️ Cancelar", use_container_width=True, key=f"cancel_{id_str}"):
            st.session_state.pop(f"cot_edit_{id_str}", None)
            st.rerun()


def _form_generar_cc(cot):
    cc_svc = CuentaCobroService()
    id_str = str(cot["_id"])

    titulo = st.text_input("Título", value=cot.get("titulo", ""), key=f"cc_tit_{id_str}")
    st.write("Descripción")
    descripcion = st_quill(
        value=cot.get("descripcion", ""), html=True, toolbar=QUILL_TOOLBAR,
        key=f"cc_desc_{id_str}",
    )
    fecha = st.date_input("Fecha", value=datetime.today(), key=f"cc_fecha_{id_str}")

    df_init = df_desde_lista(cot.get("materiales_lista", []))
    edited = st.data_editor(
        df_init, num_rows="dynamic", use_container_width=True,
        key=f"cc_mat_{id_str}", column_config=_COLCONFIG,
    )
    materiales_lista, mat_total_editor = procesar_editor(edited)

    col1, col2 = st.columns(2)
    with col1:
        mano_obra = st.number_input(
            "Mano de obra ($)", min_value=0, value=int(cot.get("mano_obra", 0)),
            step=10000, key=f"cc_mo_{id_str}",
        )
    with col2:
        base_mat = int(cot.get("materiales_total", 0)) if mat_total_editor == 0 else 0
        matman_key = f"cc_matman_{id_str}"
        if matman_key not in st.session_state:
            st.session_state[matman_key] = base_mat
        if mat_total_editor > 0:
            st.session_state[matman_key] = int(mat_total_editor)
        mat_manual = st.number_input(
            "Materiales ($)", min_value=0, step=10000,
            disabled=mat_total_editor > 0, key=matman_key,
        )
    materiales_total = mat_total_editor if mat_total_editor > 0 else float(mat_manual)

    anticipo_cot = float(cot.get("anticipo", 0) or 0)
    aplicar_ant = False
    if anticipo_cot > 0:
        aplicar_ant = st.checkbox(
            f"Aplicar anticipo de la cotización (${anticipo_cot:,.0f})",
            value=True, key=f"cc_apant_{id_str}",
        )
    descuento_cot = float(cot.get("descuento", 0) or 0)
    aplicar_desc = False
    if descuento_cot > 0:
        aplicar_desc = st.checkbox(
            f"Aplicar descuento de la cotización (${descuento_cot:,.0f})",
            value=True, key=f"cc_apdesc_{id_str}",
        )
    descuento_adicional = st.number_input(
        "Descuento adicional ($)", min_value=0.0, step=10000.0, value=0.0,
        key=f"cc_descad_{id_str}",
    )

    soportes = st.file_uploader(
        "Soportes (opcional)", type=["jpg", "jpeg", "png", "pdf"],
        accept_multiple_files=True, key=f"cc_sop_{id_str}",
    )

    tot = total_cuenta_cobro(
        mano_obra, materiales_total,
        anticipo=(anticipo_cot if aplicar_ant else 0),
        descuento_cotizacion=(descuento_cot if aplicar_desc else 0),
        descuento_adicional=descuento_adicional,
    )
    st.metric("Total a cobrar", f"${tot['total']:,.0f}")

    if st.button("💾 Generar Cuenta de Cobro", type="primary", key=f"cc_gen_{id_str}"):
        if not titulo or not descripcion or descripcion == "<p><br></p>":
            st.warning("Título y descripción son obligatorios.")
            return
        if mano_obra <= 0:
            st.warning("La mano de obra debe ser mayor a cero.")
            return
        rutas = cc_svc.guardar_soportes(cot["numero_cotizacion"], soportes)
        datos = {
            "fecha": datetime.combine(fecha, datetime.min.time()),
            "titulo": titulo,
            "descripcion": descripcion,
            "mano_obra": mano_obra,
            "materiales_total": materiales_total,
            "materiales_lista": materiales_lista,
            "anticipo": anticipo_cot if aplicar_ant else 0,
            "descuento_cotizacion": descuento_cot if aplicar_desc else 0,
            "descuento_adicional": descuento_adicional,
        }
        cc_svc.crear_desde_cotizacion(cot, datos, rutas)
        st.session_state["cot_msg"] = "Cuenta de cobro generada."
        st.rerun()
