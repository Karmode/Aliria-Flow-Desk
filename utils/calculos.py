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
