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
