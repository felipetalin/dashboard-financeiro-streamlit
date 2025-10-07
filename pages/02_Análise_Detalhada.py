# Código para o novo arquivo: pages/02_Análise_Detalhada.py

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import datetime
from babel.numbers import format_currency

# --- Funções e Carregamento de Dados ---
# Cada página precisa carregar os dados. O cache do Streamlit garante que isso não seja lento.
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
    if _gc is None: return tuple(pd.DataFrame() for _ in range(3))
    try:
        sh = _gc.open_by_key(spreadsheet_id)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        for df, col in zip([receitas, despesas], ["Data Recebimento", "Data Pagamento"]):
            if col in df.columns and not df.empty: df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        for col in ["Valor Recebido", "Valor Pago"]:
            for df in [receitas, despesas]:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return projetos, receitas, despesas
    except Exception as e: return tuple(pd.DataFrame() for _ in range(3))

# --- INICIALIZAÇÃO E CARGA DE DADOS ---
spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas = carregar_dados(spreadsheet_id, gc)
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
receitas_f = receitas.copy()
despesas_f = despesas.copy()
if cliente_selecionado != "Todos":
    codigos_cliente = projetos[projetos["Cliente"] == cliente_selecionado]["Código"].tolist()
    receitas_f = receitas_f[receitas_f["Projeto"].isin(codigos_cliente)]
    despesas_f = despesas_f[despesas_f["Projeto"].isin(codigos_cliente)]
if projeto_selecionado != "Todos":
    receitas_f = receitas_f[receitas_f["Projeto"] == projeto_selecionado]
    despesas_f = despesas_f[despesas_f["Projeto"] == projeto_selecionado]
if data_inicio and data_fim and data_inicio <= data_fim:
    receitas_f = receitas_f[receitas_f["Data Recebimento"].between(data_inicio, data_fim)]
    despesas_f = despesas_f[despesas_f["Data Pagamento"].between(data_inicio, data_fim)]

# --- LAYOUT DA PÁGINA "ANÁLISE DETALHADA" ---
st.title("📊 Análise Detalhada de Lançamentos")
st.markdown("Explore todas as receitas e despesas para o período e filtros selecionados.")
st.markdown("---")

st.header("Receitas Detalhadas")
st.dataframe(receitas_f, use_container_width=True)

st.header("Despesas Detalhadas")
st.dataframe(despesas_f, use_container_width=True)
