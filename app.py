import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🚀 Acompanhamento do Laboratório")

# 2. Configuração da API Key
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key não encontrada.")
    st.stop()

# 3. Carregamento da Lista de Produtos
@st.cache_data
def carregar_lista_produtos():
    codecs = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for c in codecs:
        try:
            df_prod = pd.read_csv('lista_produtos.csv', sep=None, engine='python', encoding=c)
            lista = df_prod.iloc[:, 0].dropna().astype(str).str.strip().tolist()
            return lista
        except Exception:
            continue
    return []

lista_oficial = carregar_lista_produtos()
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário ou etiqueta", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Detectado", width=350)
        
        if st.button("Executar Extração e Validação"):
            with st.spinner("Validando litragens e produtos sob encomenda..."):
                try:
                    # PROMPT AJUSTADO PARA LITRAGEM E ETIQUETAS DOURADAS
                    prompt = f"""
                    Atue como um extrator de dados para fábrica de tintas.
                    
                    REGRAS DE IDENTIFICAÇÃO DE PRODUTO:
                    - ATENÇÃO À LITRAGEM: Identifique se o produto é 15L, 18L, 3,6L ou 25kg. Isso é CRUCIAL e deve constar no nome do produto.
                    - ETIQUETAS DOURADAS/AMARELAS: Se a etiqueta for dourada ou se houver menção a 'especial' ou 'encomenda', o produto é obrigatoriamente um item 'COR SOB ENCOMENDA'.
                    - Procure termos como 'Arenado sob encomenda' ou 'Colorflex sob encomenda' na imagem.
                    
                    REGRAS DE HORÁRIO:
                    - O intervalo que começou mais cedo é PIGMENTAÇÃO. O posterior é ANÁLISE FQ.
                    
                    SAÍDA CSV (separado por ;):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    REGRAS DE VALORES:
                    - Viscosidade: Apenas número inteiro.
                    - pH e Densidade: Vírgula decimal.
                    - Data: {datetime.now().strftime('%d/%m/%Y')}
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto_resposta = response.text
                    
                    linhas = [l for l in texto_resposta.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas:
                        csv_io = io.StringIO("\n".join(linhas))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # --- VALIDAÇÃO REFORÇADA (THEFUZZ) ---
                        if lista_oficial:
                            def encontrar_oficial(nome_lido):
                                # Aumentamos o limite para 75% para evitar trocas erradas de litragem
                                match = process.extractOne(str(nome_lido), lista_oficial)
                                if match and match[1] > 75: 
                                    return match[0]
                                return nome_lido
                            
                            df_temp['Produto'] = df_temp['Produto'].apply(encontrar_oficial)
                        
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        # Limpeza final
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        st.success("Extração concluída com validação de litragem!")
                        st.table(df_temp)
                    else:
                        st.error("Dados não detectados. Verifique se a etiqueta dourada está visível.")
                
                except Exception as e:
                    st.error(f"Erro: {e}")

with tab2:
    # (Código da aba de histórico permanece o mesmo)
    st.header("Histórico de Extrações")
    if not st.session_state.historico.empty:
        datas = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Escolha a data:", datas)
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        st.dataframe(df_filtrado, use_container_width=True)
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        st.download_button(label=f"📥 Baixar CSV de {data_sel}", data=csv_buffer.getvalue(), 
                           file_name=f"extração_{data_sel.replace('/', '_')}.csv", mime="text/csv")
    else:
        st.info("Histórico vazio.")

