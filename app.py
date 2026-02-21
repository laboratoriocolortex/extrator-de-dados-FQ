import streamlit as st
import google.generativeai as genai
from PIL import Image
import time

st.set_page_config(page_title="Extrator Pro", layout="wide")

# Função para conectar ao modelo apenas uma vez (Economiza Quota)
@st.cache_resource
def configurar_modelo(api_key, model_name):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

st.title("🎨 Extrator de Produção (Gemini 2.0/3)")

with st.sidebar:
    api_key = st.text_input("Sua API Key:", type="password")
    # Mantendo o modelo que você preferiu
    modelo_selecionado = 'models/gemini-2.0-flash-exp' 

if api_key:
    try:
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
        
        uploaded_file = st.file_uploader("Foto do Diário", type=["jpg", "png", "jpeg"])
        
        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, width=300)
            
            if st.button("🚀 Processar Agora"):
                with st.spinner("Analisando... Por favor, aguarde."):
                    # O seu prompt mestre
                    prompt = "Extraia os dados de produção desta imagem. Retorne em formato de tabela e depois em bloco de código CSV (ponto e vírgula)."
                    
                    try:
                        response = model.generate_content([prompt, img])
                        st.success("Concluído!")
                        st.markdown(response.text)
                    except Exception as e:
                        if "429" in str(e):
                            st.error("Limite de velocidade atingido! Aguarde 60 segundos antes de tentar a próxima foto.")
                        else:
                            st.error(f"Erro: {e}")
                            
    except Exception as e:
        st.error(f"Erro na configuração: {e}")
else:
    st.info("Aguardando API Key...")

