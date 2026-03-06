import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from thefuzz import process, fuzz
import re
import unicodedata # Biblioteca para manipular acentos

# 1. Função para Normalizar Texto (Remove acentos e espaços extras)
def normalizar_texto(texto):
    if not texto:
        return ""
    # Remove acentos (Ex: Estância -> Estancia)
    nfkd_form = unicodedata.normalize('NFKD', texto)
    texto_sem_acento = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Remove espaços extras e deixa em caixa alta
    return texto_sem_acento.upper().strip()

# 2. Configuração da Página
st.set_page_config(page_title="Acompanhamento de Liberações", layout="wide")

# 3. Configuração do Motor Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"temperature": 0} 
    )
except Exception:
    st.error("Erro na API Key. Verifique os Secrets.")
    st.stop()

# 4. Carregamento da Lista Oficial
@st.cache_data
def carregar_lista_produtos():
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding=enc)
            # Retorna uma lista de strings
            return df.iloc[:, 0].dropna().astype(str).tolist()
        except:
            continue
    return []

lista_bruta = carregar_lista_produtos()

# 5. Estado da Sessão
if "df_validacao" not in st.session_state:
    st.session_state.df_validacao = pd.DataFrame(columns=[
        "Produto Lido", "Produto Oficial", "Lote", 
        "FQ_Inicio", "FQ_Fim", 
        "Pig_Inicio", "Pig_Fim", 
        "Visc", "pH", "Dens", "Ajustes/Correções"
    ])

st.title("🚀 Acompanhamento de Liberações")
st.markdown("---")

uploaded_file = st.file_uploader("Suba a imagem do diário ou etiquetas", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=450, caption="Documento Detectado")
    
    if st.button("🔍 Processar e Validar Dados", type="primary"):
        with st.spinner("Normalizando nomes e validando produtos..."):
            try:
                prompt = """Analise a imagem e extraia os dados em formato CSV (separador ;).
                REGRAS DE HORÁRIOS:
                - Cronologia: Horário mais cedo (ex: 07:00) em Pig_Inicio/Fim. 
                - Horário mais tarde (ex: 09:00) em FQ_Inicio/Fim.
                - 'Massa Acrílica' -> 'MASSA ACRILICA PREMIUM XKG'
                - 'Massa Corrida' -> 'MASSA CORRIDA PREMIUM XKG'
                COLUNAS: Produto;Lote;FQ_Inicio;FQ_Fim;Pig_Inicio;Pig_Fim;Viscosidade;pH;Densidade;Ajustes
                """

                response = model.generate_content([image, prompt])
                linhas = response.text.strip().split('\n')
                
                novos_itens = []
                for linha in linhas:
                    if ';' in linha and 'Produto;' not in linha:
                        partes = [p.strip() for p in linha.split(';')]
                        if len(partes) >= 10:
                            prod_lido_original = partes[0].upper()
                            prod_lido_limpo = normalizar_texto(prod_lido_original)
                            
                            prod_validado = ""
                            
                            # Regra das Massas
                            if "MASSA ACRILICA" in prod_lido_limpo:
                                peso = re.search(r'(\d+)\s*KG', prod_lido_limpo)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA ACRILICA PREMIUM {peso_str}"
                            elif "MASSA CORRIDA" in prod_lido_limpo:
                                peso = re.search(r'(\d+)\s*KG', prod_lido_limpo)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA CORRIDA PREMIUM {peso_str}"
                            else:
                                # Validação 90% com Normalização
                                if lista_bruta:
                                    # Criamos um dicionário Temporário: {NomeSemAcento: NomeOriginalDaLista}
                                    lista_normalizada = {normalizar_texto(p): p for p in lista_bruta}
                                    
                                    # Procura o termo lido (sem acento) na lista (também sem acento)
                                    match, score = process.extractOne(
                                        prod_lido_limpo, 
                                        list(lista_normalizada.keys()), 
                                        scorer=fuzz.token_set_ratio
                                    )
                                    
                                    if score >= 90:
                                        # Retorna o nome original da lista (com acento se tiver)
                                        prod_validado = lista_normalizada[match]
                                    else:
                                        prod_validado = "❌ NÃO ENCONTRADO"

                            novos_itens.append([
                                prod_lido_original, prod_validado, partes[1], 
                                partes[2], partes[3], partes[4], partes[5],
                                partes[6], partes[7], partes[8], partes[9]
                            ])

                if novos_itens:
                    df_temp = pd.DataFrame(novos_itens, columns=st.session_state.df_validacao.columns)
                    st.session_state.df_validacao = pd.concat([st.session_state.df_validacao, df_temp], ignore_index=True)
                    st.success("Dados validados com sucesso!")
            except Exception as e:
                st.error(f"Erro: {e}")

# --- REVISÃO ---
if not st.session_state.df_validacao.empty:
    st.divider()
    st.subheader("📋 Revisão Técnica")
    st.data_editor(st.session_state.df_validacao, num_rows="dynamic", use_container_width=True)

    csv = st.session_state.df_validacao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("📥 Baixar Planilha Final", csv, "producao_validada.csv", "text/csv")
