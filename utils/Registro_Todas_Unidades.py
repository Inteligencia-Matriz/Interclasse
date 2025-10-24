# utils/Registro_Todas_Unidades.py
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.sheets import *
from utils.Login import verificar_autenticacao

def obter_senha_admin():
    """Obtém a senha de administrador da célula G2 da aba AUTORIZADOS"""
    try:
        ws_autorizados = get_ws('AUTORIZADOS')
        if not ws_autorizados:
            return None
        
        # Pega a senha da célula G2 (índice 7, linha 2)
        senha_admin = ws_autorizados.acell('G2').value
        return senha_admin if senha_admin else None
        
    except Exception as e:
        st.error(f"Erro ao obter senha de administrador: {e}")
        return None

def verificar_acesso_admin():
    """Verifica se o usuário tem acesso à página de administração"""
    
    # Inicializa estados da sessão para controle de acesso
    if 'admin_autenticado' not in st.session_state:
        st.session_state.admin_autenticado = False
    if 'tentativas_admin' not in st.session_state:
        st.session_state.tentativas_admin = 0
    if 'bloqueado_admin_ate' not in st.session_state:
        st.session_state.bloqueado_admin_ate = None
    
    # Verifica se está bloqueado
    if st.session_state.bloqueado_admin_ate and datetime.now() < st.session_state.bloqueado_admin_ate:
        tempo_restante = st.session_state.bloqueado_admin_ate - datetime.now()
        segundos_restantes = int(tempo_restante.total_seconds())
        
        st.error(f"🚫 Acesso bloqueado. Tente novamente em {segundos_restantes} segundos.")
        st.stop()
    
    # Se já está autenticado, permite acesso
    if st.session_state.admin_autenticado:
        return True
    
    # Se não está autenticado, exige senha
    return False

def pagina_autenticacao_admin():
    """Página de autenticação para acesso administrativo"""
    
    st.title("🔐 Acesso administrativo")
    st.markdown("---")
    st.warning("**Acesso Restrito:** Esta página contém informações confidenciais de todas as unidades.")
    
    senha_correta = obter_senha_admin()
    
    if not senha_correta:
        st.error("❌ Sistema temporariamente indisponível. Contate o administrador.")
        return
    
    with st.form("form_admin_auth"):
        st.subheader("Digite a senha de administração")
        
        senha_digitada = st.text_input("Senha Administrativa:", type="password", 
                                     placeholder="Digite a senha de acesso")
        
        submitted = st.form_submit_button("🔓 Acessar registros", type="primary")
        
        if submitted:
            if not senha_digitada:
                st.error("Por favor, digite a senha.")
            else:
                if senha_digitada == senha_correta:
                    # Senha correta
                    st.session_state.admin_autenticado = True
                    st.session_state.tentativas_admin = 0
                    st.session_state.bloqueado_admin_ate = None
                    st.success("✅ Acesso concedido!")
                    st.rerun()
                else:
                    # Senha incorreta
                    st.session_state.tentativas_admin += 1
                    tentativas_restantes = 3 - st.session_state.tentativas_admin
                    
                    if st.session_state.tentativas_admin >= 3:
                        # Bloqueia por 1 minuto
                        st.session_state.bloqueado_admin_ate = datetime.now() + timedelta(minutes=1)
                        st.error("🚫 Muitas tentativas falhas. Acesso bloqueado por 1 minuto.")
                        st.rerun()
                    else:
                        st.error(f"❌ Senha incorreta. {tentativas_restantes} tentativas restantes.")

def pagina_registro_todas_unidades():
    """Página para exibir registros de todas as unidades"""
    
    # Verifica autenticação básica do usuário
    verificar_autenticacao()
    
    # Verifica acesso administrativo
    if not verificar_acesso_admin():
        pagina_autenticacao_admin()
        return
    
    # Se chegou aqui, tem acesso administrativo
    st.title("REGISTRO DE TODAS AS UNIDADES")
    st.markdown("---")
    
    # Botão para sair do modo admin
    if st.button("🚪 Sair do modo administrativo"):
        st.session_state.admin_autenticado = False
        st.rerun()
    
    # Carrega dados dos inscritos
    try:
        df_inscritos = load_full_sheet_as_df('INSCRITOS-UNIDADE')
        
        if df_inscritos.empty:
            st.info("Nenhum aluno inscrito encontrado.")
            return
        
        # Verifica e padroniza os nomes das colunas
        if len(df_inscritos.columns) >= 9:
            df_inscritos = df_inscritos.iloc[:, :9]
            df_inscritos.columns = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade', 'Unidade Modalidade', 'Data/Hora', 'Usuario']
        else:
            # Preenche colunas faltantes
            colunas_base = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade']
            colunas_extras = ['Unidade Modalidade', 'Data/Hora', 'Usuario'][:len(df_inscritos.columns)-6]
            df_inscritos.columns = colunas_base + colunas_extras
        
        st.subheader("Todos os alunos inscritos")
        st.write(f"**Total de inscrições:** {len(df_inscritos)}")
        
        # Filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Filtro por unidade
            unidades = sorted(df_inscritos['Unidade'].dropna().unique())
            unidade_selecionada = st.selectbox(
                "Filtrar por Unidade:",
                options=["Todas"] + unidades,
                index=0
            )
        
        with col2:
            # Filtro por modalidade
            modalidades = sorted(df_inscritos['Modalidade'].dropna().unique())
            modalidade_selecionada = st.selectbox(
                "Filtrar por Modalidade:",
                options=["Todas"] + modalidades,
                index=0
            )
        
        with col3:
            # Filtro por gênero
            generos = sorted(df_inscritos['Genero Modalidade'].dropna().unique())
            genero_selecionado = st.selectbox(
                "Filtrar por Gênero:",
                options=["Todos"] + generos,
                index=0
            )
        
        # Aplica filtros
        df_filtrado = df_inscritos.copy()
        
        if unidade_selecionada != "Todas":
            df_filtrado = df_filtrado[df_filtrado['Unidade'] == unidade_selecionada]
        
        if modalidade_selecionada != "Todas":
            df_filtrado = df_filtrado[df_filtrado['Modalidade'] == modalidade_selecionada]
        
        if genero_selecionado != "Todos":
            df_filtrado = df_filtrado[df_filtrado['Genero Modalidade'] == genero_selecionado]
        
        # Estatísticas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Filtrado", len(df_filtrado))
        with col2:
            st.metric("Unidades", df_filtrado['Unidade'].nunique())
        with col3:
            st.metric("Modalidades", df_filtrado['Modalidade'].nunique())
        with col4:
            st.metric("Alunos Únicos", df_filtrado['Nome Aluno'].nunique())
        
        # Tabela com todos os registros
        st.subheader("📋 Lista completa de inscrições")
        
        # Seleciona colunas para exibição
        colunas_exibicao = ['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Genero Modalidade', 'Modalidade', 'Data/Hora']
        colunas_disponiveis = [col for col in colunas_exibicao if col in df_filtrado.columns]
        
        # Exibe a tabela
        st.dataframe(
            df_filtrado[colunas_disponiveis],
            use_container_width=True,
            hide_index=True
        )
        
        # Botão para exportar dados
        if st.button("📥 Exportar para CSV"):
            csv = df_filtrado.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="💾 Baixar CSV",
                data=csv,
                file_name=f"registros_todas_unidades_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")