"""Componentes de interface Streamlit."""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List

from core import data_processing


def render_header():
    """Renderiza o cabeçalho da aplicação com customização de abas."""
    st.markdown("""
        <style>
            [data-baseweb="tab-list"] {
                gap: 40px !important;
            }
            button[data-baseweb="tab"] {
                display: flex !important;
                justify-content: center !important;
                text-align: center !important;
                padding-left: 20px !important;
                padding-right: 20px !important;
                min-width: 120px !important;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
    # 🎲 DATAONE <span style='font-size: 18px; color: #888;'>| Central Inteligente de Data Processing</span>
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
    """Aba de diagnóstico do arquivo."""
    st.subheader("🔍 Análise de Saúde dos Dados")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Linhas", df.shape[0])
    m2.metric("Total de Colunas", df.shape[1])
    m3.metric("Células Vazias", df.isna().sum().sum())
    m4.metric("Linhas Duplicadas", df.duplicated().sum())

    st.divider()
    outliers = data_processing.detectar_outliers_iqr(df)
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
    """Aba de limpeza de dados."""
    st.subheader("🧼 Gerenciar Colunas")
    st.markdown("#### ❌ Excluir Colunas")
    cols_ex = st.multiselect("Selecione colunas para remover:", options=df.columns, key=f"del_col_{id_arquivo}")
    if st.button("Excluir Colunas", key=f"btn_del_{id_arquivo}", type="primary"):
        if cols_ex: st.session_state['action_limpeza'] = ('excluir_coluna', cols_ex)
        else: st.error("⚠️ Selecione pelo menos uma coluna.")

    st.divider()
    st.markdown("#### ➕ Inserir Coluna")
    c1, c2 = st.columns(2)
    nome = c1.text_input("Nome:", key=f"new_col_name_{id_arquivo}")
    pos = c2.selectbox("Inserir antes de:", options=list(df.columns) + [None], key=f"new_col_pos_{id_arquivo}")
    val = st.text_input("Valor Padrão:", value="", key=f"new_col_val_{id_arquivo}")
    if st.button("Inserir", key=f"btn_ins_{id_arquivo}"):
        if not nome.strip():
            st.error("⚠️ Nome não pode estar vazio.")
        elif nome in df.columns:
            st.error(f"⚠️ Já existe uma coluna '{nome}'.")
        else:
            st.session_state['action_limpeza'] = ('inserir_coluna', nome, pos, val)

    st.divider()
    st.dataframe(df.head(100), hide_index=True, use_container_width=True)


def render_texto_tab(df: pd.DataFrame):
    """Aba de padronização de texto."""
    st.subheader("🔤 Formatação de Strings")
    c1, c2 = st.columns(2)
    with c1:
        str_cols = df.select_dtypes(include=['object', 'category', 'string']).columns.tolist()
        cols = st.multiselect("Ajustar Caixa:", options=str_cols, key='txt_caixa')
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
    """Aba de formatação visual."""
    st.subheader("⚙️ Configurações Visuais")
    c1, c2 = st.columns(2)

    col_m = c1.multiselect('💵 Moedas:', options=df.columns, key='ctrl_moeda', help="Selecione colunas de valor para formatar (Ex: R$, US$)")
    dict_m = {c: c1.selectbox(f'Fmt {c}:', ['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'], key=f'm_{c}') for c in col_m}

    col_d = c2.multiselect('📅 Datas:', options=df.columns, key='ctrl_data', help="Selecione colunas que contenham datas")
    dict_d = {c: c2.selectbox(f'Fmt {c}:', ['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'], key=f'd_{c}') for c in col_d}

    st.session_state['config_moedas'], st.session_state['config_datas'] = dict_m, dict_d
    st.divider()

    st.markdown("##### Preview com Formatação Visual")
    fmt_config = get_column_config(df.columns.tolist(), {**dict_m, **dict_d})
    st.dataframe(df.head(100), hide_index=True, column_config=fmt_config, use_container_width=True)


def _gerar_insights(df: pd.DataFrame, numeric_cols: list, categorical_cols: list) -> list:
    """Gera lista de insights automáticos."""
    insights = []
    n = len(df)
    total_cells = n * len(df.columns)
    null_cells = df.isna().sum().sum()

    fill_rate = ((total_cells - null_cells) / total_cells * 100) if total_cells > 0 else 100
    if fill_rate >= 95:
        insights.append(("✅", "Qualidade dos Dados", f"Taxa de preenchimento de {fill_rate:.1f}% — dados muito consistentes.", "40,167,112"))
    elif fill_rate >= 80:
        insights.append(("⚠️", "Qualidade dos Dados", f"Taxa de preenchimento de {fill_rate:.1f}% — há campos vazios que merecem atenção.", "255,193,7"))
    else:
        insights.append(("🔴", "Qualidade dos Dados", f"Taxa de preenchimento baixa ({fill_rate:.1f}%). Considere tratar valores ausentes antes de analisar.", "220,53,69"))

    if null_cells > 0:
        null_cols = df.isna().sum()
        null_cols = null_cols[null_cols > 0].sort_values(ascending=False)
        worst = null_cols.index[0]
        pct = null_cols.iloc[0] / n * 100
        insights.append(("📭", "Coluna Mais Problemática", f"'{worst}' tem {pct:.1f}% de valores nulos ({null_cols.iloc[0]}/{n} registros).", "255,152,0"))

    n_dups = df.duplicated().sum()
    if n_dups > 0:
        insights.append(("🔀", "Registros Duplicados", f"{n_dups} registro(s) idêntico(s) detectado(s) ({n_dups/n*100:.1f}% dos dados).", "156,39,176"))
    else:
        insights.append(("✅", "Sem Duplicatas", "Nenhum registro duplicado encontrado.", "40,167,112"))

    if numeric_cols:
        total_outliers = 0
        cols_with_outliers = []
        for col in numeric_cols:
            s = df[col].dropna()
            if len(s) < 4: continue
            q1, q3 = s.quantile(0.25), s.quantile(0.75)
            iqr = q3 - q1
            n_out = ((s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)).sum()
            if n_out > 0:
                total_outliers += n_out
                cols_with_outliers.append((col, n_out))
        if total_outliers > 0:
            cols_with_outliers.sort(key=lambda x: x[1], reverse=True)
            worst_col, worst_n = cols_with_outliers[0]
            insights.append(("📊", "Outliers Detectados", f"{total_outliers} valor(es) extremo(s) em {len(cols_with_outliers)} coluna(s).", "23,162,184"))
        else:
            insights.append(("✅", "Sem Outliers", "Nenhum valor extremo detectado pelo método IQR.", "40,167,112"))

    return insights[:6]


def render_analysis_tab(df: pd.DataFrame):
    """Aba de análisis com Plotly interativo."""
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    import numpy as np

    st.subheader("📊 Analysis Hub")

    if df.empty:
        st.warning("⚠️ Carregue um arquivo para visualizar as análises.")
        return

    df_clean = df.loc[:, ~df.columns.duplicated()].copy()
    numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df_clean.select_dtypes(include=['object', 'category', 'string']).columns.tolist()

    st.markdown("#### 📈 Visão Geral")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Registros", f"{len(df_clean):,}")
    k2.metric("Colunas", len(df_clean.columns))
    k3.metric("Numéricas", len(numeric_cols))
    k4.metric("Categóricas", len(categorical_cols))
    k5.metric("Vazios", f"{df_clean.isna().sum().sum():,}")

    st.divider()

    st.markdown("#### 💡 Insights Automáticos")
    insights = _gerar_insights(df_clean, numeric_cols, categorical_cols)
    cols_ins = st.columns(2)
    for i, (icone, titulo, texto, cor) in enumerate(insights):
        with cols_ins[i % 2]:
            st.markdown(f"""
            <div style="background:rgba({cor},0.08);border-left:4px solid rgba({cor},0.6);padding:12px 16px;border-radius:6px;margin-bottom:8px;">
                <b>{icone} {titulo}</b><br><span style="color:#ccc;">{texto}</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    tab_dist, tab_box, tab_corr, tab_cat, tab_pair = st.tabs([
        "📊 Distribuição", "📦 Box Plot", "🔥 Correlações", "🏷️ Categóricas", "🔗 Multi-Variável"
    ])

    with tab_dist:
        if not numeric_cols:
            st.info("Nenhuma coluna numérica encontrada.")
        else:
            col_sel = st.selectbox("Selecionar coluna:", numeric_cols, key='dist_col')
            dados = df_clean[col_sel].dropna()

            if dados.empty:
                st.warning("Coluna sem dados válidos.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Média", f"{dados.mean():,.2f}")
                c2.metric("Mediana", f"{dados.median():,.2f}")
                c3.metric("Desvio Padrão", f"{dados.std():,.2f}")
                c4.metric("Assimetria", f"{dados.skew():.2f}")

                fig = make_subplots(rows=1, cols=2, subplot_titles=("Histograma com Curva de Densidade", "Box Plot"), column_widths=[0.65, 0.35])

                fig.add_trace(go.Histogram(x=dados, nbinsx=30, name="Frequência", marker_color="#636EFA", opacity=0.75), row=1, col=1)

                from scipy.stats import gaussian_kde
                try:
                    kde = gaussian_kde(dados)
                    x_range = np.linspace(dados.min(), dados.max(), 200)
                    kde_vals = kde(x_range)
                    kde_scaled = kde_vals * len(dados) * (dados.max() - dados.min()) / 30
                    fig.add_trace(go.Scatter(x=x_range, y=kde_scaled, mode='lines', name="Densidade", line=dict(color='#EF553B', width=2)), row=1, col=1)
                except Exception: pass

                fig.add_trace(go.Box(y=dados, name=col_sel, marker_color='#00CC96', boxpoints='outliers'), row=1, col=2)

                fig.update_layout(height=400, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1), margin=dict(t=50, b=30))
                st.plotly_chart(fig, use_container_width=True)

                with st.expander("📋 Estatísticas Descritivas Completas"):
                    stats = pd.DataFrame({
                        'Métrica': ['Contagem', 'Média', 'Mediana', 'Moda', 'Desvio Padrão', 'Mínimo', 'Q1 (25%)', 'Q3 (75%)', 'Máximo', 'Assimetria', 'Curtose', 'Variação (%)'],
                        'Valor': [len(dados), dados.mean(), dados.median(), dados.mode().iloc[0] if not dados.mode().empty else None, dados.std(), dados.min(), dados.quantile(0.25), dados.quantile(0.75), dados.max(), dados.skew(), dados.kurtosis(), (dados.std() / dados.mean() * 100) if dados.mean() != 0 else None]
                    })
                    st.dataframe(stats, hide_index=True, use_container_width=True)

    with tab_box:
        if len(numeric_cols) < 1:
            st.info("Nenhuma coluna numérica encontrada.")
        else:
            st.markdown("##### Comparação entre Colunas Numéricas")
            cols_box = st.multiselect("Selecionar colunas:", numeric_cols, default=numeric_cols[:min(5, len(numeric_cols))], key='box_cols')
            if cols_box:
                fig = go.Figure()
                colors = px.colors.qualitative.Set2
                for i, col in enumerate(cols_box):
                    fig.add_trace(go.Box(y=df_clean[col].dropna(), name=col, marker_color=colors[i % len(colors)], boxpoints='outliers'))
                fig.update_layout(height=450, title="Distribuição por Coluna", yaxis_title="Valor", showlegend=False, margin=dict(t=50, b=30))
                st.plotly_chart(fig, use_container_width=True)

    with tab_corr:
        if len(numeric_cols) < 2:
            st.info("Necessário pelo menos 2 colunas numéricas para correlação.")
        else:
            st.markdown("##### Mapa de Correlação (Pearson)")
            corr_matrix = df_clean[numeric_cols].corr()
            fig_corr = px.imshow(corr_matrix, text_auto='.2f', aspect='auto', color_continuous_scale='RdBu_r', zmin=-1, zmax=1, title="Matriz de Correlação")
            fig_corr.update_layout(height=max(400, len(numeric_cols) * 50), margin=dict(t=60, b=30))
            st.plotly_chart(fig_corr, use_container_width=True)

    with tab_cat:
        if not categorical_cols:
            st.info("Nenhuma coluna categórica/texto encontrada.")
        else:
            col_cat = st.selectbox("Selecionar coluna:", categorical_cols, key='cat_col')
            top_n = st.slider("Top N categorias:", 5, 50, 15, key='cat_top')
            vals = df_clean[col_cat].dropna().value_counts().head(top_n)
            fig_bar = px.bar(x=vals.values, y=vals.index.astype(str), orientation='h', labels={'x': 'Quantidade', 'y': col_cat}, title=f"Distribuição de {col_cat}", color=vals.values, color_continuous_scale='Viridis')
            fig_bar.update_layout(height=max(350, top_n * 25), yaxis=dict(autorange="reversed"), margin=dict(t=50, b=30), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab_pair:
        if len(numeric_cols) < 2:
            st.info("Necessário pelo menos 2 colunas numéricas.")
        else:
            st.markdown("##### Análise Multi-Variável")
            bubble_c1, bubble_c2, bubble_c3 = st.columns(3)
            col_bx = bubble_c1.selectbox("Eixo X:", numeric_cols, key='bubble_x')
            remaining_y = [c for c in numeric_cols if c != col_bx]
            col_by = bubble_c2.selectbox("Eixo Y:", remaining_y, key='bubble_y')
            remaining_size = ["Nenhum"] + [c for c in numeric_cols if c not in (col_bx, col_by)]
            col_bubble = bubble_c3.selectbox("Tamanho:", remaining_size, key='bubble_size')

            df_bubble = df_clean[[col_bx, col_by] + ([col_bubble] if col_bubble != "Nenhum" else [])].dropna()
            if not df_bubble.empty:
                fig_bubble = px.scatter(df_bubble, x=col_bx, y=col_by, size=col_bubble if col_bubble != "Nenhum" else None, opacity=0.6, title=f"{col_bx} vs {col_by}", color_discrete_sequence=['#636EFA'])
                fig_bubble.update_layout(height=450, margin=dict(t=50, b=30))
                st.plotly_chart(fig_bubble, use_container_width=True)

    st.divider()
    with st.expander("✅ Ver Dados Brutos"):
        st.dataframe(df_clean, hide_index=True, use_container_width=True)


def render_formulas_tab():
    """Aba de fórmulas Excel."""
    st.subheader("📑 Central de Fórmulas Excel")
    st.markdown("Consulte rapidamente as principais fórmulas para turbinar suas planilhas.")

    formulas = [
        {"nome": "SOMA", "cat": "Matemáticas", "sin": "=SOMA(intervalo)", "desc": "Soma todos os números em um intervalo de células.", "ex": "=SOMA(A1:A10)"},
        {"nome": "MÉDIA", "cat": "Estatísticas", "sin": "=MÉDIA(intervalo)", "desc": "Retorna a média aritmética dos argumentos.", "ex": "=MÉDIA(B1:B20)"},
        {"nome": "SE", "cat": "Lógicas", "sin": "=SE(teste_lógico; valor_se_verdadeiro; valor_se_falso)", "desc": "Verifica se uma condição é atendida.", "ex": "=SE(C2>=7; \"Aprovado\"; \"Reprovado\")"},
        {"nome": "SEERRO", "cat": "Lógicas", "sin": "=SEERRO(valor; valor_se_erro)", "desc": "Retorna um valor específico se houver erro.", "ex": "=SEERRO(A1/B1; 0)"},
        {"nome": "PROCV", "cat": "Pesquisa e Referência", "sin": "=PROCV(valor_procurado; matriz_tabela; num_indice_coluna; [procurar_intervalo])", "desc": "Procura um valor na primeira coluna de uma tabela.", "ex": "=PROCV(\"Produto A\"; A2:E50; 3; FALSO)"},
        {"nome": "PROCX", "cat": "Pesquisa e Referência", "sin": "=PROCX(pesquisa_valor; matriz_pesquisa; matriz_retorno; [se_não_encontrado]; [modo_correspondência])", "desc": "Versão moderna e flexível do PROCV.", "ex": "=PROCX(F2; A2:A100; C2:C100; \"Não encontrado\")"},
        {"nome": "HOJE", "cat": "Data e Hora", "sin": "=HOJE()", "desc": "Retorna a data atual.", "ex": "=HOJE()"},
        {"nome": "CONT.SE", "cat": "Estatísticas", "sin": "=CONT.SE(intervalo; critérios)", "desc": "Conta células que atendem critérios.", "ex": "=CONT.SE(A1:A500; \">100\")"},
        {"nome": "SOMASE", "cat": "Matemáticas", "sin": "=SOMASE(intervalo; critérios; [intervalo_soma])", "desc": "Adiciona células especificadas por critérios.", "ex": "=SOMASE(B2:B25; \"Frutas\"; C2:C25)"},
    ]

    c_search, c_filter = st.columns([2, 1])
    search_term = c_search.text_input("🔍 Pesquisar fórmula:", placeholder="Ex: PROCV, soma, data...")
    categorias = sorted(list(set(f['cat'] for f in formulas)))
    selected_cat = c_filter.multiselect("📂 Filtrar Categorias:", options=categorias, default=categorias)

    filtered_formulas = [f for f in formulas if (search_term.lower() in f['nome'].lower() or search_term.lower() in f['cat'].lower() or search_term.lower() in f['desc'].lower()) and (f['cat'] in selected_cat)]

    st.divider()

    if not filtered_formulas:
        st.info("Nenhuma fórmula encontrada com esses critérios.")
    else:
        cols = st.columns(2)
        for i, f in enumerate(filtered_formulas):
            with cols[i % 2]:
                with st.container(border=True):
                    st.markdown(f"**{f['nome']}** · {f['cat']}")
                    st.markdown(f"{f['desc']}")
                    st.code(f['sin'], language="excel")
                    st.caption(f"Ex: `{f['ex']}`")


def render_export_tab(df: pd.DataFrame, column_config: Dict[str, Any]):
    """Aba de exportação."""
    st.subheader("📊 Preview Final")
    st.dataframe(df, hide_index=True, column_config=column_config, use_container_width=True)
    st.info("Use o botão na barra lateral ou abaixo para exportar.")


def _icon_html(href: str, svg_b64: str, alt: str, title: str) -> str:
    """Gera HTML de um botão de ícone com fundo branco."""
    img_filter = "" if alt in ("LinkedIn", "Portfólio") else "filter:brightness(0);"
    return f"""
    <a href="{href}" target="_blank" title="{title}"
       style="display:flex;align-items:center;justify-content:center;width:100%;height:38px;
              background:white;border:1px solid white;border-radius:6px;text-decoration:none;
              cursor:pointer;box-sizing:border-box;">
        <img src="data:image/svg+xml;base64,{svg_b64}" width="20" height="20" alt="{alt}"
             style="{img_filter}"/>
    </a>
    """


def render_footer():
    """Renderiza o rodapé com links e botão 'Sobre mim'."""
    from ui.assets import GITHUB_SVG, LINKEDIN_SVG, PORTFOLIO_SVG

    st.markdown("<br><br><br><br><br>", unsafe_allow_html=True)
    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### **DATAONE**")
        st.markdown("Central inteligente de processamento projetada para simplificar fluxos complexos.")

    with col_right:
        st.markdown("<div style='text-align: right;'>", unsafe_allow_html=True)
        st.markdown("**Desenvolvido por Manoel — Data Scientist**")

        c_space, ic1, ic2, ic3, ic4 = st.columns([2, 1, 1, 1, 1])
        with ic1:
            if GITHUB_SVG:
                st.html(_icon_html("https://github.com/manoelja/DataOne", GITHUB_SVG, "GitHub", "GitHub"))
        with ic2:
            if LINKEDIN_SVG:
                st.html(_icon_html("https://www.linkedin.com/in/manoel-ara%C3%BAjo-79b62239b", LINKEDIN_SVG, "LinkedIn", "LinkedIn"))
        with ic3:
            if PORTFOLIO_SVG:
                st.html(_icon_html("https://portfolio-manoelja.vercel.app", PORTFOLIO_SVG, "Portfólio", "Portfólio"))
        with ic4:
            if st.button("", key="btn_sobre_mim", icon=":material/person:", help="Sobre o Desenvolvedor", use_container_width=True):
                st.session_state.show_developer = not st.session_state.show_developer
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.show_developer:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.chat_message("user", avatar=":material/person:"):
            st.markdown("""
            #### **Sobre o Desenvolvedor**
            Manoel é um Data Scientist apaixonado por transformar dados brutos em inteligência e por democratizar o
            acesso ao conhecimento técnico.
            """)
