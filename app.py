import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process

# Configuração da Página
st.set_page_config(page_title="Extrator Industrial Pro 3.1", layout="wide")

# Gerenciamento de Histórico
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

# Configuração do Modelo
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
    model = genai.GenerativeModel('gemini-1.5-pro') # 3.1 Pro Preview
except:
    st.error("Erro na API Key. Verifique os Secrets.")
    st.stop()

# Cache da Lista Mestra
@st.cache_data
def load_products():
    try:
        df = pd.read_csv('lista_produtos.csv', sep=None, engine='python', encoding='latin-1')
        return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
    except: return []

lista_produtos = load_products()

st.title("🚀 Extrator de Produção - Gemini 1.5 Pro Preview")

tab1, tab2 = st.tabs(["🚀 Extração", "📚 Histórico"])

with tab1:
    img_file = st.file_uploader("Suba a foto", type=['jpg', 'png', 'jpeg'])
    if img_file:
        img = Image.open(img_file)
        st.image(img, width=400)
        
        if st.button("Analisar com Alta Precisão"):
            with st.spinner("Decifrando manuscritos e cores..."):
                try:
                    # Prompt que vai para a "cabeça" da IA
                    sys_prompt = f"""
                    Extraia os dados da etiqueta e anotações:
                    - TUDO EM CAPSLOCK.
                    - Etiquetas Bronze/Douradas: Produto + ' COR SOB ENCOMENDA'.
                    - Horário menor: PIGMENTAÇÃO. Horário maior: ANÁLISE FQ.
                    - Saída CSV (separador ;): Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    Data: {datetime.now().strftime('%d/%m/%Y')}
                    """
                    
                    response = model.generate_content([sys_prompt, img])
                    res_text = response.text
                    
                    # Processamento da linha CSV
                    if ";" in res_text:
                        line = [l for l in res_text.split('\n') if ';' in l][0]
                        df_row = pd.read_csv(io.StringIO(line), sep=';', header=None, names=[
                            "Produto", "Lote", "IniPig", "FimPig", "IniFQ", "FimFQ", "Visc", "pH", "Dens", "Status"
                        ])

                        # Validação Fuzzy contra os 792 itens
                        if lista_produtos:
                            best_match = process.extractOne(str(df_row['Produto'][0]).upper(), lista_produtos)
                            if best_match[1] > 70: df_row['Produto'] = best_match[0]

                        # Formatação final
                        df_row['Visc'] = pd.to_numeric(df_row['Visc'], errors='coerce').fillna(0).astype(int)
                        df_row.insert(0, "Data", datetime.now().strftime('%d/%m/%Y'))
                        
                        st.session_state.historico = pd.concat([st.session_state.historico, df_row], ignore_index=True)
                        st.table(df_row)
                except Exception as e:
                    st.error(f"Erro: {e}. Aguarde 1 minuto se for erro de cota.")

with tab2:
    if not st.session_state.historico.empty:
        st.dataframe(st.session_state.historico)
        csv = st.session_state.historico.to_csv(index=False, sep=';', encoding='utf-8-sig')
        st.download_button("📥 Baixar CSV", csv, "producao.csv", "text/csv")
