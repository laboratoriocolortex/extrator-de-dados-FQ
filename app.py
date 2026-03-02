import streamlit as st
import google.generativeai as genai
from PIL import Image
import pandas as pd
from datetime import datetime
import io
from thefuzz import process

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Logístico de Tintas Pro", layout="wide")

# Inicializa o histórico na sessão do navegador
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🚀 Acompanhamento de Liberações")
st.markdown("---")

# 2. Configuração da API Key via Secrets
try:
    api_key = st.secrets["GEMINI_CHAVE"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("Erro: API Key 'GEMINI_CHAVE' não encontrada nos Secrets do Streamlit.")
    st.stop()

# 3. Carregamento da Lista de Produtos (Validação de UTF-8 e CAPSLOCK)
@st.cache_data
def carregar_lista_produtos():
    # Lista de codificações comuns para arquivos salvos pelo Excel no Windows
    codecs = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
    for c in codecs:
        try:
            df_prod = pd.read_csv('lista_produtos.csv', sep=None, engine='python', encoding=c)
            # Pega a primeira coluna, remove vazios, espaços e converte para MAIÚSCULO
            lista = df_prod.iloc[:, 0].dropna().astype(str).str.strip().str.upper().tolist()
            return lista
        except Exception:
            continue
    return []

lista_oficial = carregar_lista_produtos()
model = genai.GenerativeModel('gemini-1.5-flash')

# --- INTERFACE POR ABAS ---
tab1, tab2 = st.tabs(["🚀 Nova Extração", "📚 Histórico Acumulado"])

with tab1:
    uploaded_file = st.file_uploader("Carregue a foto do diário ou etiqueta", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        # Mostra a imagem em tamanho médio para conferência
        st.image(image, caption="Documento Detectado", width=400)
        
        if st.button("Executar Extração e Validação em CAPSLOCK"):
            with st.spinner("Analisando imagem, cronologia e padronizando em MAIÚSCULAS..."):
                try:
                    # PROMPT REFINADO: Validação Rígida, Lógica de Horários e Douradas
                    prompt = f"""
                    Aja como um especialista em controle de qualidadeOCR de uma fábrica de tintas.
                    Sua saída deve ser stritamente em CAPSLOCK (MAIÚSCULAS).
                    
                    REGRAS PARA NOME DO PRODUTO:
                    1. IDENTIFIQUE A COR E LITRAGEM: O nome deve incluir Produto + Cor (se houver) + Litragem/Peso (Ex: Colormax Preto 15L).
                    2. ETIQUETAS DOURADAS/BRONZE: Se a etiqueta for de cor bronze ou dourada, o produto é "COR SOB ENCOMENDA".
                    3. ETIQUETAS AMARELAS: São produtos padrão, não adicione "sob encomenda".
                    
                    REGRAS DE HORÁRIO (CONFERÊNCIA CRONOLÓGICA):
                    - Você verá manuscritos ao lado da etiqueta com horários (ex: 08:30-10:00 e 10:10-10:30).
                    - O intervalo que começou mais cedo é a PIGMENTAÇÃO.
                    - O intervalo que começou mais tarde (posterior) é a ANÁLISE FQ.
                    
                    FORMATO DE SAÍDA CSV (USE ; COMO SEPARADOR E TUDO EM CAPSLOCK):
                    Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
                    
                    REGRAS DE VALORES:
                    - Viscosidade: Apenas o número inteiro (Ex: se ler 92.00, escreva 92).
                    - pH e Densidade: Use VÍRGULA decimal.
                    - Data atual: {datetime.now().strftime('%d/%m/%Y')}
                    """
                    
                    response = model.generate_content([prompt, image])
                    texto_resposta = response.text
                    
                    # Filtra apenas a linha que contém os dados CSV reais
                    linhas = [l for l in texto_resposta.split('\n') if ';' in l and 'Produto' not in l]
                    
                    if linhas:
                        csv_io = io.StringIO("\n".join(linhas))
                        df_temp = pd.read_csv(csv_io, sep=';', header=None, names=[
                            "Produto", "Lote", "Ini Pig", "Fim Pig", "Ini FQ", "Fim FQ", "Visc", "pH", "Dens", "Status"
                        ])
                        
                        # --- VALIDAÇÃO INTELIGENTE COM A LISTA DE 792 PRODUTOS ---
                        if lista_oficial:
                            def encontrar_oficial(nome_lido):
                                # Converte o nome lido para CAPSLOCK antes de comparar
                                match = process.extractOne(str(nome_lido).upper(), lista_oficial)
                                # Se a similaridade for maior que 70%, substitui pelo oficial
                                if match and match[1] > 70:
                                    return match[0]
                                return str(nome_lido).upper()
                            
                            df_temp['Produto'] = df_temp['Produto'].apply(encontrar_oficial)
                        
                        # Inserção da Data de Extração
                        df_temp.insert(0, "Data Extração", datetime.now().strftime('%d/%m/%Y'))
                        
                        # --- PADRONIZAÇÃO FORÇADA EM CAPSLOCK (Python) ---
                        # Garante que Lote e Status também fiquem em maiúsculas
                        df_temp['Produto'] = df_temp['Produto'].astype(str).str.upper()
                        df_temp['Lote'] = df_temp['Lote'].astype(str).str.upper()
                        df_temp['Status'] = df_temp['Status'].astype(str).str.upper()
                        
                        # --- LIMPEZA DE FORMATOS NUMÉRICOS (Python) ---
                        # Remove decimais (Ex: 92.0 vira 92)
                        df_temp['Visc'] = pd.to_numeric(df_temp['Visc'], errors='coerce').fillna(0).astype(int)
                        # Garante vírgulas em pH e Densidade (caso o modelo use ponto)
                        df_temp['pH'] = df_temp['pH'].astype(str).str.replace('.', ',', regex=False)
                        df_temp['Dens'] = df_temp['Dens'].astype(str).str.replace('.', ',', regex=False)
                        
                        # Salva no histórico da sessão
                        st.session_state.historico = pd.concat([st.session_state.historico, df_temp], ignore_index=True)
                        
                        st.success("Dados extraídos e padronizados em CAPSLOCK!")
                        # Mostra a tabela de conferência
                        st.table(df_temp)
                    else:
                        st.error("Não foi possível identificar o padrão de dados. Tente uma foto mais legível.")
                
                except Exception as e:
                    st.error(f"Erro no processamento: {e}")

with tab2:
    st.header("Histórico de Extrações")
    
    if not st.session_state.historico.empty:
        # Filtro por Data
        datas_disp = st.session_state.historico['Data Extração'].unique()
        data_sel = st.selectbox("Escolha a data para download:", datas_disp)
        
        df_filtrado = st.session_state.historico[st.session_state.historico['Data Extração'] == data_sel]
        # Mostra o histórico completo da data
        st.dataframe(df_filtrado, use_container_width=True)
        
        # Cria o arquivo CSV para download (encoding 'utf-8-sig' resolve erros de acento no Excel)
        csv_buffer = io.StringIO()
        df_filtrado.to_csv(csv_buffer, index=False, sep=';', encoding='utf-8-sig')
        
        st.download_button(
            label=f"📥 Baixar CSV de {data_sel}",
            data=csv_buffer.getvalue(),
            file_name=f"extração_{data_sel.replace('/', '_')}.csv",
            mime="text/csv"
        )
        
        # Opção para limpar o histórico e começar do zero
        if st.button("Limpar Histórico da Sessão"):
            st.session_state.historico = pd.DataFrame()
            st.rerun()
    else:
        st.info("Nenhuma extração registrada nesta sessão ainda.")

st.markdown("---")
st.caption("v2.2 | Sistema de Apoio à Produção com Inteligência Cronológica, Fuzzy Matching e CAPSLOCK.")
