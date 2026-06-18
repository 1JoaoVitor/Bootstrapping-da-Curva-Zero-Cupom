import pandas as pd

def ler_titulos_anbima(caminho: str) -> tuple[str, pd.DataFrame]:
    """
    Lê o arquivo TXT da ANBIMA (separador @, encoding latin-1).

    Retorna
    -------
    data_base : str   — data de referência no formato 'YYYY-MM-DD'
    df        : DataFrame com colunas [Titulo, Data Vencimento, PU, Tx. Indicativas]
                filtrado para LTN e NTN-F, ordenado por vencimento.
    """
    # Pula duas linhas de cabeçaçho
    df = pd.read_csv(caminho, sep="@", encoding="latin1", skiprows=2)

    titulos = ['LTN', 'NTN-F']

    df = df[df['Titulo'].isin(titulos)].copy()

    df['PU'] = df['PU'].astype(str).str.replace(',', '.').astype(float)
    df['Tx. Indicativas'] = df['Tx. Indicativas'].astype(str).str.replace(',', '.').astype(float)

    df["Data Vencimento"] = pd.to_datetime(df["Data Vencimento"], format="%Y%m%d")

    data_base_raw = df["Data Referencia"].iloc[0]
    data_base_str = pd.to_datetime(str(data_base_raw), format="%Y%m%d").strftime("%Y-%m-%d")

    df = df[["Titulo", "Data Vencimento", "PU", "Tx. Indicativas"]].sort_values("Data Vencimento")

    return data_base_str, df