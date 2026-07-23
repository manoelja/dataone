"""Processamento e transformação de dados."""

import pandas as pd
import numpy as np
import io
from typing import List, Optional, Tuple, Dict, Any

from .validators import gerar_cpf_valido, gerar_cnpj_valido


__all__ = [
    "detectar_outliers_iqr",
    "carregar_dados",
    "listar_abas",
    "detectar_delimitador",
    "remover_duplicados",
    "tratar_nulos",
    "inserir_coluna",
    "limpar_espacos_fantasmas",
    "ajustar_caixa_texto",
    "gerar_ids_sequenciais",
    "aplicar_mascara_documento",
    "preencher_documentos_fakes",
    "processar_formatacoes_finais",
    "exportar_para_excel",
]


def detectar_outliers_iqr(df: pd.DataFrame) -> Dict[str, int]:
    """Detecta outliers em colunas numéricas utilizando o método do IQR."""
    outliers_count = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        count = ((df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))).sum()
        if count > 0: outliers_count[col] = int(count)
    return outliers_count


def carregar_dados(file, **kwargs) -> pd.DataFrame:
    """Carrega dados de Excel ou CSV com suporte a parâmetros dinâmicos."""
    if file.name.endswith('.xlsx'):
        sheet = kwargs.get('sheet_name', 0)
        return pd.read_excel(file, sheet_name=sheet)
    
    sep = kwargs.get('sep', None)
    if sep is None or sep == "Auto-Detectar":
        sep = detectar_delimitador(file)
    
    return pd.read_csv(
        file, 
        sep=sep, 
        decimal=kwargs.get('decimal', ','), 
        encoding=kwargs.get('encoding', 'utf-8')
    )


def listar_abas(file) -> List[str]:
    """Retorna a lista de abas de um arquivo Excel."""
    if not file.name.endswith('.xlsx'): return []
    try:
        xl = pd.ExcelFile(file)
        return xl.sheet_names
    except: return []


def detectar_delimitador(file) -> str:
    """Detecta automaticamente o delimitador de um arquivo CSV."""
    file.seek(0)
    sample = file.read(2048).decode('utf-8', errors='ignore')
    file.seek(0)
    delimiters, best_delimiter, max_cols = [';', ',', '\t', '|'], ';', 0
    for d in delimiters:
        cols = sample.split('\n')[0].count(d)
        if cols > max_cols: max_cols, best_delimiter = cols, d
    return best_delimiter


def remover_duplicados(df: pd.DataFrame, geral: bool, colunas_chave: List[str]) -> pd.DataFrame:
    """Remove linhas duplicadas."""
    if geral: df = df.drop_duplicates()
    if colunas_chave: df = df.drop_duplicates(subset=colunas_chave)
    return df


def tratar_nulos(df: pd.DataFrame, colunas: List[str], estrategia: str) -> pd.DataFrame:
    """Trata valores nulos com proteção de tipo."""
    df_copia = df.copy()
    for col in colunas:
        if estrategia == "Preencher com Zero (0)":
            converted = pd.to_numeric(df_copia[col], errors='coerce')
            if converted.notna().sum() > 0:
                df_copia[col] = converted.fillna(0)
            else:
                df_copia[col] = df_copia[col].fillna(0)
        elif estrategia == "Preencher com 'Não Informado'":
            df_copia[col] = df_copia[col].fillna("Não Informado")
    if estrategia == "Excluir a linha inteira":
        df_copia = df_copia.dropna(subset=colunas)
    return df_copia


def inserir_coluna(df: pd.DataFrame, nome: str, pos_direita: Optional[str], valor_padrao: Any) -> pd.DataFrame:
    """Insere nova coluna."""
    idx = df.columns.get_loc(pos_direita) if pos_direita in df.columns else len(df.columns)
    df.insert(idx, nome, valor_padrao)
    return df


def limpar_espacos_fantasmas(df: pd.DataFrame) -> pd.DataFrame:
    """Limpa espaços em branco."""
    for col in df.select_dtypes(include=['object']).columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def ajustar_caixa_texto(df: pd.DataFrame, colunas: List[str], modo: str) -> pd.DataFrame:
    """Ajusta capitalização de texto."""
    for c in colunas:
        if modo == "TUDO EM MAIÚSCULO": df[c] = df[c].astype(str).str.upper()
        elif modo == "tudo em minúsculo": df[c] = df[c].astype(str).str.lower()
        else: df[c] = df[c].astype(str).str.title()
    return df


def gerar_ids_sequenciais(df: pd.DataFrame, col: str, inicio: int) -> pd.DataFrame:
    """Gera IDs sequenciais."""
    df_res = df.copy()
    dest = "id_gerado" if col.startswith("Criar nova coluna") else col
    df_res[dest] = range(int(inicio), int(inicio) + len(df_res))
    return df_res


def aplicar_mascara_documento(df: pd.DataFrame, col: str, tipo: str) -> pd.DataFrame:
    """Aplica máscara de CPF/CNPJ."""
    def mask_cpf(v):
        v = "".join(filter(str.isdigit, str(v))).zfill(11)
        return f"{v[0:3]}.{v[3:6]}.{v[6:9]}-{v[9:11]}" if len(v) == 11 else v
    def mask_cnpj(v):
        v = "".join(filter(str.isdigit, str(v))).zfill(14)
        return f"{v[0:2]}.{v[2:5]}.{v[5:8]}/{v[8:12]}-{v[12:14]}" if len(v) == 14 else v
    df[col] = df[col].apply(mask_cpf if "CPF" in tipo else mask_cnpj)
    return df


def preencher_documentos_fakes(df: pd.DataFrame, col: str, tipo: str) -> pd.DataFrame:
    """Preenche com documentos fakes."""
    df[col] = [gerar_cpf_valido() if tipo == "CPF" else gerar_cnpj_valido() for _ in range(len(df))]
    return df


def processar_formatacoes_finais(df: pd.DataFrame, col_moeda: List[str], dict_moedas: Dict[str, str], col_data: List[str], dict_datas: Dict[str, str], col_dem: Optional[str] = None, col_adm: Optional[str] = None, rh_ativo: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Aplica conversões finais de tipos."""
    df_f, fmt = df.copy(), {}
    for c in df_f.columns:
        if c == col_dem and rh_ativo:
            fmt[c], df_f[c] = "datetime", pd.to_datetime(df_f[c], errors='coerce')
        elif c in col_moeda:
            df_f[c] = pd.to_numeric(df_f[c].astype(str).str.replace(r'[R\$\s\.€]', '', regex=True).str.replace(',', '.', regex=False), errors='coerce')
            fmt[c] = dict_moedas.get(c, 'R$ (Real - Brasil)')
        elif c in col_data or (c == col_adm and rh_ativo):
            df_f[c], fmt[c] = pd.to_datetime(df_f[c], dayfirst=True, errors='coerce'), dict_datas.get(c, 'DD/MM/YYYY')
        else:
            if not any(x in c.lower() for x in ['cpf', 'cnpj', 'id', 'documento', 'cep', 'codigo', 'matrícula']):
                try: df_f[c] = pd.to_numeric(df_f[c])
                except: pass
    return df_f, fmt


def exportar_para_excel(df: pd.DataFrame, col_moeda: List[str], dict_moedas: Dict[str, str], col_data: List[str], dict_datas: Dict[str, str]) -> bytes:
    """Exporta para Excel formatado."""
    df_d = df.copy()
    for c in df_d.columns:
        if pd.api.types.is_datetime64_any_dtype(df_d[c]):
            f_u = dict_datas.get(c, 'DD/MM/YYYY')
            df_d[c] = df_d[c].dt.strftime('%d/%m/%Y' if f_u == 'DD/MM/YYYY' else '%Y-%m-%d' if f_u == 'YYYY-MM-DD' else '%d/%m/%Y %H:%M').replace('NaT', '')
        elif c in col_moeda:
            df_d[c] = pd.to_numeric(df_d[c].astype(str).str.replace(r'[R\$\s\.€]', '', regex=True).str.replace(',', '.', regex=False), errors='coerce')
    
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df_d.to_excel(writer, index=False, sheet_name='Dados Tratados')
        ws = writer.sheets['Dados Tratados']
        map_f = {'R$ (Real - Brasil)': 'R$ #,##0.00', '$ (Dólar - EUA)': '"$"#,##0.00', '€ (Euro)': '[$€-2] #,##0.00', 'Apenas Decimal (1.250,00)': '#,##0.00'}
        for i, col in enumerate(df_d.columns):
            if col in col_moeda:
                fmt_key = dict_moedas.get(col)
                if fmt_key in map_f:
                    for r in range(2, len(df_d) + 2): 
                        cell = ws.cell(row=r, column=i+1)
                        if cell.value is not None:
                            cell.number_format = map_f[fmt_key]
    return buf.getvalue()
