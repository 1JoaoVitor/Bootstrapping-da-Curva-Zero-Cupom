import numpy as np
import pandas as pd
from src.calculo_du import ler_feriados, prazo_em_anos, calcular_du

def extrair_curva(d: np.ndarray, vertices: list, data_base_str: str, feriados: np.ndarray) -> list[dict]:
    """
    Converte o vetor de fatores de desconto na curva zero-cupom.

    Para cada vértice i:
        DU_i       = dias úteis entre data_base e vértice i
        p_i        = DU_i / 252
        taxa_spot  = d_i^(-1/p_i) - 1

    """
    curva = []
    for i, vertice in enumerate(vertices):
        v_str = vertice.strftime("%Y-%m-%d")
        du = calcular_du(data_base_str, v_str, feriados)
        p = prazo_em_anos(du)
        fator = float(d[i])
        taxa = 0.0 

        if p > 0:
            taxa = (fator ** (-1.0 / p)) - 1

        curva.append({
            "data":                v_str,
            "du":                  du,
            "fator_desconto":      round(fator, 6),   
            "taxa_spot":           round(taxa, 6),
        })
    return curva


def validar_reprecificacao(C: np.ndarray, P: np.ndarray, d: np.ndarray, tolerancia: float = 1e-4) -> dict:
    """
    Re-precifica todos os títulos usando produto matricial
    e compara com os PUs originais de mercado.

    Retorna dict com detalhes por título e o erro máximo.
    """

    P_calc = np.dot(C, d)
    
    erros = np.abs(P_calc - P)
    max_erro = np.max(erros)
    
    resultados = {}
    for i in range(len(P)):
        chave = f"Titulo_Linha_{i}"
        resultados[chave] = {
            "pu_mercado": round(P[i], 6),
            "pu_calculado": round(P_calc[i], 6),
            "erro": round(erros[i], 8),
        }
        
    return {
        "aprovado": bool(max_erro < tolerancia),
        "max_erro": round(float(max_erro), 8),
        "titulos": resultados,
    }