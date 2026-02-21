import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
import io

# Configurações da página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

st.title("🎨 Extrator de Diários de Produção")
st.markdown("Transforme fotos de etiquetas e cadernos em dados estruturados instantaneamente.")

# Barra lateral para configuração
with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("Insira sua Gemini API Key:", type="password")
    st.info("Obtenha sua chave em: https://aistudio.google.com/app/apikey")

# O Prompt mestre que definimos
SYSTEM_PROMPT = """
Você é um especialista em OCR e estruturação de dados para logística química. 
Sua função é processar imagens de etiquetas e diários de produção.

REGRAS DE CLASSIFICAÇÃO:
1. FAMÍLIA: Identifique pelo nome (Massa, Esmalte, Textura, Selador, Piso, Latéx, Pasta, Efeito).
2. TIPO DE COR:
   - NÃO SE APLICA: Massas, Seladores, Fundos, Texturas Rústicas, Pastas Base.
   - COLORIDO: Cores nomes (Azul, etc) ou "BRANCO GELO".
   - BRANCO: Branco Total, Neve, Base ou apenas Branco (exceto Gelo).

DIRETRIZES DE LIMPEZA:
- LOTE: Padrão XXXXX/XXXX.
- HORÁRIOS: Sempre que houver dois horários (ex: 21:30 e 21:33), concatene como "HH:MM - HH:MM". Ignore textos como "análise FQ".
- TÉCNICO: O primeiro valor numérico manual é pH, o segundo é Densidade.

SAÍDA: Forneça EXCLUSIVAMENTE uma tabela em Markdown e o bloco de código CSV separado por ponto e vírgula (;).
"""

# Interface de Upload
col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Arraste a foto do diário aqui", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Imagem Carregada", use_container_width=True)

with col2:
    if uploaded_file and api_key:
        if st.button("🚀 Processar e Gerar Planilha"):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                with st.spinner("Analisando imagem..."):
                    response = model.generate_content([SYSTEM_PROMPT, image])
                    
                    # Exibe o resultado de texto
                    st.markdown("### Resultado da Extração")
                    st.markdown(response.text)
                    
                    # Lógica simples para extrair o CSV da resposta e permitir download
                    if "Familia;" in response.text:
                        csv_data = response.text.split("csv")[-1].split("")[0].strip()
                        st.download_button(
                            label="📥 Baixar Planilha (CSV)",
                            data=csv_data,
                            file_name="producao_extraida.csv",
                            mime="text/csv"
                        )
            except Exception as e:
                st.error(f"Erro ao processar: {e}")
    elif not api_key:
        st.warning("Por favor, insira sua API Key na barra lateral para começar.")