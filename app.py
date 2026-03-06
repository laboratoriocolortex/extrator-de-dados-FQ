import streamlit as st
import pandas as pd
import numpy as np
import easyocr
from PIL import Image
from thefuzz import process, fuzz
import re

# Configuração da página
st.set_page_config(page_title="Extrator Industrial de Precisão", layout="wide")

@st.cache_resource
def carregar_leitor():
    # Carrega o motor de leitura para Português e Inglês
    return easyocr.Reader(['pt', 'en'], gpu=False)

reader = carregar_leitor()

@st.cache_data
def carregar_lista_produtos():
    try:
        df = pd.read_csv("lista_produtos.csv", sep=";", encoding="latin-1")
        return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
    except:
        return []

lista_oficial = carregar_lista_produtos()

if "historico" not in st.session_state:
    st.session_state.historico = pd.DataFrame()

st.title("🏭 Leitor de Diário de Produção")

uploaded_file = st.file_uploader("Suba a foto do diário", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, width=600, caption="Imagem carregada")
    
    if st.button("🔍 Extrair Todos os Lotes", type="primary"):
        with st.spinner("Agrupando etiquetas e manuscritos..."):
            img_np = np.array(image)
            # Lê o texto com coordenadas detalhadas
            resultados = reader.readtext(img_np, detail=1)
            
            # Agrupar palavras que estão na mesma altura (Eixo Y)
            blocos_por_linha = {}
            tolerancia_altura = 50 # Define o que é considerado "mesma linha"
            
            for (bbox, texto, prob) in resultados:
                centro_y = (bbox[0][1] + bbox[2][1]) / 2
                encontrou = False
                for y_ref in blocos_por_linha.keys():
                    if abs(centro_y - y_ref) < tolerancia_altura:
                        blocos_por_linha[y_ref].append(texto.upper())
                        encontrou = True
                        break
                if not encontrou:
                    blocos_por_linha[centro_y] = [texto.upper()]

            registros_da_foto = []
            
            # Processa cada linha horizontal como um Lote único
            for y in sorted(blocos_por_linha.keys()):
                texto_linha = " ".join(blocos_por_linha[y])
                
                # Regex para pegar Horários (ex: 18:10 ou 18.10)
                horas = re.findall(r'\b(?:[012]?\d)[:\.\-][0-5]\d\b', texto_linha)
                # Regex para pegar pH/Densidade (números com vírgula ou ponto)
                decimais = re.findall(r'\d+[,\.]\d+', texto_linha)
                
                # Validação Rígida 90% contra seu CSV
                produto_validado = "❌ NÃO ENCONTRADO"
                score = 0
                if lista_oficial:
                    match, score_match = process.extractOne(texto_linha, lista_oficial, scorer=fuzz.token_set_ratio)
                    if score_match >= 90:
                        produto_validado = match
                        score = score_match
                
                # Organiza os dados extraídos
                registros_da_foto.append({
                    "Produto Lido": texto_linha[:40],
                    "Produto Oficial": produto_validado,
                    "Confiança": f"{score}%",
                    "Horário 1": horas[0] if len(horas) > 0 else "-",
                    "Horário 2": horas[1] if len(horas) > 1 else "-",
                    "Analise 1": decimais[0] if len(decimais) > 0 else "-",
                    "Analise 2": decimais[1] if len(decimais) > 1 else "-",
                })

            df_novo = pd.DataFrame(registros_da_foto)
            st.session_state.historico = pd.concat([st.session_state.historico, df_novo], ignore_index=True)

# Exibição e Edição
if not st.session_state.historico.empty:
    st.subheader("📋 Tabela de Conferência")
    st.session_state.historico = st.data_editor(st.session_state.historico, use_container_width=True)
    
    csv = st.session_state.historico.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button("📥 Baixar Planilha Corrigida", csv, "producao.csv", "text/csv")
