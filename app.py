import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process # Biblioteca para busca inteligente

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🚀 Extrator Industrial (Alta Precisão)")

# 2. Configuração da API Key
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key não encontrada.")
    st.stop()

# 3. Carregamento da Lista de Produtos (792 itens)
@st.cache_data
def carregar_lista_produtos():
    try:
        df_prod = pd.read_csv('lista_produtos.csv', sep=None, engine='python')
        return df_prod.iloc[:, 0].dropna().astype(str).str.strip().tolist()
    except Exception as e:
        st.error(f"Erro ao ler lista: {e}")
        return []

lista_oficial = carregar_lista_produtos()
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Atual", width=350)
        
        if st.button("Executar Extração"):
            with st.spinner("Extraindo e validando contra 792 produtos..."):
                try:
                    # PROMPT FOCADO EM DADOS BRUTOS (O Python fará o resto)
                    prompt = f"""
                    Extraia os dados deste diário de produção.
                    
                    REGRAS CRONOLÓGICAS:
                    - Compare os horários: O intervalo MENOR é sempre PIGMENTAÇÃO. O intervalo MAIOR/POSTERIOR é sempre ANÁLISE FQ.
                    
                    FORMATO DE SAÍDA (CSV):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    REGRAS DE VALORES:
                    - Viscosidade: Apenas número inteiro.
                    - pH e Densidade: Use vírgula.
                    - Se não houver Pigmentação, use '---'.
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto_resposta = response.text
                    
                    # Filtra a linha do CSV
                    linhas = [l for l in texto_resposta.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas:
                        csv_io = io.StringIO("\n".join(linhas))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # --- VALIDAÇÃO INTELIGENTE (FUZZY MATCHING) ---
                        if lista_oficial:
                            def encontrar_oficial(nome_lido):
                                # Busca o nome mais parecido na lista de 792 itens
                                melhor_match, score = process.extractOne(str(nome_lido), lista_oficial)
                                return melhor_match if score > 60 else nome_lido
                            
                            df_temp['Produto'] = df_temp['Produto'].apply(encontrar_oficial)
                        
                        # Adiciona a Data
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        # Limpeza Final
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        st.success("Dados processados e validados!")
                        st.table(df_temp)
                    else:
                        st.error("Falha na leitura. Tente uma foto mais nítida.")
                
                except Exception as e:
                    st.error(f"Erro: {e}")

with tab2:
    # (O código da Aba 2 permanece o mesmo da versão anterior)
    st.header("Histórico de Extrações")
    if not st.session_state.historico.empty:
        datas = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Filtrar por data:", datas)
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        st.dataframe(df_filtrado, use_container_width=True)
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        st.download_button(label=f"📥 Baixar CSV de {data_sel}", data=csv_buffer.getvalue(), 
                           file_name=f"producao_{data_sel.replace('/', '_')}.csv", mime="text/csv")

