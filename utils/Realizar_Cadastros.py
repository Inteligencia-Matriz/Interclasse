# utils/Realizar_Cadastros.py
import streamlit as st
import pandas as pd
import logging
import os
from utils.sheets import *

# Configuração de logging robusta
try:
    # Cria o diretório logs se não existir
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    logging.basicConfig(
        filename=os.path.join(log_dir, 'app.log'),
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s',
        encoding='utf-8'
    )
except Exception as e:
    # Fallback: logging sem arquivo se houver erro
    logging.basicConfig(
        level=logging.ERROR,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.warning(f"Erro ao configurar arquivo de log: {e}. Usando logging sem arquivo.")

# NOVA FUNÇÃO: Callback para atualização imediata do session_state
def sync_modalidade_selection(aluno_id, numero_modalidade):
    """Atualiza imediatamente o session_state quando uma modalidade é selecionada"""
    try:
        # Obtém a chave do selectbox que foi alterado
        key = f"modal{numero_modalidade}_{aluno_id}"
        
        # Obtém o valor selecionado diretamente do session_state do Streamlit
        if key in st.session_state:
            valor_selecionado = st.session_state[key]
            
            # Atualiza o session_state organizado
            if (aluno_id in st.session_state.cadastro['selecoes_alunos'] and 
                not st.session_state.cadastro['selecoes_alunos'][aluno_id].get(f'modalidade{numero_modalidade}_registrada', False)):
                
                st.session_state.cadastro['selecoes_alunos'][aluno_id][f'modalidade{numero_modalidade}'] = valor_selecionado
                
    except Exception as e:
        logging.error(f"Erro no callback sync_modalidade_selection: {e}")

@st.cache_data(ttl=600)
def carregar_modalidades_completas():
    """Carrega todas as informações da aba MODALIDADES com tratamento robusto"""
    try:
        df_modalidades = load_full_sheet_as_df('MODALIDADES')
        
        if df_modalidades.empty:
            st.warning("Nenhuma modalidade encontrada na aba MODALIDADES")
            return pd.DataFrame()
        
        # Verifica e padroniza os nomes das colunas
        if len(df_modalidades.columns) >= 4:
            # Usa apenas as primeiras 4 colunas essenciais
            df_modalidades = df_modalidades.iloc[:, :7]  # Pega até 7 colunas se existirem
            if len(df_modalidades.columns) >= 7:
                df_modalidades.columns = ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga', 'Limite_Vagas', 'Inscritos', 'Vagas_Restantes']
            else:
                # Preenche colunas faltantes
                colunas_base = ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga']
                colunas_extras = ['Limite_Vagas', 'Inscritos', 'Vagas_Restantes'][:len(df_modalidades.columns)-4]
                df_modalidades.columns = colunas_base + colunas_extras
        
        # Limpeza e tratamento dos dados
        for col in ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga']:
            if col in df_modalidades.columns:
                df_modalidades[col] = df_modalidades[col].astype(str).str.strip()
        
        # CORREÇÃO ADICIONAL: Converter colunas numéricas para o tipo correto
        colunas_numericas = ['Limite_Vagas', 'Inscritos', 'Vagas_Restantes']
        for col in colunas_numericas:
            if col in df_modalidades.columns:
                # Converte para numérico, forçando erros para NaN (coerce)
                df_modalidades[col] = pd.to_numeric(df_modalidades[col], errors='coerce')
                # Preenche NaN com 0
                df_modalidades[col] = df_modalidades[col].fillna(0)
        
        # Remove linhas completamente vazias
        df_modalidades = df_modalidades.dropna(how='all')
        
        return df_modalidades
        
    except Exception as e:
        logging.exception("Erro ao carregar modalidades completas")
        st.error("Falha ao carregar modalidades. Tente novamente.")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def carregar_alunos_permitidos():
    """Carrega os dados dos alunos que têm permissão da aba INSCRITOS-ECOMMERCE"""
    try:
        df_alunos = load_full_sheet_as_df('INSCRITOS-ECOMMERCE')
        
        if df_alunos.empty:
            st.warning("Nenhum aluno encontrado na aba INSCRITOS-ECOMMERCE")
            return pd.DataFrame()
        
        # Usa as primeiras 4 colunas independentemente do nome
        if len(df_alunos.columns) >= 4:
            df_alunos = df_alunos.iloc[:, :4]
            df_alunos.columns = ['Unidade', 'Nome do Aluno', 'RA', 'Turma do Aluno']
            
            # Limpeza dos dados
            for col in df_alunos.columns:
                df_alunos[col] = df_alunos[col].astype(str).str.strip()
            
            # Remove linhas vazias
            df_alunos = df_alunos.dropna(how='all')
            df_alunos = df_alunos[df_alunos['Unidade'] != '']
            
        else:
            st.error("A planilha de alunos não tem colunas suficientes")
            return pd.DataFrame()
        
        return df_alunos
        
    except Exception as e:
        logging.exception("Erro ao carregar alunos permitidos")
        st.error("Falha ao carregar lista de alunos. Tente novamente.")
        return pd.DataFrame()

def carregar_modalidades(unidade_usuario, genero_filtro=None, apenas_com_vaga=True):
    """CARREGAMENTO UNIFICADO - Carrega modalidades com filtros flexíveis"""
    try:
        df_modalidades = carregar_modalidades_completas()
        
        if df_modalidades.empty:
            return []
        
        # Filtra por unidade
        modalidades_filtradas = df_modalidades[df_modalidades['Unidade'] == unidade_usuario]
        
        # Filtra por vagas se solicitado
        if apenas_com_vaga:
            modalidades_filtradas = modalidades_filtradas[
                (modalidades_filtradas['Tem_Vaga'] != 'NÃO') & 
                (modalidades_filtradas['Vagas_Restantes'] > 0)
            ]
        
        # Filtro adicional por gênero se especificado
        if genero_filtro and genero_filtro != "Todos":
            modalidades_filtradas = modalidades_filtradas[
                (modalidades_filtradas['Genero'] == genero_filtro) | 
                (modalidades_filtradas['Genero'] == 'M / F')
            ]
        
        # Cria lista formatada
        opcoes_modalidades = []
        for _, row in modalidades_filtradas.iterrows():
            opcoes_modalidades.append({
                'texto': row['Modalidade'],
                'modalidade': row['Modalidade'],
                'genero': row['Genero'],
                'unidade': row['Unidade'],
                'limite_vagas': row['Limite_Vagas'],
                'inscritos': row['Inscritos'],
                'vagas_restantes': row['Vagas_Restantes'],
                'tem_vaga': row['Tem_Vaga']
            })
        
        return opcoes_modalidades
        
    except Exception as e:
        logging.exception(f"Erro ao carregar modalidades para unidade {unidade_usuario}")
        st.error("Falha ao carregar modalidades. Tente novamente.")
        return []

def calcular_vagas_utilizadas(selecoes_alunos, modalidades_filtradas):
    """Calcula quantas vagas já foram selecionadas para cada modalidade"""
    vagas_utilizadas = {}
    
    for modalidade in modalidades_filtradas:
        vagas_utilizadas[modalidade['modalidade']] = 0
    
    for aluno_id, selecoes in selecoes_alunos.items():
        modalidades_aluno = [
            selecoes['modalidade1'],
            selecoes['modalidade2'], 
            selecoes['modalidade3']
        ]
        
        for modalidade_texto in modalidades_aluno:
            if modalidade_texto != "Nenhuma" and modalidade_texto in vagas_utilizadas:
                vagas_utilizadas[modalidade_texto] += 1
    
    return vagas_utilizadas

def atualizar_opcoes_select(modalidades_filtradas, vagas_utilizadas, selecoes_aluno_atual=None):
    """Atualiza as opções do selectbox considerando as vagas utilizadas E mantendo seleções atuais"""
    opcoes_select = ["Nenhuma"]
    
    # Adiciona apenas modalidades com vagas disponíveis
    for modalidade in modalidades_filtradas:
        vagas_restantes_base = modalidade['vagas_restantes']
        if isinstance(vagas_restantes_base, str):
            try:
                vagas_restantes_base = float(vagas_restantes_base)
            except ValueError:
                vagas_restantes_base = 0
        
        # Calcula vagas disponíveis considerando as seleções atuais
        vagas_selecionadas = vagas_utilizadas.get(modalidade['modalidade'], 0)
        vagas_disponiveis_agora = vagas_restantes_base - vagas_selecionadas
        
        # Só inclui modalidade se tiver vagas disponíveis
        if vagas_disponiveis_agora > 0:
            opcoes_select.append(modalidade['modalidade'])
    
    # NOVA LÓGICA: Adiciona as seleções atuais do aluno mesmo que não estejam mais disponíveis
    if selecoes_aluno_atual:
        selecoes_atuais = [
            selecoes_aluno_atual['modalidade1'],
            selecoes_aluno_atual['modalidade2'],
            selecoes_aluno_atual['modalidade3']
        ]
        
        for selecao in selecoes_atuais:
            if (selecao != "Nenhuma" and 
                selecao not in opcoes_select and 
                any(m['modalidade'] == selecao for m in modalidades_filtradas)):
                # Adiciona a seleção atual mesmo que não tenha vaga disponível
                opcoes_select.append(selecao)
    
    return opcoes_select

def contar_modalidades_selecionadas(selecoes_aluno):
    """Conta quantas modalidades um aluno já selecionou"""
    modalidades = [selecoes_aluno['modalidade1'], selecoes_aluno['modalidade2'], selecoes_aluno['modalidade3']]
    return sum(1 for m in modalidades if m != "Nenhuma")

def verificar_duplicatas_modalidades(selecoes_aluno):
    """Verifica se há modalidades duplicadas nas seleções do aluno"""
    modalidades = [selecoes_aluno['modalidade1'], selecoes_aluno['modalidade2'], selecoes_aluno['modalidade3']]
    modalidades_validas = [m for m in modalidades if m != "Nenhuma"]
    modalidades_unicas = set(modalidades_validas)
    
    if len(modalidades_validas) != len(modalidades_unicas):
        return False, modalidades_validas
    return True, modalidades_validas

@st.cache_data(ttl=600)
def carregar_inscricoes_existentes_detalhadas():
    """Carrega as inscrições já existentes com detalhes das modalidades por aluno"""
    try:
        df_inscritos = load_full_sheet_as_df('INSCRITOS-UNIDADE')
        if df_inscritos.empty:
            return {}
        
        if len(df_inscritos.columns) >= 6:
            modalidades_por_aluno = {}
            for _, row in df_inscritos.iterrows():
                ra_aluno = str(row.iloc[2]).strip()
                modalidade = str(row.iloc[5]).strip()
                
                if ra_aluno and ra_aluno != 'nan':
                    if ra_aluno not in modalidades_por_aluno:
                        modalidades_por_aluno[ra_aluno] = []
                    if modalidade and modalidade != 'nan':
                        modalidades_por_aluno[ra_aluno].append(modalidade)
            
            return modalidades_por_aluno
        
        return {}
    except Exception as e:
        logging.exception("Erro ao carregar inscrições existentes detalhadas")
        st.error("Falha ao carregar inscrições existentes. Tente novamente.")
        return {}

def filtrar_alunos_por_pesquisa(df_alunos, termo_pesquisa):
    """Filtra alunos por nome ou RA baseado no termo de pesquisa"""
    if not termo_pesquisa:
        return df_alunos
    
    termo_lower = termo_pesquisa.lower()
    mask = (
        df_alunos['Nome do Aluno'].str.lower().str.contains(termo_lower, na=False) |
        df_alunos['RA'].str.lower().str.contains(termo_lower, na=False)
    )
    return df_alunos[mask]

def criar_lista_suspensa_alunos(df_alunos_filtrados):
    """Cria lista suspensa formatada para seleção de alunos"""
    opcoes_alunos = []
    
    for idx, aluno in df_alunos_filtrados.iterrows():
        ra_aluno = str(aluno['RA']).strip()
        nome_aluno = str(aluno['Nome do Aluno']).strip()
        
        opcoes_alunos.append({
            'id': f"{ra_aluno}_{idx}",
            'texto': f"{nome_aluno} (RA: {ra_aluno})",
            'ra': ra_aluno,
            'nome': nome_aluno,
            'index': idx
        })
    
    return opcoes_alunos

def inicializar_session_state():
    """Inicializa o estado da sessão de forma organizada"""
    if 'cadastro' not in st.session_state:
        st.session_state.cadastro = {
            'selecoes_alunos': {},
            'filtro_genero_alunos': {},
            'aluno_selecionado': None,
            'ultima_turma': None,
            'ultimo_genero_filtro': None
        }

def pagina_principal():
    """Página principal de cadastro de inscrições - VERSÃO OTIMIZADA"""
    
    # Inicializa session state organizado
    inicializar_session_state()
    
    st.title("SISTEMA DE INSCRIÇÃO")
    
    # Verifica conexão com Google Sheets
    if get_workbook() is None:
        st.error("Falha crítica ao conectar com o Google Sheets. A aplicação não pode continuar.")
        return
    
    # Carrega dados com cache
    df_alunos = carregar_alunos_permitidos()
    if df_alunos.empty:
        st.error("Não foi possível carregar a lista de alunos permitidos.")
        return
    
    unidade_usuario = st.session_state.user_info['unidade']
    
    # Filtro por turma
    st.subheader("FILTROS PARA SELEÇÃO")
    
    col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
    
    with col_filtro1:
        st.write(f"**Unidade:** {unidade_usuario}")
        df_alunos_filtro_unidade = df_alunos[df_alunos['Unidade'] == unidade_usuario]
        
    with col_filtro2:
        turmas_disponiveis = sorted(df_alunos_filtro_unidade['Turma do Aluno'].unique())
        if turmas_disponiveis:
            turma_selecionada = st.selectbox(
                "Selecione a Turma:",
                options=turmas_disponiveis,
                index=0,
                help="Filtre os alunos por turma"
            )
        else:
            st.error("Nenhuma turma disponível para esta unidade.")
            return
    
    with col_filtro3:
        generos_disponiveis = ["Todos", "M", "F", "M / F"]
        genero_filtro = st.selectbox(
            "Filtrar por Gênero:",
            options=generos_disponiveis,
            index=0,
            help="Filtre as modalidades da tabela abaixo por gênero"
        )
    
    # Filtra alunos
    df_alunos_filtrados = df_alunos[
        (df_alunos['Unidade'] == unidade_usuario) & 
        (df_alunos['Turma do Aluno'] == turma_selecionada)
    ].reset_index(drop=True)
    
    # Carrega modalidades usando função unificada
    opcoes_modalidades_tabela = carregar_modalidades(unidade_usuario, genero_filtro, apenas_com_vaga=True)
    opcoes_modalidades_alunos = carregar_modalidades(unidade_usuario, apenas_com_vaga=True)
    
    if not opcoes_modalidades_tabela and not opcoes_modalidades_alunos:
        st.error("Não foi possível carregar as modalidades disponíveis para sua unidade.")
        return
    
    # Carrega inscrições existentes
    inscricoes_existentes_detalhadas = carregar_inscricoes_existentes_detalhadas()
    
    # Calcula vagas utilizadas - AGORA ATUALIZADO EM TEMPO REAL
    vagas_utilizadas = calcular_vagas_utilizadas(
        st.session_state.cadastro['selecoes_alunos'], 
        opcoes_modalidades_alunos
    )
    
    # Tabela de modalidades - AGORA ATUALIZA EM TEMPO REAL
    st.subheader("MODALIDADES DISPONÍVEIS")
    st.write(f"**Unidade:** {unidade_usuario}")
    if genero_filtro != "Todos":
        st.write(f"**Gênero filtrado:** {genero_filtro}")
    
    dados_modalidades = []
    for modalidade in opcoes_modalidades_tabela:
        vagas_selecionadas = vagas_utilizadas.get(modalidade['modalidade'], 0)
        vagas_restantes_base = modalidade['vagas_restantes']
        
        if isinstance(vagas_restantes_base, str):
            try:
                vagas_restantes_base = float(vagas_restantes_base)
            except ValueError:
                vagas_restantes_base = 0
        
        # Calcula vagas disponíveis considerando seleções atuais
        vagas_disponiveis_agora = vagas_restantes_base - vagas_selecionadas
        status = "Disponível" if vagas_disponiveis_agora > 0 else "Lotada"
        
        dados_modalidades.append({
            'Modalidade': modalidade['modalidade'],
            'Gênero': modalidade['genero'],
            'Limite de Vagas': modalidade['limite_vagas'],
            'Vagas Restantes Agora': max(0, vagas_disponiveis_agora),
            'Status': status
        })
    
    df_info_modalidades = pd.DataFrame(dados_modalidades)
    
    # Exibe apenas as colunas relevantes para o usuário
    st.dataframe(
        df_info_modalidades[['Modalidade', 'Gênero', 'Limite de Vagas', 'Vagas Restantes Agora', 'Status']],
        use_container_width=True,
        hide_index=True,
        height=250
    )
    
    # Lista de Alunos como Lista Suspensa
    st.subheader("LISTA DE ALUNOS")
    st.info("**Cada aluno pode se inscrever em até 3 modalidades diferentes**")
    
    # Pesquisa de alunos
    col_pesquisa1, col_pesquisa2 = st.columns([2, 1])
    
    with col_pesquisa1:
        termo_pesquisa = st.text_input(
            "Pesquisar aluno por nome ou RA:",
            placeholder="Digite o nome ou RA do aluno...",
            help="Busque alunos pelo nome ou número de RA"
        )
    
    with col_pesquisa2:
        st.write("")  # Espaçamento
        st.write("")  # Espaçamento
        if st.button("Limpar pesquisa", use_container_width=True):
            termo_pesquisa = ""
            st.session_state.cadastro['aluno_selecionado'] = None
            st.rerun()
    
    # Filtra alunos baseado na pesquisa
    df_alunos_pesquisados = filtrar_alunos_por_pesquisa(df_alunos_filtrados, termo_pesquisa)
    
    if df_alunos_pesquisados.empty:
        st.warning("Nenhum aluno encontrado com os filtros aplicados.")
        return
    
    # Cria lista suspensa de alunos
    opcoes_alunos = criar_lista_suspensa_alunos(df_alunos_pesquisados)
    
    # Remove alunos que já têm 3 modalidades registradas
    opcoes_alunos_filtradas = []
    for aluno_opcao in opcoes_alunos:
        ra_aluno = aluno_opcao['ra']
        modalidades_registradas = inscricoes_existentes_detalhadas.get(ra_aluno, [])
        if len(modalidades_registradas) < 3:
            opcoes_alunos_filtradas.append(aluno_opcao)
    
    if not opcoes_alunos_filtradas:
        st.success("Todos os alunos desta turma já estão inscritos em 3 modalidades!")
        return
    
    # Lista suspensa para selecionar aluno
    opcoes_selectbox = ["Selecione um aluno..."] + [aluno['texto'] for aluno in opcoes_alunos_filtradas]
    
    aluno_selecionado_texto = st.selectbox(
        "Selecione o aluno:",
        options=opcoes_selectbox,
        index=0,
        help="Selecione um aluno para definir suas modalidades"
    )
    
    # Encontra o aluno selecionado
    aluno_selecionado_data = None
    if aluno_selecionado_texto != "Selecione um aluno...":
        for aluno in opcoes_alunos_filtradas:
            if aluno['texto'] == aluno_selecionado_texto:
                aluno_selecionado_data = aluno
                break
    
    # Se um aluno foi selecionado, mostra as opções de modalidades
    if aluno_selecionado_data:
        aluno_id = aluno_selecionado_data['id']
        ra_aluno = aluno_selecionado_data['ra']
        nome_aluno = aluno_selecionado_data['nome']
        
        modalidades_registradas = inscricoes_existentes_detalhadas.get(ra_aluno, [])
        modalidades_existentes = len(modalidades_registradas)
        
        # Inicializa seleções para este aluno
        if aluno_id not in st.session_state.cadastro['selecoes_alunos']:
            modalidade1 = modalidades_registradas[0] if modalidades_registradas else "Nenhuma"
            modalidade2 = modalidades_registradas[1] if len(modalidades_registradas) > 1 else "Nenhuma"
            modalidade3 = modalidades_registradas[2] if len(modalidades_registradas) > 2 else "Nenhuma"
            
            st.session_state.cadastro['selecoes_alunos'][aluno_id] = {
                'modalidade1': modalidade1,
                'modalidade2': modalidade2, 
                'modalidade3': modalidade3,
                'nome': nome_aluno,
                'ra': ra_aluno,
                # Flags para controle de modalidades registradas
                'modalidade1_registrada': modalidade1 in modalidades_registradas,
                'modalidade2_registrada': modalidade2 in modalidades_registradas,
                'modalidade3_registrada': modalidade3 in modalidades_registradas
            }
        
        if aluno_id not in st.session_state.cadastro['filtro_genero_alunos']:
            generos_modalidades = list(set([m['genero'] for m in opcoes_modalidades_alunos]))
            generos_filtro = [g for g in generos_modalidades if g != 'M / F']
            st.session_state.cadastro['filtro_genero_alunos'][aluno_id] = generos_filtro[0] if generos_filtro else "M"
        
        # Container para as seleções do aluno
        with st.container():
            st.markdown(f"### Configurando modalidades para: **{nome_aluno}**")
            st.write(f"**RA:** {ra_aluno}")
            
            if modalidades_existentes > 0:
                st.info(f"Este aluno já possui {modalidades_existentes}/3 modalidades registradas:")
                for i, modalidade in enumerate(modalidades_registradas, 1):
                    st.write(f"  {i}. {modalidade}")
            
            col_genero, col1, col2, col3 = st.columns([1.5, 2, 2, 2])
            
            with col_genero:
                generos_modalidades = list(set([m['genero'] for m in opcoes_modalidades_alunos]))
                generos_filtro = [g for g in generos_modalidades if g != 'M / F']
                
                genero_aluno = st.selectbox(
                    "Gênero para filtrar modalidades:",
                    options=generos_filtro,
                    key=f"genero_{aluno_id}",
                    index=generos_filtro.index(st.session_state.cadastro['filtro_genero_alunos'][aluno_id])
                )
                st.session_state.cadastro['filtro_genero_alunos'][aluno_id] = genero_aluno
            
            # Filtra modalidades para o aluno
            genero_selecionado = st.session_state.cadastro['filtro_genero_alunos'][aluno_id]
            modalidades_aluno_filtradas = [
                m for m in opcoes_modalidades_alunos 
                if m['genero'] == genero_selecionado or m['genero'] == 'M / F'
            ]
            
            # ATUALIZAÇÃO: Agora considera as vagas utilizadas em tempo real E mantém seleções atuais
            selecoes = st.session_state.cadastro['selecoes_alunos'][aluno_id]
            opcoes_select = atualizar_opcoes_select(modalidades_aluno_filtradas, vagas_utilizadas, selecoes)
            
            # Desabilita modalidades já registradas
            modalidade1_registrada = selecoes['modalidade1_registrada']
            modalidade2_registrada = selecoes['modalidade2_registrada']
            modalidade3_registrada = selecoes['modalidade3_registrada']
            
            with col1:
                def encontrar_indice(modalidade_atual, opcoes):
                    if modalidade_atual == "Nenhuma":
                        return 0
                    return opcoes.index(modalidade_atual) if modalidade_atual in opcoes else 0
                
                selecao1 = st.selectbox(
                    "Modalidade 1",
                    options=opcoes_select,
                    key=f"modal1_{aluno_id}",
                    index=encontrar_indice(selecoes['modalidade1'], opcoes_select),
                    disabled=modalidade1_registrada,
                    # NOVO: Callback para atualização imediata
                    on_change=sync_modalidade_selection,
                    args=(aluno_id, 1)
                )
                # REMOVIDO: A atualização manual não é mais necessária
                # O callback sync_modalidade_selection cuida disso
                
            with col2:
                selecao2 = st.selectbox(
                    "Modalidade 2",
                    options=opcoes_select,
                    key=f"modal2_{aluno_id}",
                    index=encontrar_indice(selecoes['modalidade2'], opcoes_select),
                    disabled=modalidade2_registrada,
                    # NOVO: Callback para atualização imediata
                    on_change=sync_modalidade_selection,
                    args=(aluno_id, 2)
                )
                # REMOVIDO: A atualização manual não é mais necessária
                
            with col3:
                selecao3 = st.selectbox(
                    "Modalidade 3",
                    options=opcoes_select,
                    key=f"modal3_{aluno_id}",
                    index=encontrar_indice(selecoes['modalidade3'], opcoes_select),
                    disabled=modalidade3_registrada,
                    # NOVO: Callback para atualização imediata
                    on_change=sync_modalidade_selection,
                    args=(aluno_id, 3)
                )
                # REMOVIDO: A atualização manual não é mais necessária
            
            # Verifica duplicatas
            sem_duplicatas, modalidades_selecionadas = verificar_duplicatas_modalidades(selecoes)
            if not sem_duplicatas:
                st.warning(f"⚠️ O aluno selecionou modalidades repetidas: {', '.join(set([m for m in modalidades_selecionadas if modalidades_selecionadas.count(m) > 1]))}")
            
            # Exibe mensagem se há modalidades registradas
            if any([modalidade1_registrada, modalidade2_registrada, modalidade3_registrada]):
                st.warning("Modalidades em cinza já estão registradas e não podem ser alteradas.")
            
            st.markdown("---")
    
    # Preview e registro
    st.subheader("Prévia das inscrições")
    
    total_inscricoes = 0
    inscricoes_para_salvar = []
    
    for aluno_id, selecoes in st.session_state.cadastro['selecoes_alunos'].items():
        ra_aluno = selecoes['ra']
        aluno_na_lista = any(
            str(aluno['RA']).strip() == str(ra_aluno).strip()
            for _, aluno in df_alunos_filtrados.iterrows()
        )
        
        if not aluno_na_lista:
            continue
            
        modalidades_aluno = [selecoes['modalidade1'], selecoes['modalidade2'], selecoes['modalidade3']]
        modalidades_registradas_aluno = inscricoes_existentes_detalhadas.get(str(ra_aluno).strip(), [])
        
        modalidades_validas = []
        for modalidade_nome in modalidades_aluno:
            if (modalidade_nome != "Nenhuma" and 
                modalidade_nome not in modalidades_registradas_aluno):
                modalidades_validas.append(modalidade_nome)
        
        # Remove duplicatas
        modalidades_unicas = list(set(modalidades_validas))
        if len(modalidades_validas) != len(modalidades_unicas):
            st.warning(f"O aluno {selecoes['nome']} tem modalidades duplicadas. Corrija antes de registrar.")
            continue
        
        for modalidade_nome in modalidades_validas:
            modalidade_info = next((m for m in opcoes_modalidades_alunos if m['modalidade'] == modalidade_nome), None)
            if modalidade_info:
                total_inscricoes += 1
                inscricoes_para_salvar.append({
                    'Nome Aluno': selecoes['nome'],
                    'RA Aluno': selecoes['ra'],
                    'Modalidade': modalidade_info['modalidade'],
                    'Gênero Modalidade': modalidade_info['genero']
                })
    
    if total_inscricoes > 0:
        df_preview = pd.DataFrame(inscricoes_para_salvar)
        st.write(f"**Serão realizadas {total_inscricoes} inscrição(ões):**")
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
        
        # Botão de registro
        if st.button("REGISTRAR INSCRIÇÕES", type="primary"):
            try:
                inscricoes_realizadas = 0
                erros = 0
                
                for inscricao in inscricoes_para_salvar:
                    dados_inscricao = [
                        unidade_usuario,
                        inscricao['Nome Aluno'],
                        inscricao['RA Aluno'],
                        turma_selecionada,
                        inscricao['Gênero Modalidade'],
                        inscricao['Modalidade'],
                        unidade_usuario,
                        pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),
                        st.session_state.user_info['nome']
                    ]
                    
                    if append_row_and_clear_cache('INSCRITOS-UNIDADE', dados_inscricao):
                        inscricoes_realizadas += 1
                    else:
                        erros += 1
                
                if erros == 0:
                    st.success(f"✅ {inscricoes_realizadas} inscrição(ões) registrada(s) com sucesso!")
                    # Limpa apenas os dados de cadastro, mantendo outros estados
                    st.session_state.cadastro = {
                        'selecoes_alunos': {},
                        'filtro_genero_alunos': {},
                        'aluno_selecionado': None,
                        'ultima_turma': turma_selecionada,
                        'ultimo_genero_filtro': genero_filtro
                    }
                    st.rerun()
                else:
                    st.warning(f"⚠️ {inscricoes_realizadas} inscrição(ões) bem-sucedidas, {erros} com erro.")
            except Exception as e:
                logging.exception("Erro ao registrar inscrições")
                st.error("Falha ao registrar inscrições. Tente novamente.")
    else:
        st.info("Nenhuma inscrição selecionada. Selecione modalidades para os alunos acima.")