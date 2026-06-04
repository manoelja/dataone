import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import processing

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
            # Carrega e armazena o DataFrame secundário em session_state de forma persistente
            try:
                df_sec = processing.carregar_dados(secondary_file)
                st.session_state[f'df_sec_stored_{id_arquivo}'] = df_sec.copy()
                
                st.success("✅ Arquivo secundário carregado com sucesso!")
                st.markdown(f"**Colunas disponíveis:** {', '.join(df_sec.columns.tolist())}")
                
                c_k1, c_k2 = st.columns(2)
                with c_k1:
                    key1 = st.selectbox(
                        "Coluna de ligação (Base Principal):", 
                        options=df.columns, 
                        key=f"key1_{id_arquivo}"
                    )
                with c_k2:
                    key2 = st.selectbox(
                        "Coluna de ligação (Base Secundária):", 
                        options=df_sec.columns, 
                        key=f"key2_{id_arquivo}"
                    )
                
                st.info(f"💡 Será feito um LEFT JOIN usando: **{key1}** (principal) → **{key2}** (secundária)")

                if st.button("🔗 Mesclar Bases de Dados", type="primary", key=f"btn_merge_{id_arquivo}"):
                    # Passa o DataFrame já armazenado, não o arquivo
                    st.session_state['action_merge'] = (df_sec.copy(), key1, key2)
            except Exception as e:
                st.error(f"❌ Erro ao carregar arquivo secundário: {str(e)}")

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
        # PROTEÇÃO CONTRA VALOR VAZIO / NONE
        if col_esquerda and col_esquerda in df.columns:
            idx_esq_atual = list(df.columns).index(col_esquerda)
            opcoes_direita = list(df.columns)[idx_esq_atual + 1:]
            if opcoes_direita:
                col_direita = st.selectbox("Coluna da Direita (Y):", options=opcoes_direita, key=f"col_direita_pos_{id_arquivo}")
            else:
                st.caption("⚠️ Não há colunas depois desta.")
                col_direita = None
        else:
            st.caption("Aguardando seleção da coluna...")
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
    st.markdown("##### 📊 Visualização Parcial (Dados Atuais)")
    
    # Mostra informações da base atual
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Total de Linhas", len(df))
    with col_info2:
        st.metric("Total de Colunas", len(df.columns))
    with col_info3:
        percentual_completo = (1 - (df.isna().sum().sum() / (len(df) * len(df.columns)))) * 100
        st.metric("Completude (%)", f"{percentual_completo:.1f}%")
    
    # Exibe preview com expander para facilitar navegação
    with st.expander("📋 Ver dados da tabela", expanded=True):
        st.dataframe(df, hide_index=True, use_container_width=True)

def render_texto_tab(df: pd.DataFrame):
    """Aba 3: Padronização de Texto."""
    st.subheader("🔤 Formatação de Strings e Cadastro")

    c_txt1, c_txt2 = st.columns(2)
    with c_txt1:
        st.markdown("#### Caixa do Texto")
        cols_caixa = st.multiselect("Selecionar colunas para ajustar LETRAS:", options=df.columns, key='txt_caixa')
        
        if cols_caixa:
            # 🔍 VALIDAÇÃO: Descobre se existem colunas que NÃO são do tipo 'object' ou 'string'
            colunas_invalidas = [col for col in cols_caixa if not pd.api.types.is_object_dtype(df[col]) and not pd.api.types.is_string_dtype(df[col])]
            
            if colunas_invalidas:
                # Mostra o aviso e impede que o resto do código (selectbox e botão) apareça
                st.error(f"⚠️ Atenção: Apenas colunas de texto (str) podem ser ajustadas. Remova as colunas: {', '.join(colunas_invalidas)}")
            else:
                # Se todas forem texto, o fluxo continua normalmente
                modo_caixa = st.selectbox("Formato desejado:", ["TUDO EM MAIÚSCULO", "tudo em minúsculo", "Primeira Letra Maiúscula (Capitalize)"])
                
                if st.button("Ajustar Caixa de Texto"):
                    st.session_state['action_texto'] = ('caixa_texto', cols_caixa, modo_caixa)

    with c_txt2:
        st.markdown("#### 🆔 Gerador de ID Sequencial")
        NOVA_COLUNA_SENTINELA = "Criar nova coluna 'id_gerado'"
        col_id_destino = st.selectbox("Escolha uma coluna para substituir por IDs (ou criar uma nova):",
                                      options=[NOVA_COLUNA_SENTINELA] + list(df.columns),
                                      key='sb_id_destino')
        valor_inicio = st.number_input("Iniciar contagem a partir de:", min_value=0, value=1, step=1, key='ni_id_inicio')
        if st.button("Gerar Sequência de IDs", key='btn_gerar_ids'):
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

    if 'config_moedas' not in st.session_state:
        st.session_state['config_moedas'] = {}
    if 'config_datas' not in st.session_state:
        st.session_state['config_datas'] = {}
    if 'ctrl_moeda' not in st.session_state:
        st.session_state['ctrl_moeda'] = []
    if 'ctrl_data' not in st.session_state:
        st.session_state['ctrl_data'] = []

    dict_formatos_moeda = {}
    dict_formatos_data = {}

    # Criamos uma cópia do dataframe para a visualização na tela não quebrar
    df_visualizacao = df.copy()

    with c_moeda_sel:
        colunas_numericas_validas = [
            col for col in df.columns 
            if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])
        ]
        
        colunas_moeda = st.multiselect(
            '💵 Colunas de Valor/Moeda:', 
            options=colunas_numericas_validas,
            default=[c for c in st.session_state['ctrl_moeda'] if c in colunas_numericas_validas],
            key='ctrl_moeda_input'
        )
        st.session_state['ctrl_moeda'] = colunas_moeda
        
        for col in colunas_moeda:
            padrao_anterior = st.session_state['config_moedas'].get(col, 'R$ (Real - Brasil)')
            formato = st.selectbox(
                f'Formato para "{col}":',
                options=['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'],
                index=['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'].index(padrao_anterior),
                key=f'fmt_moeda_{col}'
            )
            dict_formatos_moeda[col] = formato

    with c_data_sel:
        colunas_data_validas = [
            col for col in df.columns 
            if not pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])
        ]
        
        colunas_data = st.multiselect(
            '📅 Colunas de Data Comum:', 
            options=colunas_data_validas,
            default=[c for c in st.session_state['ctrl_data'] if c in colunas_data_validas],
            key='ctrl_data_input',
            help="Aceita colunas de data ou colunas de texto contendo datas."
        )
        st.session_state['ctrl_data'] = colunas_data
        
        for col in colunas_data:
            padrao_anterior = st.session_state['config_datas'].get(col, 'DD/MM/YYYY')
            formato = st.selectbox(
                f'Formato para "{col}":',
                options=['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'],
                index=['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'].index(padrao_anterior),
                key=f'fmt_data_{col}'
            )
            dict_formatos_data[col] = formato 

            try:
                if col in df_visualizacao.columns:
                    df_visualizacao[col] = pd.to_datetime(df_visualizacao[col], errors='coerce')
            except Exception:
                pass
    st.session_state['config_moedas'] = dict_formatos_moeda
    st.session_state['config_datas'] = dict_formatos_data

    st.divider()
    st.markdown("##### 📊 Visualização Parcial (Com as Formatações Escolhidas)")
    
    mapa_formatos_unido = {**dict_formatos_moeda, **dict_formatos_data}
    config_colunas_streamlit = get_column_config(list(df.columns), mapa_formatos_unido)

    # Exibe a cópia que teve as strings de data convertidas temporariamente
    st.dataframe(
        df_visualizacao, 
        hide_index=True, 
        column_config=config_colunas_streamlit, 
        use_container_width=True
    )
def render_rh_tab(df: pd.DataFrame):
    """Aba 5: Toolkit de Gestão de Pessoas (Reformulado)."""
    st.subheader("🛠️ Toolkit Avançado de Gestão de Pessoas")
    
    # Criando tabs para organizar melhor as funcionalidades
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Análise & Dashboards",
        "📅 Tempo de Serviço", 
        "💰 Gestão Salarial",
        "✅ Compliance & Auditoria"
    ])

    # ==================== TAB 1: ANÁLISE & DASHBOARDS ====================
    with tab1:
        st.markdown("#### 📊 Análise Estratégica de RH")
        st.caption("Visualize métricas-chave e tendências de sua equipe")
        
        col_anal1, col_anal2 = st.columns(2)
        
        with col_anal1:
            st.markdown("##### Colunas Disponíveis para Análise:")
            colunas_numericas = [col for col in df.columns 
                                if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])]
            colunas_datas = [col for col in df.columns 
                            if pd.api.types.is_datetime64_any_dtype(df[col]) or 
                            (pd.api.types.is_object_dtype(df[col]) and ('data' in col.lower() or 'date' in col.lower()))]
            
            if colunas_numericas:
                st.write(f"💵 **Colunas Numéricas:** {len(colunas_numericas)}")
                for col in colunas_numericas[:3]:
                    st.caption(f"  • {col}")
            
            if colunas_datas:
                st.write(f"📅 **Colunas de Data:** {len(colunas_datas)}")
                for col in colunas_datas[:3]:
                    st.caption(f"  • {col}")
        
        with col_anal2:
            st.markdown("##### Resumo da Base:")
            st.metric("Total de Colaboradores", len(df))
            st.metric("Total de Colunas", len(df.columns))
            percentual_completo = (1 - (df.isna().sum().sum() / (len(df) * len(df.columns)))) * 100
            st.metric("Dados Completos (%)", f"{percentual_completo:.1f}%")
        
        st.divider()
        st.markdown("##### 🎯 Gerar Relatório de Análise")
        
        col_rel1, col_rel2 = st.columns(2)
        
        with col_rel1:
            analise_tipo = st.selectbox(
                "Tipo de Análise:",
                options=[
                    "Estatísticas Descritivas de Salário",
                    "Distribuição de Tempo de Casa",
                    "Perfil de Departamentos"
                ],
                key='rh_analise_tipo'
            )
        
        with col_rel2:
            if analise_tipo == "Distribuição de Tempo de Casa":
                if colunas_datas:
                    col_analise = st.selectbox(
                        "Coluna de Data para Análise:",
                        options=colunas_datas,
                        key='rh_col_analise_data'
                    )
                else:
                    col_analise = None
                    st.warning("⚠️ Nenhuma coluna de data encontrada")
            else:
                if colunas_numericas:
                    col_analise = st.selectbox(
                        "Coluna para Análise:",
                        options=colunas_numericas,
                        key='rh_col_analise'
                    )
                else:
                    col_analise = None
                    st.warning("⚠️ Nenhuma coluna numérica encontrada")

        if st.button("📈 Gerar Análise", key='btn_analise_rh'):
            if col_analise:
                st.session_state['action_rh'] = ('analise', analise_tipo, col_analise)
            else:
                st.error("⚠️ Por favor, selecione uma coluna válida para a análise.")
        
        # ===== Gráficos Visuais =====
        st.divider()
        st.markdown("##### 📊 Visualizações Automáticas")
        
        col_viz1, col_viz2 = st.columns(2)
        
        # Gráfico de distribuição de valores numéricos
        with col_viz1:
            if colunas_numericas:
                col_selecionada = st.selectbox(
                    "Selecione coluna para histograma:",
                    options=colunas_numericas,
                    key='rh_hist_col'
                )
                
                if col_selecionada:
                    dados_validos = df[col_selecionada].dropna()
                    st.markdown(f"**Distribuição de {col_selecionada}**")
                    st.bar_chart(dados_validos.value_counts().head(10))
        
        # Gráfico de preenchimento de dados
        with col_viz2:
            st.markdown("**Preenchimento de Dados por Coluna (%)**")
            completude = ((df.notna().sum() / len(df)) * 100).sort_values(ascending=True)
            st.bar_chart(completude)

    # ==================== TAB 2: TEMPO DE SERVIÇO ====================
    with tab2:
        st.markdown("#### 📅 Cálculo de Tempo de Serviço")
        st.caption("Calcule e categorize automaticamente o tempo de permanência dos colaboradores")
        
        col_adm = st.selectbox(
            "Selecione a coluna com Data de Admissão:",
            options=df.columns,
            key='rh_col_admissao_tempo'
        )
        
        col_temp1, col_temp2 = st.columns(2)
        
        with col_temp1:
            categorizar = st.checkbox(
                "✅ Categorizar em Faixas (Junior/Pleno/Senior)",
                value=True,
                key='rh_categorizar_tempo'
            )
        
        with col_temp2:
            if categorizar:
                st.markdown("**Faixas Padrão:**")
                st.caption("• Junior: < 2 anos")
                st.caption("• Pleno: 2-5 anos")
                st.caption("• Senior: > 5 anos")
        
        st.divider()
        
        col_pre1, col_pre2 = st.columns([2, 1])
        with col_pre1:
            st.markdown("**Preview (Primeiras 5 linhas):**")
            if col_adm:
                preview_tempo = df[[col_adm]].head(5).copy()
                preview_tempo.columns = ["Data Admissão"]
                st.dataframe(preview_tempo, hide_index=True, use_container_width=True)
            else:
                st.caption("Aguardando seleção de coluna...")
        
        with col_pre2:
            if st.button("🔄 Calcular Tempo de Casa", key='btn_tempo_casa_novo'):
                if col_adm:
                    st.session_state['action_rh'] = ('tempo_casa', col_adm, categorizar)
                else:
                    st.error("⚠️ Por favor, selecione a coluna de admissão.")

    # ==================== TAB 3: GESTÃO SALARIAL ====================
    with tab3:
        st.markdown("#### 💰 Gestão de Faixas Salariais")
        st.caption("Defina ranges salariais e valide colaboradores fora da faixa")
        
        # Selecionar coluna de salário
        colunas_numericas = [col for col in df.columns 
                            if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col])]
        
        if not colunas_numericas:
            st.error("❌ Nenhuma coluna numérica encontrada para análise salarial")
        else:
            col_salario = st.selectbox(
                "Coluna de Salário:",
                options=colunas_numericas,
                key='rh_col_salario_novo'
            )
            
            st.divider()
            st.markdown("##### 📋 Definir Faixas Salariais")
            
            modo_faixa = st.radio(
                "Como deseja definir as faixas?",
                options=["Usar Faixas Padrão", "Definir Manualmente"],
                key='rh_modo_faixa'
            )
            
            if modo_faixa == "Usar Faixas Padrão":
                st.info("""
                **Faixas Padrão (BRL):**
                - 🔵 Junior: R$ 0 - R$ 3.000
                - 🟡 Pleno: R$ 3.000 - R$ 6.000
                - 🟢 Senior: R$ 6.000 - R$ 10.000
                - 🔴 Executivo: > R$ 10.000
                """)
                faixas_input = "0-3000:Junior; 3000-6000:Pleno; 6000-10000:Senior; 10000-999999:Executivo"
            else:
                st.markdown("**Formato:** `min-max:Categoria; min-max:Categoria`")
                st.markdown("**Exemplo:** `0-3000:Junior; 3000-6000:Pleno; 6000-99999:Senior`")
                faixas_input = st.text_area(
                    "Defina as faixas salariais:",
                    value="0-3000:Junior; 3000-6000:Pleno; 6000-10000:Senior",
                    key='rh_faixas_manual'
                )
            
            st.divider()
            st.markdown("##### 📊 Prévia de Distribuição")
            
            col_prev1, col_prev2 = st.columns([2, 1])
            
            with col_prev1:
                if col_salario:
                    salarios_sample = df[[col_salario]].head(10).copy()
                    salarios_sample.columns = ["Salário"]
                    st.dataframe(salarios_sample, hide_index=True, use_container_width=True)
                else:
                    st.caption("Aguardando seleção de coluna...")
            
            with col_prev2:
                if col_salario:
                    st.metric("Min", f"R$ {df[col_salario].min():.2f}")
                    st.metric("Média", f"R$ {df[col_salario].mean():.2f}")
                    st.metric("Max", f"R$ {df[col_salario].max():.2f}")
                else:
                    st.caption("Aguardando seleção...")

            st.divider()
            st.markdown("##### 📈 Gráfico de Distribuição Salarial")

            # Cria histograma de salários
            salarios_clean = df[col_salario].dropna() if col_salario else pd.Series()

            if not salarios_clean.empty:
                col_dist1, col_dist2 = st.columns([2, 1])

                with col_dist1:
                    # Histograma
                    st.markdown("**Histograma de Salários**")
                    bins = st.slider("Número de faixas:", 5, 50, 15, key='rh_salary_bins')

                    # Cria histograma com índices válidos
                    counts, bin_edges = np.histogram(salarios_clean, bins=bins)
                    bin_labels = [f"R${bin_edges[i]:.0f}-{bin_edges[i+1]:.0f}" for i in range(len(bin_edges)-1)]

                    hist_df = pd.DataFrame({
                        'Faixa': bin_labels,
                        'Quantidade': counts
                    })

                    st.bar_chart(hist_df.set_index('Faixa'))

                with col_dist2:
                    st.markdown("**Estatísticas**")
                    st.metric("Q1 (25%)", f"R$ {salarios_clean.quantile(0.25):.2f}")
                    st.metric("Mediana", f"R$ {salarios_clean.median():.2f}")
                    st.metric("Q3 (75%)", f"R$ {salarios_clean.quantile(0.75):.2f}")
                    st.metric("StdDev", f"R$ {salarios_clean.std():.2f}")
            else:
                st.info(" Selecione uma coluna de salário válida para ver a distribuição.")
            
            if st.button("💾 Aplicar Banding Salarial", key='btn_banding_novo', type='primary'):
                st.session_state['action_rh'] = ('banding', col_salario, faixas_input)

    # ==================== TAB 4: COMPLIANCE & AUDITORIA ====================
    with tab4:
        st.markdown("#### ✅ Validação de Compliance & Auditoria")
        st.caption("Identifique problemas de dados e inconsistências")
        
        col_comp1, col_comp2 = st.columns(2)
        
        with col_comp1:
            st.markdown("##### 🔍 Validações Disponíveis")
            validacoes = st.multiselect(
                "Selecione as validações a executar:",
                options=[
                    "Datas Futuras/Inválidas",
                    "Documentos Inválidos (CPF/CNPJ)",
                    "Duplicação de Documentos",
                    "Campos Obrigatórios Vazios"
                ],
                default=["Datas Futuras/Inválidas", "Documentos Inválidos (CPF/CNPJ)"],
                key='rh_validacoes'
            )
        
        with col_comp2:
            st.markdown("##### 📋 Colunas para Validar")
            colunas_data = [col for col in df.columns 
                           if pd.api.types.is_datetime64_any_dtype(df[col]) or 
                           (pd.api.types.is_object_dtype(df[col]) and 'data' in col.lower())]
            colunas_doc = [col for col in df.columns 
                          if pd.api.types.is_object_dtype(df[col]) and 
                          ('cpf' in col.lower() or 'cnpj' in col.lower() or 'documento' in col.lower())]
            
            if colunas_data:
                col_data_val = st.selectbox("Coluna de Data:", options=colunas_data, key='rh_col_data_comp')
            else:
                col_data_val = None
                st.caption("⚠️ Nenhuma coluna de data encontrada")
            
            if colunas_doc:
                col_doc_val = st.selectbox("Coluna de Documento:", options=colunas_doc, key='rh_col_doc_comp')
            else:
                col_doc_val = None
                st.caption("⚠️ Nenhuma coluna de documento encontrada")
        
        st.divider()
        st.markdown("##### 📊 Relatório de Erros Esperados")
        
        erros_estimados = pd.DataFrame({
            'Validação': validacoes,
            'Status': ['✅ Pronto' for _ in validacoes]
        })
        st.dataframe(erros_estimados, hide_index=True, use_container_width=True)
        
        if st.button("🛡️ Executar Validação de Compliance", key='btn_compliance_novo', type='primary'):
            st.session_state['action_rh'] = (
                'compliance', 
                col_data_val, 
                col_doc_val,
                validacoes
            )

    st.divider()
    st.markdown("##### 📊 Visualização dos Dados (RH)")
    st.dataframe(df, hide_index=True, use_container_width=True)

def render_export_tab(df: pd.DataFrame, column_config: Dict[str, Any]):
    """Aba 6: Exportação."""
    st.subheader("📊 Visualização Prévia dos Dados Tratados")
    st.dataframe(df, hide_index=True, column_config=column_config, use_container_width=True)

    st.divider()
    st.subheader("💾 Exportar para Excel (.xlsx)")

    # O botão de download será tratado no main.py para gerenciar o buffer de bytes
    st.info("Clique no botão abaixo para baixar a base formatada.")
