# Login.py
import streamlit as st
import uuid
import smtplib
import bcrypt
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from utils.sheets import *

# ------------------------------------------------------------
# Configurações de Segurança
# ------------------------------------------------------------
SMTP_USER = 'inteligencia@matrizeducacao.com.br'
SMTP_PASSWORD = 'fqbk yrsj fvlt belq' #Senha básica criada so para enviar mensagens
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587

# ------------------------------------------------------------
# Funções de Autenticação Segura
# ------------------------------------------------------------
def verificar_autenticacao():
    """
    Chame esta função no topo de cada página privada para garantir
    que o usuário esteja autenticado. Se não estiver, para a execução.
    """
    if not st.session_state.get("autenticado"):
        st.error("🚫 Acesso não autorizado. Faça login para continuar.")
        st.stop()

def carregar_usuarios_autorizados_com_senhas():
    """Carrega os usuários autorizados com senhas da aba AUTORIZADOS"""
    try:
        df_autorizados = load_full_sheet_as_df('AUTORIZADOS')
        
        if df_autorizados.empty:
            st.error("Nenhum usuário autorizado encontrado na aba AUTORIZADOS")
            return {}
        
        # Verifica se tem pelo menos 6 colunas (A até F)
        if len(df_autorizados.columns) < 6:
            st.error("A planilha AUTORIZADOS não tem colunas suficientes")
            return {}
        
        # Pega as colunas: Unidade (A), Nome (B), Coluna_C (C), Email (D), Telefone (E), Senha (F)
        df_autorizados = df_autorizados.iloc[:, :6]
        df_autorizados.columns = ['Unidade', 'Nome', 'Coluna_C', 'Email', 'Telefone', 'Senha']
        
        # Limpeza dos dados
        for col in ['Unidade', 'Nome', 'Email', 'Telefone', 'Senha']:
            if col in df_autorizados.columns:
                df_autorizados[col] = df_autorizados[col].astype(str).str.strip()
        
        # Remove linhas vazias
        df_autorizados = df_autorizados.dropna(subset=['Email'])
        df_autorizados = df_autorizados[df_autorizados['Email'] != '']
        df_autorizados = df_autorizados[df_autorizados['Email'] != 'nan']
        
        # Cria dicionário de usuários
        usuarios = {}
        for _, row in df_autorizados.iterrows():
            email = row['Email'].lower().strip()
            usuarios[email] = {
                'unidade': row['Unidade'],
                'nome': row['Nome'],
                'telefone': row['Telefone'],
                'senha_hash': row['Senha'] if row['Senha'] and row['Senha'] != 'nan' else '',
                'tem_senha': bool(row['Senha'] and row['Senha'] != 'nan' and row['Senha'] != '')
            }
        
        return usuarios
        
    except Exception as e:
        st.error(f"Erro ao carregar usuários autorizados: {e}")
        return {}

def limpar_hash(hash_sujo):
    """Remove quebras de linha e espaços extras do hash"""
    if not hash_sujo:
        return ""
    # Remove quebras de linha e espaços extras
    hash_limpo = hash_sujo.replace('\n', '').replace('\r', '').strip()
    return hash_limpo

def atualizar_senha_usuario(email, senha_hash):
    """Atualiza a senha do usuário na coluna F da planilha AUTORIZADOS"""
    try:
        ws_autorizados = get_ws('AUTORIZADOS')
        if not ws_autorizados:
            st.error("Não foi possível acessar a aba AUTORIZADOS")
            return False
        
        # Encontra a linha do usuário pelo email
        todas_linhas = ws_autorizados.get_all_values()
        linha_encontrada = -1
        
        for idx, linha in enumerate(todas_linhas):
            if len(linha) > 3 and linha[3].strip().lower() == email.lower():
                linha_encontrada = idx
                break
        
        if linha_encontrada == -1:
            st.error("Usuário não encontrado na planilha para atualização de senha")
            return False
        
        # Limpa o hash antes de salvar
        senha_hash_limpo = limpar_hash(senha_hash)
        
        # Atualiza a coluna F (índice 6) - senha hash
        ws_autorizados.update_cell(linha_encontrada + 1, 6, senha_hash_limpo)
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao atualizar senha: {e}")
        return False

def enviar_codigo_verificacao(email, token):
    """Envia código de verificação por email"""
    try:
        msg = MIMEText(f"""
        Olá!
        
        Seu código de verificação para cadastro de senha é: {token}
        
        Este código é válido por 10 minutos.
        
        Equipe Sistema de Inscrição
        """)
        msg['Subject'] = 'Código de Verificação - Cadastro de Senha'
        msg['From'] = SMTP_USER
        msg['To'] = email

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Erro ao enviar código: {e}")
        return False

def registrar_login(user_info):
    """Registra o login na aba LOGIN"""
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
            datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "LOGIN_OK"
        ]
        
        # Encontra a próxima linha vazia
        todas_celulas = ws_login.get_all_values()
        proxima_linha = len(todas_celulas) + 1
        
        # Escreve a partir da coluna A
        range_escrita = f'A{proxima_linha}'
        ws_login.update(range_escrita, [dados_login], value_input_option="USER_ENTERED")
        
        return True
        
    except Exception as e:
        st.error(f"Erro ao registrar login: {e}")
        return False

def validar_forca_senha(senha):
    """Valida a força da senha"""
    if len(senha) < 8:
        return False, "A senha deve ter pelo menos 8 caracteres"
    
    if not any(c.isupper() for c in senha):
        return False, "A senha deve ter pelo menos uma letra maiúscula"
    
    if not any(c.islower() for c in senha):
        return False, "A senha deve ter pelo menos uma letra minúscula"
    
    if not any(c.isdigit() for c in senha):
        return False, "A senha deve ter pelo menos um número"
    
    return True, "Senha forte"

# ------------------------------------------------------------
# Interface de Login Segura
# ------------------------------------------------------------
def pagina_login():
    """Página de login com sistema seguro de autenticação"""
    
    # Configuração da página
    st.set_page_config(
        page_title="Sistema de Login Seguro - E-commerce", 
        layout="centered", 
        page_icon="🔐"
    )
    
    # Inicialização do estado da sessão
    if "etapa_login" not in st.session_state:
        st.session_state.etapa_login = "email"
    if "tentativas_login" not in st.session_state:
        st.session_state.tentativas_login = 0
    if "bloqueado_ate" not in st.session_state:
        st.session_state.bloqueado_ate = None
    
    # Verifica se está bloqueado
    if st.session_state.bloqueado_ate and datetime.now() < st.session_state.bloqueado_ate:
        tempo_restante = st.session_state.bloqueado_ate - datetime.now()
        minutos = int(tempo_restante.total_seconds() // 60)
        segundos = int(tempo_restante.total_seconds() % 60)
        
        st.error(f"🚫 Muitas tentativas falhas. Sistema bloqueado por {minutos}min {segundos}s.")
        st.stop()
    
    st.title("🔐 Sistema de Inscrição - Login Seguro")
    st.markdown("---")
    
    # Carrega usuários
    usuarios = carregar_usuarios_autorizados_com_senhas()
    
    if not usuarios:
        st.error("Sistema temporariamente indisponível. Tente novamente mais tarde.")
        return
    
    # ETAPA 1: Email
    if st.session_state.etapa_login == "email":
        with st.form("form_email"):
            st.subheader("📧 Identificação")
            email = st.text_input("Digite seu e-mail institucional:", placeholder="seu.email@empresa.com")
            
            submitted = st.form_submit_button("Continuar", type="primary")
            
            if submitted:
                email = email.strip().lower()
                
                if not email:
                    st.error("Por favor, digite seu e-mail.")
                elif email not in usuarios:
                    st.error("E-mail não autorizado para acesso ao sistema.")
                else:
                    st.session_state.email_login = email
                    st.session_state.dados_usuario = usuarios[email]
                    
                    if usuarios[email]['tem_senha']:
                        st.session_state.etapa_login = "senha"
                        st.rerun()
                    else:
                        # Primeiro acesso - gera token
                        token = str(uuid.uuid4())[:6].upper()
                        st.session_state.token_verificacao = token
                        st.session_state.etapa_login = "verificacao"
                        
                        if enviar_codigo_verificacao(email, token):
                            st.success("📨 Código de verificação enviado para seu e-mail!")
                            st.rerun()
                        else:
                            st.error("❌ Erro ao enviar código. Tente novamente.")
    
    # ETAPA 2: Verificação (primeiro acesso)
    elif st.session_state.etapa_login == "verificacao":
        st.info(f"📨 Um código de verificação foi enviado para: **{st.session_state.email_login}**")
        
        with st.form("form_verificacao"):
            st.subheader("🔒 Cadastro de Senha Segura")
            
            token_digitado = st.text_input("Código de verificação:", placeholder="Digite o código de 6 dígitos")
            nova_senha = st.text_input("Crie sua senha:", type="password", 
                                     placeholder="Mínimo 8 caracteres com maiúsculas, minúsculas e números")
            confirmar_senha = st.text_input("Confirme sua senha:", type="password")
            
            submitted = st.form_submit_button("Criar Senha Segura", type="primary")
            
            if submitted:
                if token_digitado != st.session_state.token_verificacao:
                    st.error("❌ Código de verificação inválido.")
                elif nova_senha != confirmar_senha:
                    st.error("❌ As senhas não coincidem.")
                else:
                    senha_valida, mensagem = validar_forca_senha(nova_senha)
                    if not senha_valida:
                        st.error(f"❌ {mensagem}")
                    else:
                        # Cria hash da senha
                        try:
                            # Garantir encoding consistente
                            senha_bytes = nova_senha.encode('utf-8')
                            salt = bcrypt.gensalt()
                            senha_hash = bcrypt.hashpw(senha_bytes, salt).decode('utf-8')
                            
                            # Limpa o hash antes de salvar
                            senha_hash_limpo = limpar_hash(senha_hash)
                            
                            # Salva no Google Sheets
                            if atualizar_senha_usuario(st.session_state.email_login, senha_hash_limpo):
                                # Atualiza o session_state com o hash limpo
                                st.session_state.dados_usuario['senha_hash'] = senha_hash_limpo
                                st.session_state.dados_usuario['tem_senha'] = True
                                
                                st.success("✅ Senha criada com sucesso! Faça o login.")
                                st.session_state.etapa_login = "senha"
                                st.rerun()
                            else:
                                st.error("❌ Erro ao salvar senha. Tente novamente.")
                        except Exception as e:
                            st.error(f"❌ Erro ao processar senha: {e}")
    
    # ETAPA 3: Senha
    elif st.session_state.etapa_login == "senha":
        st.info(f"👤 Logando como: **{st.session_state.email_login}**")
        
        with st.form("form_senha"):
            st.subheader("🔑 Digite sua senha")
            senha_digitada = st.text_input("Senha:", type="password", placeholder="Digite sua senha")
            
            submitted = st.form_submit_button("Entrar no Sistema", type="primary")
            
            if submitted:
                if not senha_digitada:
                    st.error("Por favor, digite sua senha.")
                else:
                    # Limpa o hash da sessão antes de comparar
                    senha_hash_sessao = limpar_hash(st.session_state.dados_usuario['senha_hash'])
                    
                    try:
                        # Teste com encoding consistente e hash limpo
                        if bcrypt.checkpw(senha_digitada.encode('utf-8'), senha_hash_sessao.encode('utf-8')):
                            # Login bem-sucedido
                            st.session_state.autenticado = True
                            st.session_state.logged_in = True
                            st.session_state.user_info = {
                                'unidade': st.session_state.dados_usuario['unidade'],
                                'nome': st.session_state.dados_usuario['nome'],
                                'email': st.session_state.email_login
                            }
                            st.session_state.tentativas_login = 0
                            st.session_state.bloqueado_ate = None
                            
                            # Registra o login na aba LOGIN
                            registrar_login(st.session_state.user_info)
                            
                            st.success(f"✅ Bem-vindo(a), {st.session_state.dados_usuario['nome']}!")
                            st.rerun()
                        else:
                            # Senha incorreta
                            st.session_state.tentativas_login += 1
                            tentativas_restantes = 5 - st.session_state.tentativas_login
                            
                            if st.session_state.tentativas_login >= 5:
                                # Bloqueia por 15 minutos
                                st.session_state.bloqueado_ate = datetime.now() + timedelta(minutes=15)
                                st.error("🚫 Muitas tentativas falhas. Sistema bloqueado por 15 minutos.")
                            else:
                                st.error(f"❌ Senha incorreta. {tentativas_restantes} tentativas restantes.")
                            
                            st.rerun()
                            
                    except Exception as e:
                        st.error(f"❌ Erro ao verificar senha: {e}")
        
        # Link para recuperação de senha
        st.markdown("---")
        with st.expander("🔓 Esqueci minha senha"):
            st.info("""
            **Recuperação de Senha:**
            - Entre em contato com o administrador do sistema:
                alberto.bernardo@matrizeducacao.com.br

            """)
            
            if st.button("Voltar para identificação"):
                st.session_state.etapa_login = "email"
                st.rerun()

# Função de logout para ser usada em outras páginas
def fazer_logout():
    """Realiza logout seguro"""
    st.session_state.clear()
    st.rerun()