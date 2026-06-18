# Bootstrapping da Curva Zero-Cupom

Solução para o desafio técnico de construção da curva zero-cupom a partir dos preços indicativos da ANBIMA para títulos públicos brasileiros (LTN e NTN-F).

---

## Como Executar

```bash
# Instalar dependências
pip install numpy pandas openpyxl xlrd

# Executar o projeto (na raiz)
python main.py data/ANBIMA_tabela.txt data/feriados_nacionais.xls
```

---

## Estrutura

O projeto foi construído com separação de responsabilidades para garantir escalabilidade e fácil manutenção. Os arquivos principais estão dentro das pasta "src".

| Arquivo | Responsabilidade |
|----------|------------------|
| `main.py` | Organizador |
| `ler_anbima.py` | Leitura e limpeza do arquivo TXT da ANBIMA |
| `calculo_du.py` | Contagem de dias úteis e cálculo dos prazos |
| `matriz_titulos.py` | Construção dos fluxos e resolução do sistema linear |
| `curva_zero.py` | Extração das taxas spot e reprecificação |

---

# Testes Automatizados

O projeto inclui uma suíte de testes construída com pytest, desenhada para validar desde a infraestrutura matemática até o comportamento do sistema em casos específicos.

## Como Executar

```bash

pip install pytest

python -m pytest tests/test_reprecificacao.py -v

```

ATENÇÃO: Variáveis CAMINHO_FERIADOS e CAMINHO_ANBIMA do arquivo de teste contêm o caminho 
e nome dos arquivos de dados, ou seja, variam, se atentar na hora de rodar os testes.

## Cobertura dos Testes

- Infraestrutura Financeira: Valida o cálculo exato do valor dos cupons e a contagem correta de dias úteis utilizando o calendário real da ANBIMA. 
- Integridade Matricial: Assegura que a matriz de fluxos C seja estritamente quadrada e triangular inferior, sem vértices singulares na diagonal principal.
- Consistência com Taxas Indicativas: Varre o dataframe garantindo que a Taxa Spot extraída para os vértices compostos por LTNs (zero-cupom) seja rigorosamente igual à Taxa Indicativa original.
- Validação e Reprecificação (R5): Garante que a multiplicação da matriz de fluxos pelo vetor de fatores de desconto resulte nos preços originais com erro absoluto inferior a 1e-4.
- Casos de Borda Específicos: O cálculo foi testado contra 'anomalias' financeiras e matemáticas possíveis:

  - Divisão por Zero: Verifica títulos que vencem exatamente no dia da data-base (prazo zero).

  - Cupons Ex-Dividendo: Cupons que vencem exatamente na data-base são corretamente ignorados no fluxo de caixa de precificação.

  - Fins de Semana e Feriados: O sistema suporta marcação a mercado utilizando datas de referência que não recaem em dias úteis convencionais.

# (a) Modelação do Problema

## Dias Úteis e Prazos

O mercado brasileiro utiliza contagem em **dias úteis**, excluindo fins de semana e feriados nacionais, sobre uma base de **252 dias úteis por ano**.

A contagem é realizada através da função vetorizada:

```python
numpy.busday_count()
```

alimentada pelo calendário oficial da ANBIMA, usado a partir do argumento "holiday".

---

## Fluxos de Caixa

### LTN

Título **zero-cupom**, possuindo apenas um fluxo:

- R$ 1.000,00 no vencimento.

### NTN-F

Possui:

- Cupons semestrais de R$ 48,8088;
- Pagamento de principal de R$ 1.000,00 no vencimento.

O valor do cupom deriva da taxa nominal de 10% a.a.:

Cupom = 1000 × ((1,10)^(1/2) − 1) = R$ 48,8088

---

## Sistema Linear

O preço de cada título corresponde à soma dos seus fluxos futuros descontados.

Em forma matricial:

C · d = P

onde:

| Símbolo | Descrição |
|----------|------------|
| **C** | Matriz de fluxos de caixa (m × n) |
| **d** | Vetor dos fatores de desconto |
| **P** | Vetor dos preços observados (PU) |

---

## Estrutura Triangular

Ao ordenar os títulos por vencimento e selecionar um título por vértice, a matriz **C** torna-se quadrada e triangular inferior.

### Critério de Seleção

Para cada vencimento:

1. Prioriza-se a **LTN**;
2. Uma **NTN-F** é aceita apenas quando todos os seus cupons intermediários já estão cobertos por vértices anteriores;
3. Caso contrário, a NTN-F é descartada para evitar que o sistema fique subdeterminado (matriz singular).

---

## Conversão de Fator para Taxa Spot

A taxa spot anualizada (base 252) é obtida a partir do fator de desconto:

taxa_spot = fator_desconto ^ (-1 / prazo_anos) - 1

onde:

prazo_anos = DU / 252
DU = Contagem de dias úteis (DU), excluindo fins de semana e feriados nacionais.

---

# (b) Método de Resolução

## Substituição Progressiva Vetorizada

Como a matriz **C** é triangular inferior, o sistema é resolvido através de substituição progressiva.

Em vez de utilizar:

```python
np.linalg.solve()
```

foi implementado um algoritmo específico para matrizes triangulares, explorando a dependência causal do problema para maior otimização.

A contribuição dos fluxos já conhecidos é calculada através de produto escalar vetorizado:

```python
contribuicao_conhecida = np.dot(C[i, :i], d[:i])
d[i] = (P[i] - contribuicao_conhecida) / C[i, i]
```

---

# (c) Complexidade Computacional

| Etapa | Complexidade |
|---------|--------------|
| Leitura dos arquivos | O(t) |
| Geração dos fluxos e montagem da matriz | O(n²) |
| Resolução por substituição progressiva | O(n²) |
| Validação matricial (`C · d`) | O(n²) |
| **Complexidade total** | **O(n²)** |

onde:

- **t** = número de títulos/linhas;
- **n** = número de vértices da curva.

---

# Validação e Reprecificação (R5)

Após a construção da curva, todos os títulos são reprecificados para verificar a consistência da solução.

A validação é realizada através de:

```python
P_calc = np.dot(C, d)
erros = np.abs(P_calc - P)
max_erro = np.max(erros)
```

e depois:

```bash
"aprovado": bool(max_erro < tolerancia),
```

onde nesse caso tolerancia = float(1e-4)

## Controle de Precisão

Os fatores de desconto são mantidos em precisão máxima (`float64`) durante todo o processo.

O arredondamento ocorre apenas na exportação do JSON final, garantindo que o erro computacional permaneça 
limitado à precisão da máquina e a tolerância exigida de `1e-4` seja respeitada.

---

## Resultado Obtido

Localmente se obteve a seguinte saída a partir do arquivo ANBIMA (2026/06/16):

```text
  Data-base: 2026-06-16
  18 títulos (LTN/NTN-F) encontrados.
  13 vértices selecionados — matriz quadrada 13×13
  Títulos usados: {'LTN': 12, 'NTN-F': 1}
{
  "data_base": "2026-06-16",
  "erro_reprecificacao": 0.0,
  "curva": [
    {
      "data": "2026-07-01",
      "du": 11,
      "fator_desconto": 0.994176,
      "taxa_spot": 0.143177
    },
    {
      "data": "2026-10-01",
      "du": 76,
      "fator_desconto": 0.961495,
      "taxa_spot": 0.139054
    },
    {
      "data": "2027-01-01",
      "du": 138,
      "fator_desconto": 0.93018,
      "taxa_spot": 0.1413
    },
    {
      "data": "2027-04-01",
      "du": 198,
      "fator_desconto": 0.901484,
      "taxa_spot": 0.141107
    },
    {
      "data": "2027-07-01",
      "du": 261,
      "fator_desconto": 0.871037,
      "taxa_spot": 0.142604
    },
    {
      "data": "2027-10-01",
      "du": 326,
      "fator_desconto": 0.840725,
      "taxa_spot": 0.143518
    },
    {
      "data": "2028-01-01",
      "du": 389,
      "fator_desconto": 0.812937,
      "taxa_spot": 0.14358
    },
    {
      "data": "2028-04-01",
      "du": 452,
      "fator_desconto": 0.786011,
      "taxa_spot": 0.14367
    },
    {
      "data": "2028-07-01",
      "du": 513,
      "fator_desconto": 0.760758,
      "taxa_spot": 0.14376
    },
    {
      "data": "2029-01-01",
      "du": 637,
      "fator_desconto": 0.711049,
      "taxa_spot": 0.14443
    },
    {
      "data": "2029-07-01",
      "du": 761,
      "fator_desconto": 0.665082,
      "taxa_spot": 0.1446
    },
    {
      "data": "2030-01-01",
      "du": 886,
      "fator_desconto": 0.622376,
      "taxa_spot": 0.144396
    },
    {
      "data": "2032-01-01",
      "du": 1390,
      "fator_desconto": 0.476355,
      "taxa_spot": 0.143904
    }
  ]
}


STATUS DA AVALIAÇÃO: APROVADO
Erro Máximo de Re-precificação: 0.00e+00
```

O resultado demonstra que a curva construída reproduz exatamente os preços observados do conjunto de títulos utilizado.