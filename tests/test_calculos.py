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
