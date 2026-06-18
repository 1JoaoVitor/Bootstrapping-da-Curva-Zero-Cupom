"""
test_curva_zero.py - Testes automatizados do bootstrapping com Dados Reais

Execução (na raiz do projeto):
    python -m pytest tests/test_curva_zero.py -v

ATENÇÃO: Variáveis CAMINHO_FERIADOS e CAMINHO_ANBIMA desse arquivo contêm o caminho e 
nome dos arquivos de dados, ou seja, variam, se atentar na hora de rodar os testes
"""

import sys
import os   
import numpy as np
import pandas as pd
import pytest


caminho_src = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, caminho_src)

from src.calculo_du import ler_feriados, calcular_du, prazo_em_anos
from src.ler_anbima import ler_titulos_anbima
from src.matriz_titulos import gerar_fluxos, construir_sistema, resolver_sistema, CUPOM_NTNF, BASE_VALUE
from src.curva_zero import extrair_curva, validar_reprecificacao

CAMINHO_FERIADOS = "data/feriados_nacionais.xls"
CAMINHO_ANBIMA = "data/ANBIMA_tabela.txt"

@pytest.fixture(scope="module")
def feriados():
    """Carrega os feriados apenas uma vez."""
    return ler_feriados(CAMINHO_FERIADOS)


@pytest.fixture(scope="module")
def sistema_real(feriados):
    """Lê o TXT real, monta a matriz e extrai a curva."""
    data_base_str, df_bruto = ler_titulos_anbima(CAMINHO_ANBIMA)
    C, P, vertices, df_sel = construir_sistema(df_bruto, data_base_str)
    d = resolver_sistema(C, P)
    curva = extrair_curva(d, vertices, data_base_str, feriados)
    
    return data_base_str, C, P, vertices, df_sel, d, curva


class TestInfraestrutura:
    def test_cupom_ntnf(self):
        """Cupom = 1000 × ((1,10)^0,5 − 1) ≈ 48,8088."""
        esperado = 1000 * ((1.10 ** 0.5) - 1)
        assert abs(CUPOM_NTNF - esperado) < 1e-4

    def test_feriados_carregados(self, feriados):
        assert len(feriados) > 1000, "Esperado calendário até 2099"

    def test_prazo_base_252(self):
        assert prazo_em_anos(252) == 1.0

    def test_prazo_base_251(self):
        assert prazo_em_anos(251) != 1.0

    def test_prazo_base_253(self):
        assert prazo_em_anos(253) != 1.0


class TestMatrizReal:
    def test_matriz_quadrada(self, sistema_real):
        _, C, _, vertices, df_sel, _, _ = sistema_real
        assert C.shape[0] == C.shape[1], f"Matriz C não é quadrada: {C.shape}"
        assert C.shape[0] == len(vertices), "Nº de linhas diferente do nº de vértices"
        assert C.shape[0] == len(df_sel), "Nº de linhas diferente do nº de títulos selecionados"

    def test_triangular_inferior(self, sistema_real):
        """Garante que nenhum título possui fluxos após o seu próprio vencimento (acima da diagonal)."""
        _, C, _, _, _, _, _ = sistema_real
        n = C.shape[0]
        for i in range(n):
            for j in range(i + 1, n):
                assert C[i, j] == 0.0, f"Elemento C[{i},{j}] deveria ser 0.0"

    def test_diagonal_nao_zero(self, sistema_real):
        """A diagonal principal (o vencimento do título) nunca pode ser zero."""
        _, C, _, _, _, _, _ = sistema_real
        for i in range(C.shape[0]):
            assert abs(C[i, i]) > 0.0, f"Elemento diagonal C[{i},{i}] é zero. Sistema singular."


class TestCurvaValores:
    def test_ltn_spot_igual_ytm(self, sistema_real):
        """
        Para qualquer LTN a taxa spot calculada tem 
        obrigatoriamente de ser igual à Taxa Indicativa original da ANBIMA.
        """
        _, _, _, _, df_sel, _, curva = sistema_real
        
        for i, row in enumerate(df_sel.iterrows()):
            titulo_info = row[1] # Dados do título na linha i
            
            if titulo_info['Titulo'] == 'LTN':
                taxa_spot_calculada = curva[i]['taxa_spot']

                # A taxa do txt vem em percentagem (ex: 14.31)
                taxa_txt_decimal = titulo_info['Tx. Indicativas'] / 100.0
                
                # Tolerância de 1e-4 para o teste de sanidade
                assert abs(taxa_spot_calculada - taxa_txt_decimal) < 1e-4, (
                    f"Falha no Vértice {curva[i]['data']}: "
                    f"Spot Calculada ({taxa_spot_calculada}) != YTM Original ({taxa_txt_decimal})"
                )


class TestCasosDeBorda:
    def test_vencimento_igual_data_base(self, feriados):
        """
        Garante que o cálculo da Taxa Spot não quebra com dividindo por zero (1 / 0).
        """
        d_ficticio = np.array([1.0])
        vertices_ficticios = [pd.Timestamp("2026-06-01")]
        data_base = "2026-06-01"
        
        curva = extrair_curva(d_ficticio, vertices_ficticios, data_base, feriados)
        
        assert curva[0]['taxa_spot'] == 0.0, "Taxa spot de prazo zero deve ser tratada como 0.0"

    def test_cupom_exatamente_na_data_base(self):
        """
        Se a data-base cair exatamente no dia do pagamento de um cupom de NTN-F,
        esse cupom não deve entrar no fluxo futuro de precificação.
        """
        db_cupom = pd.Timestamp("2026-07-01") # Data exata de um cupom
        vencimento = pd.Timestamp("2027-01-01")
        
        fluxos = gerar_fluxos("NTN-F", vencimento, db_cupom)
        
        assert db_cupom not in fluxos, "Cupom da data-base já foi pago e não deve ser precificado!"

        # O único fluxo restante deve ser o do vencimento
        assert len(fluxos) == 1 

    def test_fim_de_semana_ou_feriado(self, feriados):
        """
        Caso da data-base cair em um dia de semana
        A contagem de dias úteis até a próxima segunda-feira deve ser tratada corretamente.
        """
        # 2026-06-06 é um Sábado. 2026-06-08 é Segunda-feira.
        data_base_sabado = "2026-06-06"
        vencimento_segunda = "2026-06-08"
        
        du = calcular_du(data_base_sabado, vencimento_segunda, feriados)
        
        assert isinstance(du, int)
        assert du >= 0

# TESTE OBRIGATÓRIO
class TestReprecificacaoR5:
    def test_r5_reprecificacao_matriz(self, sistema_real):
        """
        Re-precificar todos os títulos com a curva gerada
        deve resultar num erro absoluto < 1e-4 para a base real da ANBIMA.
        """
        _, C, P, _, _, d, _ = sistema_real
        val = validar_reprecificacao(C, P, d)
        
        assert val["aprovado"], (
            f"R5 FALHOU com dados reais — erro máximo {val['max_erro']:.2e} >= 1e-4"
        )
