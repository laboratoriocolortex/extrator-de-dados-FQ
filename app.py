import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process # Ajustado para a biblioteca thefuzz

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas", layout="wide")

# Inicializa o histórico na sessão do navegador
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🚀 Acompanhamento - Laboratório")

# 2. Configuração da API Key via Secrets
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key 'GEMINI_CHAVE' não encontrada nos Secrets do Streamlit.")
    st.stop()

# 3. Carregamento da Lista de Produtos com Tratamento de Codificação
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

# --- INTERFACE POR ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário de produção", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Documento Detectado", width=350)
        
        if st.button("Executar Extração e Validação"):
            with st.spinner("Analisando imagem e validando contra lista oficial..."):
                try:
                    # Prompt com lógica cronológica e formatação rigorosa
                    prompt = f"""
                    Atue como um extrator de dados OCR para uma fábrica de tintas.
                    
                    REGRAS DE HORÁRIO:
                    - Identifique os intervalos de tempo.
                    - O intervalo que começou MAIS CEDO é a PIGMENTAÇÃO.
                    - O intervalo que começou MAIS TARDE (posterior) é a ANÁLISE FQ.
                    
                    FORMATO DE SAÍDA CSV (USE ; COMO SEPARADOR):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    REGRAS DE VALORES:
                    - Viscosidade: Retorne apenas o número inteiro (sem decimais).
                    - pH e Densidade: Use vírgula como separador decimal.
                    - Data atual: {datetime.now().strftime('%d/%m/%Y')}
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto_resposta = response.text
                    
                    # Filtra apenas a linha de dados CSV
                    linhas = [l for l in texto_resposta.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas:
                        csv_io = io.StringIO("\n".join(linhas))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # --- VALIDAÇÃO COM THEFUZZ (792 PRODUTOS) ---
                        if lista_oficial:
                            def encontrar_oficial(nome_lido):
                                # Busca o termo mais próximo na sua planilha
                                match = process.extractOne(str(nome_lido), lista_oficial)
                                # Se a similaridade for maior que 60%, substitui pelo oficial
                                if match and match[1] > 60:
                                    return match[0]
                                return nome_lido
                            
                            df_temp['Produto'] = df_temp['Produto'].apply(encontrar_oficial)
                        
                        # Inserção da Data e Limpeza de Tipos
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        # Forçar Viscosidade como Inteiro e decimais como Vírgula
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        
                        # Atualizar histórico
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        
                        st.success("Dados processados e validados!")
                        st.table(df_temp)
                    else:
                        st.error("Não foi possível formatar os dados. Verifique a nitidez da foto.")
                
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

with tab2:
    st.header("Histórico de Extrações")
    
    if not st.session_state.historico.empty:
        datas_disp = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Escolha a data para download:", datas_disp)
        
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Botão de Download
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Baixar CSV de {data_sel}",
            data=csv_buffer.getvalue(),
            file_name=f"extração_{data_sel.replace('/', '_')}.csv",
            mime="text/csv"
        )
        
        if st.button("Limpar Histórico"):
            st.session_state.historico = pd.DataFrame()
            st.rerun()
    else:
        st.info("Nenhuma extração no histórico.")

st.markdown("---")
