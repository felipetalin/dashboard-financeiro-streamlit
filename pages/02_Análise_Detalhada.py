# pages/02_Análise_Detalhada.py (VERSÃO FINAL SINCRONIZADA)

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
from babel.numbers import format_currency

# --- Funções e Carregamento de Dados ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
@st.cache_resource
def conectar_sheets():
    try:
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e: return None
@st.cache_data(ttl=300)
def carregar_dados(spreadsheet_id, _gc):
    if _gc is None: return tuple(pd.DataFrame() for _ in range(4))
    try:
        sh = _gc.open_by_key(spreadsheet_id)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        # CORREÇÃO: Usando os nomes exatos das abas
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        custos = pd.DataFrame(sh.worksheet("Custos_Fixos_Variaveis").get_all_records())
        
        for df, col in zip([receitas, despesas, custos], ["Data Recebimento", "Data Pagamento", "Data"]):
            if col in df.columns and not df.empty: df[col] = pd.to_datetime(df[col], errors='coerce')
        
        for df, col in zip([receitas, despesas, custos], ["Valor Recebido", "Valor Pago", "Valor"]):
             if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
                
        return projetos, receitas, despesas, custos
    except gspread.exceptions.WorksheetNotFound as e:
        st.error(f"Erro: A aba '{e.args[0]}' não foi encontrada. Verifique o nome na planilha.")
        return tuple(pd.DataFrame() for _ in range(4))
    except Exception as e:
        st.error(f"Ocorreu um erro ao ler os dados: {e}")
        return tuple(pd.DataFrame() for _ in range(4))

# --- INICIALIZAÇÃO E CARGA DE DADOS ---
spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas, custos = carregar_dados(spreadsheet_id, gc)
if projetos.empty:
    st.error("Falha ao carregar dados. A página não pode ser exibida.")
    st.stop()

# --- SIDEBAR COM FILTROS ---
st.sidebar.title("Configurações")
st.sidebar.header("Filtros")
cliente_selecionado = st.sidebar.selectbox("Cliente", ["Todos"] + projetos["Cliente"].unique().tolist())
projetos_cliente = projetos[projetos["Cliente"] == cliente_selecionado] if cliente_selecionado != "Todos" else projetos
projeto_selecionado = st.sidebar.selectbox("Projeto", ["Todos"] + projetos_cliente["Código"].tolist())
hoje = datetime.date.today()
data_inicio = st.sidebar.date_input("Data de Início", hoje.replace(day=1))
data_fim = st.sidebar.date_input("Data de Fim", hoje)

# --- APLICAÇÃO DOS FILTROS ---
receitas_f, despesas_f, custos_f = receitas.copy(), despesas.copy(), custos.copy()
start_date, end_date = pd.to_datetime(data_inicio), pd.to_datetime(data_fim)
if cliente_selecionado != "Todos":
    codigos_cliente = projetos[projetos["Cliente"] == cliente_selecionado]["Código"].tolist()
    receitas_f = receitas_f[receitas_f["Projeto"].isin(codigos_cliente)]
    despesas_f = despesas_f[despesas_f["Projeto"].isin(codigos_cliente)]
if projeto_selecionado != "Todos":
    receitas_f = receitas_f[receitas_f["Projeto"] == projeto_selecionado]
    despesas_f = despesas_f[despesas_f["Projeto"] == projeto_selecionado]
if start_date and end_date and start_date <= end_date:
    receitas_f = receitas_f[receitas_f["Data Recebimento"].between(start_date, end_date)]
    despesas_f = despesas_f[despesas_f["Data Pagamento"].between(start_date, end_date)]
    custos_f = custos_f[custos_f["Data"].between(start_date, end_date)]

# --- LAYOUT DA PÁGINA "ANÁLISE DETALHADA" ---
st.title("📊 Análise Detalhada de Lançamentos")
st.markdown("Explore todos os lançamentos para o período e filtros selecionados.")
st.markdown("---")

st.header("Receitas Detalhadas")
st.dataframe(receitas_f, use_container_width=True)

st.header("Despesas Detalhadas")
st.dataframe(despesas_f, use_container_width=True)

st.header("Custos Fixos e Variáveis Detalhados")
st.dataframe(custos_f, use_container_width=True)
