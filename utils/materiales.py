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
