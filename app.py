import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico Pro", layout="wide")

if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🎨 Extrator Industrial - Inteligência Visual Pro")
st.info("Utilizando Gemini 1.5 Pro: Máxima precisão em cores e manuscritos.")

# 2. Configuração da API Key
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key não encontrada nos Secrets.")
    st.stop()

# 3. Carregamento da Lista de Produtos (792 itens em CAPSLOCK)
@st.cache_data
def carregar_lista_produtos():
    codecs = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for c in codecs:
        try:
            df_prod = pd.read_csv('lista_produtos.csv', sep=None, engine='python', encoding=c)
            lista = df_prod.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
            return lista
        except: continue
    return []

lista_oficial = carregar_lista_produtos()
# DEFINIÇÃO DO MODELO PRO
model = genai.GenerativeModel('gemini-1.5-pro')

# --- INTERFACE ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto da etiqueta ou diário", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Imagem para análise", width=400)
        
        if st.button("Executar Extração Profissional"):
            with st.spinner("O Gemini Pro está analisando os detalhes..."):
                try:
                    prompt = f"""
                    Atue como um inspetor de qualidade de tintas. Extraia os dados em CAPSLOCK.
                    
                    REGRAS DE PRODUTO:
                    1. NOME COMPLETO: Extraia Produto + Cor + Litragem (Ex: COLORMAX PRETO 15L).
                    2. ETIQUETAS DOURADAS/BRONZE: Se a etiqueta for dourada/bronze, adicione "COR SOB ENCOMENDA" ao nome.
                    3. ETIQUETAS AMARELAS: São produtos de linha normal.
                    
                    REGRAS CRONOLÓGICAS:
                    - Compare os horários manuscritos. O intervalo que inicia mais cedo é PIGMENTAÇÃO. O posterior é ANÁLISE FQ.
                    
                    SAÍDA CSV (separado por ;):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    VALORES: Viscosidade (Inteiro), pH/Densidade (Vírgula). Data: {datetime.now().strftime('%d/%m/%Y')}
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto = response.text
                    
                    linhas = [l for l in texto.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas:
                        csv_io = io.StringIO("\n".join(linhas))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # Validação Fuzzy contra os 792 itens
                        if lista_oficial:
                            def validar(n):
                                m = process.extractOne(str(n).upper(), lista_oficial)
                                return m[0] if m and m[1] > 70 else str(n).upper()
                            df_temp['Produto'] = df_temp['Produto'].apply(validar)

                        # Padronização Final
                        df_temp['Lote'] = df_temp['Lote'].astype(str).str.upper()
                        df_temp['Status'] = df_temp['Status'].astype(str).str.upper()
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        st.success("Extração concluída com sucesso!")
                        st.table(df_temp)
                    else:
                        st.error("Não foi possível formatar os dados. Tente uma foto mais clara.")
                
                except Exception as e:
                    if "429" in str(e):
                        st.error("Limite de cota atingido. Aguarde 60 segundos para a próxima foto.")
                    else:
                        st.error(f"Erro: {e}")

with tab2:
    if not st.session_state.historico.empty:
        st.dataframe(st.session_state.historico, use_container_width=True)
        csv_ready = st.session_state.historico.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("📥 Baixar CSV para Excel", csv_ready, "producao.csv", "text/csv")
