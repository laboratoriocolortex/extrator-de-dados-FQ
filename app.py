import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from thefuzz import process, fuzz
import re
import io

# 1. Configuração da Página
st.set_page_config(page_title="Acompanhamento de Liberações", layout="wide")

# 2. Configuração do Motor Gemini
try:
    genai.configure(api_key=st.secrets["GEMINI_CHAVE"])
    # Usando o modelo flash para maior velocidade e estabilidade
    model = genai.GenerativeModel(
        model_name="gemini-3-flash-preview", 
        generation_config={"temperature": 0} 
    )
except Exception:
    st.error("Erro na API Key. Verifique os Secrets.")
    st.stop()

# 3. Carregamento da Lista Oficial
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

# 4. Estado da Sessão (Colunas ajustadas conforme pedido)
if "df_validacao" not in st.session_state:
    st.session_state.df_validacao = pd.DataFrame(columns=[
        "Produto Lido", "Produto Oficial", "Lote", "IniPig", "FimPig", "Visc", "pH", "Dens", "Ajustes/Correções"
    ])

st.title("🚀 Acompanhamento de Liberações")
st.markdown("---")

uploaded_file = st.file_uploader("Suba a imagem do diário ou etiquetas", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=450, caption="Documento Detectado")
    
    if st.button("🔍 Processar e Validar Dados", type="primary"):
        with st.spinner("Extraindo e formatando dados..."):
            try:
                prompt = """Extraia os dados da imagem seguindo estas regras:
                1. Identifique: Produto; Lote; Horário Início (Pigmentação); Horário Fim (Análise FQ); Viscosidade; pH; Densidade; Ajustes de Correção.
                2. Regra Especial de Nome: 
                   - Se ler 'Massa Acrílica', retorne como 'MASSA ACRILICA PREMIUM XKG' (onde X é o peso lido).
                   - Se ler 'Massa Corrida', retorne como 'MASSA CORRIDA PREMIUM XKG' (onde X é o peso lido).
                3. Ajustes: Se houver anotações de '+ água', '+ espessante', etc., extraia na coluna Ajustes.
                4. Saída apenas em CSV (separador ;).
                """

                response = model.generate_content([image, prompt])
                linhas = response.text.strip().split('\n')
                
                novos_itens = []
                for linha in linhas:
                    if ';' in linha and 'Produto;' not in linha:
                        partes = [p.strip() for p in linha.split(';')]
                        if len(partes) >= 8:
                            prod_lido = partes[0].upper()
                            ajuste = partes[7] if len(partes) > 7 else ""
                            
                            # --- VALIDAÇÃO E REGRAS DE MASSA ---
                            prod_validado = ""
                            
                            # Verifica se é uma das massas primeiro (Regra de Negócio)
                            if "MASSA ACRILICA" in prod_lido:
                                peso = re.search(r'(\d+)\s*KG', prod_lido)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA ACRILICA PREMIUM {peso_str}"
                            elif "MASSA CORRIDA" in prod_lido:
                                peso = re.search(r'(\d+)\s*KG', prod_lido)
                                peso_str = peso.group(0) if peso else "XKG"
                                prod_validado = f"MASSA CORRIDA PREMIUM {peso_str}"
                            else:
                                # Validação 90% para outros produtos
                                if lista_oficial:
                                    match, score = process.extractOne(prod_lido, lista_oficial, scorer=fuzz.token_set_ratio)
                                    prod_validado = match if score >= 90 else "❌ NÃO ENCONTRADO"
                                else:
                                    prod_validado = "❌ LISTA NÃO CARREGADA"

                            novos_itens.append([
                                prod_lido, prod_validado, partes[1], partes[2], 
                                partes[3], partes[4], partes[5], partes[6], ajuste
                            ])

                if novos_itens:
                    df_temp = pd.DataFrame(novos_itens, columns=st.session_state.df_validacao.columns)
                    st.session_state.df_validacao = pd.concat([st.session_state.df_validacao, df_temp], ignore_index=True)
                    st.success("Dados processados com sucesso!")
            except Exception as e:
                st.error(f"Erro no processamento: {e}")

# --- REVISÃO E EDIÇÃO ---
if not st.session_state.df_validacao.empty:
    st.divider()
    st.subheader("📋 Revisão Técnica")
    
    st.session_state.df_validacao = st.data_editor(
        st.session_state.df_validacao,
        num_rows="dynamic",
        use_container_width=True,
    )

    col1, col2 = st.columns(2)
    csv = st.session_state.df_validacao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    col1.download_button("📥 Baixar Planilha Final", csv, "liberacao_producao.csv", "text/csv")
    
    if col2.button("🗑️ Limpar Tudo"):
        st.session_state.df_validacao = pd.DataFrame(columns=st.session_state.df_validacao.columns)
        st.rerun()
