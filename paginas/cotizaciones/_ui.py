import base64

import streamlit as st

ESTADOS = ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]

ESTADOS_ICONOS = {
    "Aprobada": "✅ Aprobada",
    "Rechazada": "❌ Rechazada",
    "Pendiente": "⏳ Pendiente",
    "Por Cobrar": "💼 Por Cobrar",
    "Pagada": "💰 Pagada",
}

QUILL_TOOLBAR = [
    [{"header": [1, 2, 3, False]}],
    ["bold", "italic", "underline"],
    [{"list": "ordered"}, {"list": "bullet"}],
    ["clean"],
]


def preview_pdf(pdf_bytes):
    b64 = base64.b64encode(pdf_bytes).decode()
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" '
        f'height="600" style="border:1px solid #ddd;"></iframe>',
        unsafe_allow_html=True,
    )


def color_estado(estado):
    e = (estado or "").lower()
    if "pendiente" in e:
        return "background-color:#FFF3E0;color:#E65100;"
    if "rechaz" in e:
        return "background-color:#FFEBEE;color:#B71C1C;"
    if "aprob" in e:
        return "background-color:#E3F2FD;color:#0D47A1;"
    if "cobrar" in e:
        return "background-color:#FFFDE7;color:#F57F17;"
    if "pagada" in e:
        return "background-color:#E8F5E9;color:#1B5E20;"
    return ""
