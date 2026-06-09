import pandas as pd
import numpy as np
import io
import random
from typing import List, Optional, Tuple, Dict, Any, Final

__all__ = [
    "validar_cpf",
    "validar_cnpj",
    "gerar_cpf_valido",
    "gerar_cnpj_valido",
    "detectar_outliers_iqr",
    "detectar_delimitador",
    "carregar_dados",
    "remover_duplicados",
    "tratar_nulos",
    "inserir_coluna",
    "limpar_espacos_fantasmas",
    "ajustar_caixa_texto",
    "gerar_ids_sequenciais",
    "aplicar_mascara_documento",
    "preencher_documentos_fakes",
    "aplicar_banding_salarial",
    "calcular_demissao_rh",
    "processar_formatacoes_finais",
    "exportar_para_excel",
    "calcular_tempo_casa_v2",
    "gerar_relatorio_rh",
    "validar_compliance_rh_v2",
]


# ===================== Validação e Geração de Documentos =====================

def validar_cpf(cpf: str) -> bool:
    """Valida um CPF verificando o formato e os dígitos verificadores."""
    cpf_limpo = "".join(filter(str.isdigit, str(cpf)))
    if len(cpf_limpo) != 11 or len(set(cpf_limpo)) == 1:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf_limpo[j]) * ((i + 1) - j) for j in range(i))
        resto = (soma * 10) % 11
        if resto == 10: resto = 0
        if resto != int(cpf_limpo[i]):
            return False
    return True

def validar_cnpj(cnpj: str) -> bool:
    """Valida um CNPJ verificando o formato e os dígitos verificadores."""
    cnpj_limpo = "".join(filter(str.isdigit, str(cnpj)))
    if len(cnpj_limpo) != 14 or len(set(cnpj_limpo)) == 1:
        return False
    pesos1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma1 = sum(int(cnpj_limpo[i]) * pesos1[i] for i in range(12))
    resto1 = soma1 % 11
    digito1 = 0 if resto1 < 2 else 11 - resto1
    if int(cnpj_limpo[12]) != digito1:
        return False
    pesos2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    soma2 = sum(int(cnpj_limpo[i]) * pesos2[i] for i in range(13))
    resto2 = soma2 % 11
    digito2 = 0 if resto2 < 2 else 11 - resto2
    return int(cnpj_limpo[13]) == digito2

def gerar_cpf_valido() -> str:
    """Gera um CPF válido aleatório formatado."""
    nine_digits = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum((len(nine_digits) + 1 - i) * v for i, v in enumerate(nine_digits)) % 11
        nine_digits.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, nine_digits[0:3]))}.{''.join(map(str, nine_digits[3:6]))}.{''.join(map(str, nine_digits[6:9]))}-{''.join(map(str, nine_digits[9:11]))}"

def gerar_cnpj_valido() -> str:
    """Gera um CNPJ válido aleatório formatado."""
    cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for _ in range(2):
        pesos = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2) if len(cnpj) == 12 else (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
        val = sum(pesos[i] * v for i, v in enumerate(cnpj)) % 11
        cnpj.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, cnpj[0:2]))}.{''.join(map(str, cnpj[2:5]))}.{''.join(map(str, cnpj[5:8]))}/{''.join(map(str, cnpj[8:12]))}-{''.join(map(str, cnpj[12:14]))}"


# ===================== Processamento de Dados =====================

def detectar_outliers_iqr(df: pd.DataFrame) -> Dict[str, int]:
    """Detecta outliers em colunas numéricas utilizando o método do Intervalo Interquartil (IQR)."""
    outliers_count = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        count = ((df[col] < (q1 - 1.5 * iqr)) | (df[col] > (q3 + 1.5 * iqr))).sum()
        if count > 0: outliers_count[col] = int(count)
    return outliers_count

def carregar_dados(file, **kwargs) -> pd.DataFrame:
    """Carrega dados com suporte a parâmetros dinâmicos."""
    if file.name.endswith('.xlsx'):
        sheet = kwargs.get('sheet_name', 0)
        return pd.read_excel(file, sheet_name=sheet)
    
    # Parâmetros para CSV
    sep = kwargs.get('sep', None)
    if sep == "Auto-Detectar": sep = detectar_delimitador(file)
    
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
            # Tenta converter, mas mantém original se falhar massivamente (proteção)
            converted = pd.to_numeric(df_copia[col], errors='coerce')
            if converted.notna().sum() > 0: # Só aplica se houver números
                df_copia[col] = converted.fillna(0)
        elif estrategia == "Preencher com 'Não Informado'":
            df_copia[col] = df_copia[col].fillna("Não Informado")
    if estrategia == "Excluir a linha inteira": df_copia = df_copia.dropna(subset=colunas)
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
    """Ajusta capitalização."""
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

def aplicar_banding_salarial(df: pd.DataFrame, col_salario: str, faixas_str: str) -> pd.DataFrame:
    """Aplica faixas salariais."""
    df_res = df.copy()
    try:
        salarios = pd.to_numeric(df_res[col_salario].astype(str).str.replace(r'[R\$\s\.€]', '', regex=True).str.replace(',', '.', regex=False), errors='coerce')
        faixas = []
        for item in faixas_str.split(';'):
            if not item.strip(): continue
            r, l = item.split(':')
            low, high = map(float, r.split('-'))
            faixas.append((low, high, l.strip()))
        def cat(v):
            if pd.isna(v): return "Não Informado"
            for low, high, label in faixas:
                if low <= v < high: return label
            return "Fora de Faixa"
        df_res['faixa_salarial'] = salarios.apply(cat)
    except Exception as e: raise RuntimeError(f"Erro ao aplicar banding salarial: {e}")
    return df_res

def calcular_demissao_rh(df: pd.DataFrame, col_adm: str, col_tempo: str, col_des: str, col_dem: str) -> pd.DataFrame:
    """Calcula data de demissão."""
    df_res = df.copy()
    try:
        df_res[col_adm] = pd.to_datetime(df_res[col_adm], dayfirst=True, errors='coerce')
        tempo_limpo = df_res[col_tempo].astype(str).str.strip().str.replace(',', '.', regex=False)
        df_res[col_dem] = pd.NaT
        for idx, row in df_res.iterrows():
            if str(row[col_des]).strip().upper() in ['TRUE', '1', 'SIM', 'S', 'DESLIGADO']:
                dt, t = df_res.loc[idx, col_adm], tempo_limpo.loc[idx]
                if pd.notnull(dt) and t != 'nan' and t != '':
                    partes = (t + '.0').split('.')
                    df_res.loc[idx, col_dem] = dt + pd.DateOffset(months=(int(partes[0])*12 + int(partes[1])))
        df_res[col_dem] = pd.to_datetime(df_res[col_dem]).dt.tz_localize(None)
    except Exception as e: raise RuntimeError(f"Erro no cálculo de demissão: {e}")
    return df_res

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
    """Exporta para Excel formatado com casting rigoroso."""
    df_d = df.copy()
    for c in df_d.columns:
        if pd.api.types.is_datetime64_any_dtype(df_d[c]):
            f_u = dict_datas.get(c, 'DD/MM/YYYY')
            df_d[c] = df_d[c].dt.strftime('%d/%m/%Y' if f_u == 'DD/MM/YYYY' else '%Y-%m-%d' if f_u == 'YYYY-MM-DD' else '%d/%m/%Y %H:%M').replace('NaT', '')
        elif c in col_moeda:
            # Força conversão para float para o Excel reconhecer como número real
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

def calcular_tempo_casa_v2(df: pd.DataFrame, col_adm: str, categorizar: bool = False) -> pd.DataFrame:
    """Calcula tempo de casa."""
    if col_adm not in df.columns: return df
    df_res, hoje = df.copy(), pd.Timestamp.now().normalize()
    df_res[col_adm] = pd.to_datetime(df_res[col_adm], dayfirst=True, errors='coerce')
    def calc(dt):
        if pd.isna(dt): return "N/A", None
        diff = hoje - dt
        y, m = diff.days // 365, (diff.days % 365) // 30
        cat = ("🔵 Junior" if y < 2 else "🟡 Pleno" if y < 5 else "🟢 Senior") if categorizar else None
        return f"{y} anos e {m} meses", cat
    res = df_res[col_adm].apply(calc)
    df_res['tempo_casa_atual'] = res.apply(lambda x: x[0])
    if categorizar: df_res['categoria_tempo'] = res.apply(lambda x: x[1])
    return df_res

def gerar_relatorio_rh(df: pd.DataFrame, tipo: str, col: str) -> pd.DataFrame:
    """Gera relatórios de RH."""
    try:
        if tipo == "Estatísticas Descritivas de Salário" and col:
            s = pd.to_numeric(df[col], errors='coerce')
            return pd.DataFrame({'Métrica': ['Mínimo', 'Q1', 'Mediana', 'Média', 'Q3', 'Máximo', 'Desvio'], 'Valor': [s.min(), s.quantile(0.25), s.median(), s.mean(), s.quantile(0.75), s.max(), s.std()]})
        if tipo == "Distribuição de Tempo de Casa" and col:
            diff = (pd.Timestamp.now() - pd.to_datetime(df[col], dayfirst=True, errors='coerce')).dt.days / 365
            dist = pd.cut(diff, bins=[0, 2, 5, 10, 999], labels=['<2 anos', '2-5 anos', '5-10 anos', '>10 anos']).value_counts().sort_index()
            return pd.DataFrame({'Faixa': dist.index, 'Quantidade': dist.values})
        return pd.DataFrame({'Status': ['Sem dados']})
    except Exception as e: return pd.DataFrame({'Erro': [str(e)]})

def validar_compliance_rh_v2(df: pd.DataFrame, col_data: str = None, col_doc: str = None, vals: List[str] = None) -> pd.DataFrame:
    """Validação de compliance."""
    err, hoje = [], pd.Timestamp.now().normalize()
    if "Datas Futuras/Inválidas" in vals and col_data:
        d = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce')
        q_f, q_i = (d > hoje).sum(), d.isna().sum()
        if q_f > 0: err.append({'Tipo': '📅 Datas Futuras', 'Quantidade': q_f, 'Severidade': '🔴 Alta'})
        if q_i > 0: err.append({'Tipo': '⚠️ Datas Inválidas', 'Quantidade': q_i, 'Severidade': '🟠 Média'})
    if "Documentos Inválidos (CPF/CNPJ)" in vals and col_doc:
        inv = (~df[col_doc].apply(lambda x: validar_cpf(x) or validar_cnpj(x))).sum()
        if inv > 0: err.append({'Tipo': '📄 Documentos Inválidos', 'Quantidade': inv, 'Severidade': '🟠 Média'})
    if "Duplicação de Documentos" in vals and col_doc:
        dup = df[df[col_doc].notna() & (df[col_doc] != '')][col_doc].duplicated(keep=False).sum()
        if dup > 0: err.append({'Tipo': '🔀 Documentos Duplicados', 'Quantidade': dup, 'Severidade': '🟡 Média'})
    if "Campos Obrigatórios Vazios" in vals:
        v = df.isna().sum().sum()
        if v > 0: err.append({'Tipo': '⚠️ Campos Vazios', 'Quantidade': v, 'Severidade': '🟡 Baixa'})
    return pd.DataFrame(err) if err else pd.DataFrame({'Status': ['✅ OK']})
