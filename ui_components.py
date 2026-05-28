import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Tuple

def render_header():
    """Renderiza o cabeçalho da aplicação."""
    st.markdown("""
    # 🎲 DATAONE <span style='font-size: 18px; color: #888;'>| Central Inteligente de Data processing</span>
    ##### Faça upload, limpe, padronize, aplique regras de negócio e exporte seus dados sem planilhas quebradas.
    ---
    """, unsafe_allow_html=True)

def render_sidebar(file_upload_func, audit_log: List[str]):
    """Renderiza a barra lateral com upload e histórico."""
    with st.sidebar:
        st.header("📥 Entrada de Dados")
        file_upload = file_upload_func()

        st.divider()
        st.header("🔍Histórico🌐")
        if audit_log:
            for log in reversed(audit_log):
                st.caption(log)
        else:
            st.caption("Nenhuma ação realizada ainda.")
        return file_upload

def get_column_config(df_columns: List[str], fmt_map: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte o mapa de formatos simplificado do processing.py
    para os objetos st.column_config.
    """
    config = {}
    for col in df_columns:
        fmt = fmt_map.get(col)
        if not fmt:
            continue

        if fmt == "datetime":
            config[col] = st.column_config.DatetimeColumn(col, format="DD/MM/YYYY")
        elif fmt == 'R$ (Real - Brasil)':
            config[col] = st.column_config.NumberColumn(col, format="R$ %,.2f")
        elif fmt == '$ (Dólar - EUA)':
            config[col] = st.column_config.NumberColumn(col, format="$ %,.2f")
        elif fmt == '€ (Euro)':
            config[col] = st.column_config.NumberColumn(col, format="€ %,.2f")
        elif fmt == 'Apenas Decimal (1.250,00)':
            config[col] = st.column_config.NumberColumn(col, format="%,.2f")
        elif fmt in ['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM']:
            config[col] = st.column_config.DatetimeColumn(col, format=fmt)
    return config

def render_diagnostico_tab(df: pd.DataFrame):
    """Aba 1: Diagnóstico do Arquivo."""
    st.subheader("🔍 Análise de Saúde dos Dados")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Linhas", df.shape[0])
    m2.metric("Total de Colunas", df.shape[1])
    m3.metric("Células Vazias", df.isna().sum().sum())

    linhas_duplicadas = df.duplicated().sum()
    if linhas_duplicadas > 0:
        m4.metric("Linhas Duplicadas", linhas_duplicadas, delta=f"-{linhas_duplicadas} alertas", delta_color="inverse")
    else:
        m4.metric("Linhas Duplicadas", 0)

    st.divider()

    # --- Nova Seção: Detecção de Outliers ---
    import processing
    outliers = processing.detectar_outliers_iqr(df)
    if outliers:
        with st.expander("⚠️ Alerta de Outliers (Anomalias Numéricas)", expanded=True):
            st.warning("Foram detectados valores atípicos que podem distorcer a análise.")
            outlier_df = pd.DataFrame(list(outliers.items()), columns=['Coluna', 'Qtd de Outliers'])
            st.table(outlier_df)
    else:
        st.success("✅ Nenhuma anomalia numérica significativa detectada.")

    st.markdown("### Perfil de Metadados por Coluna")

    df_tipos = pd.DataFrame({
        'Coluna': df.columns,
        'Tipo Nativo': df.dtypes.astype(str),
        'Valores Preenchidos (%)': ((df.notna().sum() / len(df)) * 100).round(1) if len(df) > 0 else 0,
        'Valores Nulos (Qtd)': df.isna().sum()
    })

    mapa_tipos = {
        'object': 'Texto / Categoria',
        'int64': 'Número Inteiro',
        'float64': 'Número Decimal',
        'datetime64[ns]': 'Data / Hora',
        'bool': 'Lógico (V/F)'
    }
    df_tipos['Tipo Simplificado'] = df_tipos['Tipo Nativo'].map(mapa_tipos).fillna(df_tipos['Tipo Nativo'])

    st.dataframe(
        df_tipos[['Coluna', 'Tipo Simplificado', 'Valores Preenchidos (%)', 'Valores Nulos (Qtd)']],
        hide_index=True,
        use_container_width=True
    )

def render_limpeza_tab(df: pd.DataFrame, id_arquivo: str):
    """Aba 2: Limpeza de Dados."""
    st.subheader("🧼 Tratamento de Anomalias e Nulos")

    col_limp_1, col_limp_2 = st.columns(2)

    with col_limp_1:
        st.markdown("#### Remover Duplicados")
        remover_dup_geral = st.checkbox("Remover linhas 100% idênticas na tabela", value=False, key=f"dup_geral_{id_arquivo}")
        ccolunas_chave_dup = st.multiselect("Ou escolher colunas-chave para checar duplicidade (Ex: CPF, ID):", options=df.columns, key=f"dup_chave_{id_arquivo}")

        if st.button("Remover Duplicados", key=f"btn_dup_{id_arquivo}"):
            if remover_dup_geral or ccolunas_chave_dup:
                st.session_state['action_limpeza'] = ('remover_dup', remover_dup_geral, ccolunas_chave_dup)
            else:
                st.error("⚠️ Por favor, selecione a opção 'Geral' ou escolha colunas-chave.")

    with col_limp_2:
        st.markdown("#### Tratar Valores Faltantes (Nulos)")
        st.markdown("Tratar os valores vazios é essencial para evitar erros ")

        chave_controle = f"selecionadas_{id_arquivo}"
        if chave_controle not in st.session_state:
            st.session_state[chave_controle] = []

        colunas_nulas = st.multiselect(
            "Selecione colunas para tratar valores vazios:",
            options=df.columns,
            default=st.session_state[chave_controle],
            key=f"nulos_cols_{id_arquivo}"
        )
        st.session_state[chave_controle] = colunas_nulas

        if colunas_nulas:
            estrategia_nulos = st.radio(
                "O que fazer com os vazios dessas colunas?",
                options=["Preencher com Zero (0)", "Preencher com 'Não Informado'", "Excluir a linha inteira"],
                key=f"estrategia_nulos_{id_arquivo}"
            )

            if st.button("Aplicar Tratamento de Nulos", key=f"btn_nulos_{id_arquivo}"):
                st.session_state['action_limpeza'] = ('tratar_nulos', colunas_nulas, estrategia_nulos)

    st.divider()
    st.markdown("#### 🔗 Mesclar Arquivos (Join)")
    with st.expander("Unir esta base com outro arquivo", expanded=False):
        secondary_file = st.file_uploader("Faça upload do arquivo secundário:", type=['xlsx', 'csv'], key=f"merge_file_{id_arquivo}")

        if secondary_file:
            # Carregamento temporário para pegar as colunas
            import processing
            df_sec = processing.carregar_dados(secondary_file)
            st.session_state[f'df_sec_{id_arquivo}'] = df_sec

            c_k1, c_k2 = st.columns(2)
            with c_k1:
                key1 = st.selectbox("Coluna de ligação (Base Principal):", options=df.columns, key=f"key1_{id_arquivo}")
            with c_k2:
                key2 = st.selectbox("Coluna de ligação (Base Secundária):", options=df_sec.columns, key=f"key2_{id_arquivo}")

            if st.button("Mesclar Bases de Dados", type="primary", key=f"btn_merge_{id_arquivo}"):
                st.session_state['action_merge'] = (secondary_file, key1, key2)

    st.divider()
    st.markdown("#### ❌ Excluir Coluna da Tabela")
    coluna_para_excluir = st.selectbox(
        "Selecione a coluna que deseja remover permanentemente:",
        options=["Selecione..."] + list(df.columns),
        key=f"coluna_deletar_{id_arquivo}"
    )
    if st.button("Remover Coluna Permanentemente", type="primary", key=f"btn_excluir_{id_arquivo}"):
        if coluna_para_excluir != "Selecione...":
            st.session_state['action_limpeza'] = ('excluir_coluna', coluna_para_excluir, None)
        else:
            st.error("⚠️ Por favor, selecione uma coluna válida para exclusão.")

    st.divider()
    st.markdown("#### ➕ Inserir Nova Coluna Entre Duas Existentes")
    nome_nova_coluna = st.text_input("Digite o nome da nova coluna:", placeholder="Ex: status_pagamento...", key=f"nome_da_nova_coluna_clean_{id_arquivo}")

    c_pos1, c_pos2 = st.columns(2)
    with c_pos1:
        col_esquerda = st.selectbox("Coluna da Esquerda (X):", options=list(df.columns), key=f"col_esquerda_pos_{id_arquivo}")
    with c_pos2:
        idx_esq_atual = list(df.columns).index(col_esquerda)
        opcoes_direita = list(df.columns)[idx_esq_atual + 1:]
        if opcoes_direita:
            col_direita = st.selectbox("Coluna da Direita (Y):", options=opcoes_direita, key=f"col_direita_pos_{id_arquivo}")
        else:
            st.caption("⚠️ Não há colunas depois desta.")
            col_direita = None

    tipo_valor_padrao = st.selectbox(
        "Valor inicial da nova coluna:",
        options=["Em branco (Vazio)", "Número Zero (0)", "Texto Customizado"],
        key=f"tipo_val_padrao_clean_{id_arquivo}"
    )

    valor_padrao = ""
    if tipo_valor_padrao == "Número Zero (0)":
        valor_padrao = 0
    elif tipo_valor_padrao == "Texto Customizado":
        valor_padrao = st.text_input("Digite o texto padrão para todas as linhas:", value="Padrão", key=f"txt_padrao_input_clean_{id_arquivo}")

    if st.button("Inserir Coluna no Meio", key=f"btn_inserir_{id_arquivo}"):
        if nome_nova_coluna.strip() == "":
            st.error("⚠️ Por favor, digite um nome válido para a coluna.")
        elif nome_nova_coluna in df.columns:
            st.error("⚠️ Já existe uma coluna com esse nome na tabela.")
        else:
            st.session_state['action_limpeza'] = ('inserir_coluna', nome_nova_coluna, col_direita, valor_padrao)

    st.divider()
    st.markdown("#### 🧼 Faxina Invisível Automática")
    if st.button("Aparar espaços em branco fantasmas (Strip) de todas as células de texto", key=f"btn_strip_{id_arquivo}"):
        st.session_state['action_limpeza'] = ('strip_all', True, None)

    st.divider()
    st.markdown("##### 📊 Visualização Parcial ")
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_texto_tab(df: pd.DataFrame):
    """Aba 3: Padronização de Texto."""
    st.subheader("🔤 Formatação de Strings e Cadastro")

    c_txt1, c_txt2 = st.columns(2)
    with c_txt1:
        st.markdown("#### Caixa do Texto")
        cols_caixa = st.multiselect("Selecionar colunas para ajustar LETRAS:", options=df.columns, key='txt_caixa')
        if cols_caixa:
            modo_caixa = st.selectbox("Formato desejado:", ["TUDO EM MAIÚSCULO", "tudo em minúsculo", "Primeira Letra Maiúscula (Capitalize)"])
            if st.button("Ajustar Caixa de Texto"):
                st.session_state['action_texto'] = ('caixa_texto', cols_caixa, modo_caixa)

    with c_txt2:
        st.markdown("#### 🆔 Gerador de ID Sequencial")
        col_id_destino = st.selectbox("Escolha uma coluna para substituir por IDs (ou criar uma nova):",
                                      options=["Criar nova coluna 'id_gerado'"] + list(df.columns))
        valor_inicio = st.number_input("Iniciar contagem a partir de:", min_value=0, value=1, step=1)
        if st.button("Gerar Sequência de IDs"):
            st.session_state['action_texto'] = ('gerar_ids', col_id_destino, valor_inicio)

    st.divider()
    st.markdown("#### 🇧🇷 Máscaras e Geradores de Documentos")
    acao_doc = st.selectbox("O que deseja fazer com os documentos?",
                            options=["Apenas aplicar máscara em dados existentes", "Substituir tudo por CPFs Válidos Aleatórios", "Substituir tudo por CNPJs Válidos Aleatórios"])

    col_doc = st.selectbox("Selecione a coluna alvo:", ["Selecione..."] + list(df.columns), key='col_doc_alvo')

    if col_doc != "Selecione...":
        if acao_doc == "Apenas aplicar máscara em dados existentes":
            tipo_doc = st.selectbox("Tipo de documento cadastrado:", ["CPF (11 dígitos)", "CNPJ (14 dígitos)"])
            if st.button("Aplicar Máscara"):
                st.session_state['action_texto'] = ('mascara_doc', col_doc, tipo_doc)
        elif acao_doc == "Substituir tudo por CPFs Válidos Aleatórios":
            if st.button("Gerar CPFs Fake Válidos"):
                st.session_state['action_texto'] = ('fake_docs', col_doc, "CPF")
        elif acao_doc == "Substituir tudo por CNPJs Válidos Aleatórios":
            if st.button("Gerar CNPJs Fake Válidos"):
                st.session_state['action_texto'] = ('fake_docs', col_doc, "CNPJ")

    st.divider()
    st.markdown("##### 📊 Visualização Parcial (Pós Padronização de Texto)")
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_formatacao_tab(df: pd.DataFrame):
    """Aba 4: Formatação Visual."""
    st.subheader("⚙️ Configurações Visuais de Exibição")
    c_moeda_sel, c_data_sel = st.columns(2)

    dict_formatos_moeda = {}
    dict_formatos_data = {}

    with c_moeda_sel:
        colunas_moeda = st.multiselect('💵 Colunas de Valor/Moeda:', options=df.columns, key='ctrl_moeda')
        for col in colunas_moeda:
            formato = st.selectbox(f'Formato para "{col}":',
                                   options=['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'],
                                   key=f'fmt_moeda_{col}')
            dict_formatos_moeda[col] = formato

    with c_data_sel:
        colunas_data = st.multiselect('📅 Colunas de Data Comum:', options=df.columns, key='ctrl_data')
        for col in colunas_data:
            formato = st.selectbox(f'Formato para "{col}":',
                                   options=['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'],
                                   key=f'fmt_data_{col}')
            dict_formatos_data[col] = formato

    st.session_state['config_moedas'] = dict_formatos_moeda
    st.session_state['config_datas'] = dict_formatos_data

    st.divider()
    st.markdown("##### 📊 Visualização Parcial (Com as Formatações Escolhidas)")
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_rh_tab(df: pd.DataFrame):
    """Aba 5: Toolkit de RH."""
    st.subheader("🛠️ Toolkit de Gestão de Pessoas")
    st.caption("Selecione uma ferramenta para processar regras de negócio de RH.")

    # Menu de Ferramentas
    tool = st.selectbox("Escolha a Ferramenta de RH:",
                        options=["Tempo de Casa Atual", "Banding Salarial", "Compliance RH", "Cálculo de Demissão (Legado)"],
                        key="rh_tool_selector")

    st.divider()

    if tool == "Tempo de Casa Atual":
        st.markdown("#### 📅 Calcular Tempo de Casa")
        st.info("Cria a coluna 'tempo_casa_atual' comparando a admissão com a data de hoje.")
        col_adm = st.selectbox('Coluna de Admissão:', options=list(df.columns), key='rh_adm_casa')
        if st.button("Calcular Tempo de Casa"):
            st.session_state['action_rh'] = ('tempo_casa', col_adm)

    elif tool == "Banding Salarial":
        st.markdown("#### 💰 Criação de Faixas Salariais")
        st.info("Agrupe salários em categorias (Ex: 0-3000:Junior; 3000-6000:Pleno)")
        col_sal = st.selectbox('Coluna de Salário:', options=list(df.columns), key='rh_sal_col')
        faixas = st.text_input('Definição das Faixas (Formato: min-max:Nome; ...):',
                               value="0-3000:Junior; 3000-6000:Pleno; 6000-10000:Senior",
                               key='rh_faixas_input')
        if st.button("Aplicar Banding Salarial"):
            st.session_state['action_rh'] = ('banding', col_sal, faixas)

    elif tool == "Compliance RH":
        st.markdown("#### 🛡️ Validação de Compliance")
        st.info("Identifica datas futuras ou documentos com formato incorreto.")
        c1, c2 = st.columns(2)
        with c1:
            col_data = st.selectbox('Coluna de Data:', options=list(df.columns), key='rh_comp_data')
        with c2:
            col_doc = st.selectbox('Coluna de Documento:', options=list(df.columns), key='rh_comp_doc')
        if st.button("Validar Compliance"):
            st.session_state['action_rh'] = ('compliance', col_data, col_doc)

    elif tool == "Cálculo de Demissão (Legado)":
        st.markdown("#### 🗓️ Cálculo de Data de Demissão")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            col_admissao = st.selectbox('Data de Admissão:', options=['Não aplicar...'] + list(df.columns), key='sb_admissao')
        with c2:
            col_tempo = st.selectbox('Tempo de Casa (Anos,Meses):', options=['Não aplicar...'] + list(df.columns), key='sb_tempo')
        with c3:
            col_desligado = st.selectbox('Coluna "Desligado?":', options=['Não aplicar...'] + list(df.columns), key='sb_desligado')
        with c4:
            col_demissao = st.selectbox('Coluna Destino (Data de Demissão):', options=['Criar nova coluna'] + list(df.columns), key='sb_demissao')

        if col_demissao == 'Criar nova coluna': col_demissao = 'data_demissao_calculada'

        if col_admissao != 'Não aplicar...' and col_tempo != 'Não aplicar...' and col_desligado != 'Não aplicar...':
            if st.button("Calcular Datas de Demissão"):
                st.session_state['action_rh'] = ('demissao', col_admissao, col_tempo, col_desligado, col_demissao)

    st.divider()
    st.markdown("##### 📊 Visualização Parcial (RH)")
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_export_tab(df: pd.DataFrame, column_config: Dict[str, Any]):
    """Aba 6: Exportação."""
    st.subheader("📊 Visualização Prévia dos Dados Tratados")
    st.dataframe(df, hide_index=True, column_config=column_config, use_container_width=True)

    st.divider()
    st.subheader("💾 Exportar para Excel (.xlsx)")

    # O botão de download será tratado no main.py para gerenciar o buffer de bytes
    st.info("Clique no botão abaixo para baixar a base formatada.")
