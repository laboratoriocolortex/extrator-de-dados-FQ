import streamlit as st
import pandas as pd
from PIL import Image
import numpy as np
import easyocr
import io
import re
from datetime import datetime
from thefuzz import process

# Configuração da página
st.set_page_config(page_title="Extrator Industrial Local", layout="wide")

# Inicializa o motor de OCR (Lê Português e Números)
@st.cache_resource
def carregar_leitor():
    return easyocr.Reader(['pt'])

reader = carregar_leitor()

# Inicializa o histórico
if 'historico' not in st.session_state:
    st.session_state.historico = pd.DataFrame()

# Carrega a lista oficial de 792 produtos
@st.cache_data
def carregar_lista():
    try:
        df = pd.read_csv('lista_produtos.csv', sep=None, engine='python')
        return df.iloc[:, 0].dropna().astype(str).str.upper().tolist()
    except:
        return []

lista_oficial = carregar_lista()

st.title("🏭 Extrator de Produção (OCR Local)")
st.info("Este app lê etiquetas impressas e dados manuscritos sem usar APIs externas.")

uploaded_file = st.file_uploader("Carregue a foto do diário/etiqueta", type=["jpg", "jpeg", "png"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, width=400, caption="Documento para análise")
    
    if st.button("🔍 Ler Imagem"):
        with st.spinner("Processando texto impresso e manuscrito..."):
            img_array = np.array(image)
            
            # O EasyOCR tenta ler blocos de texto
            # detail=1 retorna a posição do texto, o que ajuda a organizar a leitura
            resultados = reader.readtext(img_array)
            
            texto_completo = " ".join([res[1].upper() for res in resultados])
            
            # --- LÓGICA DE EXTRAÇÃO ---
            
            # 1. Identificar Produto (Comparação com lista de 792 itens)
            produto_final = "NÃO IDENTIFICADO"
            if lista_oficial:
                match = process.extractOne(texto_completo, lista_oficial)
                if match and match[1] > 60:
                    produto_final = match[0]
            
            # 2. Identificar Horários (Padrão HH:MM ou HHMM)
            # Busca padrões como 08:30, 10-15, etc.
            horarios = re.findall(r'\b\d{2}[:\-\s]?\d{2}\b', texto_completo)
            
            # 3. Identificar Lote (Geralmente números após a palavra LOTE)
            lote_match = re.search(r'LOTE\s?(\w+)', texto_completo)
            lote = lote_match.group(1) if lote_match else "---"

            # 4. Dados de Análise (Busca por números isolados com vírgula para pH/Densidade)
            numeros_decimais = re.findall(r'\d+[,\.]\d+', texto_completo)
            ph = numeros_decimais[0] if len(numeros_decimais) > 0 else "0,0"
            dens = numeros_decimais[1] if len(numeros_decimais) > 1 else "0,00"

            # Criar dicionário de dados
            dados = {
                "Data": datetime.now().strftime('%d/%m/%Y'),
                "Produto": produto_final,
                "Lote": lote.upper(),
                "Horários Detectados": " | ".join(horarios),
                "pH": ph.replace('.', ','),
                "Dens": dens.replace('.', ','),
                "Status": "APROVADO" if "APROV" in texto_completo else "ANÁLISE",
                "Texto Bruto": texto_completo[:150] + "..."
            }
            
            # Mostrar resultado e permitir edição manual antes de salvar
            st.subheader("📝 Conferência de Dados")
            with st.form("conferencia"):
                col1, col2 = st.columns(2)
                p_final = col1.text_input("Produto", dados["Produto"]).upper()
                l_final = col1.text_input("Lote", dados["Lote"]).upper()
                h_final = col2.text_input("Horários (Pigmentação/FQ)", dados["Horários Detectados"])
                s_final = col2.selectbox("Status", ["APROVADO", "REPROVADO", "PENDENTE"], index=0 if dados["Status"]=="APROVADO" else 2)
                
                if st.form_submit_button("Confirmar e Salvar no Histórico"):
                    df_novo = pd.DataFrame([{
                        "Data": dados["Data"], "Produto": p_final, "Lote": l_final, 
                        "Horários": h_final, "Status": s_final, "pH": dados["pH"], "Dens": dados["Dens"]
                    }])
                    st.session_state.historico = pd.concat([st.session_state.historico, df_novo], ignore_index=True)
                    st.success("Salvo com sucesso!")

# --- HISTÓRICO E DOWNLOAD ---
if not st.session_state.historico.empty:
    st.divider()
    st.subheader("📊 Histórico Acumulado")
    st.dataframe(st.session_state.historico, use_container_width=True)
    
    csv = st.session_state.historico.to_csv(index=False, sep=';', encoding='utf-8-sig')
    st.download_button("📥 Baixar Planilha CSV", csv, f"producao_{datetime.now().strftime('%d_%m')}.csv", "text/csv")
