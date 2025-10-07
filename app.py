import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import datetime
from babel.numbers import format_currency
import uuid

# --- Configuração da Página e Estilos ---
st.set_page_config(layout="wide", page_title="Dashboard Financeiro Opyta")

# CSS para os cards de status e containers
st.markdown("""
<style>
.metric-box {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 15px;
    margin: 5px 0;
    text-align: center;
}
.metric-box-red {
    border-left: 10px solid #FF4B4B;
    background-color: #f9e5e5;
}
.metric-box-green {
    border-left: 10px solid #28a745;
    background-color: #e9f5ec;
}
.metric-box h4 {
    font-size: 16px; margin-bottom: 5px; color: #555;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.metric-box p {
    font-size: 28px; font-weight: bold; margin: 0;
}
.stExpander {
    border: 1px solid #ddd;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# --- Funções Core (sem alterações) ---
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
@st.cache_resource
def conectar_sheets():
    try:
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        return None
@st.cache_data(ttl=300)
def carregar_dados(spreadsheet_id, _gc):
    if _gc is None: return tuple(pd.DataFrame() for _ in range(5))
    try:
        sh = _gc.open_by_key(spreadsheet_id)
        # ... (código de carregar dados permanece o mesmo)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        custos = pd.DataFrame(sh.worksheet("Custos_Fixos_Variaveis").get_all_records())
        parametros_impostos = pd.DataFrame(sh.worksheet("Parametros_Impostos").get_all_records())

        for df, col in zip([receitas, despesas], ["Data Recebimento", "Data Pagamento"]):
            if col in df.columns and not df.empty:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date
        
        # Garantir que colunas numéricas são numéricas
        for col in ["Valor Recebido", "Valor Pago", "Valor", "Meta de Receita"]:
            for df in [receitas, despesas, custos, projetos]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        return projetos, receitas, despesas, custos, parametros_impostos
    except Exception as e:
        st.error(f"Erro ao ler dados: {e}")
        return tuple(pd.DataFrame() for _ in range(5))
# ... (demais funções como escrever_dados, calcular_impostos, calcular_totais permanecem as mesmas)
def escrever_dados(spreadsheet_id, worksheet_name, data, gc):
    try:
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(worksheet_name)
        worksheet.clear()
        worksheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"Não foi possível escrever na planilha '{worksheet_name}': {e}")
def calcular_impostos(receitas_df, parametros_impostos_df):
    if receitas_df.empty or parametros_impostos_df.empty: return pd.DataFrame()
    impostos_calculados = []
    for _, receita in receitas_df.iterrows():
        valor_receita = float(receita["Valor Recebido"])
        impostos_projeto = {"ID": str(uuid.uuid4()), "Projeto": receita["Projeto"], "Valor da Receita": valor_receita}
        total_impostos = 0
        for _, parametro in parametros_impostos_df.iterrows():
            imposto = parametro["Imposto"]
            aliquota = float(str(parametro["Alíquota"]).replace(',', '.'))
            valor_imposto = valor_receita * aliquota
            impostos_projeto[imposto] = valor_imposto
            total_impostos += valor_imposto
        impostos_projeto["Total de Impostos"] = total_impostos
        impostos_calculados.append(impostos_projeto)
    return pd.DataFrame(impostos_calculados)
def calcular_totais(receitas, despesas, custos):
    total_receitas = receitas["Valor Recebido"].sum()
    total_despesas = despesas["Valor Pago"].sum()
    total_custos = custos["Valor"].sum()
    lucro_total = total_receitas - total_despesas - total_custos
    fluxo_caixa = total_receitas - total_despesas
    return total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa

# --- INICIALIZAÇÃO E CARGA DE DADOS ---
spreadsheet_id = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
gc = conectar_sheets()
projetos, receitas, despesas, custos, parametros_impostos = carregar_dados(spreadsheet_id, gc)

if projetos.empty:
    st.error("Falha crítica ao carregar os dados de 'Projetos'. O app não pode continuar.")
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
# ... (lógica de filtro permanece a mesma)
if cliente_selecionado != "Todos":
    codigos_projetos_cliente = projetos[projetos["Cliente"] == cliente_selecionado]["Código"].tolist()
    receitas_f = receitas_f[receitas_f["Projeto"].isin(codigos_projetos_cliente)]
    despesas_f = despesas_f[despesas_f["Projeto"].isin(codigos_projetos_cliente)]
if projeto_selecionado != "Todos":
    receitas_f = receitas_f[receitas_f["Projeto"] == projeto_selecionado]
    despesas_f = despesas_f[despesas_f["Projeto"] == projeto_selecionado]
if data_inicio and data_fim and data_inicio <= data_fim:
    receitas_f = receitas_f[receitas_f["Data Recebimento"].between(data_inicio, data_fim)]
    despesas_f = despesas_f[despesas_f["Data Pagamento"].between(data_inicio, data_fim)]

# --- LAYOUT PRINCIPAL REMODELADO ---

# MELHORIA 1: Container para o cabeçalho
with st.container():
    st.title("Dashboard Financeiro de Projetos")
    st.markdown("Visão geral dos indicadores financeiros para o período selecionado.")
    
    total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa = calcular_totais(receitas_f, despesas_f, custos)
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Receita Total", format_currency(total_receitas, "BRL", locale="pt_BR"))
    col2.metric("Despesa Total", format_currency(total_despesas, "BRL", locale="pt_BR"))
    col3.metric("Custos Fixos/Var.", format_currency(total_custos, "BRL", locale="pt_BR"))
    col4.metric("Lucro Total", format_currency(lucro_total, "BRL", locale="pt_BR"))
    col5.metric("Fluxo de Caixa", format_currency(fluxo_caixa, "BRL", locale="pt_BR"))

st.markdown("---")

# Gráfico de Evolução (continua sendo o principal)
st.header("📈 Evolução Financeira no Período")
df_tempo_receita = receitas_f.rename(columns={"Data Recebimento": "Data", "Valor Recebido": "Valor"}).assign(Tipo="Receita")
df_tempo_despesa = despesas_f.rename(columns={"Data Pagamento": "Data", "Valor Pago": "Valor"}).assign(Tipo="Despesa")
df_tempo = pd.concat([df_tempo_receita, df_tempo_despesa])
if not df_tempo.empty:
    fig = px.area(df_tempo, x="Data", y="Valor", color="Tipo", title="Receitas vs. Despesas",
                  labels={"Valor": "Valor (R$)", "Data": "Data"}, color_discrete_map={"Receita": "#28a745", "Despesa": "#FF4B4B"})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem dados no período para exibir o gráfico de evolução.")

st.markdown("---")

# MELHORIA 2: Novos gráficos e cards de meta em colunas
col_vis1, col_vis2 = st.columns(2)

with col_vis1:
    st.header("💡 Análise de Custos e Despesas")
    
    # MELHORIA 3: Novo Gráfico de Top 5 Despesas
    if not despesas_f.empty:
        top_despesas = despesas_f.groupby("Categoria")["Valor Pago"].sum().nlargest(5).reset_index()
        fig_bar = px.bar(top_despesas, x="Valor Pago", y="Categoria", orientation='h',
                         title="Top 5 Despesas por Categoria", labels={"Valor Pago": "Total Gasto (R$)", "Categoria": "Categoria"})
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("Não há despesas no período para analisar.")

with col_vis2:
    st.header("🚨 Status das Metas")
    projetos_com_meta = projetos[projetos['Meta de Receita'] > 0]
    status_metas = []
    for _, projeto in projetos_com_meta.iterrows():
        meta = projeto['Meta de Receita']
        receitas_projeto = receitas_f[receitas_f["Projeto"] == projeto["Código"]]
        total_receita_projeto = receitas_projeto["Valor Recebido"].sum()
        percentual = (total_receita_projeto / meta) * 100
        status_metas.append({"nome": projeto["Código"], "percentual": percentual})

    if not status_metas:
        st.info("Nenhum projeto com meta definida.")
    else:
        cols = st.columns(len(status_metas))
        for i, status in enumerate(status_metas):
            with cols[i]:
                css_class = "metric-box-green" if status['percentual'] >= 100 else "metric-box-red"
                st.markdown(f"""
                <div class="metric-box {css_class}">
                    <h4>{status['nome']}</h4>
                    <p>{status['percentual']:.1f}%</p>
                </div>
                """, unsafe_allow_html=True)

st.markdown("---")

# MELHORIA 4: Dados detalhados dentro de Expanders
st.header("📊 Dados Detalhados")
with st.expander("Clique para ver as Receitas Detalhadas"):
    st.dataframe(receitas_f.style.format({"Valor Recebido": lambda x: format_currency(x, "BRL", locale="pt_BR")}))

with st.expander("Clique para ver as Despesas Detalhadas"):
    st.dataframe(despesas_f.style.format({"Valor Pago": lambda x: format_currency(x, "BRL", locale="pt_BR")}))

# Ação na Sidebar (permanece igual)
st.sidebar.header("Ações")
if st.sidebar.button("Calcular e Salvar Impostos (Período Filtrado)"):
    if gc:
        with st.spinner("Calculando e salvando impostos..."):
            impostos_calculados = calcular_impostos(receitas_f, parametros_impostos)
            if not impostos_calculados.empty:
                escrever_dados(spreadsheet_id, "Calculo_Impostos", impostos_calculados, gc)
                st.sidebar.success("Impostos calculados e salvos!")
                # Mostra o resultado numa pequena notificação na sidebar
                with st.sidebar.expander("Ver Resultado do Cálculo", expanded=True):
                    st.dataframe(impostos_calculados)
            else:
                st.sidebar.warning("Nenhuma receita no período.")
    else:
        st.sidebar.error("Conexão falhou.")
