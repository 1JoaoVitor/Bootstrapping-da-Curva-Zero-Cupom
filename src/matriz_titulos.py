import pandas as pd
import numpy as np

BASE_VALUE = 1_000.00
CUPOM_NTNF = BASE_VALUE * ((1.10 ** 0.5) - 1)  # ≈ 48,8088


def gerar_fluxos(titulo: str, vencimento: pd.Timestamp, data_base: pd.Timestamp) -> dict:
    """
    Retorna {data: valor} com todos os fluxos futuros de um título.

    LTN  → { vencimento: 1000.00 }
    NTN-F → { cupom_1: 48.81, cupom_2: 48.81, ..., vencimento: 1048.81 }

    Os cupons da NTN-F ocorrem a cada 6 meses contados 
    regressivamente a partir do vencimento.
    """
    fluxos = {}

    if titulo == "LTN":
        if vencimento > data_base:
            fluxos[vencimento] = BASE_VALUE

    elif titulo == "NTN-F":
        if vencimento > data_base:
            fluxos[vencimento] = BASE_VALUE + CUPOM_NTNF  # principal + último cupom

        data_cupom = vencimento - pd.DateOffset(months=6)
        while data_cupom > data_base:
            fluxos[data_cupom] = CUPOM_NTNF
            data_cupom -= pd.DateOffset(months=6)

    return fluxos


def construir_sistema(df: pd.DataFrame, data_base_str: str) -> tuple:
    """
    Seleciona os títulos que formam a matriz de C e P.

    Algoritmo de seleção:

    Percorre os vencimentos em ordem crescente.
    Para cada vencimento, escolhe um título (preferencialmente LTN).
    Aceita um NTN-F somente se todos os seus cupons intermediários
    caem em vértices já cobertos.

    Retorna
    -------
    C        : np.ndarray (n×n) — matriz de fluxos (triangular inferior)
    P        : np.ndarray (n)  — vetor de preços
    vertices : list[Timestamp]  — datas dos vértices
    df_sel   : DataFrame        — títulos selecionados (para observação futura)
    """
    data_base = pd.to_datetime(data_base_str)

    df = df.copy()
    df["Fluxos"] = df.apply(
        lambda r: gerar_fluxos(r["Titulo"], r["Data Vencimento"], data_base), axis=1
    )

    vertices_confirmados = set()
    titulos_selecionados = []

    for venc in sorted(df["Data Vencimento"].unique()):
        candidatos = df[df["Data Vencimento"] == venc]

        ltn = candidatos[candidatos["Titulo"] == "LTN"]
        if not ltn.empty:
            vertices_confirmados.add(venc)
            titulos_selecionados.append(ltn.iloc[0])
            continue

        ntnf = candidatos[candidatos["Titulo"] == "NTN-F"]
        if not ntnf.empty:
            fluxos = ntnf.iloc[0]["Fluxos"]
            datas_cupom = sorted([d for d in fluxos.keys() if d != venc]) #fluxo.keys = datas que foram geradas no gerar_fluxo

            cupons_cobertos = all(d in vertices_confirmados for d in datas_cupom)

            if cupons_cobertos:
                vertices_confirmados.add(venc)
                titulos_selecionados.append(ntnf.iloc[0])

            # Se não estiver coberto, descarta esta NTN-F

    df_sel = pd.DataFrame(titulos_selecionados)
    vertices = sorted(vertices_confirmados)
    n = len(vertices)

    date_idx = {v: i for i, v in enumerate(vertices)}

    C = np.zeros((n, n))
    P = df_sel["PU"].values.astype(float)

    for index, (_, row) in enumerate(df_sel.iterrows()):
        for data, valor in row["Fluxos"].items():
            data_matriz = date_idx.get(data) # coluna 
            if data_matriz is not None:
                C[index, data_matriz] = valor

    return C, P, vertices, df_sel



def resolver_sistema(C: np.ndarray, P: np.ndarray) -> np.ndarray:
    """
    Resolve C·d = P por substituição progressiva de forma vetorizada.
    
    A fórmula se reduz a: d_i = (P_i - ProdutoEscalar(C_passado, d_calculado)) / C_atual
    """
    n = len(P)
    d = np.zeros(n)

    for i in range(n):
        item_diagonal = C[i, i] 
        
        if abs(item_diagonal) < 1e-10:
            raise ValueError(f"Sistema singular no vértice {i}. Verifique a matriz C.")


        contribuicao_conhecida = np.dot(C[i, :i], d[:i])
        
        # fórmula do pdf
        d[i] = (P[i] - contribuicao_conhecida) / item_diagonal # item_diagonal = C[i, i] atual 

    return d