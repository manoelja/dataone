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

def inicializar_versoes():
    """Inicializa sistema de versões de arquivo."""
    if 'versoes' not in st.session_state:
        st.session_state['versoes'] = {}
    if 'versao_ativa' not in st.session_state:
        st.session_state['versao_ativa'] = 'ORIGINAL'
    if 'historico_versoes' not in st.session_state:
        st.session_state['historico_versoes'] = []

def salvar_versao(versao_nome: str, df: pd.DataFrame, descricao: str = ""):
    """Salva uma versão do DataFrame com timestamp e descrição."""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    chave_versao = f"{versao_nome}_{timestamp}"
    
    st.session_state['versoes'][chave_versao] = df.copy()
    st.session_state['versao_ativa'] = chave_versao
    
    # Registra no histórico
    st.session_state['historico_versoes'].append({
        'versao': chave_versao,
        'nome': versao_nome,
        'timestamp': timestamp,
        'descricao': descricao,
        'linhas': len(df),
        'colunas': len(df.columns)
    })
    
    registrar_log(f"💾 Versão '{versao_nome}' salva - {len(df)} linhas, {len(df.columns)} colunas")
    return chave_versao

def main():
    ui_components.render_header()
    
    # Inicializa sistema de versões
    inicializar_versoes()

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

    # Exibe indicador de versão ativa
    versao_ativa = st.session_state.get('versao_ativa', 'ORIGINAL')
    col_versao1, col_versao2, col_versao3 = st.columns([2, 2, 1])
    
    with col_versao1:
        st.info(f"📌 Versão Ativa: **{versao_ativa}** | Linhas: {len(df_tratado)} | Colunas: {len(df_tratado.columns)}")
    
    with col_versao2:
        # Dropdown para selecionar versão
        versoes_disponiveis = ['ORIGINAL'] + list(st.session_state['versoes'].keys())
        versao_selecionada = st.selectbox(
            "Mudar para versão:",
            options=versoes_disponiveis,
            index=0 if versao_ativa == 'ORIGINAL' else (versoes_disponiveis.index(versao_ativa) if versao_ativa in versoes_disponiveis else 0),
            key='select_versao'
        )
        
        if versao_selecionada != versao_ativa:
            if versao_selecionada == 'ORIGINAL':
                st.session_state['df_tratado'] = df_original.copy()
                st.session_state['versao_ativa'] = 'ORIGINAL'
            else:
                st.session_state['df_tratado'] = st.session_state['versoes'][versao_selecionada].copy()
                st.session_state['versao_ativa'] = versao_selecionada
            st.success(f"✅ Versão alterada para {versao_selecionada}")
            st.rerun()
    
    with col_versao3:
        if st.button("📊 Ver Histórico", type="secondary", use_container_width=True):
            st.session_state['mostrar_historico'] = not st.session_state.get('mostrar_historico', False)
    
    # Exibe histórico se solicitado
    if st.session_state.get('mostrar_historico', False):
        st.divider()
        st.markdown("### 📜 Histórico de Versões")
        if st.session_state['historico_versoes']:
            df_historico = pd.DataFrame(st.session_state['historico_versoes'])
            st.dataframe(df_historico, hide_index=True, use_container_width=True)
        else:
            st.info("Nenhuma versão salva ainda.")
        st.divider()

    # Botão de Reset
    if st.button("🔄 Resetar todas as alterações", type="secondary"):
        st.session_state['df_tratado'] = df_original.copy()
        st.session_state['versao_ativa'] = 'ORIGINAL'
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
            
            # Oferece botão para salvar versão após operação
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Salvar esta Versão", type="primary", key='btn_save_limpeza'):
                    salvar_versao("LIMPEZA", st.session_state['df_tratado'], f"Alterações de limpeza aplicadas")
                    st.success("✅ Versão salva!")
                    st.rerun()
            
            with col_btn2:
                if st.button("📊 Ver Histórico de Versões"):
                    st.session_state['mostrar_historico'] = True
                    st.rerun()
            
            st.rerun()

        # Processamento de Ações de Merge
        if 'action_merge' in st.session_state:
            df_sec, key1, key2 = st.session_state['action_merge']
            try:
                # Verifica se as colunas existem em ambos DataFrames
                if key1 not in df_tratado.columns:
                    raise ValueError(f"Coluna '{key1}' não encontrada na base principal")
                if key2 not in df_sec.columns:
                    raise ValueError(f"Coluna '{key2}' não encontrada na base secundária")
                
                # Executa o merge
                df_mesclado = processing.merge_dataframes(df_tratado, df_sec, key1, key2)
                
                # Mostra estatísticas do merge
                linhas_antes = len(df_tratado)
                linhas_depois = len(df_mesclado)
                colunas_antes = len(df_tratado.columns)
                colunas_depois = len(df_mesclado.columns)
                
                st.session_state['df_tratado'] = df_mesclado
                
                st.success("✅ Bases mescladas com sucesso!")
                st.balloons()
                
                # Exibe estatísticas do merge
                st.divider()
                st.markdown("### 📊 Estatísticas do Merge")
                
                col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
                with col_stat1:
                    st.metric("Linhas Antes", linhas_antes)
                with col_stat2:
                    st.metric("Linhas Depois", linhas_depois)
                with col_stat3:
                    st.metric("Colunas Antes", colunas_antes)
                with col_stat4:
                    st.metric("Colunas Depois", colunas_depois)
                
                st.info(f"✅ **{colunas_depois - colunas_antes} colunas** adicionadas da base secundária")
                
                st.markdown("##### 📋 Preview dos Dados Mesclados (10 primeiras linhas)")
                st.dataframe(df_mesclado.head(10), hide_index=True, use_container_width=True)
                
                # Análise de completude das novas colunas
                st.markdown("##### 🔍 Análise de Preenchimento das Novas Colunas")
                cols_novas = df_sec.columns.tolist()
                if cols_novas:
                    preenchimento = ((df_mesclado[cols_novas].notna().sum() / len(df_mesclado)) * 100).round(1)
                    for col, pct in preenchimento.items():
                        st.progress(pct/100, text=f"{col}: {pct}% preenchido")
                
                # Botão para salvar versão
                st.divider()
                if st.button("💾 Salvar esta Versão Mesclada", type="primary", key='btn_save_merge'):
                    salvar_versao("MERGE", df_mesclado, f"Merge: {colunas_depois - colunas_antes} colunas adicionadas")
                    st.success("✅ Versão salva! Use o seletor no topo para trabalhar com ela.")
                    st.rerun()
                
                registrar_log(f"🔗 Bases mescladas: {linhas_antes} + {len(df_sec)} → {linhas_depois} linhas, {colunas_antes} → {colunas_depois} colunas")
                
            except Exception as e:
                st.error(f"❌ Erro ao mesclar bases: {str(e)}")
                st.write("**Detalhes do erro:**", str(e))

            del st.session_state['action_merge']
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
            action_data = st.session_state['action_rh']
            tool_name = action_data[0]
            params = action_data[1:]

            try:
                if tool_name == 'tempo_casa':
                    # Nova versão com categorização
                    categorizar = params[1] if len(params) > 1 else False
                    st.session_state['df_tratado'] = processing.calcular_tempo_casa_v2(df_tratado, params[0], categorizar)
                    registrar_log(f"🛠️ Tempo de casa calculado para {params[0]}. Categorização: {'Ativada' if categorizar else 'Desativada'}.")
                    
                    st.success("✅ Tempo de casa calculado com sucesso!")
                    st.balloons()
                    
                    # Mostra preview dos resultados
                    st.markdown("##### 📊 Preview dos Resultados")
                    colunas_preview = [params[0], 'tempo_casa_atual']
                    if 'categoria_tempo' in st.session_state['df_tratado'].columns:
                        colunas_preview.append('categoria_tempo')
                    st.dataframe(st.session_state['df_tratado'][colunas_preview].head(10), hide_index=True, use_container_width=True)
                    
                elif tool_name == 'analise':
                    # Gerar relatório de análise
                    analise_tipo = params[0]
                    col_analise = params[1]
                    relatorio = processing.gerar_relatorio_rh(df_tratado, analise_tipo, col_analise)
                    
                    st.success("✅ Análise concluída!")
                    st.markdown(f"##### 📊 {analise_tipo}")
                    st.dataframe(relatorio, hide_index=True, use_container_width=True)
                    registrar_log(f"📊 Relatório de {analise_tipo} gerado.")
                    
                elif tool_name == 'banding':
                    st.session_state['df_tratado'] = processing.aplicar_banding_salarial(df_tratado, params[0], params[1])
                    registrar_log(f"🛠️ Banding salarial aplicado na coluna {params[0]}.")
                    
                    st.success("✅ Banding salarial aplicado com sucesso!")
                    st.balloons()
                    
                    # Mostra preview
                    st.markdown("##### 📊 Distribuição de Faixas Salariais")
                    if 'faixa_salarial' in st.session_state['df_tratado'].columns:
                        dist = st.session_state['df_tratado']['faixa_salarial'].value_counts()
                        
                        col_band1, col_band2 = st.columns([2, 1])
                        
                        with col_band1:
                            st.markdown("**Colaboradores por Faixa**")
                            st.bar_chart(dist)
                        
                        with col_band2:
                            st.markdown("**Resumo**")
                            for faixa, count in dist.items():
                                percentual = (count / len(st.session_state['df_tratado'])) * 100
                                st.caption(f"**{faixa}**: {count} ({percentual:.1f}%)")
                    
                elif tool_name == 'compliance':
                    # Nova versão com múltiplas validações
                    col_data = params[0]
                    col_doc = params[1]
                    validacoes = params[2] if len(params) > 2 else None
                    
                    relatorio_compliance = processing.validar_compliance_rh_v2(df_tratado, col_data, col_doc, validacoes)
                    
                    st.success("✅ Validação de compliance concluída!")
                    st.markdown("##### 🛡️ Relatório de Compliance")
                    
                    # Exibe tabela de erros
                    st.dataframe(relatorio_compliance, hide_index=True, use_container_width=True)
                    
                    # Se houver erros, exibe gráfico visual
                    if 'Quantidade' in relatorio_compliance.columns and len(relatorio_compliance) > 0:
                        erros_com_qtd = relatorio_compliance[relatorio_compliance['Quantidade'] > 0]
                        
                        if len(erros_com_qtd) > 0:
                            st.divider()
                            st.markdown("##### 📊 Visualização de Erros")
                            
                            col_comp_viz1, col_comp_viz2 = st.columns([2, 1])
                            
                            with col_comp_viz1:
                                st.markdown("**Quantidade de Erros por Tipo**")
                                erro_chart = erros_com_qtd.set_index('Tipo')['Quantidade']
                                st.bar_chart(erro_chart)
                            
                            with col_comp_viz2:
                                st.markdown("**Severidade**")
                                for idx, row in erros_com_qtd.iterrows():
                                    st.caption(f"{row['Tipo']}: {row['Severidade']}")
                    
                    registrar_log(f"🛠️ Validação de compliance executada com {len(validacoes)} verificações.")
                    
                elif tool_name == 'demissao':
                    st.session_state['df_tratado'] = processing.calcular_demissao_rh(df_tratado, *params)
                    registrar_log(f"🛠️ Cálculo de demissão aplicado na coluna {params[3]}.")
                    st.success("✅ Cálculo de demissão concluído!")

            except Exception as e:
                st.error(f"❌ Erro no processamento de RH: {e}")
                import traceback
                st.caption(traceback.format_exc())

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
