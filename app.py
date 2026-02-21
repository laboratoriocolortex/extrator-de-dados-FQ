import streamlit as st
import google.generativeai as genai
from PIL import Image

st.set_page_config(page_title="Extrator Logístico", layout="wide")

st.title("🎨 Extrator de Diários de Produção")

with st.sidebar:
    api_key = st.text_input("Cole sua Gemini API Key:", type="password")

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # Tentando o caminho absoluto do modelo estável
        model_name = 'models/gemini-1.5-flash'
        model = genai.GenerativeModel('models/gemini-2.0-flash-exp-image-generation')

        uploaded_file = st.file_uploader("Suba a imagem do diário", type=["jpg", "jpeg", "png"])
        
        if uploaded_file and st.button("🚀 Processar Dados"):
            img = Image.open(uploaded_file)
            with st.spinner("Analisando..."):
                # O prompt de extração
                prompt = "Extraia os dados de produção da imagem em formato de tabela CSV (delimitador ;)."
                response = model.generate_content([prompt, img])
                st.markdown(response.text)
                
    except Exception as e:
        st.error(f"Erro detectado: {e}")
        
        # Bloco de ajuda para depuração
        st.info("Tentando listar modelos disponíveis para sua chave...")
        try:
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            st.write("Sua chave tem acesso aos seguintes modelos:", available_models)
        except:
            st.error("Não foi possível sequer listar os modelos. Verifique se sua API Key é válida.")
else:
    st.warning("Insira a API Key na barra lateral.")

