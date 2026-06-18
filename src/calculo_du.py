import pandas as pd
import numpy as np

def ler_feriados(caminho: str) -> np.ndarray:
    """
    Lê o arquivo de feriados da ANBIMA (formato excel) e retorna
    um array numpy de datas no formato datetime64[D], usado pelo
    np.busday_count para exclusão mais eficiente.

    Tudo que  não seja uma data válida é filtrado antes de converter.
    """
    ext = caminho.lower().split(".")[-1]
    engine = "xlrd" if ext == "xls" else "openpyxl"

    df = pd.read_excel(caminho, engine=engine)
    df = df.dropna(subset=["Data"])

    datas_validas = []
    for valor in df["Data"]:
        if isinstance(valor, str):
            continue 
        if hasattr(valor, "date"):
            datas_validas.append(pd.Timestamp(valor))
        elif isinstance(valor, (int, float)):
            # Em caso de guardar valores de  datas como número serial do Excel
            datas_validas.append(pd.to_datetime(valor, unit="D", origin="1899-12-30"))

    feriados = (
        pd.Series(datas_validas)
        .dt.normalize()
        .values
        .astype("datetime64[D]")
    )
    return feriados


def calcular_du(data_base: str, data_vencimento: str, feriados: np.ndarray) -> int:
    """
    Conta dias úteis entre data_base (exclusivo) e data_vencimento (inclusivo).
    np.busday_count já exclui sábados, domingos e os feriados fornecidos.
    """
    db = np.datetime64(data_base, "D")
    dv = np.datetime64(data_vencimento, "D")
    return int(np.busday_count(db, dv, holidays=feriados))


def prazo_em_anos(du: int) -> float:
    """Convenção brasileira: base 252 dias úteis por ano."""
    return du / 252.0