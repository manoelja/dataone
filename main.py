"""
DATAONE — Central Inteligente de Data processing.
Consolidado em arquitetura Flat.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import pandas as pd
import streamlit as st

import processing
import ui_components


# ===================== Gestão de Estado =====================

NAMESPACE: str = "data"

@dataclass
class AppState:
    df_original: pd.DataFrame
    df_tratado: pd.DataFrame
    audit_log: List[str] = field(default_factory=list)
    ultimo_id_arquivo: Optional[str] = None
    config_importacao: Dict[str, Any] = field(default_factory=dict)

def get_state() -> AppState:
    if NAMESPACE not in st.session_state:
        st.session_state[NAMESPACE] = AppState(df_original=pd.DataFrame(), df_tratado=pd.DataFrame())
    return st.session_state[NAMESPACE]

def init_state(df: pd.DataFrame, file_id: str, config: Dict[str, Any] = None) -> AppState:
    state = AppState(df_original=df.copy(), df_tratado=df.copy(), ultimo_id_arquivo=file_id, config_importacao=config or {})
    st.session_state[NAMESPACE] = state
    return state

def registrar_log(state: AppState, mensagem: str) -> None:
    state.audit_log.append(mensagem)

def pop_action(key: str) -> Optional[Any]:
    if key in st.session_state:
        value = st.session_state[key]
        del st.session_state[key]
        return value
    return None


# ===================== Processamento de Ações =====================

def aplicar_acao_limpeza(action: tuple, df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    tipo, *args = action
    if tipo == "remover_dup":
        return processing.remover_duplicados(df, args[0], args[1]), f"🧼 Duplicados removidos (Geral: {args[0]}, Chaves: {args[1]})."
    if tipo == "tratar_nulos":
        return processing.tratar_nulos(df, args[0], args[1]), f"🧼 Valores nulos tratados em {args[0]} via {args[1]}."
    if tipo == "excluir_coluna":
        cols = args[0]
        return df.drop(columns=cols), f"❌ Coluna(s) {cols} excluída(s)."
    if tipo == "inserir_coluna":
        return processing.inserir_coluna(df, args[0], args[1], args[2]), f"➕ Coluna '{args[0]}' inserida."
    if tipo == "strip_all":
        return processing.limpar_espacos_fantasmas(df), "🧼 Espaços em branco removidos."
    return df, "Ação desconhecida"

def aplicar_acao_texto(action: tuple, df: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    tipo, *args = action
    if tipo == "caixa_texto":
        return processing.ajustar_caixa_texto(df, args[0], args[1]), f"🔤 Caixa ajustada para {args[1]}."
    if tipo == "gerar_ids":
        return processing.gerar_ids_sequenciais(df, args[0], args[1]), f"🆔 IDs gerados em '{args[0]}'."
    if tipo == "mascara_doc":
        return processing.aplicar_mascara_documento(df, args[0], args[1]), f"🔤 Máscara de {args[1]} aplicada."
    if tipo == "fake_docs":
        return processing.preencher_documentos_fakes(df, args[0], args[1]), f"🎲 Documentos fakes gerados."
    return df, "Ação desconhecida"

def aplicar_acao_rh(action: tuple, df: pd.DataFrame) -> Tuple[pd.DataFrame, Any, str]:
    tool = action[0]
    p = action[1:]
    if tool == "tempo_casa":
        return processing.calcular_tempo_casa_v2(df, p[0], p[1] if len(p)>1 else False), None, f"🛠️ Tempo de casa calculado."
    if tool == "analise":
        return df, processing.gerar_relatorio_rh(df, p[0], p[1]), f"📊 Relatório de {p[0]} gerado."
    if tool == "banding":
        return processing.aplicar_banding_salarial(df, p[0], p[1]), None, f"🛠️ Banding salarial aplicado."
    if tool == "compliance":
        return df, processing.validar_compliance_rh_v2(df, p[0], p[1], p[2]), f"🛠️ Validação de compliance executada."
    if tool == "demissao":
        return processing.calcular_demissao_rh(df, *p), None, f"🛠️ Cálculo de demissão aplicado."
    return df, None, "Ação desconhecida"


# ===================== Helpers da UI =====================

@st.cache_data(ttl=600)
def _load_cached(f, **kwargs) -> pd.DataFrame:
    return processing.carregar_dados(f, **kwargs)

def _processar_action_limpeza(state_obj: AppState) -> None:
    action = pop_action("action_limpeza")
    if action:
        state_obj.df_tratado, msg = aplicar_acao_limpeza(action, state_obj.df_tratado)
        registrar_log(state_obj, msg)
        st.success("Ação aplicada!")
        st.rerun()

def _processar_action_texto(state_obj: AppState) -> None:
    action = pop_action("action_texto")
    if action:
        state_obj.df_tratado, msg = aplicar_acao_texto(action, state_obj.df_tratado)
        registrar_log(state_obj, msg)
        st.rerun()

def _processar_action_rh(state_obj: AppState) -> None:
    action = pop_action("action_rh")
    if action:
        df_n, extra, msg = aplicar_acao_rh(action, state_obj.df_tratado)
        state_obj.df_tratado = df_n
        registrar_log(state_obj, msg)
        if action[0] == "analise" or action[0] == "compliance": st.dataframe(extra, hide_index=True)
        else: st.success("Ação concluída!")
        st.rerun()


# ===================== Main =====================

def main():
    st.set_page_config(page_title="DATAONE", page_icon="🎲", layout="wide")
    
    # Estados de UI
    if "show_developer" not in st.session_state:
        st.session_state.show_developer = False
    
    state = get_state()
    
    with st.sidebar:
        st.header("📥 Entrada de Dados")
        file_upload = st.file_uploader("Upload:", type=["xlsx", "csv"])
        
        config_atual = {}
        if file_upload:
            st.divider()
            if file_upload.name.endswith('.csv'):
                st.subheader("⚙️ Configurações CSV")
                config_atual['sep'] = st.selectbox("Separador:", ["Auto-Detectar", ";", ",", "\\t", "|"])
                config_atual['encoding'] = st.selectbox("Encoding:", ["utf-8", "latin-1", "iso-8859-1"])
                config_atual['decimal'] = st.selectbox("Decimal:", [",", "."])
            else:
                st.subheader("⚙️ Configurações Excel")
                abas = processing.listar_abas(file_upload)
                config_atual['sheet_name'] = st.selectbox("Selecionar Aba:", options=abas) if abas else 0
            
            if st.button("🔄 Aplicar Configurações"):
                state.ultimo_id_arquivo = None # Força recarregamento
                st.rerun()

        st.divider()
        st.header("🔍 Histórico")
        if state.audit_log:
            for log in reversed(state.audit_log): st.caption(log)
        else: st.caption("Nenhuma ação realizada.")

    ui_components.render_header()

    if not file_upload:
        st.info("👋 Faça upload de um arquivo para começar.")
        return

    # Gerar ID único considerando nome, tamanho e configurações de importação
    id_f = f"{file_upload.name}_{file_upload.size}_{str(config_atual)}"
    
    if state.ultimo_id_arquivo != id_f:
        try:
            df_novo = processing.carregar_dados(file_upload, **config_atual)
            init_state(df_novo, id_f, config_atual)
            st.rerun()
        except Exception as e:
            st.error(f"❌ Erro ao carregar arquivo: {e}")
            return

    # Header de informações rápidas
    tipo_icon = "📄 CSV" if file_upload.name.endswith('.csv') else "📗 Excel"
    st.info(f"📊 **{tipo_icon} Ativo:** {len(state.df_tratado)} registros | {len(state.df_tratado.columns)} colunas")

    if st.button("🔄 Resetar tudo"):
        state.df_tratado = state.df_original.copy()
        st.rerun()

    tabs = st.tabs(["🔍 Diagnóstico", "🧼 Limpeza", "🔤 Texto", "⚙️ Formatação", "📊 Analysis", "📑 Fórmulas Excel", "💾 Exportar"])
    with tabs[0]: ui_components.render_diagnostico_tab(state.df_tratado)
    with tabs[1]:
        ui_components.render_limpeza_tab(state.df_tratado, id_f)
        _processar_action_limpeza(state)
    with tabs[2]:
        ui_components.render_texto_tab(state.df_tratado)
        _processar_action_texto(state)
    with tabs[3]: ui_components.render_formatacao_tab(state.df_tratado)
    with tabs[4]:
        ui_components.render_analysis_tab(state.df_tratado)
        _processar_action_rh(state)
    with tabs[5]:
        ui_components.render_formulas_tab()
    with tabs[6]:
        col_m, dict_m = st.session_state.get("ctrl_moeda", []), st.session_state.get("config_moedas", {})
        col_d, dict_d = st.session_state.get("ctrl_data", []), st.session_state.get("config_datas", {})
        df_f, fmt = processing.processar_formatacoes_finais(state.df_tratado, col_m, dict_m, col_d, dict_d)
        ui_components.render_export_tab(df_f, ui_components.get_column_config(df_f.columns.tolist(), fmt))
        st.download_button("📥 Baixar Excel", processing.exportar_para_excel(df_f, col_m, dict_m, col_d, dict_d), "dataone_export.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    ui_components.render_footer()

if __name__ == "__main__":
    main()
