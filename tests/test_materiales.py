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
