"""Ferramentas específicas de RH (cálculos salariais, tempo de casa, compliance)."""

import pandas as pd
from typing import List, Optional, Tuple, Any

from .validators import validar_cpf, validar_cnpj


__all__ = [
    "aplicar_banding_salarial",
    "calcular_demissao_rh",
    "calcular_tempo_casa_v2",
    "gerar_relatorio_rh",
    "validar_compliance_rh_v2",
]


def aplicar_banding_salarial(df: pd.DataFrame, col_salario: str, faixas_str: str) -> pd.DataFrame:
    """Aplica faixas salariais baseado em regras definidas."""
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
    """Calcula data de demissão baseado no tempo de casa."""
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


def calcular_tempo_casa_v2(df: pd.DataFrame, col_adm: str, categorizar: bool = False) -> pd.DataFrame:
    """Calcula tempo de casa dos funcionários."""
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
    """Validação de compliance de dados de RH."""
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
