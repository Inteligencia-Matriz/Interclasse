# Lista_inscritos.py
import streamlit as st
import pandas as pd
from utils.sheets import *

def pagina_lista_inscritos():
    """Página para visualizar e gerenciar inscrições"""
    st.title("ALUNOS INSCRITOS")
    
    # Verifica conexão com Google Sheets
    if get_workbook() is None:
        st.error("Falha crítica ao conectar com o Google Sheets. A aplicação não pode continuar.")
        return
    
    # Carrega dados dos inscritos
    try:
        df_inscritos = load_full_sheet_as_df('INSCRITOS-UNIDADE')
        
        if df_inscritos.empty:
            st.info("Nenhum aluno inscrito encontrado.")
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
            st.info(f"Nenhum aluno inscrito encontrado para a unidade {unidade_usuario}.")
            return
        
        st.subheader(f"Alunos inscritos - {unidade_usuario}")
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
            st.subheader("📋 Registros que serão excluídos")
            df_exclusao_preview = pd.DataFrame([r['dados'][:6] for r in registros_para_excluir], 
                                             columns=['Unidade', 'Nome Aluno', 'RA Aluno', 'Turma Aluno', 'Gênero', 'Modalidade'])
            st.dataframe(df_exclusao_preview, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Confirmar exclusão dos registros selecionados", type="primary"):
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