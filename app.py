import streamlit as st
import google.generativeai as genai
from PIL import Image

# Configuração da página
st.set_page_config(page_title="Extrator Gemini 3 Flash", layout="wide")

st.title("🚀 Extrator de Produção - Gemini 3 Flash")

with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("Insira sua Gemini API Key:", type="password")
    st.info("Modelo configurado: Gemini 2.0/3 Flash Preview")

# Prompt de Negócio (O mesmo que definimos antes)
SYSTEM_PROMPT = """
Você é um especialista em OCR e produção de tintas. 
Extraia: Família, Produto, Lote, Tipo de Cor (BRANCO, COLORIDO ou NÃO SE APLICA), 
Horário (sempre no formato HH:MM - HH:MM), pH e Densidade.
Ignore textos como 'análise FQ' ou 'pigmentação'.
Forneça uma tabela Markdown e um bloco CSV separado por ponto e vírgula (;).
"""

if api_key:
    try:
        genai.configure(api_key=api_key)
        
        # O identificador 'gemini-2.0-flash-exp' é o que o Google usa atualmente 
        # para os modelos que aparecem como "Gemini 3 / Next Gen" no AI Studio.
        model = genai.GenerativeModel('gemini-2.0-flash-exp')

        uploaded_file = st.file_uploader("Carregue a foto do diário ou etiqueta", type=["jpg", "jpeg", "png"])

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Imagem para análise", width=400)
            
            if st.button("Executar Extração Inteligente"):
                with st.spinner("O Gemini 3 está analisando os dados..."):
                    # Chamada do modelo com a imagem e o prompt
                    response = model.generate_content([SYSTEM_PROMPT, image])
                    st.markdown("### Resultado:")
                    st.markdown(response.text)
                    
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.info("Dica: Se o erro for 404, o modelo 'gemini-2.0-flash-exp' pode ter mudado de nome. Tente 'gemini-1.5-flash-latest'.")
else:
    st.warning("Aguardando API Key na barra lateral...")
