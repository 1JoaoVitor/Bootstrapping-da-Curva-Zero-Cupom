"""
main.py — Bootstrapping da Curva Zero-Cupom
============================================
Uso:
    python main.py <caminho/arquivo_anbima.txt> <caminho/feriados.xlsx.xls>

Exemplo:
    python main.py data/ANBIMA_tabela.txt data/feriados_nacionais.xls

Entregáveis:
    R1 — Constrói a matriz C e vetor P
    R2 — Resolve C·d = P (substituição progressiva, O(n²))
    R3 — Converte fatores de desconto em taxas spot (base 252)
    R4 — Conta dias úteis com calendário real da ANBIMA
    R5 — Re-precifica e valida erro < 1e-4 usando produto matricial
"""

import sys
import json

from src.calculo_du import ler_feriados
from src.ler_anbima import ler_titulos_anbima
from src.matriz_titulos import construir_sistema, resolver_sistema
from src.curva_zero import extrair_curva, validar_reprecificacao

def main(caminho_anbima: str, caminho_feriados: str):

    feriados = ler_feriados(caminho_feriados)
    data_base_str, df = ler_titulos_anbima(caminho_anbima)

    print(f"  Data-base: {data_base_str}")
    print(f"  {len(df)} títulos (LTN/NTN-F) encontrados.")

    C, P, vertices, df_sel = construir_sistema(df, data_base_str)
    n = len(vertices)

    print(f"  {n} vértices selecionados — matriz quadrada {n}×{n}")
    print(f"  Títulos usados: {df_sel['Titulo'].value_counts().to_dict()}")

    d = resolver_sistema(C, P)
    curva = extrair_curva(d, vertices, data_base_str, feriados)

    validacao = validar_reprecificacao(C, P, d)

    resultado = {
        "data_base": data_base_str,
        "erro_reprecificacao": validacao["max_erro"],
        "curva": curva
    }

    print(json.dumps(resultado, indent=2, ensure_ascii=False))

    print("\n")
    status = "APROVADO" if validacao["aprovado"] else "REPROVADO"
    print(f"STATUS DA AVALIAÇÃO: {status}")
    print(f"Erro Máximo de Re-precificação: {validacao['max_erro']:.2e}\n")

    return resultado


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso correto: python main.py <arquivo_anbima.txt> <feriados.xls>")
        sys.exit(1)
        
    main(sys.argv[1], sys.argv[2])