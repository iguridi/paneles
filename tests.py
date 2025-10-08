import pandas as pd

from backend import (
    parse_panel_code,
)


CANTIDADES_POR_BASE = {"WF600X2250": 10, "SF400X2000": 5}
DF_PEDIDO = pd.DataFrame(
    [
        {"Panel (base)": "WF600X2250", "Cantidad": 10},
        {"Panel (base)": "SF400X2000", "Cantidad": 5},
    ]
)


def assert_equals(x, y):
    assert x == y, f"{x} != {y}"



assert_equals(
    parse_panel_code(list(CANTIDADES_POR_BASE.keys())[0]),
    {
        "tipo": "WF",
        "base": "WF600X2250",
        "nums": [600, 2250],
        "partes": ["WF600", "2250"],
    },
)


print("All tests passed!")
