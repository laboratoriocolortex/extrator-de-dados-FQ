import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image
from thefuzz import process, fuzz
import re
import io

# 1. Configuração da Página
st.set_page_config(page_title="Extrator Industrial Local", layout="wide")

# 2. Motor OCR Local (Carrega uma vez e guarda na memória)
@st.cache_resource
def carregar_leitor():
    # 'pt' para Português, 'en' para números e siglas
    return easyocr.Reader(['pt', 'en'], gpu=False)

reader = carregar_leitor()

# 3. Lista de Produtos (Validação 90%)
@st.cache_data
def carregar_lista():
    for enc in ['utf-8', 'latin-1', 'cp1252']:
        try:
            df = pd.read_csv("lista_produtos.csv", sep=";", encoding=enc)
            return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
        except:
            continue
    return []

lista_oficial = carregar_lista()

if "df_producao" not in st.session_state:
    st.session_state.df_producao = pd.DataFrame(columns=[
        "Produto Lido", "Produto Oficial", "Confiança %", "Lote", "Horários", "pH", "Dens", "Status"
    ])

# --- INTERFACE ---
st.title("🏭 Extrator de Produção Local (EasyOCR)")
st.caption("Processamento interno: sem erros de cota (429) e sem limite de uso.")

uploaded_file = st.file_uploader("Suba a foto do diário/etiqueta", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, width=450, caption="Imagem para Processamento")
    
    if st.button("🔍 Extrair Dados Localmente", type="primary"):
        with st.spinner("O motor local está lendo os caracteres..."):
            # Converte para array que o EasyOCR processa
            img_np = np.array(image)
            
            # Leitura do texto com detalhes de posição
            resultados = reader.readtext(img_np, detail=1)
            
            # Unifica o texto e tenta identificar padrões
            texto_bruto = " ".join([res[1].upper() for res in resultados])
            
            # --- FILTROS INTELIGENTES (REGEX) ---
            
            # 1. Busca Horários (Padrões como 08:30, 09-15, 1030)
            padrao_hora = r'\b([01]?[0-9]|2[0-3])[:\-\s]?([0-5][0-9])\b'
            horas_encontradas = re.findall(padrao_hora, texto_bruto)
            horas_formatadas = [f"{h[0]}:{h[1]}" for h in horas_encontradas]
            horarios_str = " | ".join(horas_formatadas) if horas_formatadas else "---"
            
            # 2. Busca pH e Densidade (Números com vírgula ou ponto)
            numeros_decimais = re.findall(r'\d+[,\.]\d+', texto_bruto)
            ph = numeros_decimais[0] if len(numeros_decimais) > 0 else "---"
            dens = numeros_decimais[1] if len(numeros_decimais) > 1 else "---"
            
            # 3. Busca Lote (Palavra LOTE seguida de números/letras)
            lote_match = re.search(r'LOTE[:\s]*([A-Z0-9]+)', texto_bruto)
            lote = lote_match.group(1) if lote_match else "---"

            # --- VALIDAÇÃO RÍGIDA (90%) ---
            prod_oficial = "❌ NÃO ENCONTRADO NA LISTA"
            score_matching = 0
            
            if lista_oficial:
                # O EasyOCR pode ler o nome espalhado, tentamos o matching no texto todo
                match, score = process.extractOne(texto_bruto, lista_oficial, scorer=fuzz.token_set_ratio)
                if score >= 90:
                    prod_oficial = match
                    score_matching = score
                else:
                    score_matching = score

            # --- SALVAR NO HISTÓRICO ---
            novo_registro = {
                "Produto Lido": texto_bruto[:50] + "...",
                "Produto Oficial": prod_oficial,
                "Confiança %": score_matching,
                "Lote": lote,
                "Horários": horarios_str,
                "pH": ph,
                "Dens": dens,
                "Status": "REVISAR"
            }
            
            st.session_state.df_producao = pd.concat([st.session_state.df_producao, pd.DataFrame([novo_registro])], ignore_index=True)

# --- REVISÃO TÉCNICA ---
if not st.session_state.df_producao.empty:
    st.divider()
    st.subheader("📝 Tabela de Conferência")
    st.info("Como este processo é local, use a tabela abaixo para ajustar qualquer caractere que o OCR leu errado.")
    
    # Editor para correções manuais (Essencial no OCR local)
    st.session_state.df_producao = st.data_editor(
        st.session_state.df_producao,
        use_container_width=True,
        num_rows="dynamic"
    )

    col1, col2 = st.columns(2)
    csv = st.session_state.df_producao.to_csv(index=False, sep=";", encoding="utf-8-sig")
    col1.download_button("📥 Exportar Planilha Excel", csv, "producao_local.csv", "text/csv")
    
    if col2.button("🗑️ Limpar Sessão"):
        st.session_state.df_producao = pd.DataFrame(columns=st.session_state.df_producao.columns)
        st.rerun()
