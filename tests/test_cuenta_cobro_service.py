from datetime import datetime
from services.cuenta_cobro_service import CuentaCobroService


def test_query_anio_y_busqueda():
    q = CuentaCobroService.construir_query({"anio": 2026, "buscar": "25028"})
    assert q["fecha"]["$gte"] == datetime(2026, 1, 1)
    assert q["$or"][0]["nombre_cliente"]["$regex"] == "25028"
    assert q["$or"][1]["numero_cotizacion"]["$regex"] == "25028"


def test_query_sin_filtros():
    assert CuentaCobroService.construir_query(None) == {}
