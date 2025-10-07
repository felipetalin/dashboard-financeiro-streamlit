# pages/01_Visão_Geral.py (VERSÃO CORRIGIDA)

import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.graph_objects as go
import plotly.express as px
import datetime
from babel.numbers import format_currency

# --- Configuração da Página e Estilos ---
st.set_page_config(layout="wide", page_title="Resumo Financeiro | Dashboard Opyta")
st.markdown("""
<style>
.block-container { padding: 1rem 2rem 2rem; }
[data-testid="stMetric"] { background-color: #FFFFFF; border: 1px solid #E6E6E6; border-radius: 10px; padding: 15px 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.04); }
[data-testid="stMetricLabel"] { font-size: 16px; }
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
    if _gc is None: return tuple(pd.DataFrame() for _ in range(3))
    try:
        sh = _gc.open_by_key(spreadsheet_id)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        
        # CORREÇÃO: Convertendo para datetime completo para permitir resample
        for df, col in zip([receitas, despesas], ["Data Recebimento", "Data Pagamento"]):
            if col in df.columns and not df.empty:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        for col in ["Valor Recebido", "Valor Pago"]:
            for df in [receitas, despesas]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        return projetos, receitas, despesas
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return tuple(pd.DataFrame() for _ in range(3))

def calcular_metricas_resumo(receitas_f, despesas_f, receitas_total, despesas_total, data_inicio_filtro):
    receitas_periodo = receitas_f['Valor Recebido'].sum()
    despesas_periodo = despesas_f['Valor Pago'].sum()
    resultado_periodo = receitas_periodo - despesas_periodo
    
    # CORREÇÃO: Converte data do filtro para datetime para comparação
    data_inicio_dt = pd.to_datetime(data_inicio_filtro)
    
    receitas_anteriores = receitas_total[receitas_total['Data Recebimento'] < data_inicio_dt]['Valor Recebido'].sum()
    despesas_anteriores = despesas_total[despesas_total['Data Pagamento'] < data_inicio_dt]['Valor Pago'].sum()
    saldo_anterior = receitas_anteriores - despesas_anteriores
    
    saldo_atual = saldo_anterior + resultado_periodo
    
    return saldo_anterior, receitas_periodo, despesas_periodo, resultado_periodo, saldo_atual

# --- INICIALIZAÇÃO E CARGA DE DADOS ---
spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas = carregar_dados(spreadsheet_id, gc)
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

# CORREÇÃO: Converte datas do filtro para datetime
start_date = pd.to_datetime(data_inicio)
end_date = pd.to_datetime(data_fim)

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

# --- LAYOUT DA PÁGINA DE RESUMO ---
st.title("Resumo do Fluxo de Caixa")
st.markdown("---")

# 1. KPIs ESSENCIAIS
saldo_ant, rec_per, desp_per, res_per, saldo_atu = calcular_metricas_resumo(receitas_f, despesas_f, receitas, despesas, data_inicio)
kpi_cols = st.columns(5)
kpi_cols[0].metric("Saldo Anterior", format_currency(saldo_ant, "BRL", locale="pt_BR"))
kpi_cols[1].metric("Receitas do Período", format_currency(rec_per, "BRL", locale="pt_BR"))
kpi_cols[2].metric("Despesas do Período", format_currency(desp_per, "BRL", locale="pt_BR"))
kpi_cols[3].metric("Resultado do Período", format_currency(res_per, "BRL", locale="pt_BR"))
kpi_cols[4].metric("Saldo Atual", format_currency(saldo_atu, "BRL", locale="pt_BR"))

st.markdown("---")

# 2. GRÁFICO COMBINADO DE BARRAS E LINHA
st.subheader("Evolução do Fluxo de Caixa no Período")
if not receitas_f.empty or not despesas_f.empty:
    df_rec = receitas_f.set_index('Data Recebimento').resample('ME')['Valor Recebido'].sum().rename('Receitas')
    df_desp = despesas_f.set_index('Data Pagamento').resample('ME')['Valor Pago'].sum().rename('Despesas')
    df_fluxo = pd.concat([df_rec, df_desp], axis=1).fillna(0)
    df_fluxo['Resultado'] = df_fluxo['Receitas'] - df_fluxo['Despesas']

    if not df_fluxo.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_fluxo.index, y=df_fluxo['Receitas'], name='Receitas', marker_color='#28a745'))
        fig.add_trace(go.Bar(x=df_fluxo.index, y=df_fluxo['Despesas'], name='Despesas', marker_color='#FF4B4B'))
        fig.add_trace(go.Scatter(x=df_fluxo.index, y=df_fluxo['Resultado'], name='Resultado', mode='lines+markers', line=dict(color='#007bff', width=3)))
        fig.update_layout(barmode='group', title_text='Receitas, Despesas e Resultado Mensal', xaxis_title='Mês', yaxis_title='Valor (R$)', legend_title_text='Métricas', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados agregados para o gráfico de evolução.")
else:
    st.info("Sem dados no período para exibir o gráfico de evolução.")

st.markdown("---")

# 3. GRÁFICOS DE ROSCA (DONUT CHARTS)
st.subheader("Composição do Período")
col1, col2 = st.columns(2)
with col1:
    if not receitas_f.empty:
        receitas_cat = receitas_f.groupby("Categoria")['Valor Recebido'].sum().reset_index()
        fig_rec = px.pie(receitas_cat, values='Valor Recebido', names='Categoria', title='Receitas por Categoria', hole=0.4)
        st.plotly_chart(fig_rec, use_container_width=True)
    else:
        st.info("Não há receitas para exibir no gráfico de categorias.")
with col2:
    if not despesas_f.empty:
        despesas_cat = despesas_f.groupby("Categoria")['Valor Pago'].sum().reset_index()
        fig_desp = px.pie(despesas_cat, values='Valor Pago', names='Categoria', title='Despesas por Categoria', hole=0.4)
        st.plotly_chart(fig_desp, use_container_width=True)
    else:
        st.info("Não há despesas para exibir no gráfico de categorias.")
