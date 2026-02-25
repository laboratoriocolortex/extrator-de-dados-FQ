import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

# Inicializar o histórico na sessão se não existir
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🎨 Extrator Pro com Histórico")

# 2. Configuração da API Key
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key não encontrada nos Secrets.")
    st.stop()

# 3. Carregamento da Lista de Produtos
@st.cache_data
def carregar_lista_produtos():
    try:
        df_prod = pd.read_csv('lista_produtos.csv', sep=None, engine='python')
        return ", ".join(df_prod.iloc[:, 0].astype(str).tolist())
    except:
        return "Lista não carregada."

produtos_referencia = carregar_lista_produtos()
model = genai.GenerativeModel('gemini-1.5-flash')

# --- CRIAÇÃO DAS ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Atual", width=350)
        
        if st.button("Executar Extração"):
            with st.spinner("Analisando..."):
                try:
                    prompt = f"""
                    VOCÊ É UM ESPECIALISTA EM OCR INDUSTRIAL. 
                    LISTA OFICIAL: [{produtos_referencia}]
                    Extraia os dados em formato CSV (separado por ;) com as seguintes colunas EXATAS:
                    Data Extração;Produto/Família;Lote;Início Pigmentação;Fim Pigmentação;Início Análises FQ;Fim Análises FQ;Viscosidade;pH;Densidade;Status
                    
                    REGRAS:
                    - Na 'Data Extração' use: {datetime.now().strftime('%d/%m/%Y')}
                    - pH e Densidade com VÍRGULA.
                    - Viscosidade APENAS NÚMERO.
                    - Use o nome oficial da lista se encontrar correspondência.
                    - Retorne APENAS as linhas de dados, sem cabeçalho repetido.
                    """
                    
                    response = model.generate_content([prompt, image])
                    dados_conferência = response.text
                    
                    # Processar a resposta para o DataFrame do Histórico
                    # Criamos um DataFrame temporário com a nova extração
                    df_temp = pd.read_csv(io.StringIO(dados_conferência), sep=';', header=None, names=[
                        "Data Extração", "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                    ])
                    
                    # Adicionar ao histórico na sessão
                    st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                    
                    st.success("Dados extraídos e adicionados ao histórico!")
                    st.table(df_temp)
                    
                except Exception as e:
                    st.error(f"Erro: {e}")

with tab2:
    st.header("Histórico de Extrações")
    
    if not st.session_state.historico.empty:
        # Filtro de Data
        datas_disponiveis = st.session_state.historico['Data Extração'].unique()
        data_selecionada = st.selectbox("Filtrar por data:", datas_disponiveis)
        
        # Filtrar o DataFrame
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_selecionada]
        
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Botão de Download para a data específica
        csv_filtrado = df_filtrado.to_csv(index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Baixar CSV de {data_selecionada}",
            data=csv_filtrado,
            file_name=f"producao_{data_selecionada.replace('/', '_')}.csv",
            mime="text/csv",
        )
        
        if st.button("Limpar todo o histórico"):
            st.session_state.historico = pd.DataFrame()
            st.rerun()
    else:
        st.info("Nenhuma extração realizada nesta sessão ainda.")

st.markdown("---")
