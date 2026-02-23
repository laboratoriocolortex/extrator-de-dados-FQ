import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd # Biblioteca para facilitar a criação do arquivo

st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

st.title("🎨 Extrator de Produção e Qualidade")
st.markdown("---")

try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key 'GEMINI_CHAVE' não encontrada nos Secrets.")
    st.stop()

model = genai.GenerativeModel('gemini-3-flash-preview')

PROMPT_SISTEMA = """
VOCÊ É UM ANALISTA DE CONTROLO DE QUALIDADE INDUSTRIAL ESPECIALISTA EM OCR.
Extraia os dados do diário de produção seguindo estas regras:

ORDEM DAS COLUNAS:
1. Produto / Família; 2. Lote; 3. Horário de Pigmentação (Início - Fim); 4. Horário de Análises FQ (Início - Fim); 5. Viscosidade (adicione "KU"); 6. pH (use vírgula); 7. Densidade (use vírgula); 8. Status.

REGRAS:
- Substitua PONTO por VÍRGULA em todos os valores numéricos de pH e Densidade.
- Use ponto e vírgula (;) como único separador de colunas no bloco CSV.
- Se não houver dados, use "---".

SAÍDA:
1. Tabela Markdown.
2. Bloco de código CSV completo.
"""

uploaded_file = st.file_uploader("Carregue a foto do diário", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Documento Carregado", width=400)
    
    if st.button("🚀 Executar Extração"):
        with st.spinner("O Gemini está processando..."):
            try:
                response = model.generate_content([PROMPT_SISTEMA, image])
                resultado = response.text
                
                st.success("Extração concluída!")
                st.markdown(resultado)

                # Lógica para criar o botão de download
                # Tentamos isolar apenas a parte CSV da resposta
                if "csv" in resultado:
                    csv_content = resultado.split("csv")[1].split("```")[0].strip()
                elif ";" in resultado:
                    # Caso o modelo não coloque os backticks mas use ponto e vírgula
                    lines = [l for l in resultado.split('\n') if ';' in l]
                    csv_content = "\n".join(lines)
                else:
                    csv_content = resultado

                st.download_button(
                    label="📥 Baixar Dados para Excel (CSV)",
                    data=csv_content,
                    file_name="extração_produção.csv",
                    mime="text/csv",
                )
                
            except Exception as e:
                st.error(f"Erro: {e}")

st.markdown("---")
