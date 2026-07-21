from datetime import datetime

import pandas as pd
import streamlit as st

from services.cotizacion_service import CotizacionService
from paginas.cotizaciones._ui import ESTADOS_ICONOS, color_estado
from paginas.cotizaciones.modal_cotizacion import abrir_modal_cotizacion
from paginas.cotizaciones.form_cotizacion import render_form, validar


def show():
    st.title("Cotizaciones")
    svc = CotizacionService()

    if "cot_msg" in st.session_state:
        st.success(st.session_state.pop("cot_msg"))

    tab_list, tab_new = st.tabs(["📋 Listado y Gestión", "➕ Nueva Cotización"])
    with tab_list:
        _tab_listado(svc)
    with tab_new:
        _tab_nueva(svc)


def _tab_listado(svc):
    c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
    with c1:
        buscar = st.text_input("🔍 Buscar (cliente o número)", key="cot_buscar")
    with c2:
        estado = st.selectbox(
            "Estado",
            ["Todas", "Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"],
            key="cot_estado",
        )
    with c3:
        anio = st.number_input(
            "Año", min_value=2020, max_value=datetime.now().year,
            value=datetime.now().year, step=1, key="cot_anio",
        )
    with c4:
        st.write("")
        st.write("")
        if st.button("🔄", help="Actualizar", use_container_width=True):
            st.rerun()

    cotizaciones = svc.listar({"buscar": buscar, "estado": estado, "anio": int(anio)})
    if not cotizaciones:
        st.info("No hay cotizaciones con esos filtros.")
        return

    filas = []
    for c in cotizaciones:
        total = float(c.get("total_general", c.get("mano_obra", 0) + c.get("materiales_total", 0)))
        fecha = c.get("fecha")
        filas.append({
            "_id": str(c["_id"]),
            "Número": c.get("numero_cotizacion", ""),
            "Cliente": c.get("nombre_cliente", ""),
            "Título": c.get("titulo", ""),
            "Fecha": fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else str(fecha),
            "Total": f"${total:,.0f}",
            "Estado": ESTADOS_ICONOS.get(c.get("estado", ""), c.get("estado", "")),
        })
    df = pd.DataFrame(filas)

    def _style(row):
        styles = [""] * len(row)
        styles[row.index.get_loc("Estado")] = color_estado(row["Estado"])
        return styles

    st.caption("Selecciona una fila para gestionar la cotización.")
    styled = df.drop(columns=["_id"]).style.apply(_style, axis=1)
    event = st.dataframe(
        styled, use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        height=(len(df) + 1) * 35 + 3,
    )

    if event.selection.rows:
        idx = event.selection.rows[0]
        id_sel = df.iloc[idx]["_id"]
        if st.session_state.get("cot_last_open") != id_sel:
            st.session_state["cot_last_open"] = id_sel
            cot = svc.buscar_por_id(id_sel)
            if cot:
                abrir_modal_cotizacion(cot)
    else:
        st.session_state["cot_last_open"] = None


def _tab_nueva(svc):
    st.subheader("Nueva Cotización")
    clientes_dict = svc.clientes_dict()
    if not clientes_dict:
        st.warning("No hay clientes registrados. Crea un cliente primero.")
        return

    if "cot_new_key" not in st.session_state:
        st.session_state["cot_new_key"] = 0
    prefix = f"new_{st.session_state['cot_new_key']}"

    datos = render_form(prefix, clientes_dict)
    if st.button("✓ Guardar Cotización", type="primary", use_container_width=True):
        err = validar(datos)
        if err:
            st.warning(err)
            return
        numero = svc.crear(datos)
        st.session_state["cot_msg"] = f"Cotización {numero} guardada."
        st.session_state["cot_new_key"] += 1
        st.rerun()
