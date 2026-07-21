from datetime import datetime

import pandas as pd
import streamlit as st

from services.cuenta_cobro_service import CuentaCobroService
from paginas.cuentas_cobro.modal_cuenta_cobro import abrir_modal_cuenta


def show():
    st.title("Cuentas de Cobro")
    svc = CuentaCobroService()

    if "cc_msg" in st.session_state:
        st.success(st.session_state.pop("cc_msg"))

    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        buscar = st.text_input("🔍 Buscar (cliente o número)", key="cc_buscar")
    with c2:
        anio = st.number_input(
            "Año", min_value=2020, max_value=datetime.now().year,
            value=datetime.now().year, step=1, key="cc_anio",
        )
    with c3:
        st.write("")
        st.write("")
        if st.button("🔄", help="Actualizar", use_container_width=True):
            st.rerun()

    cuentas = svc.listar({"buscar": buscar, "anio": int(anio)})
    if not cuentas:
        st.info("No hay cuentas de cobro con esos filtros.")
        return

    filas = []
    for c in cuentas:
        fecha = c.get("fecha")
        filas.append({
            "_id": str(c["_id"]),
            "Número": c.get("numero_cotizacion", ""),
            "Cliente": c.get("nombre_cliente", ""),
            "Título": c.get("titulo", ""),
            "Fecha": fecha.strftime("%d/%m/%Y") if isinstance(fecha, datetime) else str(fecha),
            "Total": f"${float(c.get('total', 0)):,.0f}",
        })
    df = pd.DataFrame(filas)

    st.caption("Selecciona una fila para gestionar la cuenta de cobro.")
    event = st.dataframe(
        df.drop(columns=["_id"]), use_container_width=True, hide_index=True,
        on_select="rerun", selection_mode="single-row",
        height=(len(df) + 1) * 35 + 3,
    )

    if event.selection.rows:
        idx = event.selection.rows[0]
        id_sel = df.iloc[idx]["_id"]
        if st.session_state.get("cc_last_open") != id_sel:
            st.session_state["cc_last_open"] = id_sel
            cc = svc.buscar_por_id(id_sel)
            if cc:
                abrir_modal_cuenta(cc)
    else:
        st.session_state["cc_last_open"] = None
