# AtivarAQUI.py
import streamlit as st

# st.set_page_config() está no local CORRETO (primeiro comando)
st.set_page_config(
    page_title="Sistema de Inscrição - E-commerce", 
    layout="wide", 
    page_icon="📊"
)

try:
    # Tenta importar com utils (VS Code)
    from utils.Login import pagina_login, verificar_autenticacao, fazer_logout
    from utils.Realizar_Cadastros import pagina_principal
    from utils.Lista_inscritos import pagina_lista_inscritos
    from utils.Registro_Todas_Unidades import pagina_registro_todas_unidades
except ImportError:
    try:
        # Tenta importar sem utils (Streamlit Cloud)
        from Login import pagina_login, verificar_autenticacao, fazer_logout
        from Realizar_Cadastros import pagina_principal
        from Lista_inscritos import pagina_lista_inscritos
        from Registro_Todas_Unidades import pagina_registro_todas_unidades
    except ImportError as e:
        st.error(f"Erro crítico: Não foi possível importar os módulos. Erro: {e}")
        st.stop()

def main_app():
    """Aplicação principal após login"""
    
    # Verificar autenticação
    verificar_autenticacao()
    
    # Header com informações do usuário - REMOVIDO DAQUI (agora está na sidebar)
    # As informações do usuário foram movidas para a parte inferior da sidebar
    
    st.markdown("---")
    
    # Sidebar com navegação ATUALIZADA
    with st.sidebar:
        st.header("🧭 Navegação")
        
        # Define a página atual
        if 'pagina_atual' not in st.session_state:
            st.session_state.pagina_atual = "Cadastro"
        
        # Botões de navegação ATUALIZADOS
        if st.button("📝 Realizar Cadastros", use_container_width=True, 
                    type="primary" if st.session_state.pagina_atual == "Cadastro" else "secondary"):
            st.session_state.pagina_atual = "Cadastro"
            # CORREÇÃO 2: st.rerun() REMOVIDO. O clique no botão já causa o rerun.
            
        if st.button("📋 Ver Lista de Inscritos", use_container_width=True,
                    type="primary" if st.session_state.pagina_atual == "Lista" else "secondary"):
            st.session_state.pagina_atual = "Lista"
            # CORREÇÃO 2: st.rerun() REMOVIDO.
            
        if st.button("📊 Registro de Todas as Unidades", use_container_width=True,
                    type="primary" if st.session_state.pagina_atual == "TodasUnidades" else "secondary"):
            st.session_state.pagina_atual = "TodasUnidades"
            # CORREÇÃO 2: st.rerun() REMOVIDO.
        
        st.markdown("---")
        st.info("💡 **Dicas:**\n- Use a página de cadastro para inscrever alunos\n- Use a lista para visualizar e gerenciar inscrições\n- Use o registro geral para ver todos os dados")
        
        # NOVA SEÇÃO: Informações do usuário na parte inferior da sidebar
        st.markdown("---")
        st.markdown("### 👤 Informações do Usuário")
        
        if 'user_info' in st.session_state:
            st.write(f"**Nome:** {st.session_state.user_info['nome']}")
            st.write(f"**Unidade:** {st.session_state.user_info['unidade']}")
            
            # Botão de sair na parte inferior
            st.markdown("---")
            if st.button("🚪 Sair", use_container_width=True, type="secondary"):
                fazer_logout()
    
    # Renderiza a página selecionada ATUALIZADA
    # Esta lógica está PERFEITA.
    if st.session_state.pagina_atual == "Cadastro":
        pagina_principal()
    elif st.session_state.pagina_atual == "Lista":
        pagina_lista_inscritos()
    elif st.session_state.pagina_atual == "TodasUnidades":
        pagina_registro_todas_unidades()

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