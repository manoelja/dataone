import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import random

def gerar_cpf_valido():
    nine_digits = [random.randint(0, 9) for _ in range(9)]
    for _ in range(2):
        val = sum([(len(nine_digits) + 1 - i) * v for i, v in enumerate(nine_digits)]) % 11
        nine_digits.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, nine_digits[0:3]))}.{''.join(map(str, nine_digits[3:6]))}.{''.join(map(str, nine_digits[6:9]))}-{''.join(map(str, nine_digits[9:11]))}"

def gerar_cnpj_valido():
    cnpj = [random.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for _ in range(2):
        pesos = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if len(cnpj) == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        val = sum([pesos[i] * v for i, v in enumerate(cnpj)]) % 11
        cnpj.append(0 if val < 2 else 11 - val)
    return f"{''.join(map(str, cnpj[0:2]))}.{''.join(map(str, cnpj[2:5]))}.{''.join(map(str, cnpj[5:8]))}/{''.join(map(str, cnpj[8:12]))}-{''.join(map(str, cnpj[12:14]))}"

# 1. CONFIGURAÇÃO DA PÁGINA
st.set_page_config(page_title='DATAONE', page_icon='🎲', layout='wide')

st.markdown("""
# 🎲 DATAONE <span style='font-size: 18px; color: #888;'>| Central Inteligente de Data processing</span>
##### Faça upload, limpe, padronize, aplique regras de negócio e exporte seus dados sem planilhas quebradas.
---
""", unsafe_allow_html=True)

# Inicializa um log de auditoria na sessão se não existir
if 'audit_log' not in st.session_state:
    st.session_state['audit_log'] = []

def registrar_log(mensagem):
    """Função auxiliar para registrar ações no histórico de auditoria"""
    st.session_state['audit_log'].append(mensagem)

# SIDEBAR: Upload de Arquivo e Logs
with st.sidebar:
    st.header("📥 Entrada de Dados")
    file_upload = st.file_uploader('Faça upload do seu arquivo:', type=['xlsx', 'csv'])
    
    st.divider()
    st.header("🔍Histórico🌐")
    if st.session_state['audit_log']:
        for log in reversed(st.session_state['audit_log']):
            st.caption(log)
    else:
        st.caption("Nenhuma ação realizada ainda.")

if file_upload:
    # 2. LEITURA E CARREGAMENTO INICIAL
    id_arquivo = f"{file_upload.name}_{file_upload.size}"
    # Usamos o st.cache_data para evitar ler o arquivo do zero a cada clique na tela
    @st.cache_data(ttl=600)
    def carregar_dados(file):
        registrar_log(f"📥 Arquivo '{file.name}' carregado.")
        if file.name.endswith('.xlsx'):
            return pd.read_excel(file)
        else:
            return pd.read_csv(file, sep=';', decimal=',')

    df_original = carregar_dados(file_upload)
    id_arquivo_atual = f"{file_upload.name}_{file_upload.size}"
    if "ultimo_id_arquivo" not in st.session_state or st.session_state["ultimo_id_arquivo"] != id_arquivo_atual:
        st.session_state["ultimo_id_arquivo"] = id_arquivo_atual
        
        # Lista de todas as chaves de texto e seleções que precisam zerar
        chaves_para_limpar = [
            "nome_da_nova_coluna_clean", 
            "txt_padrao_input_clean",
            "coluna_deletar_clean",
            "col_esquerda_pos",
            "col_direita_pos",
            "tipo_val_padrao_clean"
        ]
        
        # Apaga o passado da memória
        for chave in chaves_para_limpar:
            if chave in st.session_state:
                del st.session_state[chave]
                
        # Zera também o dataframe tratado para carregar o novo
        st.session_state['df_tratado'] = df_original.copy()
        st.rerun()
    # =========================================================================
    # ADICIONADO AQUI: CONTROLADOR DE MEMÓRIA E BOTÃO DE RESET (CLIQUE ÚNICO)
    # =========================================================================
    if 'df_tratado' not in st.session_state:
        st.session_state['df_tratado'] = df_original.copy()
        registrar_log("🔄 Base de dados inicializada.")

    # Botão simples que aparece logo acima das abas
    if st.button("🔄 Resetar todas as alterações", type="secondary"):
        st.session_state['df_tratado'] = df_original.copy()
        registrar_log("🔄 Base de dados resetada para o formato original.")
        st.success("Tabela resetada com sucesso! Todas as abas foram limpas.")
        st.rerun()

    # Substituímos o seu antigo 'df_tratado = df_original.copy()' por este:
    df_tratado = st.session_state['df_tratado']
    # =========================================================================
    
    columns_fmt = {}

    # CRIANDO AS ABAS DO SISTEMA WIZARD
    aba_diag, aba_limpeza, aba_texto, aba_format, aba_rh, aba_export = st.tabs([
        "🔍 1. Diagnóstico", 
        "🧼 2. Limpeza de Dados", 
        "🔤 3. Padronização de Texto",
        "⚙️ 4. Formatação Visual", 
        "🛠️ 5. Regras de RH", 
        "💾 6. Exportar Base"
    ])
    # =========================================================================
    # ABA 1: DIAGNÓSTICO DO ARQUIVO
    # =========================================================================
    with aba_diag:
        st.subheader("🔍 Análise de Saúde dos Dados")
        
        df_atual = st.session_state['df_tratado']
        
        # Cartões de Métricas Globais
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Linhas", df_atual.shape[0])      
        m2.metric("Total de Colunas", df_atual.shape[1])       
        m3.metric("Células Vazias", df_atual.isna().sum().sum()) 
        
        linhas_duplicadas = df_atual.duplicated().sum()         
        if linhas_duplicadas > 0:
            m4.metric("Linhas Duplicadas", linhas_duplicadas, delta=f"-{linhas_duplicadas} alertas", delta_color="inverse")
        else:
            m4.metric("Linhas Duplicadas", 0)

        st.divider()
        
        # Tabela Detalhada de Tipos e Faltantes
        st.markdown("### Perfil de Metadados por Coluna")
        df_tipos = pd.DataFrame({
            'Coluna': df_atual.columns,                        
            'Tipo Nativo': df_atual.dtypes.astype(str),        
            'Valores Preenchidos (%)': ((df_atual.notna().sum() / len(df_atual)) * 100).round(1) if len(df_atual) > 0 else 0, # 🟢 Trocado por df_atual e adicionada trava para tabela vazia
            'Valores Nulos (Qtd)': df_atual.isna().sum()       
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
    # =========================================================================
    # ABA 2: LIMPEZA DE DADOS (DATA CLEANING) - VERSÃO CORRIGIDA (SEM CHAVES DUPLICADAS)
    # =========================================================================
    with aba_limpeza:
        st.subheader("🧼 Tratamento de Anomalias e Nulos")
        
        col_limp_1, col_limp_2 = st.columns(2)
 #################################################################      
        with col_limp_1:
            st.markdown("#### Remover Duplicados")
               
            remover_dup_geral = st.checkbox("Remover linhas 100% idênticas na tabela", value=False, key=f"dup_geral_{id_arquivo}")
            ccolunas_chave_dup = st.multiselect("Ou escolher colunas-chave para checar duplicidade (Ex: CPF, ID):", options=st.session_state['df_tratado'].columns, key=f"dup_chave_{id_arquivo}")

            if remover_dup_geral:
                st.session_state['df_tratado'] = st.session_state['df_tratado'].drop_duplicates()
                remover_dup_geral = False 
                
            if ccolunas_chave_dup:
                st.session_state['df_tratado'] = st.session_state['df_tratado'].drop_duplicates(subset=ccolunas_chave_dup)
                registrar_log(f"🧼 Duplicados removidos com base nas colunas {ccolunas_chave_dup}.")
        
        with col_limp_2:
            st.markdown("#### Tratar Valores Faltantes (Nulos)")
            st.markdown("Tratar os valores vazios é essencial para evitar erros ")
            
            # 1. Criamos uma chave para controlar as colunas selecionadas de forma segura
            chave_controle = f"selecionadas_{id_arquivo}"
            if chave_controle not in st.session_state:
                st.session_state[chave_controle] = []

            # 2. O multiselect usa o st.session_state[chave_controle] como padrão (default)
            colunas_nulas = st.multiselect(
                "Selecione colunas para tratar valores vazios:", 
                options=st.session_state['df_tratado'].columns, 
                default=st.session_state[chave_controle], 
                key=f"nulos_cols_{id_arquivo}"
            )
            
            # Sincroniza o que o usuário escolheu com a nossa variável de controle
            st.session_state[chave_controle] = colunas_nulas

            if colunas_nulas:
                estrategia_nulos = st.radio(
                    "O que fazer com os vazios dessas colunas?", 
                    options=["Preencher com Zero (0)", "Preencher com 'Não Informado'", "Excluir a linha inteira"],
                    key=f"estrategia_nulos_{id_arquivo}"
                )

                if st.button("Aplicar Tratamento de Nulos", key=f"btn_nulos_{id_arquivo}"):
                    df_copia = st.session_state['df_tratado'].copy()
                    # Aplica os tratamentos normalmente
                    if estrategia_nulos == "Preencher com Zero (0)":
                        for col in colunas_nulas:
                            # 🟢 GARANTIA ANTI-FALHA: Converte para numérico jogando erros para NaN, limpa strings 'nan' e bota o 0
                            df_copia[col] = pd.to_numeric(df_copia[col], errors='coerce')
                            df_copia[col] = df_copia[col].fillna(0)
                            # Trata o caso de a coluna ser lida como inteira pelo Streamlit
                            df_copia[col] = df_copia[col].replace({"nan": 0, "NaN": 0})
                            
                    elif estrategia_nulos == "Preencher com 'Não Informado'":
                        for col in colunas_nulas:
                            df_copia[col] = None
                            
                    elif estrategia_nulos == "Excluir a linha inteira":
                        for col in colunas_nulas:
                            df_copia[col] = ''
                    
                    # Atualiza o estado global com os dados modificados
                    st.session_state['df_tratado'] = df_copia
                    st.session_state[chave_controle] = [] # Limpa a seleção e fecha os campos extras
                    
                    registrar_log(f"🧼 Tratados valores nulos nas colunas {colunas_nulas} usando: {estrategia_nulos}.")
                    st.success("Tratamento de nulos aplicado com sucesso!")
                    st.rerun()
################################################################
        # --- SEÇÃO: EXCLUIR COLUNA EXISTENTE ---
        st.divider()
        st.markdown("#### ❌ Excluir Coluna da Tabela")
        
        coluna_para_excluir = st.selectbox(
            "Selecione a coluna que deseja remover permanentemente:", 
            options=["Selecione..."] + list(st.session_state['df_tratado'].columns),
            key=f"coluna_deletar_{id_arquivo}"
        )

        if st.button("Remover Coluna Permanentemente", type="primary", key=f"btn_excluir_{id_arquivo}"):
            if coluna_para_excluir == "Selecione...":
                st.error("⚠️ Por favor, selecione uma coluna válida para exclusão.")
            else:
                st.session_state['df_tratado'] = st.session_state['df_tratado'].drop(columns=[coluna_para_excluir])
                registrar_log(f"❌ Coluna '{coluna_para_excluir}' foi excluída da base de dados.")
                st.success(f"Coluna '{coluna_para_excluir}' removida com sucesso!")
                st.rerun()

        # --- SEÇÃO: INSERIR NOVA COLUNA ENTRE DUAS EXISTENTES ---
        st.divider()
        st.markdown("#### ➕ Inserir Nova Coluna Entre Duas Existentes")
        
        nome_nova_coluna = st.text_input("Digite o nome da nova coluna:", placeholder="Ex: status_pagamento...", key=f"nome_da_nova_coluna_clean_{id_arquivo}")
        
        c_pos1, c_pos2 = st.columns(2)
        with c_pos1:
            col_esquerda = st.selectbox("Coluna da Esquerda (X):", options=list(st.session_state['df_tratado'].columns), key=f"col_esquerda_pos_{id_arquivo}")

        with c_pos2:
            idx_esq_atual = list(st.session_state['df_tratado'].columns).index(col_esquerda)
            opcoes_direita = list(st.session_state['df_tratado'].columns)[idx_esq_atual + 1:]
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
            valor_padrao = st.text_input(
                "Digite o texto padrão para todas as linhas:", 
                value="Padrão", 
                key=f"txt_padrao_input_clean_{id_arquivo}"
            )
            
        if st.button("Inserir Coluna no Meio", key=f"btn_inserir_{id_arquivo}"):
            if nome_nova_coluna.strip() == "":
                st.error("⚠️ Por favor, digite um nome válido para a coluna.")
            elif nome_nova_coluna in st.session_state['df_tratado'].columns:
                st.error("⚠️ Já existe uma coluna com esse nome na tabela.")
            else:
                if col_direita:
                    idx_posicao = st.session_state['df_tratado'].columns.get_loc(col_direita)
                else:
                    idx_posicao = len(st.session_state['df_tratado'].columns)
                    
                st.session_state['df_tratado'].insert(idx_posicao, nome_nova_coluna, valor_padrao)
                    
                registrar_log(f"➕ Coluna '{nome_nova_coluna}' inserida entre '{col_esquerda}' e '{col_direita}'.")
                st.success(f"Coluna '{nome_nova_coluna}' criada com sucesso!")
                st.rerun()
        
        # --- SEÇÃO: FAXINA AUTOMÁTICA E VISUALIZAÇÃO ---
        st.divider()
        st.markdown("#### 🧼 Faxina Invisível Automática")
        limpar_espacos = st.checkbox("Aparar espaços em branco fantasmas (Strip) de todas as células de texto", value=True, key=f"strip_{id_arquivo}")
        
        if limpar_espacos:
            for col in st.session_state['df_tratado'].select_dtypes(include=['object']).columns:
                st.session_state['df_tratado'][col] = st.session_state['df_tratado'][col].astype(str).str.strip()
                
        st.divider()
        st.markdown("##### 📊 Visualização Parcial ")
        st.dataframe(st.session_state['df_tratado'], hide_index=True, use_container_width=True)
    # =========================================================================
    # ABA 3: PADRONIZAÇÃO DE TEXTO E DOCUMENTOS
    # =========================================================================
    with aba_texto:
        st.subheader("🔤 Formatação de Strings e Cadastro")
        
        c_txt1, c_txt2 = st.columns(2)
        
        with c_txt1:
            st.markdown("#### Caixa do Texto")
            cols_caixa = st.multiselect("Selecionar colunas para ajustar LETRAS:", options=st.session_state['df_tratado'].columns, key='txt_caixa')
            if cols_caixa:
                modo_caixa = st.selectbox("Formato desejado:", ["TUDO EM MAIÚSCULO", "tudo em minúsculo", "Primeira Letra Maiúscula (Capitalize)"])
                if st.button("Ajustar Caixa de Texto"):
                    for c in cols_caixa:
                        if modo_caixa == "TUDO EM MAIÚSCULO":
                            st.session_state['df_tratado'][c] = st.session_state['df_tratado'][c].astype(str).str.upper()
                        elif modo_caixa == "tudo em minúsculo":
                            st.session_state['df_tratado'][c] = st.session_state['df_tratado'][c].astype(str).str.lower()
                        else:
                            st.session_state['df_tratado'][c] = st.session_state['df_tratado'][c].astype(str).str.title()
                    registrar_log(f"🔤 Ajustada caixa de texto das colunas {cols_caixa} para {modo_caixa}.")
                    st.success("Texto padronizado!")

        with c_txt2:
            st.markdown("#### 🆔 Gerador de ID Sequencial")
            col_id_destino = st.selectbox("Escolha uma coluna para substituir por IDs (ou criar uma nova):", 
                                          options=["Criar nova coluna 'id_gerado'"] + list(st.session_state['df_tratado'].columns))
            valor_inicio = st.number_input("Iniciar contagem a partir de:", min_value=0, value=1, step=1)
            
            if st.button("Gerar Sequência de IDs"):
                nome_col_id = 'id_gerado' if col_id_destino == "Criar nova coluna 'id_gerado'" else col_id_destino
                # Cria a sequência matemática baseada no tamanho do DataFrame atual
                st.session_state['df_tratado'][nome_col_id] = range(int(valor_inicio), int(valor_inicio) + len(st.session_state['df_tratado']))
                registrar_log(f"🆔 Gerada coluna de ID '{nome_col_id}' começando em {valor_inicio}.")
                st.success(f"IDs gerados com sucesso na coluna '{nome_col_id}'!")

        st.divider()

        st.markdown("#### 🇧🇷 Máscaras e Geradores de Documentos")
        # Adicionamos "Substituir por CPF Válido" e "Substituir por CNPJ Válido" nas opções de ação
        acao_doc = st.selectbox("O que deseja fazer com os documentos?", 
                                options=[
                                    "Apenas aplicar máscara em dados existentes", 
                                    "Substituir tudo por CPFs Válidos Aleatórios", 
                                    "Substituir tudo por CNPJs Válidos Aleatórios"
                                ])
        
        col_doc = st.selectbox("Selecione a coluna alvo:", ["Selecione..."] + list(st.session_state['df_tratado'].columns), key='col_doc_alvo')
        
        if col_doc != "Selecione...":
            if acao_doc == "Apenas aplicar máscara em dados existentes":
                tipo_doc = st.selectbox("Tipo de documento cadastrado:", ["CPF (11 dígitos)", "CNPJ (14 dígitos)"])
                if st.button("Aplicar Máscara"):
                    df_tratado[col_doc] = df_tratado[col_doc].astype(str).str.replace(r'\D', '', regex=True)
                    
                    def aplicar_cpf(val):
                        val = val.zfill(11)
                        return f"{val[0:3]}.{val[3:6]}.{val[6:9]}-{val[9:11]}" if len(val) == 11 else val
                    
                    def aplicar_cnpj(val):
                        val = val.zfill(14)
                        return f"{val[0:2]}.{val[2:5]}.{val[5:8]}/{val[8:12]}-{val[12:14]}" if len(val) == 14 else val
                    
                    df_tratado[col_doc] = df_tratado[col_doc].apply(aplicar_cpf if "CPF" in tipo_doc else aplicar_cnpj)
                    registrar_log(f"🔤 Aplicada máscara na coluna {col_doc}.")
                    st.success("Máscara aplicada!")
                    
            elif acao_doc == "Substituir tudo por CPFs Válidos Aleatórios":
                if st.button("Gerar CPFs Fake Válidos"):
                    # Preenche a coluna inteira chamando a função de sorteio para cada linha
                    df_tratado[col_doc] = [gerar_cpf_valido() for _ in range(len(df_tratado))]
                    registrar_log(f"🎲 Coluna {col_doc} preenchida com CPFs válidos gerados.")
                    st.success("CPFs gerados de forma randômica!")
                    
            elif acao_doc == "Substituir tudo por CNPJs Válidos Aleatórios":
                if st.button("Gerar CNPJs Fake Válidos"):
                    # Preenche a coluna inteira chamando a função de sorteio para cada linha
                    df_tratado[col_doc] = [gerar_cnpj_valido() for _ in range(len(df_tratado))]
                    registrar_log(f"🎲 Coluna {col_doc} preenchida com CNPJs válidos gerados.")
                    st.success("CNPJs gerados de forma randômica!")
        with aba_texto:
        # ... seu código atual de texto (Caixa alta/baixa, máscaras CPF) ...
        
        #  ADICIONE ISSO NO FINAL DA ABA 3:
            st.divider()
            st.markdown("##### 📊 Visualização Parcial (Pós Padronização de Texto)")
            st.dataframe(st.session_state['df_tratado'], hide_index=True, column_config=columns_fmt, use_container_width=True)
    # =========================================================================
    # ABA 4: CONFIGURAÇÃO DE MOEDAS E DATAS PADRÃO
    # =========================================================================
    with aba_format:
        st.subheader("⚙️ Configurações Visuais de Exibição")
        c_moeda_sel, c_data_sel = st.columns(2)
        
        dict_formatos_moeda = {}
        dict_formatos_data = {}
        
        with c_moeda_sel:
            colunas_moeda = st.multiselect('💵 Colunas de Valor/Moeda:', options=st.session_state['df_tratado'].columns, key='ctrl_moeda')
            for col in colunas_moeda:
                formato = st.selectbox(f'Formato para "{col}":', 
                                       options=['R$ (Real - Brasil)', '$ (Dólar - EUA)', '€ (Euro)', 'Apenas Decimal (1.250,00)'], 
                                       key=f'fmt_moeda_{col}')
                dict_formatos_moeda[col] = formato

        with c_data_sel:
            colunas_data = st.multiselect('📅 Colunas de Data Comum:', options=st.session_state['df_tratado'].columns, key='ctrl_data')
            for col in colunas_data:
                formato = st.selectbox(f'Formato para "{col}":', 
                                       options=['DD/MM/YYYY', 'YYYY-MM-DD', 'DD/MM/YYYY HH:MM'], 
                                       key=f'fmt_data_{col}')
                dict_formatos_data[col] = formato
        with aba_format:
        # ... seu código atual de seleção de moedas e datas ...
        
        #  ADICIONE ISSO NO FINAL DA ABA 4:
            st.divider()
            st.markdown("##### 📊 Visualização Parcial (Com as Formatações Escolhidas)")
            st.dataframe(st.session_state['df_tratado'], hide_index=True, column_config=columns_fmt, use_container_width=True)        

    # =========================================================================
    # ABA 5: REGRA DE NEGÓCIO (RH - CÁLCULO DE DEMISSÃO)
    # =========================================================================
    with aba_rh:
        st.subheader("🛠️ Regra de Calendário de RH")
        st.caption("Calcule dinamicamente a data exata de desligamento com base na data de admissão e tempo de casa.")
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            col_admissao = st.selectbox('Data de Admissão:', options=['Não aplicar...'] + list(st.session_state['df_tratado'].columns), key='sb_admissao')
        with c2:
            col_tempo = st.selectbox('Tempo de Casa (Anos,Meses):', options=['Não aplicar...'] + list(st.session_state['df_tratado'].columns), key='sb_tempo')
        with c3:
            col_desligado = st.selectbox('Coluna "Desligado?":', options=['Não aplicar...'] + list(st.session_state['df_tratado'].columns), key='sb_desligado')
        with c4:
            col_demissao = st.selectbox('Coluna Destino (Data de Demissão):', options=['Criar nova coluna'] + list(st.session_state['df_tratado'].columns), key='sb_demissao')

        if col_demissao == 'Criar nova coluna':
            col_demissao = 'data_demissao_calculada'

        calculo_rh_ativo = (col_admissao != 'Não aplicar...' and col_tempo != 'Não aplicar...' and col_desligado != 'Não aplicar...')
        
        if calculo_rh_ativo:
            try:
                df_tratado[col_admissao] = pd.to_datetime(df_tratado[col_admissao], dayfirst=True, errors='coerce')
                tempo_limpo = df_tratado[col_tempo].astype(str).str.strip().str.replace(',', '.', regex=False)
                df_tratado[col_demissao] = pd.NaT
                
                for idx, row in df_tratado.iterrows():
                    status = str(row[col_desligado]).strip().upper()
                    if status in ['TRUE', '1', 'SIM', 'S', 'DESLIGADO']:
                        dt_adm = df_tratado.loc[idx, col_admissao]
                        tempo_val = tempo_limpo.loc[idx]
                        
                        if pd.notnull(dt_adm) and tempo_val != 'nan' and tempo_val != '':
                            if '.' not in tempo_val:
                                tempo_val = tempo_val + '.0'
                                
                            partes = tempo_val.split('.')
                            qtd_anos = int(partes[0]) if partes[0].isdigit() else 0
                            qtd_meses = int(partes[1]) if partes[1].isdigit() else 0
                            
                            meses_totais = (qtd_anos * 12) + qtd_meses
                            df_tratado.loc[idx, col_demissao] = dt_adm + pd.DateOffset(months=meses_totais)
                            
                df_tratado[col_demissao] = pd.to_datetime(df_tratado[col_demissao]).dt.tz_localize(None)
                st.success("🎉 Coluna de Demissão calculada com sucesso!")
            except Exception as e:
                st.error(f"Erro no processamento do cálculo de demissão: {e}")

        with aba_rh:
        # ... seu código atual de cálculo de rescisão/demissão ...
        
        #  ADICIONE ISSO NO FINAL DA ABA 5:
            st.divider()
            st.markdown("##### 📊 Visualização Parcial (Com Cálculos de RH Aplicados)")
            st.dataframe(st.session_state['df_tratado'], hide_index=True, column_config=columns_fmt, use_container_width=True)
    # =========================================================================
    # PROCESSAMENTO FINAL DAS MÁSCARAS DO STREAMLIT DE ACORDO COM SELEÇÕES
    # =========================================================================
    for coluna in st.session_state['df_tratado'].columns:
        if coluna == col_demissao and calculo_rh_ativo:
            columns_fmt[coluna] = st.column_config.DatetimeColumn(coluna, format="DD/MM/YYYY")
            
        elif coluna in colunas_moeda:
            if st.session_state['df_tratado'][coluna].dtype == 'object':
                st.session_state['df_tratado'][coluna] = (
                    st.session_state['df_tratado'][coluna].astype(str)
                    .str.replace(r'[R\$\s\.€]', '', regex=True)
                    .str.replace(',', '.', regex=False)
                )
            df_tratado[coluna] = pd.to_numeric(df_tratado[coluna], errors='coerce')
            
            fmt_escolhido = dict_formatos_moeda[coluna]
            if fmt_escolhido == 'R$ (Real - Brasil)':
                columns_fmt[coluna] = st.column_config.NumberColumn(coluna, format="R$ %,.2f")
            elif fmt_escolhido == '$ (Dólar - EUA)':
                columns_fmt[coluna] = st.column_config.NumberColumn(coluna, format="$ %,.2f")
            elif fmt_escolhido == '€ (Euro)':
                columns_fmt[coluna] = st.column_config.NumberColumn(coluna, format="€ %,.2f")
            else:
                columns_fmt[coluna] = st.column_config.NumberColumn(coluna, format="%,.2f")

        elif coluna in colunas_data or (coluna == col_admissao and calculo_rh_ativo):
            df_tratado[coluna] = pd.to_datetime(df_tratado[coluna], dayfirst=True, errors='coerce')
            fmt_escolhido = dict_formatos_data.get(coluna, 'DD/MM/YYYY')
            columns_fmt[coluna] = st.column_config.DatetimeColumn(coluna, format=fmt_escolhido)

        elif coluna in df_original.columns:
            if coluna != col_tempo:
                try:
                    df_tratado[coluna] = pd.to_numeric(df_tratado[coluna])
                except:
                    pass
    # =========================================================================
    # ABA 6: VISUALIZAÇÃO FINAL E DOWNLOAD
    # =========================================================================
    with aba_export:
        st.subheader("📊 Visualização Prévia dos Dados Tratados")
        st.dataframe(df_tratado, hide_index=True, column_config=columns_fmt, use_container_width=True)
        
        st.divider()
        st.subheader("💾 Exportar para Excel (.xlsx)")
        
        # Preparação do arquivo para download com OpenPyXL
        df_download = df_tratado.copy()
        for col in df_download.columns:
            if pd.api.types.is_datetime64_any_dtype(df_download[col]):
                fmt_excel_str = '%d/%m/%Y'
                if dict_formatos_data.get(col) == 'YYYY-MM-DD':
                    fmt_excel_str = '%Y-%m-%d'
                elif dict_formatos_data.get(col) == 'DD/MM/YYYY HH:MM':
                    fmt_excel_str = '%d/%m/%Y %H:%M'
                    
                df_download[col] = df_download[col].dt.strftime(fmt_excel_str)
                df_download[col] = df_download[col].replace('NaT', '')

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_download.to_excel(writer, index=False, sheet_name='Dados Tratados')
            
            workbook = writer.book
            worksheet = writer.sheets['Dados Tratados']
            
            mapa_formatos_excel = {
                'R$ (Real - Brasil)': 'R$ #,##0.00;_R$ (#,##0.00);_R$ "-"_._;_(@_)',
                '$ (Dólar - EUA)': '"$"#,##0.00_-;[Red]("$"#,##0.00);"-"_._;_-@_-',
                '€ (Euro)': '[$€-2] #,##0.00;-[$€-2] #,##0.00;"-"??;_@_',
                'Apenas Decimal (1.250,00)': '#,##0.00'
            }
            
            for idx, col_name in enumerate(df_download.columns):
                if col_name in colunas_moeda:
                    tipo_fmt_usuario = dict_formatos_moeda[col_name]
                    formato_excel_final = mapa_formatos_excel[tipo_fmt_usuario]
                    
                    for row in range(2, len(df_download) + 2):
                        worksheet.cell(row=row, column=idx+1).number_format = formato_excel_final

        st.download_button(
            label="📥 Baixar Base de Dados Tratada e Formatada",
            data=buffer.getvalue(),
            file_name="base_dados_clean_pro.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )