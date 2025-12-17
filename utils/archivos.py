from pathlib import Path

def guardar_soportes(numero_cotizacion, archivos):
    base = Path("uploads/soportes") / numero_cotizacion
    base.mkdir(parents=True, exist_ok=True)

    rutas = []

    for file in archivos:
        destino = base / file.name
        with open(destino, "wb") as f:
            f.write(file.getbuffer())
        rutas.append(destino)

    return rutas