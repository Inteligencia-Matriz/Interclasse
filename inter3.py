import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from functools import lru_cache
import os

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
# Funções de dados - MODIFICADA
# =============================================================================

@st.cache_data(ttl=600)
def carregar_modalidades_completas():
    """Carrega todas as informações da aba MODALIDADES com as novas colunas"""
    df_modalidades = load_full_sheet_as_df('MODALIDADES')
    
    if df_modalidades.empty:
        st.warning("Nenhuma modalidade encontrada na aba MODALIDADES")
        return pd.DataFrame()
    
    # MODIFICAÇÃO 1: Carrega 7 colunas em vez de 4
    if len(df_modalidades.columns) >= 7:
        df_modalidades.columns = ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga', 'Limite_Vagas', 'Inscritos', 'Restam'] + list(df_modalidades.columns[7:])
        
        # Limpeza dos dados
        for col in ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga']:
            if col in df_modalidades.columns:
                df_modalidades[col] = df_modalidades[col].astype(str).str.strip()
        
        # Converte colunas numéricas
        for col in ['Limite_Vagas', 'Inscritos', 'Restam']:
            if col in df_modalidades.columns:
                df_modalidades[col] = pd.to_numeric(df_modalidades[col], errors='coerce')
        
        df_modalidades = df_modalidades.dropna(how='all')
        
    return df_modalidades

@st.cache_data(ttl=600)
def carregar_alunos_permitidos():
    """Carrega os dados dos alunos da aba INSCRITOS-ECOMMERCE"""
    df_alunos = load_full_sheet_as_df('INSCRITOS-ECOMMERCE')
    
    if df_alunos.empty:
        st.warning("Nenhum aluno encontrado na aba INSCRITOS-ECOMMERCE")
        return pd.DataFrame()
    
    if len(df_alunos.columns) >= 4:
        df_alunos = df_alunos.iloc[:, :4]
        df_alunos.columns = ['Unidade', 'Nome do Aluno', 'RA do Aluno', 'Turma do Aluno']
        
        # Limpeza dos dados
        for col in df_alunos.columns:
            df_alunos[col] = df_alunos[col].astype(str).str.strip()
        
        df_alunos = df_alunos.dropna(how='all')
        df_alunos = df_alunos[df_alunos['Unidade'] != '']
        
    return df_alunos

def append_row_and_clear_cache(ws_title: str, row_data: list):
    """Adiciona uma nova linha e limpa os caches de dados"""
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

# =============================================================================
# Aplicação Streamlit Principal - MODIFICADA
# =============================================================================

def main():
    st.set_page_config(
        page_title="Sistema de Matrícula - E-commerce", 
        layout="wide", 
        page_icon="📊"
    )
    
    st.title("📊 Sistema de Matrícula em Modalidades")
    
    # Verifica conexão com Google Sheets
    if get_workbook() is None:
        st.error("Falha crítica ao conectar com o Google Sheets. A aplicação não pode continuar.")
        return
    
    # Carrega dados
    df_alunos = carregar_alunos_permitidos()
    df_modalidades_completas = carregar_modalidades_completas()
    
    if df_alunos.empty or df_modalidades_completas.empty:
        st.error("Não foi possível carregar os dados necessários.")
        return
    
    # NOVO: Filtro por turma antes de exibir a tabela
    st.subheader("🎯 Filtros para Seleção de Alunos")
    
    col_filtro1, col_filtro2 = st.columns(2)
    
    with col_filtro1:
        # FILTRO POR UNIDADE
        unidades_disponiveis = sorted(df_alunos['Unidade'].unique())
        unidade_selecionada = st.selectbox(
            "Selecione a Unidade:",
            options=unidades_disponiveis,
            index=0,
            help="Selecione a unidade para filtrar os alunos"
        )
    
    with col_filtro2:
        # FILTRO POR TURMA - Agora filtra a tabela completa
        turmas_disponiveis = sorted(df_alunos[df_alunos['Unidade'] == unidade_selecionada]['Turma do Aluno'].unique())
        turma_selecionada = st.selectbox(
            "Selecione a Turma:",
            options=turmas_disponiveis,
            index=0,
            help="Filtre os alunos por turma"
        )
    
    # Filtra alunos pela unidade e turma selecionadas
    df_alunos_filtrados = df_alunos[
        (df_alunos['Unidade'] == unidade_selecionada) & 
        (df_alunos['Turma do Aluno'] == turma_selecionada)
    ].reset_index(drop=True)
    
    # MODIFICAÇÃO 1: Tabela interativa com checkboxes integrados
    st.subheader("📋 Lista de Alunos Disponíveis - Selecione os Alunos")
    
    # Inicializa session_state para armazenar alunos selecionados
    if 'alunos_selecionados' not in st.session_state:
        st.session_state.alunos_selecionados = []
    if 'modalidades_selecionadas' not in st.session_state:
        st.session_state.modalidades_selecionadas = []
    
    # Cria DataFrame com coluna de seleção
    df_display = df_alunos_filtrados.copy()
    df_display['Selecionar'] = False
    
    # MODIFICAÇÃO 2: Usando st.data_editor para tabela interativa com checkboxes 
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
    
    # MODIFICAÇÃO 3: Tabela interativa para modalidades com SELEÇÃO MÚLTIPLA
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
        (df_modalidades_completas['Unidade'] == unidade_selecionada) &
        (df_modalidades_completas['Tem_Vaga'] != 'NÃO')
    ].reset_index(drop=True)
    
    # MODIFICAÇÃO 4: Tabela interativa para modalidades com NOVAS COLUNAS
    if not modalidades_filtradas.empty:
        st.write("**Selecione uma ou mais modalidades:**")
        
        # MODIFICAÇÃO 5: Cria DataFrame com as NOVAS COLUNAS (sem Tem_Vaga)
        df_modalidades_display = modalidades_filtradas[['Genero', 'Modalidade', 'Unidade', 'Limite_Vagas', 'Inscritos', 'Restam']].copy()
        df_modalidades_display['Selecionar'] = False
        
        # MODIFICAÇÃO 6: Editor de dados para modalidades com NOVAS COLUNAS
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
                "Restam": st.column_config.NumberColumn(
                    "Vagas Restantes",
                    help="Vagas ainda disponíveis",
                    format="%d"
                )
            },
            hide_index=True,
            use_container_width=True,
            key="modalidades_editor"
        )
        
        # MODIFICAÇÃO 7: Permite múltiplas modalidades selecionadas
        modalidades_selecionadas = []
        for idx, row in edited_modalidades.iterrows():
            if row['Selecionar']:
                modalidades_selecionadas.append({
                    'modalidade': row['Modalidade'],
                    'genero': row['Genero'],
                    'unidade': row['Unidade'],
                    'limite_vagas': row['Limite_Vagas'],
                    'inscritos': row['Inscritos'],
                    'restam': row['Restam']
                })
        
        st.session_state.modalidades_selecionadas = modalidades_selecionadas
        
        if modalidades_selecionadas:
            st.success(f"✅ {len(modalidades_selecionadas)} modalidade(s) selecionada(s)")
            
            # MODIFICAÇÃO 8: Exibe informações detalhadas das modalidades selecionadas
            for modalidade in modalidades_selecionadas:
                status_vaga = "🟢 Disponível" if modalidade['restam'] > 0 else "🔴 Lotada"
                st.write(f"• **{modalidade['modalidade']}** - {modalidade['restam']} vaga(s) restante(s) {status_vaga}")
        else:
            st.info("ℹ️ Selecione uma ou mais modalidades na tabela acima")
    else:
        st.warning(f"Nenhuma modalidade disponível para gênero {genero_selecionado} na unidade {unidade_selecionada}")
        st.session_state.modalidades_selecionadas = []
    
    # Exibe modalidades sem vaga
    modalidades_sem_vaga = df_modalidades_completas[
        (df_modalidades_completas['Genero'] == genero_selecionado) & 
        (df_modalidades_completas['Unidade'] == unidade_selecionada) &
        (df_modalidades_completas['Tem_Vaga'] == 'NÃO')
    ]['Modalidade'].dropna().unique().tolist()
    
    if modalidades_sem_vaga:
        st.caption("🚫 Modalidades sem vaga:")
        for modalidade in modalidades_sem_vaga[:3]:
            st.caption(f"• {modalidade}")

    # MODIFICAÇÃO 9: Preview detalhado com COMBINAÇÕES de alunos x modalidades
    if st.session_state.alunos_selecionados and st.session_state.modalidades_selecionadas:
        st.subheader("📋 Prévia dos Dados que Serão Salvos")
        
        # MODIFICAÇÃO 10: Cria combinações de alunos x modalidades
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
                    'Modalidade': modalidade['modalidade'],
                    'Unidade Modalidade': modalidade['unidade'],
                    'Data/Hora': pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                })
                total_registros += 1
        
        df_preview = pd.DataFrame(dados_para_salvar)
        
        st.write(f"**Serão criados {total_registros} registro(s) na planilha 'INSCRITOS-UNIDADE':**")
        st.dataframe(
            df_preview,
            use_container_width=True,
            hide_index=True
        )
        
        # Resumo estatístico aprimorado
        col_resumo1, col_resumo2, col_resumo3, col_resumo4 = st.columns(4)
        with col_resumo1:
            st.metric("Total de Alunos", len(st.session_state.alunos_selecionados))
        with col_resumo2:
            st.metric("Total de Modalidades", len(st.session_state.modalidades_selecionadas))
        with col_resumo3:
            st.metric("Total de Registros", total_registros)
        with col_resumo4:
            st.metric("Unidade", unidade_selecionada)
        
        # MODIFICAÇÃO 11: Detalhamento das combinações com informações de vagas
        st.write("**Detalhamento das combinações:**")
        for aluno in st.session_state.alunos_selecionados:
            st.write(f"**{aluno['nome']}** será matriculado em:")
            for modalidade in st.session_state.modalidades_selecionadas:
                status_vaga = f"({modalidade['restam']} vaga(s) restante(s))" if modalidade['restam'] > 0 else "(LOTADA)"
                st.write(f"  • {modalidade['modalidade']} {status_vaga}")

    # Botão para registrar as matrículas
    if st.button("🎓 Registrar Matrículas em Lote", type="primary"):
        if not st.session_state.alunos_selecionados or not st.session_state.modalidades_selecionadas:
            st.error("Por favor, selecione pelo menos um aluno e uma modalidade.")
        else:
            # MODIFICAÇÃO 12: Verifica disponibilidade de vagas antes de registrar
            modalidades_sem_vaga_suficiente = []
            for modalidade in st.session_state.modalidades_selecionadas:
                if modalidade['restam'] < len(st.session_state.alunos_selecionados):
                    modalidades_sem_vaga_suficiente.append(modalidade['modalidade'])
            
            if modalidades_sem_vaga_suficiente:
                st.error(f"❌ As seguintes modalidades não têm vagas suficientes: {', '.join(modalidades_sem_vaga_suficiente)}")
                return
            
            matriculas_realizadas = 0
            erros = 0
            
            # MODIFICAÇÃO 13: Processa COMBINAÇÕES de alunos x modalidades
            for aluno_info in st.session_state.alunos_selecionados:
                for modalidade_info in st.session_state.modalidades_selecionadas:
                    # Prepara os dados para salvar
                    dados_inscricao = [
                        aluno_info['unidade'],
                        aluno_info['nome'],
                        aluno_info['ra'],
                        aluno_info['turma'],
                        modalidade_info['genero'],
                        modalidade_info['modalidade'],
                        modalidade_info['unidade'],
                        pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")
                    ]
                    
                    # Tenta salvar na planilha
                    if append_row_and_clear_cache('INSCRITOS-UNIDADE', dados_inscricao):
                        matriculas_realizadas += 1
                    else:
                        erros += 1
            
            total_processado = len(st.session_state.alunos_selecionados) * len(st.session_state.modalidades_selecionadas)
            
            if erros == 0:
                st.success(f"✅ {matriculas_realizadas} matrícula(s) registrada(s) com sucesso!")
                st.info(f"📊 Foram criadas {matriculas_realizadas} combinações de alunos x modalidades")
                
                # Limpa seleção após registro bem-sucedido
                st.session_state.alunos_selecionados = []
                st.session_state.modalidades_selecionadas = []
                st.rerun()  # Recarrega a página para limpar as seleções
            else:
                st.warning(f"⚠️ {matriculas_realizadas} matrícula(s) bem-sucedidas, {erros} com erro.")

if __name__ == "__main__":
    main()