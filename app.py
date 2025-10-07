# app.py
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

st.set_page_config(layout="wide")
st.title("Teste de Conexão com Google Sheets (Feito no GitHub!)")

# Escopos de permissão
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Função de conexão
@st.cache_resource
def conectar_sheets():
    try:
        creds = Credentials.from_service_account_info(st.secrets["google_credentials"], scopes=SCOPES)
        gc = gspread.service_account(credentials=creds)
        return gc
    except Exception as e:
        st.error(f"Falha ao conectar: {e}")
        st.warning("Verifique se você colou os segredos corretamente no Streamlit Cloud.")
        return None

gc = conectar_sheets()

if gc:
    st.success("Conexão com a API do Google bem-sucedida! ✅")
    try:
        SPREADSHEET_ID = "1Ut25HiLC17oq7X6ThTKqMPHnPUoBjXsIRaVVFJDa7r4"
        sh = gc.open_by_key(SPREADSHEET_ID)
        worksheet = sh.worksheet("Projetos")
        st.success("Planilha e aba 'Projetos' abertas com sucesso! ✅")
        
        dados = pd.DataFrame(worksheet.get_all_records())
        st.subheader("Dados lidos da sua planilha:")
        st.dataframe(dados)
    except Exception as e:
        st.error(f"Erro ao ler os dados da planilha: {e}")
else:
    st.error("A conexão inicial com a API falhou. Os segredos não foram carregados.")
