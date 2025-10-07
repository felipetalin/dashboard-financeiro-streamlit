# app.py (O novo arquivo na raiz)
import streamlit as st

st.set_page_config(
    page_title="Dashboard Financeiro Opyta",
    page_icon="📊",
    layout="wide"
)

st.title("Bem-vindo ao Dashboard Financeiro")
st.markdown("---")
st.image("https://media.licdn.com/dms/image/D4D0BAQG0Qd-o5L4B9w/company-logo_200_200/0/1699564294472/opyta_logo?e=1729728000&v=beta&t=k6hFj-2-l1zD1zP8tX8Y6w-J7n3-4w-Y7k7Z-J9o-A8")
st.markdown(
    """
    Este é o seu centro de controle financeiro.
    
    **👈 Use o menu na barra lateral** para navegar entre as diferentes seções.
    
    - **Visão Geral:** KPIs, gráficos de evolução e status das metas.
    """
)
