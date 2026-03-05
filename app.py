import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from thefuzz import process, fuzz
import io

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Industrial 3.1 Pro - Validação Rígida", layout="wide")

# 2. Configuração do Motor Pro
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
    model = genai.GenerativeModel(
        model_name="gemini-3.1-pro-preview",
        generation_config={"temperature": 0} 
    )
except Exception:
    st.error("Erro na API Key. Verifique os Secrets.")
    st.stop()

# 3. Carregamento da Lista Oficial (792 Produtos)
@st.cache_data
def carregar_lista_produtos():
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding=enc)
            return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        except:
            continue
    return []

lista_oficial = carregar_lista_produtos()

# 4. Estado da Sessão
if "df_validacao" not in st.session_state:
    st.session_state.df_validacao = pd.DataFrame(columns=[
        "Produto Lido (IA)", "Produto Oficial (Lista)", "Confiança %", "Lote", "IniPig", "FimPig", "Visc", "pH", "Dens", "Status"
    ])

# --- INTERFACE ---
st.title("🚀 Extrator Industrial - Validação Rígida (90%)")
st.markdown("---")

uploaded_file = st.file_uploader("Suba a imagem do diário ou etiquetas", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=450, caption="Documento Detectado")
    
    if st.button("🔍 Processar e Validar Dados", type="primary"):
        with st.spinner("Analisando com 90% de critério de similaridade..."):
            try:
                # Prompt focado em manter a estrutura da linha
                prompt = """Extraia todos os dados presentes na imagem.
                REGRAS:
                - TUDO EM CAPSLOCK.
                - Saída em CSV (separador ;).
                - Identifique Produto;Lote;IniPig;FimPig;Visc;pH;Dens;Status.
                - Se a etiqueta for DOURADA/BRONZE, adicione 'COR SOB ENCOMENDA' ao produto.
                """

                response = model.generate_content([image, prompt])
                linhas = response.text.strip().split('\n')
                
                novos_itens = []
                for linha in linhas:
                    if ';' in linha and 'Produto;' not in linha:
                        partes = [p.strip() for p in linha.split(';')]
                        if len(partes) >= 8:
                            prod_lido = partes[0].upper()
                            
                            # --- LÓGICA DE ASSOCIAÇÃO RÍGIDA (90%) ---
                            prod_validado = ""
                            score_final = 0
                            
                            if lista_oficial:
                                # Usamos o scorer token_set_ratio para lidar com inversões de palavras
                                match, score = process.extractOne(prod_lido, lista_oficial, scorer=fuzz.token_set_ratio)
                                
                                if score >= 90:
                                    prod_validado = match
                                    score_final = score
                                else:
                                    # NOVA INSTRUÇÃO: Identificação clara de não encontrado
                                    prod_validado = "❌ PRODUTO NÃO ENCONTRADO NA LISTA"
                                    score_final = score

                            novos_itens.append([
                                prod_lido, prod_validado, score_final,
                                partes[1], partes[2], partes[3], partes[4], partes[5], partes[6], partes[7]
                            ])

                if novos_itens:
                    df_temp = pd.DataFrame(novos_itens, columns=st.session_state.df_validacao.columns)
                    st.session_state.df_validacao = pd.concat([st.session_state.df_validacao, df_temp], ignore_index=True)
                    st.success("Processamento concluído.")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# --- REVISÃO E EDIÇÃO ---
if not st.session_state.df_validacao.empty:
    st.divider()
    st.subheader("📋 Revisão Técnica dos Dados")
    st.warning("⚠️ Atenção: Itens marcados com '❌' não atingiram 90% de similaridade e devem ser corrigidos manualmente.")
    
    # Editor de dados dinâmico
    st.session_state.df_validacao = st.data_editor(
        st.session_state.df_validacao,
        num_rows="dynamic",
        use_container_width=True,
        key="editor_90_confianca"
    )

    col1, col2 = st.columns(2)
    
    # Exportação
    csv = st.session_state.df_validacao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    col1.download_button("📥 Baixar Planilha Validada", csv, "producao_90_precisao.csv", "text/csv")
    
    if col2.button("🗑️ Limpar Histórico"):
        st.session_state.df_validacao = pd.DataFrame(columns=st.session_state.df_validacao.columns)
        st.rerun()


