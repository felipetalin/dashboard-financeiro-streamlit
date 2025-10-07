import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px
import datetime
from babel.numbers import format_currency
import uuid

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Dashboard Financeiro")

# --- CSS PARA OS CARDS DE STATUS DE META ---
# Este bloco de código injeta o estilo para os "mini boxes" que vamos criar.
st.markdown("""
<style>
.metric-box {
    border: 1px solid #ddd;
    border-radius: 10px;
    padding: 15px;
    margin: 5px 0;
    text-align: center;
    color: #333; /* Cor do texto padrão */
}
.metric-box-red {
    border-left: 10px solid #FF4B4B; /* Borda vermelha grossa */
    background-color: #f9e5e5; /* Fundo vermelho bem claro */
}
.metric-box-green {
    border-left: 10px solid #28a745; /* Borda verde grossa */
    background-color: #e9f5ec; /* Fundo verde bem claro */
}
.metric-box h4 {
    font-size: 16px;
    margin-bottom: 5px;
    color: #555; /* Cor do título do projeto */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis; /* Adiciona '...' se o nome do projeto for muito longo */
}
.metric-box p {
    font-size: 28px;
    font-weight: bold;
    margin: 0;
}
</style>
""", unsafe_allow_html=True)


# --- Funções de Conexão e Lógica de Negócio ---

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

@st.cache_resource
def conectar_sheets():
    """Conecta ao Google Sheets usando as credenciais do st.secrets."""
    try:
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Erro ao carregar as credenciais do Google Sheets: {e}")
        return None

@st.cache_data(ttl=600)
def carregar_dados(spreadsheet_id, _gc):
    """Carrega todas as planilhas necessárias do Google Sheets."""
    if _gc is None:
        return tuple(pd.DataFrame() for _ in range(5))

    try:
        sh = _gc.open_by_key(spreadsheet_id)
        projetos = pd.DataFrame(sh.worksheet("Projetos").get_all_records())
        receitas = pd.DataFrame(sh.worksheet("Receitas_Reais").get_all_records())
        despesas = pd.DataFrame(sh.worksheet("Despesas_Reais").get_all_records())
        custos = pd.DataFrame(sh.worksheet("Custos_Fixos_Variaveis").get_all_records())
        parametros_impostos = pd.DataFrame(sh.worksheet("Parametros_Impostos").get_all_records())

        for df, col in zip([receitas, despesas], ["Data Recebimento", "Data Pagamento"]):
            if col in df.columns and not df.empty:
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.date

        return projetos, receitas, despesas, custos, parametros_impostos
    except Exception as e:
        st.error(f"Erro ao ler os dados da planilha: {e}")
        return tuple(pd.DataFrame() for _ in range(5))

def escrever_dados(spreadsheet_id, worksheet_name, data, gc):
    """Escreve um DataFrame em uma planilha, limpando a aba antes."""
    try:
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(worksheet_name)
        worksheet.clear()
        worksheet.update([data.columns.values.tolist()] + data.values.tolist())
    except Exception as e:
        st.error(f"Não foi possível escrever na planilha '{worksheet_name}': {e}")

def calcular_impostos(receitas_df, parametros_impostos_df):
    """Calcula os impostos com base nas receitas e parâmetros."""
    if receitas_df.empty or parametros_impostos_df.empty:
        return pd.DataFrame()

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
    """Calcula os totais para as métricas."""
    total_receitas = pd.to_numeric(receitas["Valor Recebido"], errors='coerce').sum()
    total_despesas = pd.to_numeric(despesas["Valor Pago"], errors='coerce').sum()
    total_custos = pd.to_numeric(custos["Valor"], errors='coerce').sum()
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

# --- SIDEBAR (FILTROS E AÇÕES) ---
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
    codigos_projetos_cliente = projetos[projetos["Cliente"] == cliente_selecionado]["Código"].tolist()
    receitas_f = receitas_f[receitas_f["Projeto"].isin(codigos_projetos_cliente)]
    despesas_f = despesas_f[despesas_f["Projeto"].isin(codigos_projetos_cliente)]
if projeto_selecionado != "Todos":
    receitas_f = receitas_f[receitas_f["Projeto"] == projeto_selecionado]
    despesas_f = despesas_f[despesas_f["Projeto"] == projeto_selecionado]
if data_inicio and data_fim and data_inicio <= data_fim:
    receitas_f = receitas_f[receitas_f["Data Recebimento"].between(data_inicio, data_fim)]
    despesas_f = despesas_f[despesas_f["Data Pagamento"].between(data_inicio, data_fim)]

# --- LAYOUT PRINCIPAL ---
st.title("Dashboard Financeiro de Projetos")
total_receitas, total_despesas, total_custos, lucro_total, fluxo_caixa = calcular_totais(receitas_f, despesas_f, custos)
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Receita Total", format_currency(total_receitas, "BRL", locale="pt_BR"))
col2.metric("Despesa Total", format_currency(total_despesas, "BRL", locale="pt_BR"))
col3.metric("Custos Fixos/Var.", format_currency(total_custos, "BRL", locale="pt_BR"))
col4.metric("Lucro Total", format_currency(lucro_total, "BRL", locale="pt_BR"))
col5.metric("Fluxo de Caixa", format_currency(fluxo_caixa, "BRL", locale="pt_BR"))
st.markdown("---")

# Ação de Calcular Impostos
st.sidebar.header("Ações")
if st.sidebar.button("Calcular e Salvar Impostos (Período Filtrado)"):
    if gc:
        with st.spinner("Calculando e salvando impostos..."):
            impostos_calculados = calcular_impostos(receitas_f, parametros_impostos)
            if not impostos_calculados.empty:
                escrever_dados(spreadsheet_id, "Calculo_Impostos", impostos_calculados, gc)
                st.success("Impostos calculados e salvos!")
                st.subheader("Resultado do Cálculo de Impostos")
                st.dataframe(impostos_calculados.style.format(precision=2, thousands=".", decimal=","))
            else:
                st.warning("Nenhuma receita encontrada no período.")
    else:
        st.error("Não é possível salvar. Conexão falhou.")

# Visualizações
st.header("📊 Análise Detalhada")
tab1, tab2, tab3 = st.tabs(["Evolução no Tempo", "Receitas Detalhadas", "Despesas Detalhadas"])
with tab1:
    df_tempo_receita = receitas_f.rename(columns={"Data Recebimento": "Data", "Valor Recebido": "Valor"}).assign(Tipo="Receita")
    df_tempo_despesa = despesas_f.rename(columns={"Data Pagamento": "Data", "Valor Pago": "Valor"}).assign(Tipo="Despesa")
    df_tempo = pd.concat([df_tempo_receita, df_tempo_despesa])
    if not df_tempo.empty:
        fig = px.area(df_tempo, x="Data", y="Valor", color="Tipo", title="Evolução de Receitas e Despesas",
                      labels={"Valor": "Valor (R$)", "Data": "Data"}, color_discrete_map={"Receita": "#87A96B", "Despesa": "#FF4B4B"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados no período para exibir o gráfico.")
with tab2:
    st.dataframe(receitas_f.style.format({"Valor Recebido": lambda x: format_currency(x, "BRL", locale="pt_BR")}))
with tab3:
    st.dataframe(despesas_f.style.format({"Valor Pago": lambda x: format_currency(x, "BRL", locale="pt_BR")}))
st.markdown("---")

col_custos, col_alertas = st.columns(2)
with col_custos:
    st.header("💡 Custos por Categoria")
    if not custos.empty:
        custos_cat = custos.groupby("Categoria")["Valor"].sum().reset_index()
        fig_pie = px.pie(custos_cat, values="Valor", names="Categoria", title="Distribuição dos Custos", hole=0.3)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Não há dados de custos para exibir.")

# --- SEÇÃO DE ALERTAS ATUALIZADA ---
# Este bloco substitui a lista de alertas antiga por cards horizontais.
with col_alertas:
    st.header("🚨 Status das Metas")

    if 'Meta de Receita' not in projetos.columns:
        st.warning("Coluna 'Meta de Receita' não encontrada na planilha 'Projetos'.")
    else:
        # 1. Filtra projetos que têm uma meta numérica válida
        projetos_com_meta = projetos[pd.to_numeric(projetos['Meta de Receita'], errors='coerce').notna()].copy()
        projetos_com_meta['Meta de Receita'] = pd.to_numeric(projetos_com_meta['Meta de Receita'])

        # 2. Prepara os dados para cada card
        status_metas = []
        for _, projeto in projetos_com_meta.iterrows():
            meta = projeto['Meta de Receita']
            if meta > 0: # Evita divisão por zero
                receitas_projeto = receitas_f[receitas_f["Projeto"] == projeto["Código"]]
                total_receita_projeto = pd.to_numeric(receitas_projeto["Valor Recebido"], errors='coerce').sum()
                percentual = (total_receita_projeto / meta) * 100
                
                status_metas.append({
                    "nome": projeto["Código"],
                    "percentual": percentual,
                    "cor": "green" if percentual >= 100 else "red"
                })

        # 3. Exibe os cards
        if not status_metas:
            st.info("Nenhum projeto com meta definida para o período filtrado.")
        else:
            # Cria o número exato de colunas necessárias
            cols = st.columns(len(status_metas))
            
            for i, status in enumerate(status_metas):
                with cols[i]:
                    # Define a classe CSS com base na cor
                    css_class = "metric-box-green" if status['cor'] == 'green' else "metric-box-red"
                    
                    # Usa st.markdown para criar o "mini box" com HTML e CSS
                    st.markdown(f"""
                    <div class="metric-box {css_class}">
                        <h4>{status['nome']}</h4>
                        <p>{status['percentual']:.1f}%</p>
                    </div>
                    """, unsafe_allow_html=True)
