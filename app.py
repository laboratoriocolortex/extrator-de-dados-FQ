import streamlit as st
import pandas as pd
from thefuzz import process
import google.generativeai as genai
from PIL import Image

# 1. Configuração da página
st.set_page_config(page_title="Leitor de Diários de Produção", layout="wide")

# 2. Configuração da API do Gemini usando st.secrets
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
except KeyError:
    st.error("Chave da API não encontrada. Configure st.secrets['GEMINI_CHAVE'].")
    st.stop()

# 3. Instruções do Sistema para o Modelo
SYSTEM_INSTRUCTION = """
Atue como um Engenheiro de Dados e Especialista em Controle de Qualidade Industrial. Sua tarefa é processar imagens de diários de produção e etiquetas de tintas.

REGRAS DE PROCESSAMENTO VISUAL:
1. IDENTIFICAÇÃO DE PRODUTO: Combine o nome do produto, a cor e a litragem/peso detectados na etiqueta (Ex: COLORMAX AZUL 15L).
2. DISTINÇÃO DE CORES: 
   - Se a etiqueta física for de cor DOURADA ou BRONZE, você deve obrigatoriamente adicionar o sufixo "COR SOB ENCOMENDA" ao nome do produto.
   - Se a etiqueta for AMARELA ou de outra cor padrão, ignore esta instrução.
3. LEITURA DE MANUSCRITOS: Decifre os horários e valores técnicos escritos à mão.
4. LÓGICA CRONOLÓGICA:
   - O primeiro intervalo de horário (o que inicia mais cedo no dia) deve ser definido como PIGMENTAÇÃO.
   - O segundo intervalo de horário (posterior ao primeiro) deve ser definido como ANÁLISE FQ.

REGRAS DE FORMATAÇÃO (ESTRITAS):
- Saída: Forneça a resposta estritamente em uma única linha no formato CSV, usando ponto e vírgula (;) como separador.
- Letras: Tudo deve ser retornado em CAPSLOCK (MAIÚSCULAS).
- Números: 
  - Viscosidade (Visc) deve ser um número inteiro.
  - pH e Densidade devem usar VÍRGULA como separador decimal (ex: 8,2 e 1,05).
- Ordem das Colunas: Produto;Lote;IniPig;FimPig;IniFQ;FimFQ;Visc;pH;Dens;Status

PERSONALIDADE:
Seja preciso e não adicione nenhum texto explicativo, saudações ou comentários antes ou depois da linha CSV. Se não encontrar um dado, use "---".
"""

# Inicialização do modelo Gemini 2.5 Flash (ideal para visão e texto)
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction=SYSTEM_INSTRUCTION
)

# 4. Inicialização do Histórico no Session State
if "historico" not in st.session_state:
    st.session_state.historico = []

# 5. Carregamento da lista de produtos para o thefuzz
@st.cache_data
def carregar_lista_produtos():
    try:
        # Tenta ler o arquivo CSV de produtos com UTF-8
        df = pd.read_csv("lista_produtos.csv", sep=";", encoding="utf-8")
        return df.iloc[:, 0].astype(str).tolist()
    except UnicodeDecodeError:
        try:
            # Se der erro de Unicode, tenta ler com a codificação padrão do Windows/Excel
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding="latin1")
            return df.iloc[:, 0].astype(str).tolist()
        except Exception as e:
            st.error(f"Erro ao ler o arquivo com encoding latin1: {e}")
            return []
    except FileNotFoundError:
        st.warning("Arquivo 'lista_produtos.csv' não encontrado. A validação de nome com thefuzz será ignorada.")
        return []

lista_produtos = carregar_lista_produtos()

# Interface do Usuário
st.title("🏭 Processamento de Diários de Produção e Etiquetas")

# File Uploader para Imagens
uploaded_file = st.file_uploader("Envie a imagem do diário/etiqueta", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="Imagem Carregada", width=400)
    
    if st.button("Processar Imagem", type="primary"):
        with st.spinner("Analisando imagem com Gemini..."):
            try:
                # Chamada para o modelo passando a imagem
                response = model.generate_content([image, "Extraia os dados da imagem conforme as instruções do sistema."])
                resultado_csv = response.text.strip()
                
                # Colunas esperadas conforme a instrução
                colunas = ["Produto", "Lote", "IniPig", "FimPig", "IniFQ", "FimFQ", "Visc", "pH", "Dens", "Status"]
                valores = resultado_csv.split(";")
                
                if len(valores) == len(colunas):
                    produto_extraido = valores[0]
                    
                    # Validação com thefuzz
                    if lista_produtos:
                        melhor_correspondencia, pontuacao = process.extractOne(produto_extraido, lista_produtos)
                        
                        # Se a pontuação for boa (ex: >= 80), substitui pelo nome oficial
                        if pontuacao >= 80:
                            valores[0] = melhor_correspondencia
                            st.success(f"✅ Produto validado: **{produto_extraido}** ➔ **{melhor_correspondencia}** (Score: {pontuacao})")
                        else:
                            st.warning(f"⚠️ Baixa correspondência na lista para: **{produto_extraido}** (Melhor: {melhor_correspondencia} com score {pontuacao})")
                    
                    # Salva no histórico
                    registro = dict(zip(colunas, valores))
                    st.session_state.historico.append(registro)
                    st.success("Dados extraídos e adicionados ao histórico com sucesso!")
                    
                else:
                    st.error(f"Erro de formatação na resposta do modelo. Esperado {len(colunas)} colunas, recebido {len(valores)}.\nResposta bruta: {resultado_csv}")
            
            except Exception as e:
                st.error(f"Erro ao processar a imagem: {e}")

# 6. Exibição e Download do Histórico
if st.session_state.historico:
    st.divider()
    st.subheader("📋 Histórico de Processamento")
    
    df_historico = pd.DataFrame(st.session_state.historico)
    st.dataframe(df_historico, use_container_width=True)
    
    # Configuração do CSV para download (sep=';', encoding='utf-8-sig')
    csv_data = df_historico.to_csv(index=False, sep=";", encoding="utf-8-sig")
    
    st.download_button(
        label="📥 Baixar Histórico em CSV",
        data=csv_data,
        file_name="historico_producao.csv",
        mime="text/csv"
    )

