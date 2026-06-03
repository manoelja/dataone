import pandas as pd
import numpy as np
import io
import random
import csv
from typing import List, Optional, Tuple, Dict, Any, Union

def detectar_outliers_iqr(df: pd.DataFrame) -> Dict[str, int]:
    """Detecta outliers em colunas numéricas utilizando o método do Intervalo Interquartil (IQR)."""
    outliers_count = {}

    # Seleciona apenas colunas numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Conta quantos valores estão fora dos limites
        count = ((df[col] < lower_bound) | (df[col] > upper_bound)).sum()
        if count > 0:
            outliers_count[col] = int(count)

    return outliers_count

def gerar_cpf_valido() -> str:
    """Gera um CPF válido aleatoriamente."""
    nine_digits = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum([(len(nine_digits) + 1 - i) * v for i, v in enumerate(nine_digits)]) % 11
        nine_digits.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, nine_digits[0:3]))}.{''.join(map(str, nine_digits[3:6]))}.{''.join(map(str, nine_digits[6:9]))}-{''.join(map(str, nine_digits[9:11]))}"

def gerar_cnpj_valido() -> str:
    """Gera um CNPJ válido aleatoriamente."""
    cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for _ in range(2):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(cnpj) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        val = sum([pesos[i] * v for i, v in enumerate(cnpj)]) % 11
        cnpj.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, cnpj[0:2]))}.{''.join(map(str, cnpj[2:5]))}.{''.join(map(str, cnpj[5:8]))}/{''.join(map(str, cnpj[8:12]))}-{''.join(map(str, cnpj[12:14]))}"

def merge_dataframes(df1: pd.DataFrame, df2: pd.DataFrame, key1: str, key2: str) -> pd.DataFrame:
    """Mescla dois DataFrames com base em chaves selecionadas (Left Join)."""
    return pd.merge(df1, df2, left_on=key1, right_on=key2, how='left')

def detectar_delimitador(file) -> str:
    """Detecta automaticamente o delimitador de um arquivo CSV."""
    # Volta o ponteiro do arquivo para o início
    file.seek(0)
    # Lê uma amostra do arquivo
    sample = file.read(2048).decode('utf-8', errors='ignore')
    file.seek(0)

    delimiters = [';', ',', '\t', '|']
    best_delimiter = ';' # Default
    max_cols = 0

    for d in delimiters:
        # Conta quantas vezes o delimitador aparece na primeira linha
        first_line = sample.split('\n')[0]
        cols = first_line.count(d)
        if cols > max_cols:
            max_cols = cols
            best_delimiter = d

    return best_delimiter

def carregar_dados(file) -> pd.DataFrame:
    """Carrega dados de arquivos Excel ou CSV com detecção automática de delimitador."""
    if file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    else:
        delim = detectar_delimitador(file)
        return pd.read_csv(file, sep=delim, decimal=',')

def remover_duplicados(df: pd.DataFrame, geral: bool, colunas_chave: List[str]) -> pd.DataFrame:
    """Remove linhas duplicadas com base em critérios globais ou colunas específicas."""
    if geral:
        df = df.drop_duplicates()
    if colunas_chave:
        df = df.drop_duplicates(subset=colunas_chave)
    return df

def tratar_nulos(df: pd.DataFrame, colunas: List[str], estrategia: str) -> pd.DataFrame:
    """Aplica a estratégia de tratamento de valores nulos nas colunas selecionadas."""
    df_copia = df.copy()
    if estrategia == "Preencher com Zero (0)":
        for col in colunas:
            df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')
            df_copia[col] = df_copia[col].fillna(0)
            df_copia[col] = df_copia[col].replace({"nan": 0, "NaN": 0})
    elif estrategia == "Preencher com 'Não Informado'":
        for col in colunas:
            df_copia[col] = df_copia[col].fillna("Não Informado")
    elif estrategia == "Excluir a linha inteira":
        df_copia = df_copia.dropna(subset=colunas)
    return df_copia

def inserir_coluna(df: pd.DataFrame, nome: str, pos_direita: Optional[str], valor_padrao: Any) -> pd.DataFrame:
    """Insere uma nova coluna em uma posição específica."""
    if pos_direita:
        try:
            idx_posicao = df.columns.get_loc(pos_direita)
        except KeyError:
            idx_posicao = len(df.columns)
    else:
        idx_posicao = len(df.columns)

    df.insert(idx_posicao, nome, valor_padrao)
    return df

def limpar_espacos_fantasmas(df: pd.DataFrame) -> pd.DataFrame:
    """Apara espaços em branco de todas as colunas de texto."""
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    return df

def ajustar_caixa_texto(df: pd.DataFrame, colunas: List[str], modo: str) -> pd.DataFrame:
    """Ajusta a capitalização do texto nas colunas selecionadas."""
    for c in colunas:
        if modo == "TUDO EM MAIÚSCULO":
            df[c] = df[c].astype(str).str.upper()
        elif modo == "tudo em minúsculo":
            df[c] = df[c].astype(str).str.lower()
        else:
            df[c] = df[c].astype(str).str.title()
    return df

def gerar_ids_sequenciais(df: pd.DataFrame, coluna_destino: str, inicio: int) -> pd.DataFrame:
    """Gera uma sequência de IDs numéricos."""
    df_res = df.copy()
    # Normaliza a string sentinela da UI para o nome real da coluna
    if coluna_destino.startswith("Criar nova coluna"):
        coluna_destino = "id_gerado"
    df_res[coluna_destino] = range(int(inicio), int(inicio) + len(df_res))
    return df_res

def aplicar_mascara_documento(df: pd.DataFrame, col: str, tipo: str) -> pd.DataFrame:
    """Aplica máscara de CPF ou CNPJ em dados existentes."""
    df_res = df.copy()

    def aplicar_cpf(val):
        val = "".join(filter(str.isdigit, str(val)))
        val = val.zfill(11)
        return f"{val[0:3]}.{val[3:6]}.{val[6:9]}-{val[9:11]}" if len(val) == 11 else val

    def aplicar_cnpj(val):
        val = "".join(filter(str.isdigit, str(val)))
        val = val.zfill(14)
        return f"{val[0:2]}.{val[2:5]}.{val[5:8]}/{val[8:12]}-{val[12:14]}" if len(val) == 14 else val

    df_res[col] = df_res[col].apply(aplicar_cpf if "CPF" in tipo else aplicar_cnpj)
    return df_res

def preencher_documentos_fakes(df: pd.DataFrame, col: str, tipo: str) -> pd.DataFrame:
    """Preenche uma coluna inteira com CPFs ou CNPJs válidos aleatórios."""
    if tipo == "CPF":
        df[col] = [gerar_cpf_valido() for _ in range(len(df))]
    else:
        df[col] = [gerar_cnpj_valido() for _ in range(len(df))]
    return df

def calcular_tempo_casa(df: pd.DataFrame, col_admissao: str) -> pd.DataFrame:
    """Calcula o tempo de casa em anos e meses desde a data de admissão até hoje."""
    df_res = df.copy()
    df_res[col_admissao] = pd.to_datetime(df_res[col_admissao], dayfirst=True, errors='coerce')
    hoje = pd.Timestamp.now().normalize()

    def diff_tempo(dt_adm):
        if pd.isna(dt_adm): return "N/A"
        diff = hoje - dt_adm
        anos = diff.days // 365
        meses = (diff.days % 365) // 30
        return f"{anos} anos e {meses} meses"

    df_res['tempo_casa_atual'] = df_res[col_admissao].apply(diff_tempo)
    return df_res

def aplicar_banding_salarial(df: pd.DataFrame, col_salario: str, faixas_str: str) -> pd.DataFrame:
    """Aplica faixas salariais com base em uma string de definição: '0-3000:Junior; 3000-6000:Pleno'."""
    df_res = df.copy()
    try:
        # Normalização do salário para numérico
        if df_res[col_salario].dtype == 'object':
            df_res[col_salario] = (
                df_res[col_salario].astype(str)
                .str.replace(r'[R\$\s\.€]', '', regex=True)
                .str.replace(',', '.', regex=False)
            )
        salarios = pd.to_numeric(df_res[col_salario], errors='coerce')

        # Parse das faixas
        faixas = []
        for item in faixas_str.split(';'):
            if not item.strip(): continue
            range_val, label = item.split(':')
            low, high = map(float, range_val.split('-'))
            faixas.append((low, high, label.strip()))

        def categorizar(val):
            if pd.isna(val): return "Não Informado"
            for low, high, label in faixas:
                if low <= val < high:
                    return label
            return "Fora de Faixa"

        df_res['faixa_salarial'] = salarios.apply(categorizar)
    except Exception as e:
        raise RuntimeError(f"Erro ao aplicar banding salarial: {e}")

    return df_res

def validar_compliance_rh(df: pd.DataFrame, col_data: str, col_doc: str) -> pd.DataFrame:
    """Valida se há datas futuras ou documentos com tamanho incorreto."""
    df_res = df.copy()
    hoje = pd.Timestamp.now().normalize()

    def check_compliance(row):
        erros = []
        # Validação Data
        dt = pd.to_datetime(row[col_data], dayfirst=True, errors='coerce')
        if pd.notnull(dt) and dt > hoje:
            erros.append("Data Futura")

        # Validação Documento (Simplificada: CPF 11, CNPJ 14)
        doc = str(row[col_doc])
        digits = "".join(filter(str.isdigit, doc))
        if len(digits) not in [11, 14]:
            erros.append("Doc Inválido")

        return ", ".join(erros) if erros else "OK"

    df_res['compliance_status'] = df_res.apply(check_compliance, axis=1)
    return df_res

def calcular_demissao_rh(df: pd.DataFrame, col_admissao: str, col_tempo: str, col_desligado: str, col_demissao: str) -> pd.DataFrame:
    """Calcula a data de demissão com base na admissão e tempo de casa."""
    df_res = df.copy()
    try:
        df_res[col_admissao] = pd.to_datetime(df_res[col_admissao], dayfirst=True, errors='coerce')
        tempo_limpo = df_res[col_tempo].astype(str).str.strip().str.replace(',', '.', regex=False)
        df_res[col_demissao] = pd.NaT

        for idx, row in df_res.iterrows():
            status = str(row[col_desligado]).strip().upper()
            if status in ['TRUE', '1', 'SIM', 'S', 'DESLIGADO']:
                dt_adm = df_res.loc[idx, col_admissao]
                tempo_val = tempo_limpo.loc[idx]

                if pd.notnull(dt_adm) and tempo_val != 'nan' and tempo_val != '':
                    if '.' not in tempo_val:
                        tempo_val = tempo_val + '.0'

                    partes = tempo_val.split('.')
                    qtd_anos = int(partes[0]) if partes[0].isdigit() else 0
                    qtd_meses = int(partes[1]) if partes[1].isdigit() else 0

                    meses_totais = (qtd_anos * 12) + qtd_meses
                    df_res.loc[idx, col_demissao] = dt_adm + pd.DateOffset(months=meses_totais)

        df_res[col_demissao] = pd.to_datetime(df_res[col_demissao]).dt.tz_localize(None)
    except Exception as e:
        raise RuntimeError(f"Erro no processamento do cálculo de demissão: {e}")

    return df_res

def processar_formatacoes_finais(df: pd.DataFrame, colunas_moeda: List[str], dict_moedas: Dict[str, str],
                                 colunas_data: List[str], dict_datas: Dict[str, str],
                                 col_demissao: Optional[str] = None,
                                 col_admissao: Optional[str] = None,
                                 calculo_rh_ativo: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Aplica as conversões finais de tipos e gera a configuração de colunas para o Streamlit.
    Esta função replica a lógica de loop final do arquivo original.
    """
    df_final = df.copy()
    columns_fmt = {}

    for coluna in df_final.columns:
        # Regra de Demissão
        if coluna == col_demissao and calculo_rh_ativo:
            columns_fmt[coluna] = "datetime" # Marcador para o UI Component
            df_final[coluna] = pd.to_datetime(df_final[coluna], errors='coerce')

        # Regra de Moeda
        elif coluna in colunas_moeda:
            if df_final[coluna].dtype == 'object':
                df_final[coluna] = (
                    df_final[coluna].astype(str)
                    .str.replace(r'[R\$\s\.€]', '', regex=True)
                    .str.replace(',', '.', regex=False)
                )
            df_final[coluna] = pd.to_numeric(df_final[coluna], errors='coerce')
            columns_fmt[coluna] = dict_moedas.get(coluna, 'R$ (Real - Brasil)')

        # Regra de Data
        elif coluna in colunas_data or (coluna == col_admissao and calculo_rh_ativo):
            df_final[coluna] = pd.to_datetime(df_final[coluna], dayfirst=True, errors='coerce')
            columns_fmt[coluna] = dict_datas.get(coluna, 'DD/MM/YYYY')

        # Tentativa de conversão numérica geral para colunas restantes
        else:
            # Segurança: Evita converter colunas que parecem ser IDs, CEPs ou Documentos para evitar perda de zeros à esquerda
            protected_keywords = {'cpf', 'cnpj', 'id', 'documento', 'cep', 'codigo', 'matricula'}
            if not any(key in coluna.lower() for key in protected_keywords):
                try:
                    if coluna != col_demissao:
                        df_final[coluna] = pd.to_numeric(df_final[coluna])
                except:
                    pass

    return df_final, columns_fmt

def exportar_para_excel(df: pd.DataFrame, colunas_moeda: List[str], dict_moedas: Dict[str, str],
                        colunas_data: List[str], dict_datas: Dict[str, str]) -> bytes:
    """Exporta o DataFrame para um buffer de bytes XLSX com formatações específicas."""
    df_download = df.copy()

    # Formatação de Datas para Excel
    for col in df_download.columns:
        if pd.api.types.is_datetime64_any_dtype(df_download[col]):
            fmt_excel_str = '%d/%m/%Y'
            # Pega o formato definido no dicionário se existir
            fmt_user = dict_datas.get(col, 'DD/MM/YYYY')
            if fmt_user == 'YYYY-MM-DD':
                fmt_excel_str = '%Y-%m-%d'
            elif fmt_user == 'DD/MM/YYYY HH:MM':
                fmt_excel_str = '%d/%m/%Y %H:%M'

            df_download[col] = df_download[col].dt.strftime(fmt_excel_str)
            df_download[col] = df_download[col].replace('NaT', '')

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_download.to_excel(writer, index=False, sheet_name='Dados Tratados')

        workbook = writer.book
        worksheet = writer.sheets['Dados Tratados']

        mapa_formatos_excel = {
            'R$ (Real - Brasil)': 'R$ #,##0.00;_R$ (#,##0.00);_R$ "-"_._;_(@_)',
            '$ (Dólar - EUA)': '"$"#,##0.00_-;[Red]("$"#,##0.00);"-"_._;_-@_-',
            '€ (Euro)': '[$€-2] #,##0.00;-[$€-2] #,##0.00;"-"??;_@_',
            'Apenas Decimal (1.250,00)': '#,##0.00'
        }

        for idx, col_name in enumerate(df_download.columns):
            if col_name in colunas_moeda:
                tipo_fmt_usuario = dict_moedas.get(col_name)
                if tipo_fmt_usuario in mapa_formatos_excel:
                    formato_excel_final = mapa_formatos_excel[tipo_fmt_usuario]
                    for row in range(2, len(df_download) + 2):
                        worksheet.cell(row=row, column=idx+1).number_format = formato_excel_final

    return buffer.getvalue()
