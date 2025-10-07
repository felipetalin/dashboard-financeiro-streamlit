# Código ATUALIZADO para: pages/01_Visão_Geral.py

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import datetime
from babel.numbers import format_currency
import uuid

# --- Configuração da Página e Estilos ---
st.set_page_config(layout="wide", page_title="Visão Geral | Dashboard Opyta")
st.markdown("""
<style>
.block-container {
    padding: 2rem 2rem;
    border: 1px solid #e6e6e6;
    border-radius: 10px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    margin-bottom: 2rem;
}
.metric-box { border: 1px solid #ddd; border-radius: 10px; padding: 15px; margin: 5px 0; text-align: center; }
.metric-box-red { border-left: 10px solid #FF4B4B; background-color: #f9e5e5; }
.metric-box-green { border-left: 10px solid #28a745; background-color: #e9f5ec; }
.metric-box h4 { font-size: 16px; margin-bottom: 5px; color: #555; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.metric-box p { font-size: 28px; font-weight: bold; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- Funções Core ---
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
def calcular_totais(df_receitas, df_despesas, df_custos):
    receita = df_receitas["Valor Recebido"].sum()
    despesa = df_despesas["Valor Pago"].sum()
    custo = df_custos["Valor"].sum()
    lucro = receita - despesa - custo
    fluxo = receita - despesa
    return receita, despesa, custo, lucro, fluxo

# --- INICIALIZAÇÃO E CARGA DE DADOS ---
spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas, custos, parametros_impostos = carregar_dados(spreadsheet_id, gc)
if projetos.empty:
    st.error("Falha ao carregar dados. A página não pode ser exibida.")
    st.stop()

# --- SIDEBAR ---
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

# --- LAYOUT PROFISSIONAL DA "VISÃO GERAL" ---
st.title("Dashboard: Visão Geral")
st.markdown("Análise de performance financeira dos projetos.")

# KPI Container com 5 colunas
with st.container():
    st.markdown('<div class="block-container">', unsafe_allow_html=True)
    total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa = calcular_totais(receitas_f, despesas_f, custos)
    kpi_cols = st.columns(5)
    kpi_cols[0].metric("Receita Total", format_currency(total_receitas, "BRL", locale="pt_BR"))
    kpi_cols[1].metric("Despesa Total", format_currency(total_despesas, "BRL", locale="pt_BR"))
    kpi_cols[2].metric("Custos Fixos/Var.", format_currency(total_custos, "BRL", locale="pt_BR"))
    kpi_cols[3].metric("Lucro Total", format_currency(lucro_total, "BRL", locale="pt_BR"))
    kpi_cols[4].metric("Fluxo de Caixa", format_currency(fluxo_caixa, "BRL", locale="pt_BR"))
    st.markdown('</div>', unsafe_allow_html=True)

# Container para o gráfico principal
with st.container():
    st.markdown('<div class="block-container">', unsafe_allow_html=True)
    st.header("📈 Evolução Financeira")
    df_tempo_receita = receitas_f.rename(columns={"Data Recebimento": "Data", "Valor Recebido": "Valor"}).assign(Tipo="Receita")
    df_tempo_despesa = despesas_f.rename(columns={"Data Pagamento": "Data", "Valor Pago": "Valor"}).assign(Tipo="Despesa")
    df_tempo = pd.concat([df_tempo_receita, df_tempo_despesa])
    if not df_tempo.empty:
        fig_area = px.area(df_tempo, x="Data", y="Valor", color="Tipo", labels={"Valor": "Valor (R$)"}, color_discrete_map={"Receita": "#28a745", "Despesa": "#FF4B4B"})
        st.plotly_chart(fig_area, use_container_width=True)
    else:
        st.info("Sem dados no período para exibir o gráfico de evolução.")
    st.markdown('</div>', unsafe_allow_html=True)

# ** MUDANÇA AQUI: Separamos os containers para ficarem em linhas diferentes **

# Container para a seção Top 5 Despesas
with st.container():
    st.markdown('<div class="block-container">', unsafe_allow_html=True)
    st.header("💡 Top 5 Despesas")
    if not despesas_f.empty:
        top_despesas = despesas_f.groupby("Categoria")["Valor Pago"].sum().nlargest(5).reset_index()
        fig_bar = px.bar(top_despesas, x="Valor Pago", y="Categoria", orientation='h', labels={"Valor Pago": "Total Gasto (R$)", "Categoria": ""})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Não há despesas no período.")
    st.markdown('</div>', unsafe_allow_html=True)

# Container para a seção Status das Metas
with st.container():
    st.markdown('<div class="block-container">', unsafe_allow_html=True)
    st.header("🚨 Status das Metas")
    projetos_com_meta = projetos[projetos['Meta de Receita'] > 0]
    status_metas = []
    for _, projeto in projetos_com_meta.iterrows():
        meta = projeto['Meta de Receita']
        receitas_projeto = receitas_f[receitas_f["Projeto"] == projeto["Código"]]
        total_receita_projeto = receitas_projeto["Valor Recebido"].sum()
        percentual = (total_receita_projeto / meta) * 100 if meta > 0 else 0
        status_metas.append({"nome": projeto["Código"], "percentual": percentual})
    if not status_metas:
        st.info("Nenhum projeto com meta.")
    else:
        cols = st.columns(len(status_metas))
        for i, status in enumerate(status_metas):
            with cols[i]:
                css_class = "metric-box-green" if status['percentual'] >= 100 else "metric-box-red"
                st.markdown(f'<div class="metric-box {css_class}"><h4>{status["nome"]}</h4><p>{status["percentual"]:.1f}%</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
