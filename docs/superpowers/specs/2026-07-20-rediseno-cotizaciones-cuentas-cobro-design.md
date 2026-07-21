# Rediseño de Cotizaciones y Cuentas de Cobro — Estilo "Correspondencia"

**Fecha:** 2026-07-20
**Proyecto:** Aliria Flow Desk
**Objetivo:** Reemplazar la interfaz enredada de cotizaciones y cuentas de cobro (menú de 8 sub-páginas + listados con `expander`) por una interfaz fluida basada en **tabla filtrable + ventana emergente (modal) + creación en pestaña**, replicando el patrón de la página de Correspondencia del proyecto `gestion-srt-invias`.

---

## 1. Contexto y problema

El sistema actual (Streamlit + MongoDB) gestiona cotizaciones y cuentas de cobro con:

- Un menú lateral de 2 niveles: cada entidad tiene 4 sub-páginas (`Listar`, `Crear`, `Ver`, `Editar`).
- Listados construidos con `st.expander` por fila, llenos de botones que **navegan a otras páginas** vía `st.session_state.menu_principal`/`submenu`.
- El usuario salta constantemente de pantalla en pantalla; es difícil filtrar y gestionar.

El patrón deseado (ya probado en `2_correspondencia.py`):

- **Una pantalla por sección** con `st.tabs`.
- Listado como `st.dataframe` interactivo (`on_select="rerun"`, `selection_mode="single-row"`) con filtros arriba, filas con color según estado y paginación.
- Al seleccionar una fila → `@st.dialog` (ventana emergente) con toda la info y acciones.
- Creación en una pestaña de la misma pantalla.

## 2. Alcance

**Incluido en esta tanda:**
- Sección **Cotizaciones** (tabla + modal + pestaña de creación).
- Sección **Cuentas de Cobro** (tabla + modal; sin creación propia).
- Limpieza de código: extracción de lógica repetida a `utils/` y `services/`.

**Fuera de alcance (queda igual):**
- Sección **Clientes** (`listar_clientes.py`, `crear_clientes.py`).
- **Inicio** (`home.py`).
- `db/client.py` y `utils/pdf_generator.py` (se reutilizan sin cambios).

## 3. Decisiones de diseño (confirmadas con el usuario)

1. **Centro de gravedad = la cotización.** Todo (ver, editar, cambiar estado, exportar PDF, generar/ver cuenta de cobro) se gestiona desde la ventana emergente de la cotización. **Además** existe una tabla independiente de Cuentas de Cobro para ver/filtrar/exportar todas juntas.
2. **Sin historial/trazabilidad.** Se mantiene simple: solo `created_at` y `updated_at` como hoy. No se agregan campos nuevos.
3. **La estructura de datos NO cambia.** Mismas colecciones y mismos campos. Sin migración. Los documentos existentes siguen funcionando y los PDFs se generan igual.
4. **Previsualización del PDF dentro del modal** (visor incrustado por `iframe` base64), tanto en cotizaciones como en cuentas de cobro.

## 4. Modelo de datos (sin cambios — solo de referencia)

Colección **`cotizaciones`**:
`cliente_id`, `nombre_cliente`, `direccion_cliente`, `fecha`, `titulo`, `descripcion` (HTML de Quill), `materiales_lista` (lista de `{unidad, material, cantidad, valor_unitario, total}`), `mano_obra`, `materiales_total`, `subtotal`, `descuento`, `total_general`, `anticipo`, `estado`, `secuencia`, `numero_cotizacion`, `tiene_cuenta_cobro`, `cuenta_cobro_id`, `created_at`, `updated_at`.

Estados: `Pendiente`, `Aprobada`, `Rechazada`, `Por Cobrar`, `Pagada`.

Colección **`cuentas_cobro`**:
`cotizacion_id`, `numero_cotizacion`, `cliente_id`, `nombre_cliente`, `direccion_cliente`, `fecha`, `titulo`, `descripcion`, `mano_obra`, `materiales_total`, `materiales_lista`, `anticipo`, `anticipo_original`, `descuento_cotizacion`, `descuento_cotizacion_original`, `descuento_adicional`, `descuento_total`, `total_sin_descuentos`, `total`, `soportes` (rutas), `created_at`.

Colecciones **`clientes`** y **`contadores`**: sin cambios.

## 5. Arquitectura objetivo

### 5.1 Navegación (`app.py`)
El diccionario `pages` se simplifica: Cotizaciones y Cuentas de Cobro pasan de ser sub-menús con 4 páginas a **un solo módulo cada uno**.

```python
pages = {
    "Inicio": home,
    "Clientes": { "Listar Clientes": listar_clientes, "Crear Clientes": crear_clientes },
    "Cotizaciones": gestion_cotizaciones,      # módulo único con tabs internos
    "Cuentas de Cobro": gestion_cuentas_cobro, # módulo único
}
```

La lógica de submenú de `app.py` ya soporta módulos simples (rama `else: selected_page = pages[choice]`), así que el cambio es acotado.

### 5.2 Nuevos módulos de página
- `paginas/cotizaciones/gestion_cotizaciones.py` — `show()` con `st.tabs(["📋 Listado y Gestión", "➕ Nueva Cotización"])`, el modal y la tabla.
- `paginas/cuentas_cobro/gestion_cuentas_cobro.py` — `show()` con tabla + modal.

Los archivos antiguos (`crear_cotizacion.py`, `listar_cotizaciones.py`, `ver_cotizacion.py`, `editar_cotizacion.py`, y sus equivalentes de cuentas de cobro) se **eliminan** una vez migrada su lógica; se actualizan los `__init__.py` y las importaciones en `app.py`.

### 5.3 Capa de servicios (`services/`)
Nuevo paquete `services/` con:
- `cotizacion_service.py` — `CotizacionService`: `listar(filtros)`, `buscar_por_id(id)`, `crear(datos)` (incluye numeración transaccional con `contadores`), `actualizar(id, datos)`, `cambiar_estado(id, estado)`.
- `cuenta_cobro_service.py` — `CuentaCobroService`: `listar(filtros)`, `buscar_por_id(id)`, `crear_desde_cotizacion(cotizacion, datos, soportes)`, `actualizar(id, datos)`.

Cada servicio recibe/usa `MongoDBConnection`. Las páginas no vuelven a tener consultas Mongo inline.

### 5.4 Utilidades compartidas (`utils/`)
- `utils/materiales.py` — funciones para el flujo de la tabla de materiales, hoy duplicado en 3 archivos:
  - `df_desde_lista(materiales_lista) -> DataFrame` (para poblar el `data_editor`).
  - `procesar_editor(df) -> (lista_materiales, total)` (limpia filas vacías, tipa, calcula `total`).
- `utils/formato.py` (opcional) — helpers de formato de moneda/fecha si reducen repetición.
- `utils/pdf_generator.py` — se mantiene tal cual.

## 6. Pantalla de Cotizaciones — comportamiento

### 6.1 Pestaña "📋 Listado y Gestión"
- **Filtros** (fila superior): buscador (regex por `nombre_cliente` o `numero_cotizacion`), `Estado` (Todas + los 5), `Año` (rango de fechas). Botón "🔄 Actualizar".
- **Tabla** `st.dataframe` interactiva con columnas: `Número`, `Cliente`, `Título`, `Fecha`, `Total`, `Estado`. Filas coloreadas por estado (paleta tenue clara/oscura como en correspondencia). Columna `_id` oculta para la selección.
- **Selección de fila** → abre `@st.dialog("Cotización …", width="large")`.
- Paginación si el volumen lo amerita (patrón de correspondencia); orden por `numero_cotizacion` desc.

### 6.2 Ventana emergente (modal) de cotización
Contenido:
1. Cabecera: `📄 Cotización {numero}` + badge de estado + métricas (Estado, Total, Fecha, Cliente).
2. Detalle (modo vista): título, descripción (HTML renderizado), tabla de materiales, resumen de costos (mano de obra, materiales, subtotal, descuento, anticipo, total).
3. **Previsualización del PDF** incrustada (`iframe` base64) generada con `generate_pdf(..., doc_type="Cotización")`.
4. **Acciones:**
   - `✏️ Editar` → conmuta el modal a **modo edición** (mediante flag en `st.session_state`), **sin** `st.form` para que los totales se recalculen en vivo: cliente, fecha, título, descripción (`st_quill`), materiales (`st.data_editor`), mano de obra, materiales manual, anticipo, descuento, estado, con resumen en vivo y botones **Guardar / Cancelar**. Guardar llama a `CotizacionService.actualizar` y refresca.
   - `🔄 Cambiar estado` → selector rápido + guardar (`cambiar_estado`).
   - `⬇️ Exportar PDF` → `st.download_button` con los bytes del PDF.
   - Cuenta de cobro:
     - Si `tiene_cuenta_cobro` es falso → `🧾 Generar Cuenta de Cobro`: abre en el mismo modal el formulario de creación de CC (título, descripción, materiales editables prellenados desde la cotización, mano de obra, materiales, anticipo/descuento aplicables, soportes) y llama a `CuentaCobroService.crear_desde_cotizacion`.
     - Si ya tiene → `📂 Ver Cuenta de Cobro`: muestra/edita la CC (o dirige a su modal) con su previsualización y exportación.

### 6.3 Pestaña "➕ Nueva Cotización"
Formulario completo equivalente al actual `crear_cotizacion.py`: cliente, fecha, título, descripción (`st_quill`), tabla de materiales (`st.data_editor`), costos (mano de obra, materiales, anticipo, descuento). Al enviar: `CotizacionService.crear` (numeración transaccional), mensaje de éxito persistente y reset del formulario (patrón `form_key_idx`).

## 7. Pantalla de Cuentas de Cobro — comportamiento

- **Filtros:** buscador (cliente/número), `Año`. Botón actualizar.
- **Tabla** `st.dataframe` interactiva: `Número`, `Cliente`, `Título`, `Fecha`, `Total`.
- **Selección de fila** → `@st.dialog`:
  - Datos de la cuenta, materiales, soportes adjuntos.
  - **Previsualización del PDF** (`generate_pdf(..., doc_type="Cuenta de Cobro")`).
  - Acciones: `✏️ Editar`, `⬇️ Exportar PDF`, `📋 Ver Cotización original`.
- Sin pestaña de creación (las CC se generan desde la cotización).

## 8. Detalles técnicos y consideraciones

- **Edición dentro del modal:** Streamlit no re-ejecuta el script dentro de un `st.form` hasta el submit; por eso la edición (que necesita totales en vivo) va **sin** `st.form`, replicando el enfoque actual de `editar_cotizacion.py`. La creación sí puede usar `st.form` con `clear_on_submit`.
- **Estado del modal:** se usan flags en `st.session_state` (p. ej. `modo_edicion_{id}`, `last_opened_id`) para alternar vista/edición y evitar reaperturas indebidas del diálogo, siguiendo el patrón de correspondencia.
- **Componentes en diálogo:** `st_quill` y `st.data_editor` funcionan dentro de `@st.dialog`; se usa `width="large"`.
- **Colores por estado:** paleta tenue con soporte claro/oscuro (adaptada de correspondencia) aplicada con `df.style.apply`.
- **Numeración:** se conserva la lógica transaccional con `contadores` (`find_one_and_update` con `upsert`), movida al servicio.
- **Soportes:** se conserva el guardado en `uploads/cuentas_cobro/cc_{numero}/`.

## 9. Criterios de éxito

1. Cotizaciones y Cuentas de Cobro se gestionan cada una en **una sola pantalla**, sin navegar entre sub-páginas.
2. El listado es una **tabla filtrable**; al seleccionar una fila se abre una **ventana emergente** con ver/editar/estado/PDF/cuenta de cobro.
3. Se pueden **crear cotizaciones** en una pestaña de la misma pantalla.
4. La ventana emergente incluye **previsualización del PDF**.
5. **Ningún dato existente se rompe**: cotizaciones y cuentas de cobro previas se visualizan, editan y exportan correctamente.
6. La lógica repetida de materiales/guardado queda centralizada en `utils/`/`services/`.

## 10. Riesgos

- `st_quill` dentro de `@st.dialog` podría comportarse de forma inesperada en algunas versiones de Streamlit → mitigación: `key` namespaced por id y, si hiciera falta, mover la edición pesada a la pestaña de creación en modo edición como plan B.
- Diálogos grandes con previsualización de PDF pueden quedar altos → aceptable; el visor va al final con altura acotada.
