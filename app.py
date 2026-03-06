import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image
from thefuzz import process, fuzz
import re

st.set_page_config(page_title="Extrator Industrial Hierárquico", layout="wide")

@st.cache_resource
def carregar_ocr():
    return easyocr.Reader(['pt', 'en'], gpu=False)

reader = carregar_ocr()

@st.cache_data
def carregar_lista_oficial():
    try:
        df = pd.read_csv("lista_produtos.csv", sep=";", encoding="latin-1")
        return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
    except:
        return []

lista_produtos = carregar_lista_oficial()

if "df_leitura" not in st.session_state:
    st.session_state.df_leitura = pd.DataFrame()

st.title("🏭 Leitor de Diário - Fluxo de Identificação")

uploaded_file = st.file_uploader("Envie a foto do diário", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, width=500)
    
    if st.button("🚀 Processar com Hierarquia Visual", type="primary"):
        with st.spinner("Analisando Nome, Cor, Lote e Medidas..."):
            img_np = np.array(image)
            resultados = reader.readtext(img_np, detail=1)
            
            # Agrupamento por Linha (Y)
            linhas = {}
            margem_y = 60 
            
            for (bbox, texto, prob) in resultados:
                # Filtragem de "sujeira": ignora textos muito curtos (1 ou 2 letras soltas)
                if len(texto.strip()) < 3 and not texto.isdigit():
                    continue
                
                y_centro = (bbox[0][1] + bbox[2][1]) / 2
                pertence = False
                for y_ref in linhas.keys():
                    if abs(y_centro - y_ref) < margem_y:
                        linhas[y_ref].append({"txt": texto.upper(), "box": bbox})
                        pertence = True
                        break
                if not pertence:
                    linhas[y_centro] = [{"txt": texto.upper(), "box": bbox}]

            dados_consolidados = []
            
            for y in sorted(linhas.keys()):
                bloco = linhas[y]
                # Une o texto da linha para busca de padrões
                texto_linha = " ".join([b["txt"] for b in bloco])
                
                # --- IDENTIFICAÇÃO HIERÁRQUICA ---
                
                # 1. Lote (Padrão L - 12345)
                lote_match = re.search(r'L\s*[-–]\s*(\d+)', texto_linha)
                lote = lote_match.group(1) if lote_match else "---"
                
                # 2. Litragem (Número + L ou KG)
                litragem_match = re.search(r'(\d+[\.,]?\d*)\s*(L|KG)', texto_linha)
                litragem = litragem_match.group(0) if litragem_match else "---"
                
                # 3. Horários (Filtro para evitar pegar números de pH como hora)
                horas = re.findall(r'\b(?:[012]?\d)[:\.\-][0-5]\d\b', texto_linha)
                
                # 4. Análises (pH e Densidade - números com vírgula)
                decimais = re.findall(r'\d+[,\.]\d+', texto_linha)
                
                # 5. Validação do Produto (Fuzzy 90%)
                # Tentamos validar o início da linha (onde costuma estar o nome/cor)
                prod_validado = "❌ NÃO ENCONTRADO"
                confianca = 0
                if lista_produtos:
                    match, score = process.extractOne(texto_linha, lista_produtos, scorer=fuzz.token_set_ratio)
                    if score >= 90:
                        prod_validado = match
                        confianca = score

                if lote != "---" or prod_validado != "❌ NÃO ENCONTRADO":
                    dados_consolidados.append({
                        "Produto Oficial": prod_validado,
                        "Lote": lote,
                        "Litragem": litragem,
                        "Início (Pig)": horas[0] if len(horas) > 0 else "---",
                        "Fim (FQ)": horas[1] if len(horas) > 1 else "---",
                        "pH": decimais[0] if len(decimais) > 0 else "---",
                        "Densidade": decimais[1] if len(decimais) > 1 else "---",
                        "Confiança %": confianca
                    })

            st.session_state.df_leitura = pd.DataFrame(dados_consolidados)

if not st.session_state.df_leitura.empty:
    st.subheader("📋 Conferência de Extração Hierárquica")
    st.session_state.df_leitura = st.data_editor(st.session_state.df_leitura, use_container_width=True)
    
    csv = st.session_state.df_leitura.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("📥 Baixar Planilha", csv, "conferencia_industrial.csv", "text/csv")
