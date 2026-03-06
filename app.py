import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from thefuzz import process, fuzz
import re

# 1. Configuração da Página
st.set_page_config(page_title="Acompanhamento de Liberações", layout="wide")

# 2. Configuração do Motor Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"temperature": 0} 
    )
except Exception:
    st.error("Erro na API Key. Verifique os Secrets.")
    st.stop()

# 3. Carregamento da Lista Oficial
@st.cache_data
def carregar_lista_produtos():
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding=enc)
            return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        except:
            continue
    return []

lista_oficial = carregar_lista_produtos()

# 4. Estado da Sessão - Estrutura com todas as colunas de horários
if "df_validacao" not in st.session_state:
    st.session_state.df_validacao = pd.DataFrame(columns=[
        "Produto Lido", "Produto Oficial", "Lote", 
        "FQ_Inicio", "FQ_Fim",           # Horários das Análises (Aparecem primeiro no papel)
        "Pig_Inicio", "Pig_Fim",         # Horários da Pigmentação (Aparecem abaixo, mas são mais cedo)
        "Visc", "pH", "Dens", "Ajustes/Correções"
    ])

st.title("🚀 Acompanhamento de Liberações")
st.markdown("---")

uploaded_file = st.file_uploader("Suba a imagem do diário ou etiquetas", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=450, caption="Documento Detectado")
    
    if st.button("🔍 Processar e Validar Dados", type="primary"):
        with st.spinner("Analisando cronologia dos horários..."):
            try:
                # Prompt instruindo a separação por lógica de tempo (Relógio)
                prompt = """Analise a imagem e extraia os dados em formato CSV (separador ;).
                REGRAS DE HORÁRIOS:
                1. Capture todos os horários de cada lote.
                2. O horário mais cedo/antigo (ex: 07:30) deve ir para Pig_Inicio/Fim (mesmo que esteja escrito abaixo no papel).
                3. O horário posterior/mais tarde (ex: 09:00), que está junto aos dados de pH/Visc, deve ir para FQ_Inicio/Fim.
                
                REGRAS DE PRODUTO:
                - 'Massa Acrílica' -> 'MASSA ACRILICA PREMIUM XKG'
                - 'Massa Corrida' -> 'MASSA CORRIDA PREMIUM XKG'
                (Substitua X pelo peso identificado).
                
                ORDEM DAS COLUNAS: Produto;Lote;FQ_Inicio;FQ_Fim;Pig_Inicio;Pig_Fim;Viscosidade;pH;Densidade;Ajustes
                """

                response = model.generate_content([image, prompt])
                linhas = response.text.strip().split('\n')
                
                novos_itens = []
                for linha in linhas:
                    if ';' in linha and 'Produto;' not in linha:
                        partes = [p.strip() for p in linha.split(';')]
                        if len(partes) >= 10:
                            prod_lido = partes[0].upper()
                            
                            # Validação de Massas ou Lista 90%
                            if "MASSA ACRILICA" in prod_lido:
                                peso = re.search(r'(\d+)\s*KG', prod_lido)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA ACRILICA PREMIUM {peso_str}"
                            elif "MASSA CORRIDA" in prod_lido:
                                peso = re.search(r'(\d+)\s*KG', prod_lido)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA CORRIDA PREMIUM {peso_str}"
                            else:
                                if lista_oficial:
                                    match, score = process.extractOne(prod_lido, lista_oficial, scorer=fuzz.token_set_ratio)
                                    prod_validado = match if score >= 90 else "❌ NÃO ENCONTRADO"
                                else:
                                    prod_validado = "❌ LISTA NÃO CARREGADA"

                            # Preenchimento das 11 colunas
                            novos_itens.append([
                                prod_lido, prod_validado, partes[1], # Prod e Lote
                                partes[2], partes[3],               # FQ (Análises)
                                partes[4], partes[5],               # Pigmentação (Processo)
                                partes[6], partes[7], partes[8],    # Físico-químicos
                                partes[9]                            # Ajustes
                            ])

                if novos_itens:
                    df_temp = pd.DataFrame(novos_itens, columns=st.session_state.df_validacao.columns)
                    st.session_state.df_validacao = pd.concat([st.session_state.df_validacao, df_temp], ignore_index=True)
                    st.success("Dados organizados por cronologia.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# --- REVISÃO E EDIÇÃO ---
if not st.session_state.df_validacao.empty:
    st.divider()
    st.subheader("📋 Revisão Técnica")
    
    st.session_state.df_validacao = st.data_editor(
        st.session_state.df_validacao,
        num_rows="dynamic",
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    csv = st.session_state.df_validacao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    col1.download_button("📥 Baixar Planilha Final", csv, "liberacao_producao.csv", "text/csv")
    
    if col2.button("🗑️ Limpar Tudo"):
        st.session_state.df_validacao = pd.DataFrame(columns=st.session_state.df_validacao.columns)
        st.rerun()
