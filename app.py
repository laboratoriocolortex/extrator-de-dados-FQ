import streamlit as st
import google.generativeai as genai
from PIL import Image

# 1. Configuração Visual
st.set_page_config(page_title="Extrator Gemini 3 Flash", layout="centered")
st.title("🚀 Extrator Pro - Gemini 3 Flash Preview")
st.markdown("---")

# 2. Barra Lateral para API Key
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("Cole sua Gemini API Key:", type="password")
    st.info("Modelo: Gemini 2.0 Flash (Preview)")

# 3. Lógica Principal
if api_key:
    try:
        # Configura a API
        genai.configure(api_key=api_key)
        
        # DEFINIÇÃO DO MODELO (O nome técnico para o Gemini 3 Preview)
        # Esta é a linha que você estava procurando!
        model = genai.GenerativeModel(model_name='models/gemini-2.0-flash-exp')

        # Upload da Imagem
        uploaded_file = st.file_uploader("Selecione a foto do diário de produção", type=["jpg", "jpeg", "png"])

        if uploaded_file:
            img = Image.open(uploaded_file)
            st.image(img, caption="Imagem carregada", use_container_width=True)
            
            if st.button("📊 Extrair Dados"):
                with st.spinner("O Gemini 3 está analisando..."):
                    # Prompt focado em extração logística
                    prompt = """
                    Analise esta imagem de diário de produção de tintas e extraia:
                    - Família e Produto
                    - Lote
                    - Horários de pigmentação (para produtos coloridos, é o horário mais antigo) e horários de liberação físico-química (o horário mais tardio) (HH:MM)
                    - Viscosidade, pH e Densidade
                    
                    Apresente o resultado primeiro em uma Tabela organizada 
                    e depois em um bloco de código CSV usando ponto e vírgula (;).
                    """
                    
                    response = model.generate_content([prompt, img])
                    
                    st.success("Análise Concluída!")
                    st.markdown(response.text)

    except Exception as e:
        # Tratamento de erro amigável
        if "404" in str(e):
            st.error("Erro 404: O modelo 'gemini-2.0-flash-exp' não foi encontrado. Tente 'models/gemini-1.5-flash'.")
        elif "429" in str(e):
            st.error("Erro 429: Limite de uso atingido. Aguarde 60 segundos.")
        else:
            st.error(f"Ocorreu um erro: {e}")
else:
    st.warning("⚠️ Por favor, insira sua API Key na barra lateral para começar.")

st.markdown("---")
st.caption("Desenvolvido para automação de processos logísticos.")
