import streamlit as st
from datetime import datetime
from bson import ObjectId
import os
import pandas as pd # Necesario para el st.data_editor

from db.client import MongoDBConnection
from streamlit_quill import st_quill

UPLOAD_BASE = "uploads/cuentas_cobro"

# Definición de la estructura de la tabla de materiales
MATERIALES_COLUMNS = ["Unidad", "Material", "Cantidad", "Valor Unitario"]


def show():
    st.title("🧾 Generar Cuenta de Cobro")
    st.markdown("---")

    # ───────────────── Validación inicial ─────────────────
    if "cotizacion_id" not in st.session_state:
        st.warning("No hay cotización seleccionada.")
        return

    cotizacion_id = ObjectId(st.session_state.cotizacion_id)

    # ───────────────── Conexión ─────────────────
    mongo = MongoDBConnection()
    db = mongo.get_database()

    COTIZACIONES = db["cotizaciones"]
    CUENTAS = db["cuentas_cobro"]

    cotizacion = COTIZACIONES.find_one({"_id": cotizacion_id})

    if not cotizacion:
        st.error("Cotización no encontrada.")
        return

    if cotizacion.get("tiene_cuenta_cobro"):
        st.info("Esta cotización ya tiene cuenta de cobro.")
        return

    # ───────────────── Estado inicial y preparación de datos ─────────────────
    
    # Preparamos los datos de la cotización para el Data Editor (si existen)
    # 1. Renombramos los campos de la DB (unidad, material, valor_unitario, etc.) 
    #    a los nombres que espera el Data Editor (Unidad, Material, Valor Unitario).
    lista_inicial = cotizacion.get("materiales_lista", [])
    
    df_inicial_data = []
    for item in lista_inicial:
        df_inicial_data.append({
            "Unidad": item.get("unidad", ""),
            "Material": item.get("material", ""),
            # Convertimos a float para que el data_editor lo maneje como tal
            "Cantidad": float(item.get("cantidad", 0)), 
            "Valor Unitario": int(item.get("valor_unitario", 0)),
        })

    df_inicial = pd.DataFrame(df_inicial_data, columns=MATERIALES_COLUMNS)

    # Inicializamos la variable de sesión para el Data Editor
    if "materiales_df_cc" not in st.session_state or st.session_state.get("last_cot_id") != str(cotizacion_id):
        st.session_state.materiales_df_cc = df_inicial
        st.session_state.last_cot_id = str(cotizacion_id)

    # ───────────────── Encabezado ─────────────────
    st.subheader(f"Cotización {cotizacion['numero_cotizacion']}")
    st.write("**Cliente:**", cotizacion["nombre_cliente"])

    # ───────────────── Formulario ─────────────────
    with st.form("form_cuenta_cobro"):
        st.subheader("Datos de la Cuenta de Cobro")

        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Cliente",
                value=cotizacion["nombre_cliente"],
                disabled=True
            )

        with col2:
            fecha = st.date_input(
                "Fecha",
                value=datetime.today()
            )

        titulo = st.text_input(
            "Título",
            value=cotizacion.get("titulo", "")
        )

        st.write("Descripción del trabajo")
        descripcion = st_quill(
            value=cotizacion.get("descripcion", ""),
            html=True,
            toolbar=[
                [{"header": [1, 2, 3, False]}],
                ["bold", "italic", "underline"],
                [{"list": "ordered"}, {"list": "bullet"}],
                ["clean"],
            ],
            key="cc_descripcion"
        )

        # ─────────────── Materiales (st.data_editor) ───────────────
        st.markdown("---")
        st.subheader("Listado de Materiales (Editable)")

        edited_df = st.data_editor(
            st.session_state.materiales_df_cc,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Unidad": st.column_config.TextColumn(
                    "Unidad", required=True
                ),
                "Material": st.column_config.TextColumn(
                    "Material", required=True
                ),
                "Cantidad": st.column_config.NumberColumn(
                    "Cantidad", min_value=0.01, step=0.01, required=True
                ),
                "Valor Unitario": st.column_config.NumberColumn(
                    "Valor Unitario ($)", min_value=0, step=100, required=True
                ),
            },
        )
        
        # Actualizamos el estado de la sesión con los datos editados
        st.session_state.materiales_df_cc = edited_df

        # Cálculo del total de materiales en la interfaz (para deshabilitar el input manual)
        if not edited_df.empty:
            materiales_total_editor = float(
                (edited_df["Cantidad"].fillna(0) * edited_df["Valor Unitario"].fillna(0)).sum()
            )
        else:
            materiales_total_editor = 0.0

        # ─────────────── Costos ───────────────
        st.markdown("---")
        st.subheader("Costos")

        col3, col4 = st.columns(2)

        with col3:
            # Mano de obra debe ser INT
            mano_obra_input = st.number_input(
                "Mano de obra ($)",
                min_value=0,
                # Forzamos a INT ya que st.number_input puede devolver float
                value=int(cotizacion.get("mano_obra", 0)), 
                step=10000
            )

        with col4:
            # Materiales manual solo si el editor está vacío
            materiales_manual = st.number_input(
                "Materiales ($)",
                min_value=0,
                value=int(cotizacion.get("materiales_total", 0)) if materiales_total_editor == 0.0 else 0,
                step=10000,
                disabled=materiales_total_editor > 0.0, # Deshabilitado si hay datos en la tabla
                help="Se desactiva si usas el listado de materiales."
            )

        # ─────────────── Soportes ───────────────
        st.markdown("---")
        st.subheader("Soportes (opcional)")

        soportes = st.file_uploader(
            "Sube facturas o soportes",
            type=["jpg", "jpeg", "png", "pdf"],
            accept_multiple_files=True
        )

        guardar = st.form_submit_button("💾 Generar Cuenta de Cobro")

    # ───────────────── Lógica de Guardado ─────────────────
    if guardar:
        if not titulo or not descripcion or descripcion == "<p><br></p>":
            st.warning("Título y descripción son obligatorios.")
            return

        if mano_obra_input <= 0:
            st.warning("La mano de obra debe ser mayor a cero.")
            return
            
        # 1. Procesamiento del DataFrame (Similar a la creación de cotización)
        df_a_guardar = st.session_state.materiales_df_cc.copy()
        materiales_lista_final = []

        if not df_a_guardar.empty:
            
            # A. FILTRAR FILAS INVÁLIDAS Y VACÍAS
            df_a_guardar = df_a_guardar.dropna(
                subset=["Material", "Cantidad", "Valor Unitario"],
                how="any"
            ).reset_index(drop=True)
            
            # Asegurar que los valores numéricos sean válidos
            df_a_guardar = df_a_guardar[
                (df_a_guardar["Cantidad"] > 0)
            ].reset_index(drop=True)

        if not df_a_guardar.empty:
            
            # B. RENOMBRAR COLUMNAS para schema (unidad, material, etc.)
            df_a_guardar.rename(
                columns={
                    "Unidad": "unidad",
                    "Material": "material",
                    "Cantidad": "cantidad",
                    "Valor Unitario": "valor_unitario",
                },
                inplace=True,
            )
            
            # C. FORZAR TIPOS DE DATOS (INT y FLOAT para MongoDB)
            df_a_guardar["valor_unitario"] = df_a_guardar["valor_unitario"].astype(int)
            df_a_guardar["cantidad"] = df_a_guardar["cantidad"].astype(float)

            # D. Calcular la columna "total" (FLOAT/DOUBLE)
            df_a_guardar["total"] = (
                df_a_guardar["cantidad"] *
                df_a_guardar["valor_unitario"]
            ).astype(float)
            
            # E. Convertir a lista de diccionarios
            materiales_lista_final = df_a_guardar.to_dict(orient="records")

        # 2. Definir valores monetarios finales
        mano_obra_int = int(mano_obra_input)
        
        if materiales_lista_final:
            materiales_total_double = float(sum(m["total"] for m in materiales_lista_final))
        else:
            materiales_total_double = float(materiales_manual) # De ser manual, forzamos a float

        total_general = float(mano_obra_int) + materiales_total_double

        try:
            # 3. Guardado de soportes
            carpeta = f"cc_{cotizacion['numero_cotizacion']}"
            ruta = os.path.join(UPLOAD_BASE, carpeta)
            os.makedirs(ruta, exist_ok=True)

            rutas_soportes = []
            for f in soportes or []:
                path = os.path.join(ruta, f.name)
                with open(path, "wb") as out:
                    out.write(f.read())
                rutas_soportes.append(path)

            # 4. Preparar el documento de la Cuenta de Cobro
            cuenta = {
                "cotizacion_id": cotizacion["_id"],
                "numero_cotizacion": cotizacion["numero_cotizacion"],
                "cliente_id": cotizacion["cliente_id"],
                "nombre_cliente": cotizacion["nombre_cliente"],
                "fecha": datetime.combine(fecha, datetime.min.time()),
                "titulo": titulo,
                "descripcion": descripcion,
                
                # Tipos de datos corregidos
                "mano_obra": mano_obra_int, 
                "materiales_total": materiales_total_double,
                "materiales_lista": materiales_lista_final,

                "total": total_general,
                "soportes": rutas_soportes,
                "created_at": datetime.now()
            }
            
            # Quitar lista si está vacía para pasar la validación
            if not materiales_lista_final:
                cuenta.pop("materiales_lista", None)

            # 5. Insertar y Actualizar
            result = CUENTAS.insert_one(cuenta)

            COTIZACIONES.update_one(
                {"_id": cotizacion["_id"]},
                {
                    "$set": {
                        "tiene_cuenta_cobro": True,
                        "cuenta_cobro_id": result.inserted_id
                    }
                }
            )

            st.success(f"Cuenta de cobro generada correctamente por ${total_general:,.0f}")

            # 6. Limpieza y redirección
            st.session_state.materiales_df_cc = pd.DataFrame(columns=MATERIALES_COLUMNS)
            st.session_state.menu_principal = "Cotizaciones"
            st.session_state.submenu = "Listar Cotizaciones"
            st.rerun()

        except Exception as e:
            st.error(f"Error al generar cuenta de cobro: {e}")