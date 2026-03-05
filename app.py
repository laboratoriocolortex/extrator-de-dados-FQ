import streamlit as st
import pandas as pd
from thefuzz import process
import google.generativeai as genai
from PIL import Image
import io

# 1. Configuração da página
st.set_page_config(page_title="Leitor de Diários Multilotes", layout="wide")

# 2. Configuração da API do Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
except KeyError:
    st.error("Chave da API não encontrada. Configure st.secrets['GEMINI_CHAVE'].")
    st.stop()

# 3. Instruções do Sistema (Ajustadas para Múltiplas Linhas)
SYSTEM_INSTRUCTION = """
Atue como um Engenheiro de Dados Industrial. Sua tarefa é processar imagens de diários de produção.
A imagem pode conter UM ou VÁRIOS produtos/lotes. Extraia TODOS os que encontrar.

REGRAS DE PROCESSAMENTO:
1. IDENTIFICAÇÃO: Combine Nome + Cor + Litragem (Ex: COLORMAX AZUL 15L).
2. ETIQUETAS DOURADAS/BRONZE: Adicione obrigatoriamente "COR SOB ENCOMENDA" ao nome.
3. CRONOLOGIA: Primeiro horário = PIGMENTAÇÃO. Segundo horário (posterior) = ANÁLISE FQ.

REGRAS DE FORMATAÇÃO (ESTRITAS):
- Saída: Retorne APENAS as linhas no formato CSV (ponto e vírgula).
- UMA LINHA POR PRODUTO/LOTE encontrado.
- TUDO EM CAPSLOCK.
- pH e Densidade: Use VÍRGULA como separador decimal.
- Viscosidade: Apenas número inteiro.
- Formato: Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # Use 'gemini-1.5-pro' para maior precisão em manuscritos
    system_instruction=SYSTEM_INSTRUCTION
)

if "historico" not in st.session_state:
    st.session_state.historico = []

# 4. Carregamento da lista de produtos
@st.cache_data
def carregar_lista_produtos():
    try:
        df = pd.read_csv("lista_produtos.csv", sep=";", encoding="utf-8")
        return df.iloc[:, 0].astype(str).tolist()
    except:
        try:
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding="latin1")
            return df.iloc[:, 0].astype(str).tolist()
        except:
            return []

lista_produtos = carregar_lista_produtos()

st.title("🏭 Processamento Multilotes - Diários e Etiquetas")

uploaded_file = st.file_uploader("Envie a imagem (Pode conter vários lotes)", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem Carregada", width=450)
    
    if st.button("Processar Toda a Imagem", type="primary"):
        with st.spinner("Analisando todos os itens detectados..."):
            try:
                # Solicita explicitamente todos os itens
                response = model.generate_content([image, "Extraia TODOS os produtos e lotes presentes nesta imagem, um por linha."])
                resultado_bruto = response.text.strip()
                
                linhas = resultado_bruto.split('\n')
                colunas = ["Produto", "Lote", "IniPig", "FimPig", "IniFQ", "FimFQ", "Visc", "pH", "Dens", "Status"]
                
                contagem = 0
                for linha in linhas:
                    if ";" not in linha: continue
                    
                    valores = [v.strip() for v in linha.split(";")]
                    
                    if len(valores) == len(colunas):
                        produto_extraido = valores[0]
                        
                        # Validação Fuzzy
                        if lista_produtos:
                            melhor_match, pontuacao = process.extractOne(produto_extraido, lista_produtos)
                            if pontuacao >= 80:
                                valores[0] = melhor_match
                        
                        registro = dict(zip(colunas, valores))
                        st.session_state.historico.append(registro)
                        contagem += 1
                
                if contagem > 0:
                    st.success(f"✅ {contagem} lotes extraídos com sucesso!")
                else:
                    st.warning("Nenhum dado formatado foi encontrado. Verifique se a imagem está clara.")
            
            except Exception as e:
                st.error(f"Erro ao processar: {e}")

# 5. Exibição e Download
if st.session_state.historico:
    st.divider()
    col_titulo, col_limpar = st.columns([4, 1])
    col_titulo.subheader("📋 Histórico de Processamento")
    
    if col_limpar.button("🗑️ Limpar Tudo"):
        st.session_state.historico = []
        st.rerun()
    
    df_historico = pd.DataFrame(st.session_state.historico)
    st.dataframe(df_historico, use_container_width=True)
    
    csv_data = df_historico.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label="📥 Baixar Planilha CSV",
        data=csv_data,
        file_name="producao_consolidada.csv",
        mime="text/csv"
    )
