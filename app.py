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

st.title("🚀 Acompanhamento de Liberações")

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
    uploaded_file = st.file_uploader("Carregue a foto do diário", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Detectado", width=400)
        
        if st.button("Executar Extração"):
            with st.spinner("Analisando cores, litragens e etiquetas douradas..."):
                try:
                    # PROMPT REFINADO PARA CORES E ETIQUETAS DOURADAS
                    prompt = f"""
                    Aja como um especialista em controle de qualidade de tintas.
                    
                    REGRAS PARA NOME DO PRODUTO:
                    1. IDENTIFIQUE A COR E LITRAGEM: O nome deve incluir Produto + Cor (se houver) + Litragem/Peso. 
                       Ex: "Colormax Dunas de Pirambu 3,6L" ou "Textura Lisa 25KG".
                    2. ETIQUETAS DOURADAS/BRONZE: Se a etiqueta for de cor bronze ou dourada (ex: Textura Rústica da foto), o produto é obrigatoriamente "COR SOB ENCOMENDA". 
                       Ex: "Textura Rústica Branco Gelo Cor Sob Encomenda 25KG".
                    3. ETIQUETAS AMARELAS: São produtos padrão, não adicione "sob encomenda".
                    
                    REGRAS CRONOLÓGICAS:
                    - Analise os horários manuscritos ao lado da etiqueta. O intervalo de horário MENOR (que aconteceu antes) é PIGMENTAÇÃO. O horário MAIOR/POSTERIOR é ANÁLISE FQ.
                    
                    FORMATO CSV (separado por ;):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    REGRAS DE VALORES:
                    - Viscosidade: Retorne apenas números inteiros.
                    - pH e Densidade: Use vírgula.
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
                        
                        # --- VALIDAÇÃO COM LISTA MESTRE (Ajustada para Litragem e Cor) ---
                        if lista_oficial:
                            def encontrar_oficial(nome_lido):
                                # Usamos um limite de confiança de 70% para permitir a junção de Cor + Litragem
                                match = process.extractOne(str(nome_lido), lista_oficial)
                                if match and match[1] > 70:
                                    return match[0]
                                return nome_lido
                            
                            df_temp['Produto'] = df_temp['Produto'].apply(encontrar_oficial)
                        
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        # Limpeza final de formatos
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        st.success("Dados extraídos com sucesso!")
                        st.table(df_temp)
                    else:
                        st.error("Erro ao formatar os dados. Tente novamente.")
                
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

with tab2:
    # (O código do histórico permanece o mesmo)
    st.header("Histórico de Extrações")
    if not st.session_state.historico.empty:
        datas = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Selecione a data:", datas)
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        st.dataframe(df_filtrado, use_container_width=True)
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        st.download_button(label=f"📥 Baixar CSV de {data_sel}", data=csv_buffer.getvalue(), 
                           file_name=f"extracao_{data_sel.replace('/', '_')}.csv", mime="text/csv")

