import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Extrator Logístico")

# Tenta pegar a chave dos Secrets
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except:
    st.error("Configure a GEMINI_CHAVE nos Secrets do Streamlit.")
    st.stop()

# Tentando o nome mais simples possível
model = genai.GenerativeModel('gemini-1.5-flash')

st.title("🚀 Extrator de Produção")

uploaded_file = st.file_uploader("Suba a foto", type=["jpg", "png", "jpeg"])

if uploaded_file and st.button("Processar"):
    img = Image.open(uploaded_file)
    try:
        # Teste simples de resposta
        response = model.generate_content(["O que você vê nesta imagem?", img])
        st.markdown(response.text)
    except Exception as e:
        st.error(f"Erro detalhado: {e}")
        # Se ainda der 404, vamos listar o que a API enxerga
        st.write("Modelos disponíveis na sua região:")
        models = [m.name for m in genai.list_models()]
        st.write(models)
