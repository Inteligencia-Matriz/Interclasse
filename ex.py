import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from functools import lru_cache
import os
from datetime import datetime

# ------------------------------------------------------------
# Configurações e credenciais
# ------------------------------------------------------------
CREDENCIAIS_JSON = "cred.json"
SHEET_ID = '1Fje2R_qHXImbIJZ07eO2gCv9XllllFQkRa6Cdp1_wfc'

# =============================================================================
# SEÇÃO DE UTILITÁRIOS DE ACESSO AO GOOGLE SHEETS
# =============================================================================

@st.cache_resource
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    if os.path.exists(CREDENCIAIS_JSON):
        creds = Credentials.from_service_account_file(CREDENCIAIS_JSON, scopes=scope)
    else:
        try:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=scope
            )
        except Exception:
            st.error("Falha ao carregar credenciais. Verifique se os 'Secrets' do Streamlit estão configurados corretamente.")
            return None
            
    try:
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Erro de autenticação com o Google Sheets: {e}")
        return None

@st.cache_resource
def get_workbook():
    client = get_gspread_client()
    if not client:
        return None
    try:
        return client.open_by_key(SHEET_ID)
    except Exception as e:
        st.error(f"❌ Não foi possível abrir a planilha. Verifique o SHEET_ID e as permissões: {e}")
        return None

@lru_cache(maxsize=10)
def get_ws(title: str):
    wb = get_workbook()
    if wb:
        try:
            return wb.worksheet(title)
        except gspread.WorksheetNotFound:
            st.error(f"Aba da planilha com o nome '{title}' não foi encontrada.")
            return None
    return None

@st.cache_data(ttl=600)
def load_full_sheet_as_df(ws_title: str):
    ws = get_ws(ws_title)
    if not ws:
        return pd.DataFrame()
    
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame()
    
    if len(values) == 1:
        return pd.DataFrame(columns=values[0])
    else:
        return pd.DataFrame(values[1:], columns=values[0])

# =============================================================================
# FUNÇÕES DE AUTENTICAÇÃO
# =============================================================================

@st.cache_data(ttl=300)
def carregar_usuarios_autorizados():
    """Carrega os usuários autorizados da aba AUTORIZADOS"""
    try:
        df_autorizados = load_full_sheet_as_df('AUTORIZADOS')
        
        if df_autorizados.empty:
            st.error("Nenhum usuário autorizado encontrado na aba AUTORIZADOS")
            return pd.DataFrame()
        
        # Verifica e padroniza os nomes das colunas
        if len(df_autorizados.columns) >= 5:
            # Pega as colunas: Unidade (A), Nome (B), Email (D), Telefone (E)
            df_autorizados = df_autorizados.iloc[:, :5]
            df_autorizados.columns = ['Unidade', 'Nome', 'Coluna_C', 'Email', 'Telefone']
            
            # Limpeza dos dados
            for col in ['Unidade', 'Nome', 'Email', 'Telefone']:
                if col in df_autorizados.columns:
                    df_autorizados[col] = df_autorizados[col].astype(str).str.strip()
            
            # Remove linhas vazias
            df_autorizados = df_autorizados.dropna(subset=['Email', 'Telefone'])
            df_autorizados = df_autorizados[(df_autorizados['Email'] != '') & (df_autorizados['Email'] != 'nan')]
            df_autorizados = df_autorizados[(df_autorizados['Telefone'] != '') & (df_autorizados['Telefone'] != 'nan')]
            
        return df_autorizados
        
    except Exception as e:
        st.error(f"Erro ao carregar usuários autorizados: {e}")
        return pd.DataFrame()

def verificar_credenciais(email, telefone):
    """Verifica se o email e telefone estão na lista de autorizados"""
    df_autorizados = carregar_usuarios_autorizados()
    
    if df_autorizados.empty:
        return False, None
    
    email = email.strip().lower()
    telefone = telefone.strip()
    
    # Procura pelo usuário
    usuario = df_autorizados[
        (df_autorizados['Email'].str.lower() == email) & 
        (df_autorizados['Telefone'] == telefone)
    ]
    
    if not usuario.empty:
        user_info = usuario.iloc[0]
        return True, {
            'unidade': user_info['Unidade'],
            'nome': user_info['Nome'],
            'email': user_info['Email']
        }
    
    return False, None

def registrar_login(user_info):
    """Registra o login na aba LOGIN a partir da coluna 2"""
    try:
        ws_login = get_ws('LOGIN')
        if not ws_login:
            st.error("Não foi possível acessar a aba LOGIN")
            return False
        
        # Prepara os dados do login
        dados_login = [
            user_info['unidade'],
            user_info['nome'], 
            user_info['email'],
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ]
        
        # Encontra a próxima linha vazia
        todas_celulas = ws_login.get_all_values()
        proxima_linha = len(todas_celulas) + 1
        
        # Escreve a partir da coluna B (índice 2)
        range_escrita = f'B{proxima_linha}'
        ws_login.update(range_escrita, [dados_login], value_input_option="USER_ENTERED")
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao registrar login: {e}")
        return False

def pagina_login():
    """Exibe a página de login"""
    st.set_page_config(
        page_title="Sistema de Login - E-commerce", 
        layout="centered", 
        page_icon="🔐"
    )
    
    st.title("🔐 Sistema de Inscrição - Login")
    st.markdown("---")
    
    with st.form("login_form"):
        st.subheader("Acesso Restrito")
        email = st.text_input("📧 Email:", placeholder="seu@email.com")
        telefone = st.text_input("📱 Telefone (senha):", type="password", placeholder="Digite seu número de telefone")
        
        submitted = st.form_submit_button("🚀 Entrar", type="primary")
        
        if submitted:
            if not email or not telefone:
                st.error("❌ Por favor, preencha todos os campos.")
            else:
                with st.spinner("Verificando credenciais..."):
                    autenticado, user_info = verificar_credenciais(email, telefone)
                    
                    if autenticado:
                        # Registra o login
                        if registrar_login(user_info):
                            # Armazena informações do usuário na session_state
                            st.session_state.user_info = user_info
                            st.session_state.logged_in = True
                            st.success(f"✅ Bem-vindo(a), {user_info['nome']}!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao registrar acesso. Tente novamente.")
                    else:
                        st.error("❌ Email ou telefone incorretos. Verifique suas credenciais.")

# =============================================================================
# Funções de dados existentes
# =============================================================================

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
        
        # CORREÇÃO ADICIONADA: Converter colunas numéricas para o tipo correto
        colunas_numericas = ['Limite_Vagas', 'Inscritos', 'Vagas_Restantes']
        for col in colunas_numericas:
            if col in df_modalidades.columns:
                # Converte para numérico, forçando erros para NaN (coerce)
                df_modalidades[col] = pd.to_numeric(df_modalidades[col], errors='coerce')
        
        # Remove linhas completamente vazias
        df_modalidades = df_modalidades.dropna(how='all')
        
        return df_modalidades
        
    except Exception as e:
        st.error(f"Erro ao carregar modalidades: {e}")
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
            df_alunos.columns = ['Unidade', 'Nome do Aluno', 'RA do Aluno', 'Turma do Aluno']
            
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
        st.error(f"Erro ao carregar alunos: {e}")
        return pd.DataFrame()

def append_row_and_clear_cache(ws_title: str, row_data: list):
    """Adiciona uma nova linha e limpa os caches de dados para forçar a releitura."""
    ws = get_ws(ws_title)
    if ws:
        try:
            ws.append_row(row_data, value_input_option="USER_ENTERED")
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Falha ao salvar na planilha '{ws_title}': {e}")
            return False
    return False

def registrar_exclusao(dados_registro, usuario_responsavel):
    """Registra a exclusão na aba REGISTROS-EXCLUIDOS"""
    try:
        ws_excluidos = get_ws('REGISTROS-EXCLUIDOS')
        if not ws_excluidos:
            st.error("Não foi possível acessar a aba REGISTROS-EXCLUIDOS")
            return False
        
        # Prepara os dados da exclusão (mantém os dados originais + usuário + data/hora)
        dados_exclusao = dados_registro + [
            usuario_responsavel,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ]
        
        # Encontra a próxima linha vazia (começando da linha 2)
        todas_celulas = ws_excluidos.get_all_values()
        proxima_linha = len(todas_celulas) + 1 if todas_celulas else 2
        
        # Escreve a partir da coluna A
        range_escrita = f'A{proxima_linha}'
        ws_excluidos.update(range_escrita, [dados_exclusao], value_input_option="USER_ENTERED")
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao registrar exclusão: {e}")
        return False

def excluir_registro_inscricao(linha_index, dados_registro, usuario_responsavel):
    """Exclui um registro da aba INSCRITOS-UNIDADE e registra na aba de exclusões"""
    try:
        ws_inscritos = get_ws('INSCRITOS-UNIDADE')
        if not ws_inscritos:
            st.error("Não foi possível acessar a aba INSCRITOS-UNIDADE")
            return False
        
        # Primeiro registra a exclusão
        if registrar_exclusao(dados_registro, usuario_responsavel):
            # Depois exclui a linha da planilha original
            # A linha_index vem do DataFrame, então adicionamos 2 (cabeçalho + índice 0-based)
            linha_planilha = linha_index + 2
            ws_inscritos.delete_rows(linha_planilha)
            
            # Limpa o cache para forçar atualização
            st.cache_data.clear()
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Erro ao excluir registro: {e}")
        return False

# =============================================================================
# PÁGINAS DA APLICAÇÃO
# =============================================================================

def pagina_principal():
    """Página principal de cadastro de inscrições"""
    st.title("📊 Sistema de Inscrição - Modalidades E-commerce")
    
    # Verifica conexão com Google Sheets
    if get_workbook() is None:
        st.error("Falha crítica ao conectar com o Google Sheets. A aplicação não pode continuar.")
        return
    
    # Carrega dados dos alunos permitidos
    df_alunos = carregar_alunos_permitidos()
    
    if df_alunos.empty:
        st.error("Não foi possível carregar a lista de alunos permitidos.")
        return
    
    # Carrega dados completas das modalidades
    df_modalidades_completas = carregar_modalidades_completas()
    
    if df_modalidades_completas.empty:
        st.error("Não foi possível carregar os dados das modalidades.")
        return
    
    # MODIFICAÇÃO: Define a unidade automaticamente baseada no usuário logado
    unidade_usuario = st.session_state.user_info['unidade']
    
    # Filtro por turma antes de exibir a tabela
    st.subheader("🎯 Filtros para Seleção")
    
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        # MODIFICAÇÃO: Unidade fixa baseada no usuário logado
        st.write(f"**Unidade:** {unidade_usuario}")
        # Filtra alunos apenas da unidade do usuário
        df_alunos_filtro_unidade = df_alunos[df_alunos['Unidade'] == unidade_usuario]
        
    with col_filtro2:
        # FILTRO POR TURMA - Agora filtra apenas alunos da unidade do usuário
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
    
    # Filtra alunos pela unidade do usuário e turma selecionada
    df_alunos_filtrados = df_alunos[
        (df_alunos['Unidade'] == unidade_usuario) & 
        (df_alunos['Turma do Aluno'] == turma_selecionada)
    ].reset_index(drop=True)
    
    # Tabela interativa com checkboxes integrados para alunos
    st.subheader("📋 Lista de Alunos Disponíveis - Selecione os Alunos")
    
    # Inicializa session_state para armazenar alunos selecionados
    if 'alunos_selecionados' not in st.session_state:
        st.session_state.alunos_selecionados = []
    if 'modalidades_selecionadas' not in st.session_state:
        st.session_state.modalidades_selecionadas = []
    
    # Cria DataFrame com coluna de seleção
    df_display = df_alunos_filtrados.copy()
    df_display['Selecionar'] = False
    
    # Usando st.data_editor para tabela interativa com checkboxes
    st.write("**Selecione os alunos:**")
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Selecionar": st.column_config.CheckboxColumn(
                "Selecionar",
                help="Marque para selecionar o aluno",
                default=False,
            ),
            "Unidade": st.column_config.TextColumn("Unidade"),
            "Nome do Aluno": st.column_config.TextColumn("Nome do Aluno"),
            "RA do Aluno": st.column_config.TextColumn("RA do Aluno"),
            "Turma do Aluno": st.column_config.TextColumn("Turma do Aluno")
        },
        hide_index=True,
        use_container_width=True,
        key="alunos_editor"
    )
    
    # Atualiza lista de alunos selecionados
    alunos_selecionados_info = []
    for idx, row in edited_df.iterrows():
        if row['Selecionar']:
            alunos_selecionados_info.append({
                'index': idx,
                'unidade': row['Unidade'],
                'nome': row['Nome do Aluno'],
                'ra': row['RA do Aluno'],
                'turma': row['Turma do Aluno']
            })
    
    st.session_state.alunos_selecionados = alunos_selecionados_info
    st.write(f"**Alunos selecionados:** {len(st.session_state.alunos_selecionados)}")
    
    # Tabela interativa para modalidades
    st.subheader("🎯 Seleção de Modalidades")
    
    # FILTRO POR GÊNERO (das modalidades)
    generos_disponiveis = df_modalidades_completas['Genero'].dropna().unique()
    genero_selecionado = st.selectbox(
        "Selecione o Gênero da Modalidade:",
        options=sorted(generos_disponiveis),
        index=0,
        help="Selecione o gênero para filtrar as modalidades"
    )
    
    # FILTRO DE MODALIDADES DISPONÍVEIS
    modalidades_filtradas = df_modalidades_completas[
        (df_modalidades_completas['Genero'] == genero_selecionado) & 
        (df_modalidades_completas['Unidade'] == unidade_usuario) &
        (df_modalidades_completas['Tem_Vaga'] != 'NÃO')
    ].reset_index(drop=True)
    
    # Tabela interativa para modalidades
    if not modalidades_filtradas.empty:
        st.write("**Selecione uma ou mais modalidades:**")
        
        # Cria DataFrame com as colunas necessárias
        df_modalidades_display = modalidades_filtradas[['Genero', 'Modalidade', 'Unidade', 'Limite_Vagas', 'Inscritos', 'Vagas_Restantes']].copy()
        df_modalidades_display['Selecionar'] = False
        
        # CORREÇÃO: Garantir que as colunas numéricas sejam do tipo correto
        df_modalidades_display['Limite_Vagas'] = pd.to_numeric(df_modalidades_display['Limite_Vagas'], errors='coerce')
        df_modalidades_display['Inscritos'] = pd.to_numeric(df_modalidades_display['Inscritos'], errors='coerce')
        df_modalidades_display['Vagas_Restantes'] = pd.to_numeric(df_modalidades_display['Vagas_Restantes'], errors='coerce')
        df_modalidades_display['Vagas_Restantes'] = df_modalidades_display['Vagas_Restantes'].fillna(0)
        
        # Editor de dados para modalidades
        edited_modalidades = st.data_editor(
            df_modalidades_display,
            column_config={
                "Selecionar": st.column_config.CheckboxColumn(
                    "Selecionar",
                    help="Marque para selecionar a modalidade",
                    default=False,
                ),
                "Genero": st.column_config.TextColumn("Gênero"),
                "Modalidade": st.column_config.TextColumn("Modalidade"),
                "Unidade": st.column_config.TextColumn("Unidade"),
                "Limite_Vagas": st.column_config.NumberColumn(
                    "Limite de Vagas",
                    help="Total de vagas disponíveis",
                    format="%d"
                ),
                "Inscritos": st.column_config.NumberColumn(
                    "Inscritos",
                    help="Número de alunos já inscritos",
                    format="%d"
                ),
                "Vagas_Restantes": st.column_config.NumberColumn(
                    "Vagas Restantes",
                    help="Vagas ainda disponíveis",
                    format="%d"
                )
            },
            hide_index=True,
            use_container_width=True,
            key="modalidades_editor"
        )
        
        # Permite múltiplas modalidades selecionadas
        modalidades_selecionadas = []
        for idx, row in edited_modalidades.iterrows():
            if row['Selecionar']:
                modalidades_selecionadas.append({
                    'modalidade': row['Modalidade'],
                    'genero': row['Genero'],
                    'unidade': row['Unidade'],
                    'limite_vagas': row['Limite_Vagas'],
                    'inscritos': row['Inscritos'],
                    'vagas_restantes': row['Vagas_Restantes']
                })
        
        st.session_state.modalidades_selecionadas = modalidades_selecionadas
        
        if modalidades_selecionadas:
            st.success(f"✅ {len(modalidades_selecionadas)} modalidade(s) selecionada(s)")
            
            # Exibe informações detalhadas das modalidades selecionadas
            for modalidade in modalidades_selecionadas:
                status_vaga = "🟢 Disponível" if modalidade['vagas_restantes'] > 0 else "🔴 Lotada"
                st.write(f"• **{modalidade['modalidade']}** - {modalidade['vagas_restantes']} vaga(s) restante(s) {status_vaga}")
        else:
            st.info("ℹ️ Selecione uma ou mais modalidades na tabela acima")
    else:
        st.warning(f"Nenhuma modalidade disponível para gênero {genero_selecionado} na unidade {unidade_usuario}")
        st.session_state.modalidades_selecionadas = []
    
    # Exibe modalidades sem vaga
    modalidades_sem_vaga = df_modalidades_completas[
        (df_modalidades_completas['Genero'] == genero_selecionado) & 
        (df_modalidades_completas['Unidade'] == unidade_usuario) &
        (df_modalidades_completas['Tem_Vaga'] == 'NÃO')
    ]['Modalidade'].dropna().unique().tolist()
    
    if modalidades_sem_vaga:
        st.caption("🚫 Modalidades sem vaga:")
        for modalidade in modalidades_sem_vaga[:3]:
            st.caption(f"• {modalidade}")

    # Preview detalhado com COMBINAÇÕES de alunos x modalidades
    if st.session_state.alunos_selecionados and st.session_state.modalidades_selecionadas:
        st.subheader("📋 Prévia dos Dados que Serão Salvos")
        
        # Cria combinações de alunos x modalidades
        dados_para_salvar = []
        total_registros = 0
        
        for aluno in st.session_state.alunos_selecionados:
            for modalidade in st.session_state.modalidades_selecionadas:
                dados_para_salvar.append({
                    'Unidade Aluno': aluno['unidade'],
                    'Nome Aluno': aluno['nome'],
                    'RA Aluno': aluno['ra'],
                    'Turma Aluno': aluno['turma'],
                    'Gênero Modalidade': modalidade['genero'],
                    'Modalidade': modalidade['modalidade']
                    # MODIFICAÇÃO: Remove "Unidade Modalidade" e "Data/Hora" da prévia
                })
                total_registros += 1
        
        df_preview = pd.DataFrame(dados_para_salvar)
        
        st.write(f"**Serão criados {total_registros} registro(s):**")
        st.dataframe(
            df_preview,
            use_container_width=True,
            hide_index=True
        )
        
        # CORREÇÃO: Resumo estatístico DENTRO do bloco if
        col_resumo1, col_resumo2, col_resumo3, col_resumo4 = st.columns(4)
        with col_resumo1:
            st.metric("Total de Alunos", len(st.session_state.alunos_selecionados))
        with col_resumo2:
            st.metric("Total de Modalidades", len(st.session_state.modalidades_selecionadas))
        with col_resumo3:
            st.metric("Total de Registros", total_registros)
        with col_resumo4:
            st.metric("Unidade", unidade_usuario)

    # Botão para registrar as inscrições em lote - CORREÇÃO APLICADA
    if st.button("🎓 Registrar Inscrições em Lote", type="primary"):
        if not st.session_state.alunos_selecionados or not st.session_state.modalidades_selecionadas:
            st.error("Por favor, selecione pelo menos um aluno e uma modalidade.")
        else:
            # Verifica disponibilidade de vagas antes de registrar
            modalidades_sem_vaga_suficiente = []
            for modalidade in st.session_state.modalidades_selecionadas:
                if modalidade['vagas_restantes'] < len(st.session_state.alunos_selecionados):
                    modalidades_sem_vaga_suficiente.append(modalidade['modalidade'])
            
            if modalidades_sem_vaga_suficiente:
                st.error(f"❌ As seguintes modalidades não têm vagas suficientes: {', '.join(modalidades_sem_vaga_suficiente)}")
                st.stop()
            
            inscricoes_realizadas = 0
            erros = 0
            
            # Processa COMBINAÇÕES de alunos x modalidades
            for aluno_info in st.session_state.alunos_selecionados:
                for modalidade_info in st.session_state.modalidades_selecionadas:
                    # MODIFICAÇÃO: Prepara os dados completos para salvar (incluindo dados extras)
                    dados_inscricao = [
                        aluno_info['unidade'],           # Unidade Aluno
                        aluno_info['nome'],              # Nome Aluno
                        aluno_info['ra'],                # RA Aluno
                        aluno_info['turma'],             # Turma Aluno
                        modalidade_info['genero'],       # Gênero Modalidade
                        modalidade_info['modalidade'],   # Modalidade
                        modalidade_info['unidade'],      # Unidade Modalidade (MODIFICAÇÃO: adicionada)
                        pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S"),  # Data/Hora (MODIFICAÇÃO: adicionada)
                        st.session_state.user_info['nome']  # MODIFICAÇÃO: Nome do usuário que realizou a ação
                    ]
                    
                    # Tenta salvar na planilha
                    if append_row_and_clear_cache('INSCRITOS-UNIDADE', dados_inscricao):
                        inscricoes_realizadas += 1
                    else:
                        erros += 1
            
            if erros == 0:
                st.success(f"✅ {inscricoes_realizadas} inscrição(ões) registrada(s) com sucesso!")
                st.info(f"📊 Foram criadas {inscricoes_realizadas} combinações de alunos x modalidades")
                
                # CORREÇÃO: Limpa as seleções E força atualização da página
                st.session_state.alunos_selecionados = []
                st.session_state.modalidades_selecionadas = []
                st.rerun()  # ← LINHA ADICIONADA para forçar a atualização
                
            else:
                st.warning(f"⚠️ {inscricoes_realizadas} inscrição(ões) bem-sucedidas, {erros} com erro.")

def pagina_lista_inscritos():
    """Página para visualizar e gerenciar inscrições"""
    st.title("📋 Lista de Alunos Inscritos")
    
    # Verifica conexão com Google Sheets
    if get_workbook() is None:
        st.error("Falha crítica ao conectar com o Google Sheets. A aplicação não pode continuar.")
        return
    
    # Carrega dados dos inscritos
    try:
        df_inscritos = load_full_sheet_as_df('INSCRITOS-UNIDADE')
        
        if df_inscritos.empty:
            st.info("📝 Nenhum aluno inscrito encontrado.")
            return
        
        # Verifica e padroniza os nomes das colunas
        if len(df_inscritos.columns) >= 6:
            # Pega as primeiras 6 colunas conforme especificado
            df_inscritos = df_inscritos.iloc[:, :9]  # Pega até 9 colunas se existirem
            if len(df_inscritos.columns) >= 9:
                df_inscritos.columns = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade', 'Unidade Modalidade', 'Data/Hora', 'Usuario']
            else:
                # Preenche colunas faltantes
                colunas_base = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade']
                colunas_extras = ['Unidade Modalidade', 'Data/Hora', 'Usuario'][:len(df_inscritos.columns)-6]
                df_inscritos.columns = colunas_base + colunas_extras
        
        # Filtra apenas os registros da unidade do usuário logado
        unidade_usuario = st.session_state.user_info['unidade']
        df_inscritos_filtrado = df_inscritos[df_inscritos['Unidade'] == unidade_usuario]
        
        if df_inscritos_filtrado.empty:
            st.info(f"📝 Nenhum aluno inscrito encontrado para a unidade {unidade_usuario}.")
            return
        
        st.subheader(f"🎯 Alunos Inscritos - {unidade_usuario}")
        st.write(f"**Total de inscrições:** {len(df_inscritos_filtrado)}")
        
        # MODIFICAÇÃO: Cria DataFrame apenas com as colunas que devem ser exibidas
        colunas_para_exibir = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade', 'Data/Hora']
        df_display = df_inscritos_filtrado[colunas_para_exibir].copy()
        df_display['Excluir'] = False
        
        # Tabela interativa com opção de exclusão
        st.write("**Selecione os registros para excluir:**")
        
        # Editor de dados para inscrições
        edited_df = st.data_editor(
            df_display,
            column_config={
                "Excluir": st.column_config.CheckboxColumn(
                    "Excluir",
                    help="Marque para excluir o registro",
                    default=False,
                ),
                "Unidade": st.column_config.TextColumn("Unidade"),
                "Nome Aluno": st.column_config.TextColumn("Nome do Aluno"),
                "RA Aluno": st.column_config.TextColumn("RA do Aluno"),
                "Turma Aluno": st.column_config.TextColumn("Turma do Aluno"),
                "Genero Modalidade": st.column_config.TextColumn("Gênero"),
                "Modalidade": st.column_config.TextColumn("Modalidade"),
                "Data/Hora": st.column_config.TextColumn("Data/Hora")
            },
            hide_index=True,
            use_container_width=True,
            key="inscritos_editor"
        )
        
        # Identifica registros selecionados para exclusão
        registros_para_excluir = []
        for idx, row in edited_df.iterrows():
            if row['Excluir']:
                # Pega o índice original no DataFrame filtrado
                index_original_filtrado = idx
                # Encontra o índice correspondente no DataFrame original
                index_original = df_inscritos_filtrado.index[index_original_filtrado]
                
                # Pega todos os dados originais do registro (incluindo colunas ocultas)
                dados_registro = [
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Unidade'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Nome Aluno'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['RA Aluno'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Turma Aluno'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Genero Modalidade'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Modalidade'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Unidade Modalidade'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Data/Hora'],
                    df_inscritos_filtrado.iloc[index_original_filtrado]['Usuario']
                ]
                registros_para_excluir.append({
                    'index_original': index_original,
                    'dados': dados_registro
                })
        
        # Botão para confirmar exclusão
        if registros_para_excluir:
            st.warning(f"⚠️ **{len(registros_para_excluir)} registro(s) selecionado(s) para exclusão**")
            
            # Exibe prévia dos registros que serão excluídos
            st.subheader("📋 Registros que Serão Excluídos")
            df_exclusao_preview = pd.DataFrame([r['dados'][:6] for r in registros_para_excluir], 
                                             columns=['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Gênero', 'Modalidade'])
            st.dataframe(df_exclusao_preview, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Confirmar Exclusão dos Registros Selecionados", type="primary"):
                with st.spinner("Excluindo registros..."):
                    exclusoes_realizadas = 0
                    erros = 0
                    
                    # Ordena pelos índices em ordem decrescente para evitar problemas de reindexação
                    registros_para_excluir.sort(key=lambda x: x['index_original'], reverse=True)
                    
                    for registro in registros_para_excluir:
                        if excluir_registro_inscricao(registro['index_original'], registro['dados'], st.session_state.user_info['nome']):
                            exclusoes_realizadas += 1
                        else:
                            erros += 1
                    
                    if erros == 0:
                        st.success(f"✅ {exclusoes_realizadas} registro(s) excluído(s) com sucesso!")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {exclusoes_realizadas} exclusão(ões) bem-sucedidas, {erros} com erro.")
        
    except Exception as e:
        st.error(f"Erro ao carregar lista de inscritos: {e}")

# =============================================================================
# Aplicação Principal
# =============================================================================

def main_app():
    """Aplicação principal após login"""
    st.set_page_config(
        page_title="Sistema de Inscrição - E-commerce", 
        layout="wide", 
        page_icon="📊"
    )
    
    # Header com informações do usuário
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 Sistema de Inscrição - Modalidades E-commerce")
    with col2:
        if 'user_info' in st.session_state:
            st.write(f"👤 **{st.session_state.user_info['nome']}**")
            st.write(f"🏢 {st.session_state.user_info['unidade']}")
            if st.button("🚪 Sair"):
                st.session_state.logged_in = False
                st.session_state.pop('user_info', None)
                st.rerun()
    
    st.markdown("---")
    
    # Sidebar com navegação
    with st.sidebar:
        st.header("🧭 Navegação")
        
        # Define a página atual
        if 'pagina_atual' not in st.session_state:
            st.session_state.pagina_atual = "Cadastro"
        
        # Botões de navegação
        if st.button("📝 Realizar Cadastros", use_container_width=True, 
                    type="primary" if st.session_state.pagina_atual == "Cadastro" else "secondary"):
            st.session_state.pagina_atual = "Cadastro"
            st.rerun()
            
        if st.button("📋 Ver Lista de Inscritos", use_container_width=True,
                    type="primary" if st.session_state.pagina_atual == "Lista" else "secondary"):
            st.session_state.pagina_atual = "Lista"
            st.rerun()
        
        st.markdown("---")
        st.info("💡 **Dicas:**\n- Use a página de cadastro para inscrever alunos\n- Use a lista para visualizar e gerenciar inscrições")
    
    # Renderiza a página selecionada
    if st.session_state.pagina_atual == "Cadastro":
        pagina_principal()
    elif st.session_state.pagina_atual == "Lista":
        pagina_lista_inscritos()

# =============================================================================
# FUNÇÃO PRINCIPAL QUE CONTROLA O FLUXO
# =============================================================================

def main():
    """Função principal que controla o fluxo de autenticação"""
    
    # Inicializa session_state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Verifica se o usuário está logado
    if not st.session_state.logged_in:
        pagina_login()
    else:
        main_app()

if __name__ == "__main__":
    main()