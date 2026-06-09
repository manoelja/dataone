import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Tuple
import processing

def render_header():
    """Renderiza o cabeçalho da aplicação com customização de abas."""
    # Injeção de CSS para espaçamento e centralização das abas
    st.markdown("""
        <style>
            /* Aumenta o espaço entre as abas no menu superior */
            [data-baseweb="tab-list"] {
                gap: 40px !important;
            }
            
            /* Centraliza o título e ajusta o visual de cada aba */
            button[data-baseweb="tab"] {
                display: flex !important;
                justify-content: center !important;
                text-align: center !important;
                padding-left: 20px !important;
                padding-right: 20px !important;
                min-width: 120px !important; /* Garante área de clique centralizada */
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    # 🎲 DATAONE <span style='font-size: 18px; color: #888;'>| Central Inteligente de Data processing</span>
    ##### Faça upload, limpe, padronize e analise seus dados sem planilhas quebradas.
    ---
    """, unsafe_allow_html=True)

def get_column_config(df_columns: List[str], fmt_map: Dict[str, Any]) -> Dict[str, Any]:
    """Converte o mapa de formatos para os objetos st.column_config."""
    config = {}
    for col in df_columns:
        fmt = fmt_map.get(col)
        if not fmt: continue
        if fmt == "datetime": config[col] = st.column_config.DatetimeColumn(col, format="DD/MM/YYYY")
        elif fmt == 'R$ (Real - Brasil)': config[col] = st.column_config.NumberColumn(col, format="R$ %,.2f")
        elif fmt == '$ (Dólar - EUA)': config[col] = st.column_config.NumberColumn(col, format="$ %,.2f")
        elif fmt == '€ (Euro)': config[col] = st.column_config.NumberColumn(col, format="€ %,.2f")
        elif fmt == 'Apenas Decimal (1.250,00)': config[col] = st.column_config.NumberColumn(col, format="%,.2f")
        elif fmt in ['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM']: config[col] = st.column_config.DatetimeColumn(col, format=fmt)
    return config

def render_diagnostico_tab(df: pd.DataFrame):
    """Aba 1: Diagnóstico do Arquivo."""
    st.subheader("🔍 Análise de Saúde dos Dados")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Linhas", df.shape[0])
    m2.metric("Total de Colunas", df.shape[1])
    m3.metric("Células Vazias", df.isna().sum().sum())
    m4.metric("Linhas Duplicadas", df.duplicated().sum())

    st.divider()
    outliers = processing.detectar_outliers_iqr(df)
    if outliers:
        with st.expander("⚠️ Alerta de Outliers", expanded=True):
            st.table(pd.DataFrame(list(outliers.items()), columns=['Coluna', 'Qtd de Outliers']))
    else: st.success("✅ Nenhuma anomalia detectada.")

    st.markdown("### Perfil de Metadados")
    df_tipos = pd.DataFrame({
        'Coluna': df.columns,
        'Tipo': df.dtypes.astype(str),
        'Preenchimento (%)': ((df.notna().sum() / len(df)) * 100).round(1) if len(df) > 0 else 0,
        'Vazios': df.isna().sum()
    })
    st.dataframe(df_tipos, hide_index=True, use_container_width=True)

def render_limpeza_tab(df: pd.DataFrame, id_arquivo: str):
    """Aba 2: Limpeza de Dados."""
    st.subheader("🧼 Tratamento de Anomalias")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Remover Duplicados")
        geral = st.checkbox("Geral (100% idênticas)", key=f"dup_geral_{id_arquivo}")
        chaves = st.multiselect("Por Colunas-Chave:", options=df.columns, key=f"dup_chave_{id_arquivo}")
        if st.button("Remover Duplicados", key=f"btn_dup_{id_arquivo}"):
            if geral or chaves: st.session_state['action_limpeza'] = ('remover_dup', geral, chaves)
            else: st.error("Selecione uma opção.")
    with c2:
        st.markdown("#### Tratar Nulos")
        cols = st.multiselect("Colunas:", options=df.columns, key=f"nulos_cols_{id_arquivo}")
        if cols:
            est = st.radio("Estratégia:", ["Preencher com Zero (0)", "Preencher com 'Não Informado'", "Excluir a linha inteira"], key=f"est_nulos_{id_arquivo}")
            if st.button("Aplicar Nulos", key=f"btn_nulos_{id_arquivo}"):
                st.session_state['action_limpeza'] = ('tratar_nulos', cols, est)

    st.divider()
    st.markdown("#### ❌ Excluir Colunas")
    cols_ex = st.multiselect("Selecione uma ou mais colunas para remover:", options=df.columns, key=f"del_col_{id_arquivo}")
    if st.button("Excluir Colunas Selecionadas", key=f"btn_del_{id_arquivo}", type="primary"):
        if cols_ex: st.session_state['action_limpeza'] = ('excluir_coluna', cols_ex)
        else: st.error("⚠️ Selecione pelo menos uma coluna.")

    st.divider()
    st.markdown("#### ➕ Inserir Coluna")
    nome = st.text_input("Nome da nova coluna:", key=f"new_col_name_{id_arquivo}")
    pos = st.selectbox("Inserir antes de (Esquerda):", options=list(df.columns) + [None], key=f"new_col_pos_{id_arquivo}")
    val = st.text_input("Valor Padrão:", value="", key=f"new_col_val_{id_arquivo}")
    if st.button("Inserir", key=f"btn_ins_{id_arquivo}"):
        if not nome.strip():
            st.error("⚠️ O nome da coluna não pode estar vazio.")
        elif nome in df.columns:
            st.error(f"⚠️ Já existe uma coluna chamada '{nome}'. Escolha um nome diferente.")
        else:
            st.session_state['action_limpeza'] = ('inserir_coluna', nome, pos, val)

    st.divider()
    if st.button("🧼 Faxina Automática (Strip)", key=f"btn_strip_{id_arquivo}"):
        st.session_state['action_limpeza'] = ('strip_all', True)

    st.divider()
    st.dataframe(df.head(100), hide_index=True, use_container_width=True)

def render_texto_tab(df: pd.DataFrame):
    """Aba 3: Padronização de Texto."""
    st.subheader("🔤 Formatação de Strings")
    c1, c2 = st.columns(2)
    with c1:
        cols = st.multiselect("Ajustar Caixa:", options=df.columns, key='txt_caixa')
        if cols:
            modo = st.selectbox("Modo:", ["TUDO EM MAIÚSCULO", "tudo em minúsculo", "Capitalize"])
            if st.button("Ajustar Caixa"): st.session_state['action_texto'] = ('caixa_texto', cols, modo)
    with c2:
        col_id = st.selectbox("Gerar ID em:", options=["Nova Coluna"] + list(df.columns), key='id_col')
        start = st.number_input("Início:", value=1)
        if st.button("Gerar IDs"): st.session_state['action_texto'] = ('gerar_ids', col_id, start)

    st.divider()
    st.markdown("#### 🇧🇷 Máscaras de Documentos")
    col_doc = st.selectbox("Coluna Alvo:", options=["Selecione..."] + list(df.columns), key='doc_col')
    if col_doc != "Selecione...":
        tipo = st.selectbox("Tipo:", ["CPF", "CNPJ"])
        if st.button("Aplicar Máscara"): st.session_state['action_texto'] = ('mascara_doc', col_doc, tipo)
        if st.button("Gerar Fakes"): st.session_state['action_texto'] = ('fake_docs', col_doc, tipo)

    st.divider()
    st.dataframe(df.head(100), hide_index=True, use_container_width=True)

def render_formatacao_tab(df: pd.DataFrame):
    """Aba 4: Formatação Visual."""
    st.subheader("⚙️ Configurações Visuais")
    c1, c2 = st.columns(2)
    
    # Permite selecionar qualquer coluna, não apenas as que já são números
    # (Pois o usuário quer justamente transformar texto sujo em moeda)
    col_m = c1.multiselect('💵 Moedas:', options=df.columns, key='ctrl_moeda', help="Selecione colunas de valor para formatar (Ex: R$, US$)")
    dict_m = {c: c1.selectbox(f'Fmt {c}:', ['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'], key=f'm_{c}') for c in col_m}
    
    col_d = c2.multiselect('📅 Datas:', options=df.columns, key='ctrl_data', help="Selecione colunas que contenham datas")
    dict_d = {c: c2.selectbox(f'Fmt {c}:', ['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'], key=f'd_{c}') for c in col_d}
    
    st.session_state['config_moedas'], st.session_state['config_datas'] = dict_m, dict_d
    st.divider()
    
    # Exibe o preview com a configuração visual aplicada
    st.markdown("##### Preview com Formatação Visual")
    fmt_config = get_column_config(df.columns.tolist(), {**dict_m, **dict_d})
    st.dataframe(df.head(100), hide_index=True, column_config=fmt_config, use_container_width=True)

def render_analysis_tab(df: pd.DataFrame):
    """Aba 5: Analysis Hub (Generalizado)."""
    st.subheader("📊 Analysis Hub")
    
    if df.empty:
        st.warning("⚠️ Carregue um arquivo para visualizar as análises.")
        return

    # 1. Dashboard de KPIs (Detecta o que for possível)
    st.markdown("#### 📈 Métricas de Impacto")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    
    # Headcount/Linhas
    total_linhas = len(df)
    kpi1.metric("Total de Registros", total_linhas)
    
    # Valores Numéricos (Tenta detectar coluna de valor/salário)
    col_valor = next((c for c in df.columns if any(x in c.lower() for x in ['valor', 'total', 'salario', 'preço', 'receita'])), None)
    if col_valor:
        valores = pd.to_numeric(df[col_valor].astype(str).str.replace(r'[R\$\s\.€]', '', regex=True).str.replace(',', '.', regex=False), errors='coerce')
        kpi2.metric("Soma Total", f"{valores.sum():,.2f}")
        kpi3.metric("Média Geral", f"{valores.mean():,.2f}")
    else:
        kpi2.metric("Soma Total", "N/A")
        kpi3.metric("Média Geral", "N/A")

    # Datas (Tenta detectar coluna de data)
    col_data_ref = next((c for c in df.columns if any(x in c.lower() for x in ['data', 'admissao', 'venda', 'criado'])), None)
    if col_data_ref:
        kpi4.metric("Ref. Temporal", col_data_ref[:15])
    else:
        kpi4.metric("Ref. Temporal", "N/A")

    st.divider()

    # 2. Insights e Sugestões Automáticas
    st.markdown("#### 💡 Insights do Sistema")
    col_cat = next((c for c in df.columns if any(x in c.lower() for x in ['categoria', 'depto', 'produto', 'status', 'tipo'])), None)

    insight_cols = st.columns(2)
    with insight_cols[0]:
        if col_cat and col_valor:
            st.info(f"✨ **Insight:** Detectamos '{col_cat}' e '{col_valor}'. Podemos analisar a soma por categoria.")
        elif col_cat:
            st.info(f"✨ **Insight:** Podemos visualizar a distribuição por '{col_cat}'.")
    
    with insight_cols[1]:
        if col_data_ref:
            st.info(f"✨ **Insight:** Detectamos '{col_data_ref}'. Podemos analisar a evolução no tempo.")

    st.divider()

    # 3. Visualizações Estratégicas
    viz_tab1, viz_tab2, viz_tab3 = st.tabs(["📊 Distribuição", "📉 Estatística", "🔗 Correlações"])

    with viz_tab1:
        st.markdown("##### Distribuição de Headcount")
        # Garante colunas únicas antes de agrupar
        df_dist = df.loc[:, ~df.columns.duplicated()].copy()
        col_dist = st.selectbox("Agrupar por:", options=[c for c in [col_cat] if c and c in df_dist.columns] + list(df_dist.columns), key='an_dist_sel')
        
        if col_dist:
            # Agregação robusta para evitar erro de dimensão no index
            counts = df_dist[col_dist].value_counts().reset_index()
            counts.columns = ['Categoria', 'Quantidade']
            st.bar_chart(counts.set_index('Categoria'))

    with viz_tab2:
        st.markdown("##### Análise Estatística")
        # Filtra colunas numéricas
        numeric_cols_only = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if not numeric_cols_only:
            st.warning("⚠️ Nenhuma coluna numérica encontrada para cálculos estatísticos.")
        else:
            col_target = st.selectbox("Selecione a coluna para calcular:", options=numeric_cols_only)
            
            if col_target:
                dados_num = df[col_target].dropna()
                
                # --- Seção: Estatísticas Descritivas ---
                st.markdown(f"**📌 Resumo Estatístico: {col_target}**")
                stat_c1, stat_c2, stat_c3 = st.columns(3)
                
                media = dados_num.mean()
                mediana = dados_num.median()
                moda_series = dados_num.mode()
                moda = moda_series[0] if not moda_series.empty else 0

                with stat_c1:
                    st.metric("Média", f"{media:,.2f}")
                    st.caption("🔍 **Média**: Soma de todos os valores dividida pela quantidade. Representa o centro de 'equilíbrio' dos dados.")
                
                with stat_c2:
                    st.metric("Mediana", f"{mediana:,.2f}")
                    st.caption("🔍 **Mediana**: O valor central. 50% dos dados estão abaixo e 50% acima deste número. Menos afetada por valores extremos.")
                
                with stat_c3:
                    st.metric("Moda", f"{moda:,.2f}")
                    st.caption("🔍 **Moda**: O valor que mais se repete na coluna. Indica a tendência de maior frequência.")

                st.divider()
                
                # Histograma
                st.markdown(f"**Histograma de Distribuição ({col_target})**")
                counts, bin_edges = np.histogram(dados_num, bins=15)
                bin_labels = [f"{bin_edges[i]:.1f}" for i in range(len(bin_edges)-1)]
                hist_df = pd.DataFrame({'Faixa': bin_labels, 'Qtd': counts})
                st.bar_chart(hist_df.set_index('Faixa'))

    with viz_tab3:
        st.markdown("##### Cruzamento de Dados (Correlações)")
        c_corr1, c_corr2 = st.columns(2)
        
        # Tenta preparar dados numéricos para correlação
        df_corr = df.loc[:, ~df.columns.duplicated()].copy()
        numeric_cols = df_corr.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) >= 2:
            col_x = c_corr1.selectbox("Eixo X:", options=numeric_cols, index=0)
            col_y = c_corr2.selectbox("Eixo Y:", options=numeric_cols, index=min(1, len(numeric_cols)-1))
            
            if col_x and col_y:
                # Cria um dataframe de plotagem com nomes de colunas únicos (aliases)
                df_plot = df_corr[[col_x, col_y]].dropna()
                df_plot.columns = ["Eixo_X", "Eixo_Y"]
                st.scatter_chart(df_plot, x="Eixo_X", y="Eixo_Y")
        else:
            st.info("⚠️ Necessário ao menos 2 colunas numéricas para correlação.")

    st.divider()

    with st.expander("✅ Ver Dados Brutos"):
        st.dataframe(df, hide_index=True, use_container_width=True)

def render_formulas_tab():
    """Aba 7: Central de Fórmulas Excel."""
    st.subheader("📑 Central de Fórmulas Excel")
    st.markdown("Consulte rapidamente as principais fórmulas para turbinar suas planilhas.")

    # Base de dados das fórmulas
    formulas = [
        {"nome": "SOMA", "cat": "Matemáticas", "sin": "=SOMA(intervalo)", "desc": "Soma todos os números em um intervalo de células.", "ex": "=SOMA(A1:A10)"},
        {"nome": "MÉDIA", "cat": "Estatísticas", "sin": "=MÉDIA(intervalo)", "desc": "Retorna a média aritmética dos argumentos.", "ex": "=MÉDIA(B1:B20)"},
        {"nome": "SE", "cat": "Lógicas", "sin": "=SE(teste_lógico; valor_se_verdadeiro; valor_se_falso)", "desc": "Verifica se uma condição é atendida e retorna um valor se VERDADEIRO e outro se FALSO.", "ex": "=SE(C2>=7; \"Aprovado\"; \"Reprovado\")"},
        {"nome": "SEERRO", "cat": "Lógicas", "sin": "=SEERRO(valor; valor_se_erro)", "desc": "Retorna um valor que você especifica se uma fórmula avaliar um erro; caso contrário, retorna o resultado da fórmula.", "ex": "=SEERRO(A1/B1; 0)"},
        {"nome": "PROCV", "cat": "Pesquisa e Referência", "sin": "=PROCV(valor_procurado; matriz_tabela; num_indice_coluna; [procurar_intervalo])", "desc": "Procura um valor na primeira coluna à esquerda de uma tabela e retorna um valor na mesma linha de uma coluna especificada.", "ex": "=PROCV(\"Produto A\"; A2:E50; 3; FALSO)"},
        {"nome": "PROCX", "cat": "Pesquisa e Referência", "sin": "=PROCX(pesquisa_valor; matriz_pesquisa; matriz_retorno; [se_não_encontrado]; [modo_correspondência])", "desc": "Versão moderna e flexível do PROCV. Pesquisa um intervalo ou uma matriz e retorna o item correspondente.", "ex": "=PROCX(F2; A2:A100; C2:C100; \"Não encontrado\")"},
        {"nome": "ÍNDICE", "cat": "Pesquisa e Referência", "sin": "=ÍNDICE(matriz; num_linha; [num_coluna])", "desc": "Retorna um valor ou a referência a um valor de dentro de uma tabela ou intervalo.", "ex": "=ÍNDICE(A1:C10; 2; 3)"},
        {"nome": "CORRESP", "cat": "Pesquisa e Referência", "sin": "=CORRESP(valor_procurado; matriz_procurada; [tipo_correspondência])", "desc": "Procura um item especificado em um intervalo de células e retorna a posição relativa desse item.", "ex": "=CORRESP(\"Venda\"; A1:A10; 0)"},
        {"nome": "CONCAT", "cat": "Texto", "sin": "=CONCAT(texto1; [texto2]; ...)", "desc": "Agrupa o texto de vários intervalos e/ou cadeias de texto.", "ex": "=CONCAT(\"Olá \"; \"Mundo\")"},
        {"nome": "HOJE", "cat": "Data e Hora", "sin": "=HOJE()", "desc": "Retorna o número de série da data atual.", "ex": "=HOJE()"},
        {"nome": "AGORA", "cat": "Data e Hora", "sin": "=AGORA()", "desc": "Retorna o número de série da data e hora atuais.", "ex": "=AGORA()"},
        {"nome": "CONT.SE", "cat": "Estatísticas", "sin": "=CONT.SE(intervalo; critérios)", "desc": "Calcula o número de células dentro de um intervalo que atendem a determinados critérios.", "ex": "=CONT.SE(A1:A500; \">100\")"},
        {"nome": "SOMASE", "cat": "Matemáticas", "sin": "=SOMASE(intervalo; critérios; [intervalo_soma])", "desc": "Adiciona as células especificadas por um determinado critério.", "ex": "=SOMASE(B2:B25; \"Frutas\"; C2:C25)"},
        {"nome": "SOMASES", "cat": "Matemáticas", "sin": "=SOMASES(intervalo_soma; intervalo_critérios1; critérios1; ...)", "desc": "Adiciona as células em um intervalo que atendem a vários critérios.", "ex": "=SOMASES(E2:E100; A2:A100; \">01/01/2023\"; B2:B100; \"SP\")"}
    ]

    # Barra de Pesquisa e Filtros
    c_search, c_filter = st.columns([2, 1])
    search_term = c_search.text_input("🔍 Pesquisar fórmula:", placeholder="Ex: PROCV, soma, data...", help="Busque por nome, categoria ou descrição.")
    
    categorias = sorted(list(set(f['cat'] for f in formulas)))
    selected_cat = c_filter.multiselect("📂 Filtrar Categorias:", options=categorias, default=categorias)

    # Lógica de Filtragem
    filtered_formulas = [
        f for f in formulas 
        if (search_term.lower() in f['nome'].lower() or 
            search_term.lower() in f['cat'].lower() or 
            search_term.lower() in f['desc'].lower()) and
           (f['cat'] in selected_cat)
    ]

    st.divider()

    # Exibição em Grid/Cards
    if not filtered_formulas:
        st.info("Nenhuma fórmula encontrada com esses critérios.")
    else:
        # Mostra em 2 colunas para layout moderno
        cols = st.columns(2)
        for i, f in enumerate(filtered_formulas):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"### **{f['nome']}**")
                    st.caption(f"📁 Categoria: {f['cat']}")
                    st.markdown(f"**Descrição:** {f['desc']}")
                    st.markdown("**Sintaxe:**")
                    st.code(f['sin'], language="excel")
                    st.markdown(f"**Exemplo:** `{f['ex']}`")
                    # O botão de cópia já está embutido no st.code do Streamlit!

def render_export_tab(df: pd.DataFrame, column_config: Dict[str, Any]):
    """Aba 6: Exportação."""
    st.subheader("📊 Preview Final")
    st.dataframe(df, hide_index=True, column_config=column_config, use_container_width=True)
    st.info("Use o botão na barra lateral ou abaixo para exportar.")

def render_footer():
    """Renderiza o rodapé simplificado com emojis e botão de texto 'Sobre mim'."""
    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.divider()
    
    col_left, col_right = st.columns([2, 1])
    
    with col_left:
        st.markdown("### **🎲 DATAONE**")
        st.markdown("""
        Central inteligente de processamento projetada para simplificar fluxos complexos. 
        Transformando dados brutos em inteligência estratégica.
        """)
        
    with col_right:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        st.markdown("**Desenvolvido por Manoel — Data Scientist**")
        
        # Botões apenas com Material Icons (Design Minimalista)
        c_space, ic1, ic2, ic3, ic4 = st.columns([2, 1, 1, 1, 1])
        with ic1: st.link_button("", "https://github.com/", icon=":material/terminal:", help="GitHub", use_container_width=True)
        with ic2: st.link_button("", "https://linkedin.com/", icon=":material/share:", help="LinkedIn", use_container_width=True)
        with ic3: st.link_button("", "#", icon=":material/public:", help="Portfólio", use_container_width=True)
        with ic4:
            if st.button("", key="btn_sobre_mim", icon=":material/person:", help="Sobre o Desenvolvedor", use_container_width=True):
                st.session_state.show_developer = not st.session_state.show_developer
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 2. Seção "Sobre o Desenvolvedor" (Toggle)
    if st.session_state.show_developer:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown("""
            #### **Sobre o Desenvolvedor**
            Manoel é um Data Scientist apaixonado por transformar dados brutos em inteligência e por democratizar o 
            acesso ao conhecimento técnico. Com experiência em modelagem preditiva e arquitetura de dados, 
            criou esta plataforma como um recurso para a comunidade brasileira de tecnologia.
            """)
