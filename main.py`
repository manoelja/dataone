import streamlit as st
import pandas as pd
import processing
import ui_components

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title='DATAONE', page_icon='🎲', layout='wide')

def registrar_log(mensagem: str):
    """Registra ações no histórico de auditoria da sessão."""
    if 'audit_log' not in st.session_state:
        st.session_state['audit_log'] = []
    st.session_state['audit_log'].append(mensagem)

def main():
    ui_components.render_header()

    # SIDEBAR: Upload e Logs
    # Passamos a função de upload para o componente de UI
    file_upload = ui_components.render_sidebar(
        file_upload_func=lambda: st.file_uploader('Faça upload do seu arquivo:', type=['xlsx', 'csv']),
        audit_log=st.session_state.get('audit_log', [])
    )

    if not file_upload:
        st.info("👋 Bem-vindo ao DATAONE! Por favor, faça upload de um arquivo para começar.")
        return

    # 2. GERENCIAMENTO DE ARQUIVO E ESTADO INICIAL
    id_arquivo_atual = f"{file_upload.name}_{file_upload.size}"

    if "ultimo_id_arquivo" not in st.session_state or st.session_state["ultimo_id_arquivo"] != id_arquivo_atual:
        # Novo arquivo carregado ou alterado: Reset de estado
        st.session_state["ultimo_id_arquivo"] = id_arquivo_atual

        # Carregamento com Cache
        @st.cache_data(ttl=600)
        def _load_cached(f):
            return processing.carregar_dados(f)

        df_original = _load_cached(file_upload)
        st.session_state['df_original'] = df_original
        st.session_state['df_tratado'] = df_original.copy()

        # Limpeza de chaves antigas de UI
        chaves_para_limpar = [
            "nome_da_nova_coluna_clean", "txt_padrao_input_clean",
            "coluna_deletar_clean", "col_esquerda_pos",
            "col_direita_pos", "tipo_val_padrao_clean",
            "action_limpeza", "action_texto", "action_rh"
        ]
        for chave in chaves_para_limpar:
            if chave in st.session_state:
                del st.session_state[chave]

        registrar_log(f"📥 Arquivo '{file_upload.name}' carregado.")
        st.rerun()

    df_original = st.session_state['df_original']
    df_tratado = st.session_state['df_tratado']

    # Botão de Reset
    if st.button("🔄 Resetar todas as alterações", type="secondary"):
        st.session_state['df_tratado'] = df_original.copy()
        registrar_log("🔄 Base de dados resetada para o formato original.")
        st.success("Tabela resetada com sucesso!")
        st.rerun()

    # 3. SISTEMA DE ABAS (WIZARD)
    aba_diag, aba_limpeza, aba_texto, aba_format, aba_rh, aba_export = st.tabs([
        "🔍 1. Diagnóstico", "🧼 2. Limpeza de Dados", "🔤 3. Padronização de Texto",
        "⚙️ 4. Formatação Visual", "🛠️ 5. Regras de RH", "💾 6. Exportar Base"
    ])

    # --- ABA 1: DIAGNÓSTICO ---
    with aba_diag:
        ui_components.render_diagnostico_tab(df_tratado)

    # --- ABA 2: LIMPEZA ---
    with aba_limpeza:
        ui_components.render_limpeza_tab(df_tratado, id_arquivo_atual)

        # Processamento de ações de limpeza
        if 'action_limpeza' in st.session_state:
            action, *args = st.session_state['action_limpeza']
            if action == 'remover_dup':
                geral, chaves = args
                st.session_state['df_tratado'] = processing.remover_duplicados(df_tratado, geral, chaves)
                registrar_log(f"🧼 Duplicados removidos (Geral: {geral}, Chaves: {chaves}).")
            elif action == 'tratar_nulos':
                cols, est = args
                st.session_state['df_tratado'] = processing.tratar_nulos(df_tratado, cols, est)
                registrar_log(f"🧼 Valores nulos tratados em {cols} via {est}.")
            elif action == 'excluir_coluna':
                col = args[0]
                st.session_state['df_tratado'] = st.session_state['df_tratado'].drop(columns=[col])
                registrar_log(f"❌ Coluna '{col}' excluída.")
            elif action == 'inserir_coluna':
                nome, dir, val = args
                st.session_state['df_tratado'] = processing.inserir_coluna(df_tratado, nome, dir, val)
                registrar_log(f"➕ Coluna '{nome}' inserida.")
            elif action == 'strip_all':
                st.session_state['df_tratado'] = processing.limpar_espacos_fantasmas(df_tratado)
                registrar_log("🧼 Espaços em branco removidos de todas as colunas.")

            del st.session_state['action_limpeza']
            st.success("Ação aplicada com sucesso!")
            st.rerun()

    # --- ABA 3: TEXTO ---
    with aba_texto:
        ui_components.render_texto_tab(df_tratado)

        if 'action_texto' in st.session_state:
            action, *args = st.session_state['action_texto']
            if action == 'caixa_texto':
                cols, modo = args
                st.session_state['df_tratado'] = processing.ajustar_caixa_texto(df_tratado, cols, modo)
                registrar_log(f"🔤 Caixa de texto ajustada para {modo} nas colunas {cols}.")
            elif action == 'gerar_ids':
                col, inicio = args
                st.session_state['df_tratado'] = processing.gerar_ids_sequenciais(df_tratado, col, inicio)
                registrar_log(f"🆔 IDs sequenciais gerados em '{col}' a partir de {inicio}.")
            elif action == 'mascara_doc':
                col, tipo = args
                st.session_state['df_tratado'] = processing.aplicar_mascara_documento(df_tratado, col, tipo)
                registrar_log(f"🔤 Máscara de {tipo} aplicada na coluna {col}.")
            elif action == 'fake_docs':
                col, tipo = args
                st.session_state['df_tratado'] = processing.preencher_documentos_fakes(df_tratado, col, tipo)
                registrar_log(f"🎲 Coluna {col} preenchida com {tipo}s fakes.")

            del st.session_state['action_texto']
            st.success("Ação aplicada com sucesso!")
            st.rerun()

    # --- ABA 4: FORMATAÇÃO ---
    with aba_format:
        ui_components.render_formatacao_tab(df_tratado)

    # --- ABA 5: RH ---
    with aba_rh:
        ui_components.render_rh_tab(df_tratado)

        if 'action_rh' in st.session_state:
            params = st.session_state['action_rh'] # (adm, tempo, deslig, demissao)
            try:
                st.session_state['df_tratado'] = processing.calcular_demissao_rh(df_tratado, *params)
                registrar_log(f"🛠️ Cálculo de demissão aplicado na coluna {params[3]}.")
                st.success("Cálculo de RH aplicado com sucesso!")
            except Exception as e:
                st.error(str(e))

            del st.session_state['action_rh']
            st.rerun()

    # 4. PROCESSAMENTO FINAL DE FORMATOS E VISUALIZAÇÃO
    # Recupecamos as configurações de UI para aplicar a tipagem final
    col_moedas = st.session_state.get('ctrl_moeda', [])
    dict_moedas = st.session_state.get('config_moedas', {})
    col_datas = st.session_state.get('ctrl_data', [])
    dict_datas = st.session_state.get('config_datas', {})

    # Parâmetros de RH para o processador final
    col_adm = st.session_state.get('sb_admissao', 'Não aplicar...')
    col_dem = st.session_state.get('sb_demissao', 'Não aplicar...')
    if col_dem == 'Criar nova coluna': col_dem = 'data_demissao_calculada'

    rh_ativo = (col_adm != 'Não aplicar...' and
                st.session_state.get('sb_tempo', 'Não aplicar...') != 'Não aplicar...' and
                st.session_state.get('sb_desligado', 'Não aplicar...') != 'Não aplicar...')

    # Aqui aplicamos a "limpeza" final de tipos que o original fazia no loop
    df_final, fmt_map = processing.processar_formatacoes_finais(
        df_tratado, col_moedas, dict_moedas, col_datas, dict_datas,
        col_demissao=col_dem, col_admissao=col_adm, calculo_rh_ativo=rh_ativo
    )

    # Converte o mapa de strings do processing para objetos do Streamlit
    column_config = ui_components.get_column_config(df_final.columns.tolist(), fmt_map)

    # --- ABA 6: EXPORTAR ---
    with aba_export:
        ui_components.render_export_tab(df_final, column_config)

        # Botão de Download (Lógica de buffer)
        excel_data = processing.exportar_para_excel(df_final, col_moedas, dict_moedas, col_datas, dict_datas)
        st.download_button(
            label="📥 Baixar Base de Dados Tratada e Formatada",
            data=excel_data,
            file_name="base_dados_clean_pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

if __name__ == "__main__":
    main()
