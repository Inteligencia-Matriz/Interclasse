# app.py
import streamlit as st
from utils.Login import pagina_login, verificar_autenticacao, fazer_logout
from utils.Realizar_Cadastros import pagina_principal
from utils.Lista_inscritos import pagina_lista_inscritos
from utils.sheets import *


def main_app():
    """Aplicação principal após login"""
    st.set_page_config(
        page_title="Sistema de Inscrição - E-commerce", 
        layout="wide", 
        page_icon="📊"
    )
    
    # Verificar autenticação
    verificar_autenticacao()
    
    # Header com informações do usuário
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("📊 Sistema de Inscrição - Modalidades E-commerce")
    with col2:
        if 'user_info' in st.session_state:
            st.write(f"👤 **{st.session_state.user_info['nome']}**")
            st.write(f"🏢 {st.session_state.user_info['unidade']}")
            if st.button("🚪 Sair"):
                fazer_logout()
    
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

def main():
    """Função principal que controla o fluxo de autenticação"""
    
    # Inicializa session_state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'autenticado' not in st.session_state:
        st.session_state.autenticado = False
    
    # Verifica se o usuário está logado
    if not st.session_state.autenticado and not st.session_state.logged_in:
        pagina_login()
    else:
        main_app()

if __name__ == "__main__":
    main()