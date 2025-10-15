# utils/sheets.py
import streamlit as st
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from functools import lru_cache
import os
from datetime import datetime

# Configurações e credenciais
CREDENCIAIS_JSON = "cred.json"
SHEET_ID = '1Fje2R_qHXImbIJZ07eO2gCv9XllllFQkRa6Cdp1_wfc'

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

def registrar_exclusao(dados_registro, usuario_responsavel):
    """Registra a exclusão na aba REGISTROS-EXCLUIDOS"""
    try:
        ws_excluidos = get_ws('REGISTROS-EXCLUIDOS')
        if not ws_excluidos:
            st.error("Não foi possível acessar a aba REGISTROS-EXCLUIDOS")
            return False
        
        dados_exclusao = dados_registro + [
            usuario_responsavel,
            datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ]
        
        todas_celulas = ws_excluidos.get_all_values()
        proxima_linha = len(todas_celulas) + 1 if todas_celulas else 2
        
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