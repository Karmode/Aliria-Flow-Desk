# Rediseño de Cotizaciones y Cuentas de Cobro — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la interfaz enredada (8 sub-páginas + `st.expander`) de cotizaciones y cuentas de cobro por una interfaz fluida: tabla filtrable → ventana emergente (modal) con ver/editar/estado/PDF/cuenta de cobro → creación en pestaña. Sin cambios en la base de datos.

**Architecture:** Se introduce una capa de servicios (`services/`) para toda la lógica de Mongo y una capa de utilidades puras (`utils/calculos.py`, `utils/materiales.py`) para cálculos y procesamiento de la tabla de materiales (hoy duplicados 3 veces). Las páginas Streamlit quedan como UI delgada que consume esos servicios/utilidades. Cada sección es un único módulo con `st.tabs` y un `@st.dialog`.

**Tech Stack:** Python, Streamlit 1.46.0, pymongo 4.13, streamlit-quill 0.0.3, fpdf2 2.8.5, pandas 2.3, pytest (dev).

## Global Constraints

- **Streamlit 1.46.0**: usar `use_container_width=True` en `st.dataframe`, `st.button`, `st.download_button`, `st.data_editor` (NO existe `width="stretch"`, que es de 1.49+). `@st.dialog(title, width="large")` y `st.dataframe(..., on_select="rerun", selection_mode="single-row")` sí están disponibles.
- **No cambiar el modelo de datos.** Mismas colecciones (`cotizaciones`, `cuentas_cobro`, `clientes`, `contadores`) y mismos campos. Sin migraciones ni campos nuevos.
- **Sin historial/trazabilidad.** Solo `created_at`/`updated_at`.
- **Reutilizar** `utils/pdf_generator.py` (`generate_pdf(data, doc_type)`) y `db/client.py` (`MongoDBConnection`) sin modificarlos.
- **Idioma:** todo el texto de UI y nombres de dominio en español, siguiendo el estilo del código existente.
- **Estados de cotización:** `["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]`.
- **Numeración:** `f"{str(año)[-2:]}{secuencia:03d}"` con contador transaccional en la colección `contadores` (`nombre="cotizaciones"`, `año=<int>`).
- Ejecutar `pytest` desde la raíz del proyecto. La conexión a Mongo requiere `MONGO_URL`; los tests NO deben tocar Mongo (solo funciones puras / staticmethods).

---

### Task 1: Andamiaje de pruebas

**Files:**
- Create: `requirements-dev.txt`
- Create: `conftest.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`

**Interfaces:**
- Produces: entorno `pytest` ejecutable desde la raíz con imports de proyecto (`from utils... import`, `from services... import`) funcionando.

- [ ] **Step 1: Crear `requirements-dev.txt`**

```
pytest==8.3.4
```

- [ ] **Step 2: Crear `conftest.py` en la raíz** (vacío; su presencia hace que pytest agregue la raíz al `sys.path`)

```python
# Presencia de este archivo en la raíz asegura que pytest incluya el
# directorio del proyecto en sys.path para importar utils/ y services/.
```

- [ ] **Step 3: Crear `tests/__init__.py`** (vacío)

```python
```

- [ ] **Step 4: Crear `tests/test_smoke.py`**

```python
def test_pytest_funciona():
    assert True
```

- [ ] **Step 5: Instalar dependencias de desarrollo y correr el smoke test**

Run: `pip install -r requirements-dev.txt && pytest tests/test_smoke.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add requirements-dev.txt conftest.py tests/__init__.py tests/test_smoke.py
git commit -m "test: añadir andamiaje de pytest"
```

---

### Task 2: Utilidades de cálculo (`utils/calculos.py`)

**Files:**
- Create: `utils/calculos.py`
- Test: `tests/test_calculos.py`

**Interfaces:**
- Produces:
  - `total_cotizacion(mano_obra, materiales_total, descuento=0) -> dict` con claves `subtotal`, `descuento`, `total_general` (todos `float`).
  - `total_cuenta_cobro(mano_obra, materiales_total, anticipo=0, descuento_cotizacion=0, descuento_adicional=0) -> dict` con claves `total_sin_descuentos`, `descuento_total`, `total` (todos `float`).
  - `formatear_numero_cotizacion(anio, secuencia) -> str` (p. ej. `2026, 5 -> "26005"`).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_calculos.py
from utils.calculos import (
    total_cotizacion,
    total_cuenta_cobro,
    formatear_numero_cotizacion,
)


def test_total_cotizacion_sin_descuento():
    r = total_cotizacion(100000, 50000)
    assert r["subtotal"] == 150000.0
    assert r["descuento"] == 0.0
    assert r["total_general"] == 150000.0


def test_total_cotizacion_con_descuento():
    r = total_cotizacion(100000, 50000, 20000)
    assert r["total_general"] == 130000.0


def test_total_cuenta_cobro_aplica_anticipo_y_descuentos():
    r = total_cuenta_cobro(
        100000, 50000, anticipo=30000,
        descuento_cotizacion=10000, descuento_adicional=5000,
    )
    assert r["total_sin_descuentos"] == 150000.0
    assert r["descuento_total"] == 15000.0
    assert r["total"] == 105000.0


def test_formatear_numero_cotizacion():
    assert formatear_numero_cotizacion(2026, 5) == "26005"
    assert formatear_numero_cotizacion(2026, 123) == "26123"
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `pytest tests/test_calculos.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'utils.calculos'`

- [ ] **Step 3: Implementar `utils/calculos.py`**

```python
def total_cotizacion(mano_obra, materiales_total, descuento=0):
    """Totales de una cotización. Devuelve floats."""
    subtotal = float(mano_obra) + float(materiales_total)
    descuento = float(descuento or 0)
    return {
        "subtotal": subtotal,
        "descuento": descuento,
        "total_general": subtotal - descuento,
    }


def total_cuenta_cobro(mano_obra, materiales_total, anticipo=0,
                       descuento_cotizacion=0, descuento_adicional=0):
    """Totales de una cuenta de cobro. Devuelve floats."""
    total_sin_descuentos = float(mano_obra) + float(materiales_total)
    descuento_total = float(descuento_cotizacion or 0) + float(descuento_adicional or 0)
    return {
        "total_sin_descuentos": total_sin_descuentos,
        "descuento_total": descuento_total,
        "total": total_sin_descuentos - float(anticipo or 0) - descuento_total,
    }


def formatear_numero_cotizacion(anio, secuencia):
    """Formato de número: dos dígitos del año + secuencia de 3 dígitos."""
    return f"{str(anio)[-2:]}{int(secuencia):03d}"
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `pytest tests/test_calculos.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add utils/calculos.py tests/test_calculos.py
git commit -m "feat: utilidades puras de cálculo de totales y numeración"
```

---

### Task 3: Utilidades de materiales (`utils/materiales.py`)

**Files:**
- Create: `utils/materiales.py`
- Test: `tests/test_materiales.py`

**Interfaces:**
- Produces:
  - `COLUMNS = ["Unidad", "Material", "Cantidad", "Valor Unitario"]`
  - `df_desde_lista(materiales_lista) -> pandas.DataFrame` con columnas `COLUMNS`; mapea claves guardadas (`unidad`, `material`, `cantidad`, `valor_unitario`) a las columnas del editor. Lista vacía → DataFrame vacío con esas columnas.
  - `procesar_editor(df) -> (list[dict], float)`: limpia filas sin `Material`/`Cantidad`/`Valor Unitario`, descarta `Cantidad <= 0`, renombra a claves de dominio, calcula `total` por fila y devuelve `(lista_materiales, suma_total)`. DataFrame vacío/None → `([], 0.0)`. Cada dict tiene `unidad, material, cantidad(float), valor_unitario(float), total(float)`.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_materiales.py
import pandas as pd
from utils.materiales import df_desde_lista, procesar_editor, COLUMNS


def test_df_desde_lista_vacia():
    df = df_desde_lista([])
    assert list(df.columns) == COLUMNS
    assert df.empty


def test_df_desde_lista_mapea_campos():
    df = df_desde_lista([
        {"unidad": "m", "material": "Cable", "cantidad": 2, "valor_unitario": 1000}
    ])
    assert df.iloc[0]["Material"] == "Cable"
    assert df.iloc[0]["Cantidad"] == 2.0
    assert df.iloc[0]["Valor Unitario"] == 1000.0


def test_procesar_editor_calcula_total_y_filtra_vacias():
    df = pd.DataFrame(
        [
            {"Unidad": "m", "Material": "Cable", "Cantidad": 2, "Valor Unitario": 1000},
            {"Unidad": "", "Material": None, "Cantidad": None, "Valor Unitario": None},
        ],
        columns=COLUMNS,
    )
    lista, total = procesar_editor(df)
    assert len(lista) == 1
    assert lista[0]["material"] == "Cable"
    assert lista[0]["total"] == 2000.0
    assert total == 2000.0


def test_procesar_editor_vacio():
    lista, total = procesar_editor(pd.DataFrame(columns=COLUMNS))
    assert lista == []
    assert total == 0.0
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `pytest tests/test_materiales.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'utils.materiales'`

- [ ] **Step 3: Implementar `utils/materiales.py`**

```python
import pandas as pd

COLUMNS = ["Unidad", "Material", "Cantidad", "Valor Unitario"]


def df_desde_lista(materiales_lista):
    """Construye el DataFrame del editor a partir de la lista guardada en la DB."""
    filas = []
    for item in (materiales_lista or []):
        filas.append({
            "Unidad": item.get("unidad", ""),
            "Material": item.get("material", ""),
            "Cantidad": float(item.get("cantidad", 0)),
            "Valor Unitario": float(item.get("valor_unitario", 0)),
        })
    return pd.DataFrame(filas, columns=COLUMNS)


def procesar_editor(df):
    """Limpia y tipa el DataFrame del editor.

    Devuelve (lista_materiales, total). Filtra filas incompletas y con
    cantidad <= 0. Cada material lleva su 'total' calculado.
    """
    if df is None or df.empty:
        return [], 0.0

    limpio = df.dropna(
        subset=["Material", "Cantidad", "Valor Unitario"], how="any"
    ).reset_index(drop=True)
    limpio = limpio[limpio["Cantidad"] > 0].reset_index(drop=True)
    if limpio.empty:
        return [], 0.0

    limpio = limpio.rename(columns={
        "Unidad": "unidad",
        "Material": "material",
        "Cantidad": "cantidad",
        "Valor Unitario": "valor_unitario",
    })
    limpio["cantidad"] = limpio["cantidad"].astype(float)
    limpio["valor_unitario"] = limpio["valor_unitario"].astype(float)
    limpio["total"] = (limpio["cantidad"] * limpio["valor_unitario"]).astype(float)

    lista = limpio.to_dict(orient="records")
    total = float(sum(m["total"] for m in lista))
    return lista, total
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `pytest tests/test_materiales.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add utils/materiales.py tests/test_materiales.py
git commit -m "feat: utilidades de tabla de materiales (df<->lista)"
```

---

### Task 4: Servicio de cotizaciones (`services/cotizacion_service.py`)

**Files:**
- Create: `services/__init__.py`
- Create: `services/cotizacion_service.py`
- Test: `tests/test_cotizacion_service.py`

**Interfaces:**
- Consumes: `utils.calculos.total_cotizacion`, `utils.calculos.formatear_numero_cotizacion`, `db.client.MongoDBConnection`.
- Produces: clase `CotizacionService` con:
  - `ESTADOS` (constante de módulo, lista de los 5 estados).
  - `__init__(self, db=None)` — usa `MongoDBConnection` si `db` es None.
  - `@staticmethod construir_query(filtros) -> dict` (pura, testeable sin DB). `filtros` puede tener `estado` (`"Todas"` = sin filtro), `anio` (int), `buscar` (str).
  - `listar(self, filtros=None) -> list`
  - `buscar_por_id(self, id_str) -> dict | None`
  - `clientes_dict(self) -> dict` (`{nombre: _id}`)
  - `crear(self, datos) -> str` (devuelve `numero_cotizacion`). `datos`: `cliente_id, nombre_cliente, fecha(datetime), titulo, descripcion, mano_obra, materiales_total, materiales_lista, descuento, anticipo, estado(opcional)`.
  - `actualizar(self, id_str, datos) -> None` (mismo `datos` + `estado`).
  - `cambiar_estado(self, id_str, estado) -> None`.

- [ ] **Step 1: Escribir el test que falla** (solo la parte pura `construir_query`)

```python
# tests/test_cotizacion_service.py
from datetime import datetime
from services.cotizacion_service import CotizacionService, ESTADOS


def test_estados_definidos():
    assert ESTADOS == ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]


def test_query_estado_anio_y_busqueda():
    q = CotizacionService.construir_query(
        {"estado": "Pagada", "anio": 2026, "buscar": "perez"}
    )
    assert q["estado"] == "Pagada"
    assert q["fecha"]["$gte"] == datetime(2026, 1, 1)
    assert q["fecha"]["$lte"] == datetime(2026, 12, 31, 23, 59, 59)
    assert q["$or"][0]["nombre_cliente"]["$regex"] == "perez"
    assert q["$or"][1]["numero_cotizacion"]["$regex"] == "perez"


def test_query_todas_no_filtra_estado():
    q = CotizacionService.construir_query({"estado": "Todas", "anio": 2026})
    assert "estado" not in q


def test_query_sin_filtros():
    assert CotizacionService.construir_query(None) == {}
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `pytest tests/test_cotizacion_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'services.cotizacion_service'`

- [ ] **Step 3: Crear `services/__init__.py`** (vacío)

```python
```

- [ ] **Step 4: Implementar `services/cotizacion_service.py`**

```python
from datetime import datetime

from bson import ObjectId

from db.client import MongoDBConnection
from utils.calculos import total_cotizacion, formatear_numero_cotizacion

ESTADOS = ["Aprobada", "Rechazada", "Pendiente", "Por Cobrar", "Pagada"]


class CotizacionService:
    def __init__(self, db=None):
        self.mongo = MongoDBConnection()
        self.db = db if db is not None else self.mongo.get_database()
        self.col = self.db["cotizaciones"]
        self.clientes = self.db["clientes"]
        self.contadores = self.db["contadores"]

    @staticmethod
    def construir_query(filtros):
        filtros = filtros or {}
        query = {}
        estado = filtros.get("estado")
        if estado and estado != "Todas":
            query["estado"] = estado
        anio = filtros.get("anio")
        if anio:
            query["fecha"] = {
                "$gte": datetime(anio, 1, 1),
                "$lte": datetime(anio, 12, 31, 23, 59, 59),
            }
        buscar = (filtros.get("buscar") or "").strip()
        if buscar:
            query["$or"] = [
                {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
                {"numero_cotizacion": {"$regex": buscar, "$options": "i"}},
            ]
        return query

    def listar(self, filtros=None):
        return list(
            self.col.find(self.construir_query(filtros)).sort("numero_cotizacion", -1)
        )

    def buscar_por_id(self, id_str):
        return self.col.find_one({"_id": ObjectId(id_str)})

    def clientes_dict(self):
        lista = self.clientes.find({}, {"_id": 1, "nombre": 1}).sort("nombre", 1)
        return {c["nombre"]: c["_id"] for c in lista}

    def crear(self, datos):
        fecha = datos["fecha"]
        with self.mongo.client.start_session() as session:
            with session.start_transaction():
                cliente_doc = self.clientes.find_one(
                    {"_id": datos["cliente_id"]}, session=session
                )
                direccion = cliente_doc.get("direccion", "") if cliente_doc else ""

                contador = self.contadores.find_one_and_update(
                    {"nombre": "cotizaciones", "año": fecha.year},
                    {
                        "$inc": {"secuencia": 1},
                        "$setOnInsert": {"nombre": "cotizaciones", "año": fecha.year},
                    },
                    upsert=True,
                    return_document=True,
                    session=session,
                )
                secuencia = contador["secuencia"]
                numero = formatear_numero_cotizacion(fecha.year, secuencia)

                totales = total_cotizacion(
                    datos["mano_obra"], datos["materiales_total"],
                    datos.get("descuento", 0),
                )
                doc = {
                    "cliente_id": datos["cliente_id"],
                    "nombre_cliente": datos["nombre_cliente"],
                    "direccion_cliente": direccion,
                    "fecha": fecha,
                    "titulo": datos["titulo"],
                    "descripcion": datos["descripcion"],
                    "mano_obra": float(datos["mano_obra"]),
                    "materiales_total": float(datos["materiales_total"]),
                    "subtotal": totales["subtotal"],
                    "descuento": totales["descuento"],
                    "total_general": totales["total_general"],
                    "anticipo": float(datos.get("anticipo", 0) or 0),
                    "estado": datos.get("estado", "Pendiente"),
                    "secuencia": secuencia,
                    "numero_cotizacion": numero,
                    "tiene_cuenta_cobro": False,
                    "created_at": datetime.now(),
                }
                if datos.get("materiales_lista"):
                    doc["materiales_lista"] = datos["materiales_lista"]

                self.col.insert_one(doc, session=session)
        return numero

    def actualizar(self, id_str, datos):
        totales = total_cotizacion(
            datos["mano_obra"], datos["materiales_total"], datos.get("descuento", 0)
        )
        cliente_doc = self.clientes.find_one({"_id": datos["cliente_id"]})
        direccion = cliente_doc.get("direccion", "") if cliente_doc else ""
        update = {
            "cliente_id": datos["cliente_id"],
            "nombre_cliente": datos["nombre_cliente"],
            "direccion_cliente": direccion,
            "fecha": datos["fecha"],
            "titulo": datos["titulo"],
            "descripcion": datos["descripcion"],
            "mano_obra": float(datos["mano_obra"]),
            "materiales_total": float(datos["materiales_total"]),
            "subtotal": totales["subtotal"],
            "descuento": totales["descuento"],
            "total_general": totales["total_general"],
            "anticipo": float(datos.get("anticipo", 0) or 0),
            "estado": datos["estado"],
            "materiales_lista": datos.get("materiales_lista") or None,
            "updated_at": datetime.now(),
        }
        self.col.update_one({"_id": ObjectId(id_str)}, {"$set": update})

    def cambiar_estado(self, id_str, estado):
        self.col.update_one(
            {"_id": ObjectId(id_str)},
            {"$set": {"estado": estado, "updated_at": datetime.now()}},
        )
```

- [ ] **Step 5: Correr los tests para verificar que pasan**

Run: `pytest tests/test_cotizacion_service.py -v`
Expected: PASS (4 passed)

- [ ] **Step 6: Commit**

```bash
git add services/__init__.py services/cotizacion_service.py tests/test_cotizacion_service.py
git commit -m "feat: CotizacionService (consultas, crear, actualizar, estado)"
```

---

### Task 5: Servicio de cuentas de cobro (`services/cuenta_cobro_service.py`)

**Files:**
- Create: `services/cuenta_cobro_service.py`
- Test: `tests/test_cuenta_cobro_service.py`

**Interfaces:**
- Consumes: `utils.calculos.total_cuenta_cobro`, `db.client.MongoDBConnection`.
- Produces: clase `CuentaCobroService` con:
  - `__init__(self, db=None)`.
  - `@staticmethod construir_query(filtros) -> dict` (`anio`, `buscar`).
  - `listar(self, filtros=None) -> list`
  - `buscar_por_id(self, id_str) -> dict | None`
  - `guardar_soportes(self, numero_cotizacion, archivos) -> list[str]` (guarda en `uploads/cuentas_cobro/cc_{numero}/`).
  - `crear_desde_cotizacion(self, cotizacion, datos, rutas_soportes) -> ObjectId` — inserta la CC y marca `tiene_cuenta_cobro`/`cuenta_cobro_id` en la cotización. `datos`: `fecha(datetime), titulo, descripcion, mano_obra, materiales_total, materiales_lista, anticipo, descuento_cotizacion, descuento_adicional`.
  - `actualizar(self, id_str, datos) -> None` (mismo `datos`).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_cuenta_cobro_service.py
from datetime import datetime
from services.cuenta_cobro_service import CuentaCobroService


def test_query_anio_y_busqueda():
    q = CuentaCobroService.construir_query({"anio": 2026, "buscar": "25028"})
    assert q["fecha"]["$gte"] == datetime(2026, 1, 1)
    assert q["$or"][0]["nombre_cliente"]["$regex"] == "25028"
    assert q["$or"][1]["numero_cotizacion"]["$regex"] == "25028"


def test_query_sin_filtros():
    assert CuentaCobroService.construir_query(None) == {}
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `pytest tests/test_cuenta_cobro_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'services.cuenta_cobro_service'`

- [ ] **Step 3: Implementar `services/cuenta_cobro_service.py`**

```python
import os
from datetime import datetime

from bson import ObjectId

from db.client import MongoDBConnection
from utils.calculos import total_cuenta_cobro

UPLOAD_BASE = "uploads/cuentas_cobro"


class CuentaCobroService:
    def __init__(self, db=None):
        self.mongo = MongoDBConnection()
        self.db = db if db is not None else self.mongo.get_database()
        self.col = self.db["cuentas_cobro"]
        self.cotizaciones = self.db["cotizaciones"]

    @staticmethod
    def construir_query(filtros):
        filtros = filtros or {}
        query = {}
        anio = filtros.get("anio")
        if anio:
            query["fecha"] = {
                "$gte": datetime(anio, 1, 1),
                "$lte": datetime(anio, 12, 31, 23, 59, 59),
            }
        buscar = (filtros.get("buscar") or "").strip()
        if buscar:
            query["$or"] = [
                {"nombre_cliente": {"$regex": buscar, "$options": "i"}},
                {"numero_cotizacion": {"$regex": buscar, "$options": "i"}},
            ]
        return query

    def listar(self, filtros=None):
        return list(
            self.col.find(self.construir_query(filtros)).sort("numero_cotizacion", -1)
        )

    def buscar_por_id(self, id_str):
        return self.col.find_one({"_id": ObjectId(id_str)})

    def guardar_soportes(self, numero_cotizacion, archivos):
        ruta = os.path.join(UPLOAD_BASE, f"cc_{numero_cotizacion}")
        os.makedirs(ruta, exist_ok=True)
        rutas = []
        for f in (archivos or []):
            path = os.path.join(ruta, f.name)
            with open(path, "wb") as out:
                out.write(f.read())
            rutas.append(path)
        return rutas

    def _doc_desde_datos(self, datos):
        totales = total_cuenta_cobro(
            datos["mano_obra"], datos["materiales_total"],
            anticipo=datos.get("anticipo", 0),
            descuento_cotizacion=datos.get("descuento_cotizacion", 0),
            descuento_adicional=datos.get("descuento_adicional", 0),
        )
        return {
            "fecha": datos["fecha"],
            "titulo": datos["titulo"],
            "descripcion": datos["descripcion"],
            "mano_obra": int(datos["mano_obra"]),
            "materiales_total": float(datos["materiales_total"]),
            "anticipo": float(datos.get("anticipo", 0) or 0),
            "descuento_cotizacion": float(datos.get("descuento_cotizacion", 0) or 0),
            "descuento_adicional": float(datos.get("descuento_adicional", 0) or 0),
            "descuento_total": totales["descuento_total"],
            "total_sin_descuentos": totales["total_sin_descuentos"],
            "total": totales["total"],
        }, totales

    def crear_desde_cotizacion(self, cotizacion, datos, rutas_soportes):
        base, _ = self._doc_desde_datos(datos)
        doc = {
            "cotizacion_id": cotizacion["_id"],
            "numero_cotizacion": cotizacion["numero_cotizacion"],
            "cliente_id": cotizacion["cliente_id"],
            "nombre_cliente": cotizacion["nombre_cliente"],
            "direccion_cliente": cotizacion.get("direccion_cliente", ""),
            "anticipo_original": float(cotizacion.get("anticipo", 0) or 0),
            "descuento_cotizacion_original": float(cotizacion.get("descuento", 0) or 0),
            "soportes": rutas_soportes,
            "created_at": datetime.now(),
            **base,
        }
        if datos.get("materiales_lista"):
            doc["materiales_lista"] = datos["materiales_lista"]

        result = self.col.insert_one(doc)
        self.cotizaciones.update_one(
            {"_id": cotizacion["_id"]},
            {"$set": {"tiene_cuenta_cobro": True, "cuenta_cobro_id": result.inserted_id}},
        )
        return result.inserted_id

    def actualizar(self, id_str, datos):
        base, _ = self._doc_desde_datos(datos)
        base["materiales_lista"] = datos.get("materiales_lista") or None
        base["updated_at"] = datetime.now()
        self.col.update_one({"_id": ObjectId(id_str)}, {"$set": base})
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `pytest tests/test_cuenta_cobro_service.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add services/cuenta_cobro_service.py tests/test_cuenta_cobro_service.py
git commit -m "feat: CuentaCobroService (consultas, crear desde cotización, actualizar)"
```

---

### Task 6: Componentes de UI compartidos y formulario de cotización

**Files:**
- Create: `paginas/cotizaciones/_ui.py`
- Create: `paginas/cotizaciones/form_cotizacion.py`

**Interfaces:**
- Consumes: `utils.materiales`, `utils.calculos.total_cotizacion`, `streamlit_quill.st_quill`.
- Produces (`_ui.py`):
  - `ESTADOS` (lista), `ESTADOS_ICONOS` (dict estado→etiqueta con emoji), `QUILL_TOOLBAR` (lista).
  - `preview_pdf(pdf_bytes) -> None` (incrusta `iframe` base64).
  - `color_estado(estado) -> str` (CSS inline para la celda de estado).
- Produces (`form_cotizacion.py`):
  - `render_form(prefix, clientes_dict, cot=None) -> dict` — renderiza los campos (FUERA de `st.form`, totales en vivo) y devuelve `{cliente_id, nombre_cliente, fecha(datetime), titulo, descripcion, mano_obra, materiales_total, materiales_lista, descuento, anticipo}`.
  - `validar(datos) -> str | None` — devuelve mensaje de error o None.

- [ ] **Step 1: Implementar `paginas/cotizaciones/_ui.py`**

```python
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
```

- [ ] **Step 2: Implementar `paginas/cotizaciones/form_cotizacion.py`**

```python
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
        materiales_manual = st.number_input(
            "Materiales ($)",
            min_value=0.0,
            step=10000.0,
            value=mat_total_editor if mat_total_editor > 0 else base_mat,
            disabled=mat_total_editor > 0,
            key=f"{prefix}_matman",
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
```

- [ ] **Step 3: Verificar que los módulos importan sin error**

Run: `python -c "import paginas.cotizaciones._ui, paginas.cotizaciones.form_cotizacion; print('ok')"`
Expected: imprime `ok` (sin conexión a Mongo; estos módulos no instancian servicios)

- [ ] **Step 4: Commit**

```bash
git add paginas/cotizaciones/_ui.py paginas/cotizaciones/form_cotizacion.py
git commit -m "feat: componentes UI y formulario reutilizable de cotización"
```

---

### Task 7: Modal de cotización (`paginas/cotizaciones/modal_cotizacion.py`)

**Files:**
- Create: `paginas/cotizaciones/modal_cotizacion.py`

**Interfaces:**
- Consumes: `CotizacionService`, `CuentaCobroService`, `render_form`, `validar`, `_ui` (ESTADOS, ESTADOS_ICONOS, QUILL_TOOLBAR, preview_pdf), `utils.materiales`, `utils.calculos.total_cuenta_cobro`, `utils.pdf_generator.generate_pdf`.
- Produces: `abrir_modal_cotizacion(cot) -> None` — decorada con `@st.dialog`; alterna vista/edición según `st.session_state[f"cot_edit_{id}"]` e incluye el formulario embebido de generación de cuenta de cobro.

- [ ] **Step 1: Implementar `paginas/cotizaciones/modal_cotizacion.py`**

```python
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
        mat_manual = st.number_input(
            "Materiales ($)", min_value=0, value=base_mat, step=10000,
            disabled=mat_total_editor > 0, key=f"cc_matman_{id_str}",
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
```

- [ ] **Step 2: Verificar import**

Run: `python -c "import paginas.cotizaciones.modal_cotizacion; print('ok')"`
Expected: imprime `ok`

- [ ] **Step 3: Commit**

```bash
git add paginas/cotizaciones/modal_cotizacion.py
git commit -m "feat: modal de cotización (ver/editar/estado/PDF/generar CC)"
```

---

### Task 8: Página de gestión de cotizaciones (`paginas/cotizaciones/gestion_cotizaciones.py`)

**Files:**
- Create: `paginas/cotizaciones/gestion_cotizaciones.py`

**Interfaces:**
- Consumes: `CotizacionService`, `abrir_modal_cotizacion`, `render_form`, `validar`, `_ui` (ESTADOS_ICONOS, color_estado).
- Produces: `show() -> None` — punto de entrada de la página (invocado por `app.py`), con `st.tabs(["📋 Listado y Gestión", "➕ Nueva Cotización"])`.

- [ ] **Step 1: Implementar `paginas/cotizaciones/gestion_cotizaciones.py`**

```python
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
```

- [ ] **Step 2: Verificar import**

Run: `python -c "import paginas.cotizaciones.gestion_cotizaciones; print('ok')"`
Expected: imprime `ok`

- [ ] **Step 3: Commit**

```bash
git add paginas/cotizaciones/gestion_cotizaciones.py
git commit -m "feat: página de gestión de cotizaciones (tabla + tabs)"
```

---

### Task 9: Página y modal de cuentas de cobro

**Files:**
- Create: `paginas/cuentas_cobro/modal_cuenta_cobro.py`
- Create: `paginas/cuentas_cobro/gestion_cuentas_cobro.py`

**Interfaces:**
- Consumes: `CuentaCobroService`, `utils.materiales`, `utils.calculos.total_cuenta_cobro`, `utils.pdf_generator.generate_pdf`, `paginas.cotizaciones._ui` (QUILL_TOOLBAR, preview_pdf), `streamlit_quill.st_quill`.
- Produces:
  - `abrir_modal_cuenta(cc) -> None` (`@st.dialog`; vista/edición según `st.session_state[f"cc_edit_{id}"]`; botón "Ver Cotización original" que navega a la página de Cotizaciones prellenando el buscador).
  - `show() -> None` — página con tabla + filtros (sin pestaña de creación).

- [ ] **Step 1: Implementar `paginas/cuentas_cobro/modal_cuenta_cobro.py`**

```python
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
        mat_manual = st.number_input(
            "Materiales ($)", min_value=0, value=base_mat, step=10000,
            disabled=mat_total_editor > 0, key=f"cced_matman_{id_str}",
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
```

- [ ] **Step 2: Implementar `paginas/cuentas_cobro/gestion_cuentas_cobro.py`**

```python
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
```

- [ ] **Step 3: Verificar imports**

Run: `python -c "import paginas.cuentas_cobro.modal_cuenta_cobro, paginas.cuentas_cobro.gestion_cuentas_cobro; print('ok')"`
Expected: imprime `ok`

- [ ] **Step 4: Commit**

```bash
git add paginas/cuentas_cobro/modal_cuenta_cobro.py paginas/cuentas_cobro/gestion_cuentas_cobro.py
git commit -m "feat: página y modal de cuentas de cobro"
```

---

### Task 10: Integrar en `app.py`, actualizar `__init__.py` y eliminar páginas antiguas

**Files:**
- Modify: `app.py:5-7` (imports) y `app.py:22-34` (dict `pages`)
- Modify: `paginas/cotizaciones/__init__.py`
- Modify: `paginas/cuentas_cobro/__init__.py`
- Delete: `paginas/cotizaciones/crear_cotizacion.py`, `listar_cotizaciones.py`, `ver_cotizacion.py`, `editar_cotizacion.py`, `exportar_cotizacion.py`
- Delete: `paginas/cuentas_cobro/crear_cuenta_cobro.py`, `listar_cuentas_cobro.py`, `ver_cuenta_cobro.py`, `editar_cuenta_cobro.py`

**Interfaces:**
- Consumes: `paginas.cotizaciones.gestion_cotizaciones.show`, `paginas.cuentas_cobro.gestion_cuentas_cobro.show`.
- Produces: app funcional con menú simplificado (Cotizaciones y Cuentas de Cobro como módulos únicos).

- [ ] **Step 1: Actualizar los imports en `app.py`** (reemplazar las líneas 5-6 actuales)

Reemplazar:

```python
from paginas.cotizaciones import crear_cotizacion, listar_cotizaciones, ver_cotizacion, editar_cotizacion
from paginas.cuentas_cobro import crear_cuenta_cobro, ver_cuenta_cobro, editar_cuenta_cobro, listar_cuentas_cobro
```

por:

```python
from paginas.cotizaciones import gestion_cotizaciones
from paginas.cuentas_cobro import gestion_cuentas_cobro
```

- [ ] **Step 2: Actualizar el dict `pages` en `app.py`** (reemplazar las entradas de Cotizaciones y Cuentas de Cobro)

Reemplazar:

```python
    "Cotizaciones": {
        "Listar Cotizaciones": listar_cotizaciones,
        "Crear Cotización": crear_cotizacion,
        "Ver Cotización": ver_cotizacion,
        "Editar Cotización": editar_cotizacion,
    },
    "Cuentas de Cobro": {
        "Listar Cuentas": listar_cuentas_cobro,
        "Crear Cuenta de Cobro": crear_cuenta_cobro,
        "Ver Cuenta de Cobro": ver_cuenta_cobro,
        "Editar Cuenta de Cobro": editar_cuenta_cobro,
    }
```

por:

```python
    "Cotizaciones": gestion_cotizaciones,
    "Cuentas de Cobro": gestion_cuentas_cobro,
```

- [ ] **Step 3: Actualizar `paginas/cotizaciones/__init__.py`**

```python
# Cotizaciones package
from paginas.cotizaciones import gestion_cotizaciones
```

- [ ] **Step 4: Actualizar `paginas/cuentas_cobro/__init__.py`**

```python
# Cuentas de Cobro package
from paginas.cuentas_cobro import gestion_cuentas_cobro
```

- [ ] **Step 5: Eliminar los archivos antiguos**

```bash
git rm paginas/cotizaciones/crear_cotizacion.py paginas/cotizaciones/listar_cotizaciones.py paginas/cotizaciones/ver_cotizacion.py paginas/cotizaciones/editar_cotizacion.py paginas/cotizaciones/exportar_cotizacion.py
git rm paginas/cuentas_cobro/crear_cuenta_cobro.py paginas/cuentas_cobro/listar_cuentas_cobro.py paginas/cuentas_cobro/ver_cuenta_cobro.py paginas/cuentas_cobro/editar_cuenta_cobro.py
```

- [ ] **Step 6: Verificar que toda la suite de tests sigue pasando**

Run: `pytest -v`
Expected: PASS (todos los tests de las tareas 1-5)

- [ ] **Step 7: Verificar que las páginas importan (sin conexión a Mongo)**

Run: `python -c "import paginas.cotizaciones.gestion_cotizaciones, paginas.cuentas_cobro.gestion_cuentas_cobro; print('ok')"`
Expected: imprime `ok`

- [ ] **Step 8: Verificación manual con la app real (skill `verify` / `run`)**

Run: `streamlit run app.py`
Verificar en el navegador:
1. Menú lateral: "Cotizaciones" abre una sola pantalla con 2 pestañas; "Cuentas de Cobro" abre la tabla.
2. En Cotizaciones → "📋 Listado y Gestión": la tabla filtra por buscador/estado/año; al seleccionar una fila se abre la ventana emergente.
3. En la ventana: se ve el detalle, la previsualización del PDF, y funcionan Editar (con Guardar/Cancelar), Cambiar estado, Exportar PDF.
4. Generar Cuenta de Cobro desde una cotización sin CC; verificar que luego aparece "Ver/Exportar Cuenta de Cobro".
5. "➕ Nueva Cotización": crear una cotización nueva; aparece el mensaje de éxito y se ve en la tabla.
6. En Cuentas de Cobro: seleccionar una fila abre su ventana con previsualización; Editar y Exportar PDF funcionan; "Ver Cotización original" lleva a Cotizaciones con el buscador prellenado.
7. Abrir una cotización y una cuenta de cobro **creadas antes del rediseño** para confirmar que los datos viejos se visualizan y exportan bien.

- [ ] **Step 9: Commit**

```bash
git add app.py paginas/cotizaciones/__init__.py paginas/cuentas_cobro/__init__.py
git commit -m "feat: integrar páginas rediseñadas y eliminar sub-páginas antiguas"
```

---

## Notas de verificación (Streamlit)

Las páginas (`gestion_*`, `modal_*`, `form_*`) no tienen pruebas automatizadas porque dependen del runtime de Streamlit; se validan con el paso de verificación manual (Task 10, Step 8). La lógica con riesgo real de error (cálculos, procesamiento de materiales, construcción de queries) sí está cubierta por tests unitarios en las tareas 2-5.

## Autorrevisión del plan (cobertura del spec)

- Estructura/navegación (spec §5.1-5.2) → Task 10.
- Capa de servicios (spec §5.3) → Tasks 4, 5.
- Utilidades compartidas (spec §5.4) → Tasks 2, 3.
- Pantalla de cotizaciones: tabla, modal, edición en modal, estado, PDF, generar CC, pestaña nueva (spec §6) → Tasks 6, 7, 8.
- Previsualización de PDF en modales (spec §3.4) → `preview_pdf` (Task 6), usada en Tasks 7 y 9.
- Pantalla de cuentas de cobro: tabla, modal, editar, PDF, ver cotización (spec §7) → Task 9.
- Sin cambios de datos / sin historial (spec §3.2-3.3) → ningún task agrega campos nuevos; solo `created_at`/`updated_at`.
- Reutilización de `pdf_generator.py` y `db/client.py` (spec §2) → consumidos, no modificados.
