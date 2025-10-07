# pages/01_Visão_Geral.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import datetime
from babel.numbers import format_currency
import uuid

st.set_page_config(layout="wide", page_title="Visão Geral | Dashboard Opyta")
st.markdown("""
<style>
.metric-box { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 5px 0; text-align: center; }
.metric-box-red { border-left: 10px solid #FF4B4B; background-color: #f9e5e5; }
.metric-box-green { border-left: 10px solid #28a745; background-color: #e9f5ec; }
.metric-box h4 { font-size: 16px; margin-bottom: 5px; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-box p { font-size: 28px; font-weight: bold; margin: 0; }
</style>
""", unsafe_allow_html=True)

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
    if _gc is None: return tuple(pd.DataFrame() for _ in range(5))
    try:
        sh = _gc.open_by_key(spreadsheet_id)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        custos = pd.DataFrame(sh.worksheet("Custos_Fixos_Variaveis").get_all_records())
        parametros_impostos = pd.DataFrame(sh.worksheet("Parametros_Impostos").get_all_records())
        for df, col in zip([receitas, despesas], ["Data Recebimento", "Data Pagamento"]):
            if col in df.columns and not df.empty: df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        for col in ["Valor Recebido", "Valor Pago", "Valor", "Meta de Receita"]:
            for df in [receitas, despesas, custos, projetos]:
                if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return projetos, receitas, despesas, custos, parametros_impostos
    except Exception as e: return tuple(pd.DataFrame() for _ in range(5))
def calcular_totais(receitas, despesas, custos):
    total_receitas = receitas["Valor Recebido"].sum()
    total_despesas = despesas["Valor Pago"].sum()
    total_custos = custos["Valor"].sum()
    lucro_total = total_receitas - total_despesas - total_custos
    fluxo_caixa = total_receitas - total_despesas
    return total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa

spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas, custos, parametros_impostos = carregar_dados(spreadsheet_id, gc)
if projetos.empty:
    st.error("Falha ao carregar dados. A página não pode ser exibida.")
    st.stop()

st.sidebar.title("Configurações")
st.sidebar.header("Filtros")
cliente_selecionado = st.sidebar.selectbox("Cliente", ["Todos"] + projetos["Cliente"].unique().tolist())
projetos_cliente = projetos[projetos["Cliente"] == cliente_selecionado] if cliente_selecionado != "Todos" else projetos
projeto_selecionado = st.sidebar.selectbox("Projeto", ["Todos"] + projetos_cliente["Código"].tolist())
hoje = datetime.date.today()
data_inicio = st.sidebar.date_input("Data de Início", hoje.replace(day=1))
data_fim = st.sidebar.date_input("Data de Fim", hoje)

receitas_f, despesas_f = receitas.copy(), despesas.copy()
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

st.title("Visão Geral do Desempenho")
total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa = calcular_totais(receitas_f, despesas_f, custos)
kpi_cols = st.columns(5)
kpi_cols[0].metric("Receita Total", format_currency(total_receitas, "BRL", locale="pt_BR"))
kpi_cols[1].metric("Despesa Total", format_currency(total_despesas, "BRL", locale="pt_BR"))
kpi_cols[2].metric("Custos Fixos/Var.", format_currency(total_custos, "BRL", locale="pt_BR"))
kpi_cols[3].metric("Lucro Total", format_currency(lucro_total, "BRL", locale="pt_BR"))
kpi_cols[4].metric("Fluxo de Caixa", format_currency(fluxo_caixa, "BRL", locale="pt_BR"))
st.markdown("---")

# ... Restante do layout da Visão Geral (gráficos, metas, etc.) ...
