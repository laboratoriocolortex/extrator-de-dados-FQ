import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🎨 Extrator Pro - Inteligência Cronológica")

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
        return df_prod.iloc[:, 0].astype(str).tolist()
    except:
        return []

lista_oficial = carregar_lista_produtos()
produtos_texto = ", ".join(lista_oficial)
model = genai.GenerativeModel('gemini-3-flash-preview')

# --- ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Atual", width=350)
        
        if st.button("Executar Extração"):
            with st.spinner("Analisando cronologia e validando dados..."):
                try:
                    # PROMPT COM A LÓGICA DE HORÁRIOS SOLICITADA
                    prompt = f"""
                    VOCÊ É UM ANALISTA DE QUALIDADE INDUSTRIAL.
                    
                    LISTA DE PRODUTOS OFICIAIS:
                    [{produtos_texto}]
                    
                    SUA MISSÃO E REGRAS OBRIGATÓRIAS:
                    1. NOME DO PRODUTO: Use EXATAMENTE o nome da LISTA OFICIAL acima que for mais parecido com o da imagem.
                    
                    2. LÓGICA CRONOLÓGICA DE HORÁRIOS (MUITO IMPORTANTE):
                       - Identifique todos os intervalos de tempo para o lote.
                       - O horário que ocorreu MAIS CEDO (o menor) deve ser colocado nas colunas de PIGMENTAÇÃO.
                       - O horário que ocorreu MAIS TARDE (o maior) deve ser colocado nas colunas de ANÁLISES FQ.
                       - Exemplo: Se ler "10:39-10:43" e "08:30-10:38", a Pigmentação é 08:30-10:38 e o FQ é 10:39-10:43.
                    
                    3. FORMATAÇÃO DE DADOS:
                       - VISCOSIDADE: Forneça APENAS o número inteiro. Remova qualquer ".00" ou decimal.
                       - pH e DENSIDADE: Use VÍRGULA como separador decimal (ex: 8,2).
                       - DATA: {datetime.now().strftime('%d/%m/%Y')}
                    
                    SAÍDA EM CSV (SEPARADO POR ;):
                    Data Extração;Produto/Família;Lote;Início Pigmentação;Fim Pigmentação;Início Análises FQ;Fim Análises FQ;Viscosidade;pH;Densidade;Status
                    """
                    
                    response = model.generate_content([prompt, image])
                    dados_brutos = response.text
                    
                    # Filtra apenas a linha que contém os dados reais
                    linhas_csv = [l for l in dados_brutos.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas_csv:
                        csv_io = io.StringIO("\n".join(linhas_csv))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Data Extração", "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # Limpeza forçada de tipos de dados no Python
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        
                        # Adicionar ao histórico
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        
                        st.success("Dados extraídos com sucesso respeitando a cronologia!")
                        st.table(df_temp)
                    else:
                        st.error("Não foi possível formatar os dados. Tente tirar uma foto mais clara.")
                    
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

with tab2:
    st.header("Histórico de Extrações")
    if not st.session_state.historico.empty:
        datas = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Filtrar por data:", datas)
        
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        st.dataframe(df_filtrado, use_container_width=True)
        
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Baixar CSV de {data_sel}",
            data=csv_buffer.getvalue(),
            file_name=f"producao_{data_sel.replace('/', '_')}.csv",
            mime="text/csv",
        )
    else:
        st.info("Nenhuma extração registrada.")

st.markdown("---")
