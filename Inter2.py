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
# Funções de diagnóstico e dados - CORRIGIDAS
# =============================================================================

@st.cache_data(ttl=600)
def diagnosticar_modalidades():
    """Função para diagnosticar problemas nas modalidades"""
    df_modalidades = carregar_modalidades_completas()
    
    if df_modalidades.empty:
        st.error("❌ A planilha MODALIDADES está vazia ou não foi carregada")
        return pd.DataFrame()
    
    st.subheader("🔍 Diagnóstico das Modalidades")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.write("**Estrutura da planilha:**")
        st.write(f"Colunas: {df_modalidades.columns.tolist()}")
        st.write(f"Total de linhas: {len(df_modalidades)}")
        
        # Mostra as primeiras linhas para debug
        st.write("**Primeiras 5 linhas:**")
        st.dataframe(df_modalidades.head())
    
    with col2:
        st.write("**Unidades disponíveis:**")
        unidades = df_modalidades['Unidade'].dropna().unique()
        st.write(unidades)
        
        st.write("**Contagem por unidade:**")
        contagem_unidades = df_modalidades['Unidade'].value_counts()
        st.write(contagem_unidades)
    
    with col3:
        st.write("**Gêneros disponíveis:**")
        generos = df_modalidades['Genero'].dropna().unique()
        st.write(generos)
        
        st.write("**Valores de vaga:**")
        valores_vaga = df_modalidades['Tem_Vaga'].value_counts()
        st.write(valores_vaga)
    
    # Verificar combinações específicas
    st.write("**Combinações Unidade-Gênero:**")
    combinacoes = df_modalidades.groupby(['Unidade', 'Genero']).size().reset_index(name='Count')
    st.dataframe(combinacoes)
    
    # Verificar valores únicos para debug
    st.write("**Valores únicos por coluna:**")
    for col in ['Genero', 'Modalidade', 'Unidade', 'Tem_Vaga']:
        st.write(f"{col}: {df_modalidades[col].unique()}")
    
    return df_modalidades

@st.cache_data(ttl=600)
def carregar_modalidades_completas():
    """Carrega todas as informações da aba MODALIDADES com tratamento robusto"""
    try:
        df_modalidades = load_full_sheet_as_df('MODALIDADES')
        
        if df_modalidades.empty:
            st.warning("Nenhuma modalidade encontrada na aba MODALIDADES")
            return pd.DataFrame()
        
        # DEBUG: Mostrar dados brutos
        st.sidebar.write("🔧 DEBUG - Dados brutos MODALIDADES:")
        st.sidebar.write(f"Colunas brutas: {df_modalidades.columns.tolist()}")
        st.sidebar.write(f"Total linhas brutas: {len(df_modalidades)}")
        
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
        
        # Remove linhas completamente vazias
        df_modalidades = df_modalidades.dropna(how='all')
        
        # DEBUG: Mostrar dados processados
        st.sidebar.write("🔧 DEBUG - Dados processados:")
        st.sidebar.write(f"Colunas finais: {df_modalidades.columns.tolist()}")
        st.sidebar.write(f"Total linhas finais: {len(df_modalidades)}")
        
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
        
        # DEBUG
        st.sidebar.write("🔧 DEBUG - Dados alunos:")
        st.sidebar.write(f"Colunas alunos: {df_alunos.columns.tolist()}")
        
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

def formatar_nome_aluno(row):
    """Formata o nome do aluno com unidade, nome e RA para o dropdown"""
    unidade = str(row['Unidade']).strip()
    nome = str(row['Nome do Aluno']).strip()
    ra = str(row['RA do Aluno']).strip()
    turma = str(row['Turma do Aluno']).strip()
    
    return f"{unidade} | {nome} | RA: {ra} | Turma: {turma}"

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

# =============================================================================
# Aplicação Streamlit Principal - CORRIGIDA
# =============================================================================

def main():
    st.set_page_config(
        page_title="Sistema de Inscrição - E-commerce", 
        layout="wide", 
        page_icon="📊"
    )
    
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
    
    # Carrega dados completos das modalidades
    df_modalidades_completas = carregar_modalidades_completas()
    
    if df_modalidades_completas.empty:
        st.error("Não foi possível carregar os dados das modalidades.")
        return
    
    # Seção de diagnóstico (opcional)
    with st.expander("🔍 Diagnóstico - Verificar Dados das Modalidades", expanded=False):
        diagnosticar_modalidades()
    
    st.subheader("Formulário de Inscrição")
    
    # Divide a tela em colunas para organização
    col1, col2 = st.columns(2)
    
    with col1:
        # FILTRO POR UNIDADE (agora única para aluno e modalidade)
        unidades_disponiveis = sorted(df_alunos['Unidade'].unique())
        
        if not unidades_disponiveis:
            st.error("Nenhuma unidade disponível para os alunos")
            return
            
        unidade_selecionada = st.selectbox(
            "Selecione a Unidade:",
            options=unidades_disponiveis,
            index=0,
            help="Selecione a unidade para alunos e modalidades"
        )
        
        # Filtra alunos pela unidade selecionada
        df_alunos_filtrados = df_alunos[df_alunos['Unidade'] == unidade_selecionada]
        
        # Prepara lista de alunos filtrados para o dropdown
        opcoes_alunos = []
        alunos_dict = {}
        
        for idx, row in df_alunos_filtrados.iterrows():
            formato_dropdown = formatar_nome_aluno(row)
            opcoes_alunos.append(formato_dropdown)
            alunos_dict[formato_dropdown] = {
                'unidade': row['Unidade'],
                'nome': row['Nome do Aluno'],
                'ra': row['RA do Aluno'],
                'turma': row['Turma do Aluno']
            }
        
        # Menu de seleção do aluno
        if opcoes_alunos:
            aluno_selecionado = st.selectbox(
                "Selecione o Aluno:",
                options=opcoes_alunos,
                index=0,
                help="Selecione o aluno pela unidade, nome, RA e turma"
            )
        else:
            st.warning(f"Nenhum aluno encontrado para a unidade {unidade_selecionada}")
            aluno_selecionado = None

    with col2:
        # FILTRO POR GÊNERO (das modalidades)
        generos_disponiveis = df_modalidades_completas['Genero'].dropna().unique()
        
        if len(generos_disponiveis) > 0:
            genero_selecionado = st.selectbox(
                "Selecione o Gênero da Modalidade:",
                options=sorted(generos_disponiveis),
                index=0,
                help="Selecione o gênero para filtrar as modalidades"
            )
        else:
            st.error("Nenhum gênero disponível nas modalidades")
            genero_selecionado = None
        
        # FILTRO DE MODALIDADES DISPONÍVEIS (usando a mesma unidade selecionada)
        if genero_selecionado and unidade_selecionada:
            # Filtra por gênero e unidade
            modalidades_filtradas = df_modalidades_completas[
                (df_modalidades_completas['Genero'] == genero_selecionado) & 
                (df_modalidades_completas['Unidade'] == unidade_selecionada)
            ]
            
            # DEBUG: Mostrar filtragem
            st.sidebar.write(f"🔧 DEBUG - Filtro:")
            st.sidebar.write(f"Gênero: {genero_selecionado}")
            st.sidebar.write(f"Unidade: {unidade_selecionada}")
            st.sidebar.write(f"Modalidades encontradas: {len(modalidades_filtradas)}")
            
            # Separa modalidades com vaga e sem vaga
            modalidades_com_vaga = modalidades_filtradas[
                modalidades_filtradas['Tem_Vaga'] != 'NÃO'
            ]['Modalidade'].dropna().unique().tolist()
            
            modalidades_sem_vaga = modalidades_filtradas[
                modalidades_filtradas['Tem_Vaga'] == 'NÃO'
            ]['Modalidade'].dropna().unique().tolist()
            
            if modalidades_com_vaga:
                modalidade_selecionada = st.selectbox(
                    "Selecione a Modalidade:",
                    options=modalidades_com_vaga,
                    help="Selecione a modalidade desejada"
                )
                
                # Mostra informações adicionais sobre a modalidade selecionada
                if modalidade_selecionada:
                    modalidade_info = modalidades_filtradas[
                        modalidades_filtradas['Modalidade'] == modalidade_selecionada
                    ]
                    
                    if not modalidade_info.empty:
                        info = modalidade_info.iloc[0]
                        st.info(f"""
                        **Informações da Modalidade:**
                        - **Vagas totais:** {info.get('Limite_Vagas', 'N/A')}
                        - **Inscritos:** {info.get('Inscritos', 'N/A')}
                        - **Vagas restantes:** {info.get('Vagas_Restantes', 'N/A')}
                        """)
            else:
                st.warning(f"Nenhuma modalidade disponível para gênero {genero_selecionado} na unidade {unidade_selecionada}")
                modalidade_selecionada = None
            
            # Exibe modalidades sem vaga (não selecionáveis)
            if modalidades_sem_vaga:
                st.caption("🚫 Modalidades sem vaga:")
                for modalidade in modalidades_sem_vaga[:3]:
                    st.caption(f"• {modalidade}")
                if len(modalidades_sem_vaga) > 3:
                    st.caption(f"... e mais {len(modalidades_sem_vaga) - 3} modalidades sem vaga")
        else:
            modalidade_selecionada = None
            st.info("Selecione um gênero para ver as modalidades disponíveis")

    # PRÉVIA DO REGISTRO
    if aluno_selecionado and modalidade_selecionada:
        st.subheader("📋 Prévia do Registro")
        aluno_info = alunos_dict[aluno_selecionado]
        
        col_previa1, col_previa2 = st.columns(2)
        with col_previa1:
            st.write("**Dados do Aluno:**")
            st.write(f"Unidade: {aluno_info['unidade']}")
            st.write(f"Nome: {aluno_info['nome']}")
            st.write(f"RA: {aluno_info['ra']}")
            st.write(f"Turma: {aluno_info['turma']}")
        
        with col_previa2:
            st.write("**Dados da Modalidade:**")
            st.write(f"Gênero: {genero_selecionado}")
            st.write(f"Modalidade: {modalidade_selecionada}")
            st.write(f"Unidade: {unidade_selecionada}")

    # Botão para registrar a inscrição
    if st.button("📝 Registrar Inscrição", type="primary"):
        if not aluno_selecionado or not modalidade_selecionada:
            st.error("Por favor, selecione um aluno e uma modalidade.")
        else:
            aluno_info = alunos_dict[aluno_selecionado]
            
            # Prepara os dados para salvar na página INSCRITOS-UNIDADE
            dados_inscricao = [
                aluno_info['unidade'],           # Unidade do aluno
                aluno_info['nome'],              # Nome do aluno
                aluno_info['ra'],                # RA do aluno
                aluno_info['turma'],             # Turma do aluno
                genero_selecionado,              # Gênero da modalidade
                modalidade_selecionada,          # Modalidade selecionada
                unidade_selecionada,             # Unidade da modalidade (mesma do aluno)
                pd.Timestamp.now().strftime("%d/%m/%Y %H:%M:%S")  # Data/hora
            ]
            
            # Tenta salvar na planilha
            if append_row_and_clear_cache('INSCRITOS-UNIDADE', dados_inscricao):
                st.success("✅ Inscrição registrada com sucesso!")
                # Removeu o st.balloons() conforme solicitado
            else:
                st.error("❌ Erro ao registrar a inscrição. Tente novamente.")

if __name__ == "__main__":
    main()