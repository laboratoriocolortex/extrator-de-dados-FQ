import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image
from thefuzz import process, fuzz
import re

# 1. Configuração de Página
st.set_page_config(page_title="Leitor Industrial por Etiquetas", layout="wide")

@st.cache_resource
def carregar_leitor():
    return easyocr.Reader(['pt', 'en'], gpu=False)

reader = carregar_leitor()

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

if "df_final" not in st.session_state:
    st.session_state.df_final = pd.DataFrame(columns=[
        "Produto Lido", "Produto Oficial", "Confiança %", "Lote", "Pigmentação", "Análise FQ", "pH", "Dens", "Visc"
    ])

st.title("🏭 Leitor de Etiquetas Individuais (Local)")
st.caption("Separação espacial de blocos para evitar mistura de dados entre produtos.")

uploaded_file = st.file_uploader("Suba a foto com várias etiquetas/linhas", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, width=500)
    
    if st.button("🔍 Processar Etiquetas Separadamente", type="primary"):
        with st.spinner("Analisando blocos de texto..."):
            img_np = np.array(image)
            # detail=1 retorna as coordenadas [x, y] de cada palavra
            resultados = reader.readtext(img_np, detail=1)
            
            # --- LÓGICA DE AGRUPAMENTO POR LINHA (Y-COORD) ---
            # Agrupamos palavras que estão em alturas próximas na foto
            linhas_detectadas = {}
            tolerancia_y = 40 # Ajuste este valor se as etiquetas forem muito grandes/pequenas
            
            for (bbox, texto, prob) in resultados:
                y_topo = bbox[0][1]
                encontrou_linha = False
                for y_ref in linhas_detectadas.keys():
                    if abs(y_topo - y_ref) < tolerancia_y:
                        linhas_detectadas[y_ref].append(texto.upper())
                        encontrou_linha = True
                        break
                if not encontrou_linha:
                    linhas_detectadas[y_topo] = [texto.upper()]

            novos_registros = []
            
            # Processar cada "linha" ou "bloco" como uma etiqueta única
            for y in sorted(linhas_detectadas.keys()):
                texto_bloco = " ".join(linhas_detectadas[y])
                
                # 1. Extração de Horários (Ordem Cronológica)
                horas = re.findall(r'\b(?:[01]\d|2[0-3])[:\-\s][0-5]\d\b', texto_bloco)
                pig = horas[0] if len(horas) > 0 else "---"
                fq = horas[1] if len(horas) > 1 else "---"
                
                # 2. Extração de Valores Químicos (pH, Dens, Visc)
                decimais = re.findall(r'\d+[,\.]\d+', texto_bloco)
                inteiros = re.findall(r'\b\d{2,3}\b', texto_bloco) # Viscosidade geralmente 2 ou 3 dígitos
                
                val_ph = decimais[0] if len(decimais) > 0 else "---"
                val_dens = decimais[1] if len(decimais) > 1 else "---"
                val_visc = inteiros[0] if len(inteiros) > 0 else "---"
                
                # 3. Extração de Lote
                lote_match = re.search(r'LOTE[:\s]*([A-Z0-9]+)', texto_bloco)
                lote = lote_match.group(1) if lote_match else "---"

                # 4. VALIDAÇÃO 90% CONTRA LISTA CSV
                prod_oficial = "❌ PRODUTO NÃO ENCONTRADO"
                score_val = 0
                if lista_oficial:
                    # Comparamos o bloco todo contra a lista para achar o nome do produto
                    match, score = process.extractOne(texto_bloco, lista_oficial, scorer=fuzz.token_set_ratio)
                    if score >= 90:
                        prod_oficial = match
                        score_val = score
                    else:
                        score_val = score

                novos_registros.append([
                    texto_bloco[:40], prod_oficial, score_val, lote, pig, fq, val_ph, val_dens, val_visc
                ])

            if novos_registros:
                df_temp = pd.DataFrame(novos_registros, columns=st.session_state.df_final.columns)
                st.session_state.df_final = pd.concat([st.session_state.df_final, df_temp], ignore_index=True)

# --- REVISÃO ---
if not st.session_state.df_final.empty:
    st.divider()
    st.subheader("📋 Revisão de Lotes Detectados")
    st.session_state.df_final = st.data_editor(st.session_state.df_final, use_container_width=True)
    
    csv = st.session_state.df_final.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("📥 Baixar Planilha", csv, "producao.csv", "text/csv")
    
    if st.button("🗑️ Limpar Tudo"):
        st.session_state.df_final = pd.DataFrame(columns=st.session_state.df_final.columns)
        st.rerun()
