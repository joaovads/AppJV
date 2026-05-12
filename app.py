import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import tempfile
import zipfile
import os
import time
import hashlib
import uuid
import base64
import json
import calendar
import re
import math
import io
from sklearn.linear_model import LinearRegression
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
import html
import streamlit.components.v1 as components

# ==========================================
# IMPORTAÇÃO DE BIBLIOTECAS EXTERNAS E IA
# ==========================================
try:
    from streamlit_cookies_controller import CookieController
    cookie_controller = CookieController()
except ImportError: 
    cookie_controller = None

try:
    from PIL import Image
except ImportError: 
    Image = None

try:
    import PyPDF2
    from groq import Groq
except ImportError:
    PyPDF2 = None
    Groq = None

# Nova biblioteca para botão de colar
try:
    from streamlit_paste_button import paste_image_button
except ImportError:
    paste_image_button = None

# ==========================================
# CONFIGURAÇÃO GERAL DA PÁGINA E MODELOS
# ==========================================
st.set_page_config(page_title="Residência PRO", page_icon="🏥", layout="wide")

MODELO_VISAO = "meta-llama/llama-4-scout-17b-16e-instruct"
MODELO_TEXTO = "llama-3.1-8b-instant"

def ativar_pwa():
    pwa_html = """
    <script>
        if (!document.getElementById('pwa-manifest')) {
            const manifest = {
                "name": "Residência PRO",
                "short_name": "Residência",
                "theme_color": "#2563eb",
                "background_color": "#0e1117",
                "display": "standalone",
                "orientation": "portrait",
                "start_url": "/",
                "icons": [{
                    "src": "https://cdn-icons-png.flaticon.com/512/3004/3004416.png", 
                    "sizes": "512x512", 
                    "type": "image/png"
                }]
            };
            const stringManifest = JSON.stringify(manifest);
            const blob = new Blob([stringManifest], {type: 'application/manifest+json'});
            const manifestUrl = URL.createObjectURL(blob);
            const link = document.createElement('link');
            link.id = 'pwa-manifest';
            link.rel = 'manifest';
            link.href = manifestUrl;
            window.parent.document.head.appendChild(link);
        }
    </script>
    """
    st.markdown(pwa_html, unsafe_allow_html=True)

ativar_pwa()

# ==========================================
# CHAVES DE ACESSO E CONEXÃO FIREBASE
# ==========================================
CHAVE_GROQ_FIXA = st.secrets.get("GROQ_KEY", st.secrets.get("GROQ_API_KEY", "")) 

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            firebase_secrets = st.secrets["textkey"] 
            schema = dict(firebase_secrets)
            if "private_key" in schema:
                pk = schema["private_key"].strip().replace('"', '').replace("'", "")
                schema["private_key"] = pk.replace("\\n", "\n")
            cred = credentials.Certificate(schema)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao conectar ao Firebase. Verifique se 'textkey' está configurado nos Secrets do Streamlit. Detalhes: {e}")
            st.stop()
    return firestore.client()

db = init_firebase()

for d in ["materiais_estudo", "imagens_flashcards", "fotos_perfil"]:
    if not os.path.exists(d): os.makedirs(d)

# ==========================================
# INICIALIZADOR E EXTRATOR SEGURO DE JSON
# ==========================================
def get_ia_client():
    if "model_ia" not in st.session_state:
        if Groq and CHAVE_GROQ_FIXA:
            try:
                st.session_state.model_ia = Groq(api_key=CHAVE_GROQ_FIXA)
            except Exception as e:
                st.session_state.model_ia = None
                st.error(f"Erro ao conectar IA: {e}")
        else:
            st.session_state.model_ia = None
    return st.session_state.model_ia

def extrair_json_seguro(texto):
    if not texto: return {}
    texto = texto.replace("```json", "")
    texto = texto.replace("```", "")
    texto = texto.strip()
    try:
        return json.loads(texto)
    except:
        try:
            match = re.search(r'(\{.*\})', texto, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except Exception as e:
            st.error("A IA enviou um formato corrompido que não pôde ser limpo.")
            return {}
    return {}

# ==========================================
# CONSTANTES E CORES
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#3b82f6", "Pediatria": "#ec4899", "Ginecologia e Obstetrícia": "#a855f7", "Medicina Preventiva": "#22c55e", "Cirurgia Geral": "#ef4444", "Geral": "#64748b"}

PRIORIDADES = {1: "💎 Azul", 2: "🟩 Verde", 3: "🟨 Amarelo", 4: "🟥 Vermelho", 5: "🟪 Roxo"}

BANCO_IMAGENS_OSCE = {
    "ecg_normal": "https://upload.wikimedia.org/wikipedia/commons/b/b6/12_lead_normal_ECG.png",
    "ecg_infarto_supra": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/12-lead_ECG_showing_inferior_STEMI.png/1024px-12-lead_ECG_showing_inferior_STEMI.png",
    "ecg_fibrilacao_atrial": "https://upload.wikimedia.org/wikipedia/commons/a/a2/Atrial_fibrillation_ecg.png",
    "ecg_taquicardia_ventricular": "https://upload.wikimedia.org/wikipedia/commons/4/41/Ventricular_tachycardia.png",
    "ecg_fibrilacao_ventricular": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/cf/Ventricular_fibrillation_-_lead_II.png/800px-Ventricular_fibrillation_-_lead_II.png",
    "rx_torax_normal": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png",
    "rx_torax_pneumonia": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Pneumonia_Chest_X-ray.jpg",
    "rx_torax_dpoc": "https://upload.wikimedia.org/wikipedia/commons/0/00/Emphysema_chest_x-ray.jpg",
    "rx_torax_edema_agudo": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Pulmonary_edema_chest_X-ray.jpg/800px-Pulmonary_edema_chest_X-ray.jpg",
    "rx_torax_pneumotorax": "https://upload.wikimedia.org/wikipedia/commons/9/98/Pneumothorax.jpg",
    "rx_abdomen_pneumoperitonio": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Pneumoperitoneum.jpg/800px-Pneumoperitoneum.jpg",
    "tc_cranio_avci": "https://upload.wikimedia.org/wikipedia/commons/d/da/Ischemic_stroke_MCA_territory.jpg",
    "tc_cranio_avch": "https://upload.wikimedia.org/wikipedia/commons/3/30/Intracerebral_hemorrhage.jpg",
    "tc_cranio_hsa": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/Subarachnoid_hemorrhage.jpg/800px-Subarachnoid_hemorrhage.jpg",
    "tc_cranio_normal": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Normal_CT_of_the_brain.jpg",
    "usg_fast_positivo": "https://upload.wikimedia.org/wikipedia/commons/5/5a/Morison%27s_pouch_fluid.jpg"
}

def renderizar_mensagem_osce(texto):
    padrao = r"(?i)\[EXAME:\s*([^\]]+)\]"
    partes = re.split(padrao, texto)
    for i, parte in enumerate(partes):
        if i % 2 == 0:
            if parte.strip(): st.write(parte)
        else:
            chave = parte.strip().lower()
            if chave in BANCO_IMAGENS_OSCE:
                img_url = BANCO_IMAGENS_OSCE[chave]
                st.markdown(f"""
                <div style="border: 1px solid #cbd5e1; border-radius: 8px; padding: 10px; margin: 10px 0; background-color: #f8fafc;">
                    <p style="color: #2563eb; font-weight: bold; margin-bottom: 5px;">📎 Laudo Anexo: {chave.replace('_', ' ').title()}</p>
                    <img src="{img_url}" style="width: 100%; border-radius: 5px;">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"*(O paciente entrega um laudo correspondente a {chave}, porém sem imagem disponível no banco)*")

# ==========================================
# BANCO DE DADOS DA CALCULADORA DE DOSES
# ==========================================
MEDICAMENTOS = {
    "Pediatria (Baseado em Peso)": {
        "Acetilcisteína (Mucolítico)": {"dose_fixa": "5 mL", "via": "VO", "obs": "Crianças > 2 anos: Xarope 20mg/mL (5mL), 2 a 3 vezes ao dia."},
        "Adrenalina (Anafilaxia)": {"dose": 0.01, "unidade": "mg/kg", "max": 0.3, "via": "IM", "obs": "0,01 mL/kg da ampola 1:1.000 no vasto lateral."},
        "Adrenalina (PCR)": {"dose": 0.01, "unidade": "mg/kg", "max": 1, "via": "EV / IO", "obs": "0,1 mL/kg da solution 1:10.000 a cada 3-5 minutos."},
        "Amiodarona (PCR)": {"dose": 5, "unidade": "mg/kg", "max": 300, "via": "EV Bolus", "obs": "Dose de ataque em Parada Cardiorrespiratória."},
        "Amoxicilina (OMA/Sinusite)": {"dose": 50, "unidade": "mg/kg/dia", "max": 1500, "via": "VO", "obs": "Dividir em 3 tomadas (8/8h)."},
        "Amoxicilina + Clavulanato": {"dose": 50, "unidade": "mg/kg/dia", "max": 1500, "via": "VO", "obs": "Cálculo pela amoxicilina. Dividir em 2 tomadas (12/12h)."},
        "Atropina (Bradicardia)": {"dose": 0.02, "unidade": "mg/kg", "max": 0.5, "via": "EV", "obs": "Dose mínima: 0,1mg. Dose máxima: 0,5mg."},
        "Azitromicina (Respiratória)": {"dose": 10, "unidade": "mg/kg/dia", "max": 500, "via": "VO", "obs": "Dose única diária por 3 a 5 dias."},
        "Cefalexina (Pele/Partes Moles)": {"dose": 50, "unidade": "mg/kg/dia", "max": 2000, "via": "VO", "obs": "25-50 mg/kg/dia, dividir em 4 tomadas (6/6h)."},
        "Ceftriaxona (Pneumonia/Sepse)": {"dose": 50, "unidade": "mg/kg/dia", "max": 2000, "via": "EV / IM", "obs": "Dividir em 1 ou 2 doses. Meningite: 100mg/kg/dia."},
        "Dexametasona (Crupe/Asma)": {"dose": 0.6, "unidade": "mg/kg", "max": 10, "via": "VO/IM/EV", "obs": "Laringite (Croup): 0,6 mg/kg dose única. Asma: 0,15 a 0,3 mg/kg/dose."},
        "Diazepam (Crise Convulsiva)": {"dose": 0.3, "unidade": "mg/kg", "max": 10, "via": "EV / Retal", "obs": "0,2 a 0,3 mg/kg EV lento (1mg/min) ou via retal."},
        "Dipirona (Febre/Dor)": {"dose": 20, "unidade": "mg/kg", "max": 1000, "via": "VO / EV", "obs": "EV: 15-20 mg/kg/dose a cada 6h. VO: 1 gota/kg."},
        "Escopolamina + Dipirona (Buscopan Comp)": {"dose": 1, "unidade": "gota/kg", "max": 40, "via": "VO", "obs": "1 gota por kg (> 1 ano), até 4 vezes ao dia."},
        "Fenitoína (Ataque Convulsão)": {"dose": 20, "unidade": "mg/kg", "max": 1000, "via": "EV em BIC", "obs": "15-20 mg/kg. NÃO exceder 1mg/kg/min (criança)."},
        "Ferro Profilático (RN Prematuro < 37s)": {"dose": 3, "unidade": "mg/kg/dia", "max": 50, "via": "VO", "obs": "2 a 4 mg/kg/dia. Início com 30 dias até 2 anos."},
        "Ferro Profilático (RN Termo AME)": {"dose": 1, "unidade": "mg/kg/dia", "max": 50, "via": "VO", "obs": "A partir dos 3 meses de vida até os 2 anos."},
        "Furosemida (Diurético)": {"dose": 2, "unidade": "mg/kg", "max": 40, "via": "VO / EV", "obs": "1-2 mg/kg/dose."},
        "Hidrocortisona (Crise Asma)": {"dose": 5, "unidade": "mg/kg", "max": 500, "via": "EV", "obs": "Ataque: 4 a 5 mg/kg. Manutenção: 1-2 mg/kg/dose a cada 6h."},
        "Ibuprofeno (Febre/Dor)": {"dose": 10, "unidade": "mg/kg", "max": 600, "via": "VO", "obs": "5-10 mg/kg/dose (> 6 meses) a cada 8h (com refeições)."},
        "Metilprednisolona": {"dose": 2, "unidade": "mg/kg/dia", "max": 125, "via": "EV", "obs": "1 a 2 mg/kg/dia, dividido em 2 doses (12/12h)."},
        "Metronidazol": {"dose": 7.5, "unidade": "mg/kg", "max": 500, "via": "EV", "obs": "7,5 mg/kg/dose a cada 8h."},
        "Morfina (Dor Intensa)": {"dose": 0.1, "unidade": "mg/kg", "max": 4, "via": "EV Lento", "obs": "0,05 a 0,1 mg/kg/dose EV lento. CUIDADO COM OPIOIDE."},
        "Nitrofurantoína (ITU)": {"dose": 7, "unidade": "mg/kg/dia", "max": 400, "via": "VO", "obs": "Crianças > 1 mês: 5-7 mg/kg/dia, dividir de 6/6h."},
        "Omeprazol / Pantoprazol": {"dose": 1, "unidade": "mg/kg/dia", "max": 40, "via": "EV / VO", "obs": "1 mg/kg/dia em jejum."},
        "Ondansetrona (Zofran)": {"dose": 0.15, "unidade": "mg/kg", "max": 8, "via": "EV", "obs": "0,15 mg/kg/dose EV lento."},
        "Paracetamol (Febre/Dor)": {"dose": 15, "unidade": "mg/kg", "max": 750, "via": "VO", "obs": "10-15 mg/kg/dose a cada 6h. Gotas 200mg/mL: 1 gota/kg."},
        "Prednisolona / Prednisona": {"dose": 2, "unidade": "mg/kg/dia", "max": 60, "via": "VO", "obs": "1 a 2 mg/kg/dia, dose única, por 3 a 5 dias."},
        "Salbutamol (Crise Asmática)": {"dose": 0.33, "unidade": "gota/kg", "max": 15, "via": "NBZ", "obs": "1 gota para cada 3-4 kg (máx 15) + 3-5mL SF 0,9%. Repetir 20/20m."},
        "Soro Fisiológico 0.9% (Choque)": {"dose": 20, "unidade": "mL/kg", "max": 1000, "via": "EV Bolus", "obs": "Correr em 20-30 min. Repetir até 3x se choque persistir."},
        "Tramadol": {"dose": 2, "unidade": "mg/kg", "max": 100, "via": "EV", "obs": "1-2 mg/kg/dose a cada 6-8h."},
        "Vancomicina": {"dose": 60, "unidade": "mg/kg/dia", "max": 2000, "via": "EV", "obs": "40-60 mg/kg/dia dividido de 6-8h. BIC em pelo menos 1h."}
    },
    "Adulto (Doses por Peso E Fixas)": {
        "AAS (SCA)": {"dose_fixa": "150-300 mg", "via": "VO (Mastigar)", "obs": "3 comprimidos infantis de 100mg macerados na boca."},
        "Acetilcisteína (Mucolítico)": {"dose_fixa": "600 mg (15mL)", "via": "VO", "obs": "Xarope 40mg/mL (15mL), 1 vez ao dia."},
        "Ácido Fólico (Gestante)": {"dose_fixa": "5 mg", "via": "VO", "obs": "1 cp/dia. Iniciar 3 meses antes da concepção."},
        "Adenosina (TPSV)": {"dose_fixa": "6 mg", "via": "EV Bolus Rápido", "obs": "Push rápido + flush 20mL SF. Se refratário: 12mg."},
        "Adrenalina (Anafilaxia)": {"dose_fixa": "0.3 a 0.5 mg", "via": "IM", "obs": "No vasto lateral da coxa. Ampola pura (1:1.000)."},
        "Adrenalina (PCR)": {"dose_fixa": "1 mg", "via": "EV Bolus", "obs": "1 ampola pura a cada 3 a 5 minutos na RCP."},
        "Alteplase (AVC Isquêmico)": {"dose": 0.9, "unidade": "mg/kg", "max": 90, "via": "EV", "obs": "10% bolus de 1 min. 90% em BIC por 60 min."},
        "Amiodarona (PCR FV/TV)": {"dose_fixa": "300 mg", "via": "EV Bolus", "obs": "1ª dose (2 ampolas) pura na PCR. 2ª dose: 150mg."},
        "Amiodarona (Taquicardia Estável)": {"dose_fixa": "150 mg", "via": "EV Lento", "obs": "Diluir 1 amp em 100mL SG 5%. Correr em 10 minutos."},
        "Amoxicilina": {"dose_fixa": "500 mg", "via": "VO", "obs": "De 8/8h por 7 dias."},
        "Amoxicilina + Clavulanato": {"dose_fixa": "875 / 125 mg", "via": "VO", "obs": "1 cp de 12/12h por 7 a 10 dias."},
        "Anlodipino (HAS)": {"dose_fixa": "5 a 10 mg", "via": "VO", "obs": "1 a 2x ao dia."},
        "Atenolol (HAS)": {"dose_fixa": "25 a 100 mg", "via": "VO", "obs": "Uma vez ao dia."},
        "Atorvastatina (Dislipidemia)": {"dose_fixa": "40 a 80 mg", "via": "VO", "obs": "Dose única diária. Qualquer hora do dia."},
        "Atropina (Bradicardia)": {"dose_fixa": "0.5 a 1 mg", "via": "EV Bolus", "obs": "Repetir a cada 3-5 min. Máx: 3mg."},
        "Azitromicina": {"dose_fixa": "500 mg", "via": "VO", "obs": "1 cp/dia por 3 a 5 dias."},
        "Bezafibrato (Triglicerídeos)": {"dose_fixa": "200 mg", "via": "VO", "obs": "3 vezes ao dia junto com refeições."},
        "Bicarbonato de Sódio 8.4% (PCR)": {"dose": 1, "unidade": "mEq/kg", "max": 150, "via": "EV", "obs": "Dose inicial: 1 mEq/Kg (1 ml = 1 mEq)."},
        "Buspirona (Ansiedade)": {"dose_fixa": "5 mg", "via": "VO", "obs": "Ansiolítico SUS."},
        "Captopril (HAS Urgência)": {"dose_fixa": "25 a 75 mg", "via": "VO", "obs": "Até 3x ao dia (geralmente 1h antes refeições)."},
        "Carvedilol (ICC/HAS)": {"dose_fixa": "3.125 a 25 mg", "via": "VO", "obs": "1 a 2x ao dia. Aumentar gradualmente."},
        "Cefalexina": {"dose_fixa": "500 mg", "via": "VO", "obs": "De 6/6h por 7 a 14 dias (Pele/ITU)."},
        "Cefepime": {"dose_fixa": "1 a 2 g", "via": "EV", "obs": "A cada 12h. Neutropenia febril: 2g a cada 8h."},
        "Ceftriaxona": {"dose_fixa": "1 a 2 g", "via": "EV / IM", "obs": "A cada 12h ou 24h."},
        "Celecoxibe (AINE)": {"dose_fixa": "200 mg", "via": "VO", "obs": "1 cp de 12/12h."},
        "Cetamina (Indução IOT)": {"dose": 1.5, "unidade": "mg/kg", "max": 200, "via": "EV Bolus", "obs": "Excelente no choque. Cuidado na hipertensão grave."},
        "Cetoprofeno (AINE Injetável)": {"dose_fixa": "100 mg", "via": "EV / IM", "obs": "Diluir em 100mL SF 0,9%, correr em 20 min."},
        "Clonazepam": {"dose_fixa": "0.5 a 2 mg", "via": "VO", "obs": "Comprimidos ou gotas (2.5mg/mL)."},
        "Clopidogrel (SCA)": {"dose_fixa": "300 a 600 mg", "via": "VO", "obs": "Ataque 300mg. 600mg para angioplastia primária."},
        "Dapagliflozina (DM2 / ICC)": {"dose_fixa": "10 mg", "via": "VO", "obs": "Uma vez ao dia (Critérios: HbA1c > 7.5%, > 55 anos)."},
        "Dexametasona": {"dose_fixa": "4 a 10 mg", "via": "VO / IM / EV", "obs": "Laringite, alergias, antiemético."},
        "Diazepam (Convulsão)": {"dose_fixa": "5 a 10 mg", "via": "EV Lento", "obs": "Correr lento (2mg/min)."},
        "Diclofenaco Sódico": {"dose_fixa": "50 a 75 mg", "via": "VO / IM", "obs": "IM: 1 ampola (75mg). VO: 50mg de 8/8h."},
        "Dimenidrinato (Dramin)": {"dose_fixa": "50 mg", "via": "EV / IM / VO", "obs": "Diluir ampola EV para evitar hipotensão."},
        "Dipirona": {"dose_fixa": "500 mg a 1 g", "via": "EV / VO", "obs": "EV diluído em 100mL SF 0.9% em 30min, a cada 6h."},
        "Dobutamina (Choque)": {"dose_fixa": "2 a 20 mcg/kg/min", "via": "BIC", "obs": "1 amp (250mg) + 230mL SG 5%."},
        "Enalapril (HAS)": {"dose_fixa": "10 a 20 mg", "via": "VO", "obs": "1 a 2 tomadas ao dia."},
        "Enoxaparina (Profilaxia TVP)": {"dose_fixa": "40 mg", "via": "SC", "obs": "1x ao dia."},
        "Enoxaparina (Tratamento TVP/TEP)": {"dose": 1, "unidade": "mg/kg", "max": 150, "via": "SC", "obs": "12/12h. Ajustar se ClCr < 30."},
        "Escopolamina + Dipirona (Buscopan)": {"dose_fixa": "1 a 2 cp / 1 amp", "via": "VO / EV", "obs": "De 6/6h para cólicas abdominais. EV Lento."},
        "Espironolactona": {"dose_fixa": "25 a 50 mg", "via": "VO", "obs": "Diurético poupador de potássio. 1-2x ao dia."},
        "Etomidato (Indução IOT)": {"dose": 0.3, "unidade": "mg/kg", "max": 40, "via": "EV Bolus", "obs": "Estabilidade hemodinâmica perfeita."},
        "Ezetimiba (Dislipidemia)": {"dose_fixa": "10 mg", "via": "VO", "obs": "Associado com estatina."},
        "Fenitoína (Ataque Convulsão)": {"dose": 20, "unidade": "mg/kg", "max": 2000, "via": "EV em BIC", "obs": "15-20 mg/kg. MÁX: 50mg/min. Monitorização cardíaca."},
        "Fentanil (Indução/Analgesia)": {"dose": 3, "unidade": "mcg/kg", "max": 300, "via": "EV Lento", "obs": "Dose IOT. Ampola = 50mcg/mL. Causa depressão resp."},
        "Fluoxetina (Depressão)": {"dose_fixa": "20 mg", "via": "VO", "obs": "1x ao dia."},
        "Fosfomicina (ITU)": {"dose_fixa": "3 g (1 envelope)", "via": "VO", "obs": "Dose única diluída em água."},
        "Furosemida": {"dose_fixa": "20 a 40 mg", "via": "EV / VO", "obs": "EV Lento. Pode titular."},
        "Haloperidol (Agitação)": {"dose_fixa": "5 mg", "via": "IM", "obs": "Pode associar com Prometazina."},
        "Heparina Não Fracionada (Ataque)": {"dose": 80, "unidade": "UI/kg", "max": 10000, "via": "EV Bolus", "obs": "Manutenção em BIC a 18 UI/kg/h. Guiar por TTPA."},
        "Hidralazina (HAS Grave)": {"dose_fixa": "50 a 200 mg/dia", "via": "VO", "obs": "Divididos em 2 a 4 tomadas."},
        "Hidroclorotiazida (HAS)": {"dose_fixa": "25 mg", "via": "VO", "obs": "1x ao dia pela manhã."},
        "Hidrocortisona (Asma/Anafilaxia)": {"dose_fixa": "100 a 500 mg", "via": "EV", "obs": "Diluir em 100mL SF, correr em 30 min."},
        "Ibuprofeno": {"dose_fixa": "400 a 600 mg", "via": "VO", "obs": "A cada 8h (com refeições)."},
        "Insulina NPH (Basal)": {"dose": 0.2, "unidade": "UI/kg", "max": 50, "via": "SC", "obs": "Início com 10 UI ou 0.1 a 0.2 UI/kg ao deitar."},
        "Insulina Regular (Cetoacidose)": {"dose_fixa": "0.1 U/kg/h BIC", "via": "EV", "obs": "Ataque 0.1 U/kg EV. Titular pela glicemia capilar."},
        "Ipratrópio (Atrovent)": {"dose_fixa": "40 gotas", "via": "NBZ", "obs": "Em crises graves associar ao Salbutamol."},
        "Levotiroxina (Hipotireoidismo)": {"dose": 1.6, "unidade": "mcg/kg/dia", "max": 200, "via": "VO", "obs": "Em jejum, 30-60 min antes do café."},
        "Losartana (HAS)": {"dose_fixa": "50 a 100 mg", "via": "VO", "obs": "1 ou 2 tomadas."},
        "Metformina (DM2)": {"dose_fixa": "500 a 850 mg", "via": "VO", "obs": "1 a 2x/dia após refeições. Máx 2.550 mg/dia."},
        "Metildopa (HAS Gestante)": {"dose_fixa": "500 a 2000 mg/dia", "via": "VO", "obs": "Divididos em 2 a 4 tomadas. 1ª escolha gestação."},
        "Metilprednisolona (Pulsoterapia/Asma)": {"dose_fixa": "40 a 125 mg", "via": "EV", "obs": "A cada 6 a 12 horas. Pulso: até 1g/dia."},
        "Metimazol (Hipertireoidismo)": {"dose_fixa": "10 a 40 mg/dia", "via": "VO", "obs": "Dose única diária inicial."},
        "Metoprolol (Controle FA)": {"dose_fixa": "5 mg", "via": "EV Lento", "obs": "Em 5 min. Pode repetir cada 5min (Máx 15mg)."},
        "Metronidazol": {"dose_fixa": "500 mg", "via": "EV / VO", "obs": "EV de 8/8h. VO de 12/12h para vaginose (7d)."},
        "Morfina (Dor Intensa)": {"dose_fixa": "2 a 4 mg", "via": "EV Lento", "obs": "Diluído em 9ml SF. Fazer a cada 4h."},
        "Nimesulida (AINE)": {"dose_fixa": "100 mg", "via": "VO", "obs": "1cp de 12/12h."},
        "Nitrofurantoína (ITU)": {"dose_fixa": "100 mg", "via": "VO", "obs": "De 6/6h por 5 a 7 dias com alimento."},
        "Nitroglicerina (Tridil)": {"dose_fixa": "5 a 20 mcg/min", "via": "BIC", "obs": "Diluir 1 amp (50mg) em 240mL SG5%. Não protege da luz."},
        "Norepinefrina (Choque)": {"dose_fixa": "0.05 a 0.5 mcg/kg/min", "via": "BIC", "obs": "Padrão: 5 amp (20mL) + 180mL SF. Titular PAM > 65."},
        "Omeprazol / Pantoprazol": {"dose_fixa": "40 mg", "via": "EV / VO", "obs": "1x ao dia em jejum."},
        "Ondansetrona (Zofran)": {"dose_fixa": "8 mg", "via": "EV Lento", "obs": "Antiemético."},
        "Oseltamivir (Tamiflu)": {"dose_fixa": "75 mg", "via": "VO", "obs": "De 12/12h por 5 dias. Iniciar em 48h."},
        "Paracetamol": {"dose_fixa": "750 mg", "via": "VO", "obs": "A cada 6h (Máx: 4g/dia)."},
        "Piperacilina + Tazobactam (Tazocin)": {"dose_fixa": "4.5 g", "via": "EV", "obs": "De 6/6h. Infusão estendida (4h) na sepse."},
        "Polimixina B": {"dose_fixa": "15.000 a 25.000 U/kg/dia", "via": "EV", "obs": "Divididas de 12/12h. Máx: 2.000.000 U."},
        "Prednisona": {"dose_fixa": "20 a 60 mg/dia", "via": "VO", "obs": "Dose única diária por 5 a 7 dias."},
        "Propiltiouracila (PTU)": {"dose_fixa": "100 a 150 mg", "via": "VO", "obs": "De 8/8h. Escolha no 1º trimestre gestação."},
        "Propofol (Indução IOT)": {"dose": 1.5, "unidade": "mg/kg", "max": 250, "via": "EV Bolus", "obs": "Hipotensor. Evitar em pacientes chocados."},
        "Propranolol (Tremor/HAS)": {"dose_fixa": "10 a 40 mg", "via": "VO", "obs": "De 6/6h ou 8/8h para sintomas adrenérgicos."},
        "Rocurônio (Bloqueador IOT)": {"dose_fixa": "1.2", "unidade": "mg/kg", "max": 150, "via": "EV Bolus", "obs": "Dose de Sequência Rápida de Intubação."},
        "Rosuvastatina (Dislipidemia)": {"dose_fixa": "5 a 40 mg", "via": "VO", "obs": "Dose única diária. Qualquer hora do dia."},
        "Salbutamol (Inalatório)": {"dose_fixa": "10 a 20 gotas", "via": "NBZ", "obs": "Nebulização com 3-5mL SF. Repetir 20/20m."},
        "Sertralina (Depressão)": {"dose_fixa": "25 a 50 mg", "via": "VO", "obs": "1x ao dia."},
        "Sinvastatina (Dislipidemia)": {"dose_fixa": "10 a 40 mg", "via": "VO", "obs": "Dose única diária, OBRIGATÓRIO à noite."},
        "Soro Fisiológico 0.9% (Expansão Adulto)": {"dose_fixa": "500 a 1000 mL", "via": "EV Bolus", "obs": "Correr em 30 a 60 minutos. Reavaliar perfusão."},
        "Succinilcolina (Bloqueador IOT)": {"dose": 1.5, "unidade": "mg/kg", "max": 150, "via": "EV Bolus", "obs": "Contraindicado em hipercalemia."},
        "Sulfato de Magnésio 50% (PCR/Eclâmpsia)": {"dose_fixa": "1 a 2 g", "via": "EV", "obs": "Ampola 10mL = 5g."},
        "Sulfato Ferroso (Gestante)": {"dose_fixa": "40 mg Fe elementar", "via": "VO", "obs": "1cp/dia. Tomar com suco cítrico. Início 20ª sem."},
        "Tenoxicam (AINE)": {"dose_fixa": "20 mg", "via": "VO / EV / IM", "obs": "1x ao dia."},
        "Tramadol": {"dose_fixa": "100 mg", "via": "EV", "obs": "Diluído em 100mL SF, correr em 30 min, a cada 8h."},
        "Vancomicina": {"dose": 15, "unidade": "mg/kg/dose", "max": 2000, "via": "EV", "obs": "A cada 8-12h. Correr em BIC em pelo menos 1h."}
    }
}

# ==========================================
# FUNÇÕES GERAIS E DATA
# ==========================================
def get_agora(): return datetime.utcnow() - timedelta(hours=3)
def hash_senha(senha): return hashlib.sha256(str.encode(senha)).hexdigest()
def is_super_admin(nome): return str(nome).lower().strip() in ['joao', 'joão', 'joao victor']

def parse_data(d):
    if not d: return get_agora().date()
    if isinstance(d, datetime): return d.date()
    if isinstance(d, date): return d
    if isinstance(d, str):
        d_str = d.strip()[:10]
        try:
            if '-' in d_str:
                parts = d_str.split('-')
                if len(parts[0]) == 4: return datetime.strptime(d_str, "%Y-%m-%d").date()
                else: return datetime.strptime(d_str, "%d-%m-%Y").date()
            elif '/' in d_str:
                parts = d_str.split('/')
                if len(parts[0]) == 4: return datetime.strptime(d_str, "%Y/%m/%d").date()
                else: return datetime.strptime(d_str, "%d/%m/%Y").date()
        except: pass
    return get_agora().date()

def formatar_data_br(d):
    if not d: return "-"
    try: return parse_data(d).strftime("%d/%m/%Y")
    except: return "-"

def safe_int(valor):
    try: return int(float(valor)) if valor else 0
    except: return 0

def invalidar_cache():
    st.session_state.pop('dados', None)
    st.session_state.user_data_loaded = False

def limpar_texto(texto):
    if not texto: return "Sem título"
    return re.sub(r'^[A-Za-z0-9_-]{10,40}\s*\|\s*', '', str(texto)).strip()

def get_user_docs(collection_name, user_id):
    try:
        todos_docs = db.collection(collection_name).where("usuario_id", "==", str(user_id)).get()
        return [{"id": d.id, **d.to_dict()} for d in todos_docs]
    except Exception as e:
        return []

def gerar_calendario_html(aulas_lista, ano, mes):
    cal = calendar.monthcalendar(ano, mes)
    aulas_dict = {}
    for a in aulas_lista:
        d = parse_data(a.get('data_aula'))
        if d.year == ano and d.month == mes: aulas_dict.setdefault(d.day, []).append(a)
        
    html_code = "<div style='background-color:#e0f2fe; padding:15px; border-radius:10px; margin-bottom:20px;'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:5px; color:#0f172a; background-color: transparent !important; border: none !important;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += "<td style='border:1px solid #bae6fd; padding:10px; background-color:#f0f9ff !important;'></td>"
            else:
                if day in aulas_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(a.get('area'), '#64748b')}; color:white !important; padding:2px 4px; border-radius:4px; font-size:10px; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{html.escape(limpar_texto(a.get('tema', '')))}'>{html.escape(limpar_texto(a.get('tema', '')))}</div>" for a in aulas_dict[day]])
                    html_code += f"<td style='border:1px solid #bae6fd; padding:5px; background-color:#ffffff !important; vertical-align:top; height:80px;'><strong style='color:#0f172a !important;'>{day}</strong><div style='margin-top:5px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid #bae6fd; padding:5px; background-color:#ffffff !important; vertical-align:top; height:80px;'><strong style='color:#64748b !important;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

def gerar_calendario_revisoes_html(revisoes_lista, ano, mes):
    cal = calendar.monthcalendar(ano, mes)
    revs_dict = {}
    for r in revisoes_lista:
        d = parse_data(r.get('data_agendada_obj') if 'data_agendada_obj' in r else r.get('data_agendada'))
        if d and d.year == ano and d.month == mes: revs_dict.setdefault(d.day, []).append(r)
        
    html_code = "<div style='background-color:#e0f2fe; padding:15px; border-radius:10px; margin-bottom:25px;'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:5px; color:#0f172a; background-color: transparent !important; border: none !important;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += "<td style='border:1px solid #bae6fd; padding:10px; background-color:#f0f9ff !important;'></td>"
            else:
                if day in revs_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(r.get('area'), '#64748b')}; color:white !important; padding:2px 4px; border-radius:4px; font-size:10px; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;' title='{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})'>{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})</div>" for r in revs_dict[day]])
                    html_code += f"<td style='border:1px solid #bae6fd; padding:5px; background-color:#ffffff !important; vertical-align:top; height:80px;'><strong style='color:#0f172a !important;'>{day}</strong><div style='margin-top:5px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid #bae6fd; padding:5px; background-color:#ffffff !important; vertical-align:top; height:80px;'><strong style='color:#64748b !important;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

# ==========================================
# GESTÃO DE LOGIN E SEGURANÇA
# ==========================================
if 'logado' not in st.session_state: 
    st.session_state.logado = False
    st.session_state.user_id = None
    st.session_state.user_nome = ""

saved_token = None
if hasattr(st, "context") and hasattr(st.context, "cookies"):
    saved_token = st.context.cookies.get("mr_token")
if not saved_token and cookie_controller:
    try: saved_token = cookie_controller.get("mr_token")
    except: pass

if not st.session_state.logado and saved_token:
    try:
        todos_usuarios = db.collection("usuarios").get()
        for doc in todos_usuarios:
            if doc.to_dict().get("token_sessao") == saved_token:
                st.session_state.logado = True
                st.session_state.user_id = doc.id
                st.session_state.user_nome = doc.to_dict().get('nome', '')
                st.rerun()
    except: pass 

if not st.session_state.logado:
    st.title("🏥 Residência PRO")
    aba_l, aba_c = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
    with aba_l:
        if cookie_controller is None: st.warning("⚠️ Biblioteca 'streamlit-cookies-controller' não detectada.")
        with st.form("login_form"):
            u, p, lembrar = st.text_input("Usuário"), st.text_input("Senha", type="password"), st.checkbox("Manter-me conectado")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                try:
                    logou = False
                    for doc in db.collection("usuarios").get():
                        if doc.to_dict().get("nome") == u and doc.to_dict().get("senha") == hash_senha(p):
                            st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                            logou = True
                            if lembrar and cookie_controller:
                                novo_token = str(uuid.uuid4())
                                db.collection("usuarios").document(doc.id).update({"token_sessao": novo_token})
                                cookie_controller.set('mr_token', novo_token, max_age=30*24*60*60, path='/')
                                time.sleep(1.5)
                            st.rerun()
                    if not logou: st.error("Usuário ou senha incorretos.")
                except Exception as e: st.error(f"🚨 Erro no Firebase: {e}")
    with aba_c:
        with st.form("cadastro_form"):
            nu, np = st.text_input("Novo Usuário"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar", use_container_width=True):
                if db.collection("usuarios").where("nome", "==", nu).get(): st.error("Usuário já existe.")
                else:
                    db.collection("usuarios").add({"nome": nu, "senha": hash_senha(np), "tema_modo": "Escuro"})
                    st.success("Conta criada! Faça login.")

# ==========================================
# APLICATIVO LOGADO
# ==========================================
else:
    u_id, hoje = str(st.session_state.user_id), get_agora().date()
    
    if 'dados' not in st.session_state:
        st.session_state.dados = {
            "aulas": [], "revisoes": [], "flashcards": [], 
            "questoes": [], "simulados": [], "focus": [], 
            "materiais": [], "cronogramas": []
        }

    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Sincronizando e Restaurando banco de dados..."):
            try:
                user_doc = db.collection("usuarios").document(u_id).get()
                st.session_state.user_settings = user_doc.to_dict() if user_doc.exists else {}
                
                aulas_recuperadas = get_user_docs("aulas", u_id)
                revisoes_recuperadas = get_user_docs("revisoes", u_id)
                
                revisoes_existentes = set()
                for r in revisoes_recuperadas:
                    revisoes_existentes.add((str(r.get("aula_id")), str(r.get("ciclo"))))

                batch = db.batch()
                novas_revisoes = []
                ciclos_padrao = {"R1":1, "R7":7, "R15":15, "R30":30, "R90":90, "R180":180, "R360":360}

                for aula in aulas_recuperadas:
                    aula_id = str(aula["id"])
                    data_aula_str = aula.get("data_aula")
                    if not data_aula_str: continue

                    d = parse_data(data_aula_str) 
                    for c, dias in ciclos_padrao.items():
                        if (aula_id, c) not in revisoes_existentes:
                            doc_ref = db.collection("revisoes").document()
                            nova_rev = {"usuario_id": u_id, "aula_id": aula_id, "ciclo": c, "data_agendada": str(d + timedelta(days=dias)), "status": "Pendente"}
                            batch.set(doc_ref, nova_rev)
                            novas_revisoes.append({"id": doc_ref.id, **nova_rev})

                if novas_revisoes:
                    batch.commit()
                    revisoes_recuperadas.extend(novas_revisoes)

                st.session_state.dados = {
                    "aulas": aulas_recuperadas,
                    "revisoes": revisoes_recuperadas,
                    "flashcards": get_user_docs("flashcards", u_id),
                    "questoes": get_user_docs("questoes_sessoes", u_id),
                    "simulados": get_user_docs("simulados", u_id),
                    "focus": get_user_docs("focus_sessoes", u_id),
                    "materiais": get_user_docs("materiais", u_id),
                    "cronogramas": get_user_docs("cronogramas", u_id)
                }
                
                if 'model_ia' not in st.session_state: 
                    st.session_state.model_ia = get_ia_client()
                
                st.session_state.user_data_loaded = True 
            except Exception as e:
                st.error(f"🚨 Falha de conexão: {str(e)}")
                st.stop()

    user_settings = st.session_state.user_settings
    
    _dados_cache = st.session_state.get("dados", {})
    dados_aulas = _dados_cache.get("aulas", [])
    mapa_aulas = {str(a["id"]).strip(): a for a in dados_aulas} 
    dados_revisoes = _dados_cache.get("revisoes", [])
    dados_questoes = _dados_cache.get("questoes", [])
    dados_flashcards = _dados_cache.get("flashcards", [])
    dados_simulados = _dados_cache.get("simulados", [])
    dados_focus = _dados_cache.get("focus", [])
    dados_materiais = _dados_cache.get("materiais", [])
    dados_cronogramas = _dados_cache.get("cronogramas", [])

    modo = user_settings.get("tema_modo", "Escuro")
    
    # CSS DINÂMICO E SEGURO
    if modo == "Escuro":
        bg_color = "#0e1117"
        text_color = "#f8fafc"
        metric_bg = "#1e293b"
        metric_border = "#334155"
        sidebar_bg = "#11151c"
        input_bg = "#1e293b"
        menu_text = "#94a3b8"
        menu_hover = "#334155"
        bg_tabela = "#1e293b"
        cor_texto_tabela = "#f8fafc"
    else:
        bg_color = "#f8f9fa"
        text_color = "#0f172a"
        metric_bg = "#ffffff"
        metric_border = "#cbd5e1"
        sidebar_bg = "#ffffff"
        input_bg = "#ffffff"
        menu_text = "#64748b"
        menu_hover = "#f1f5f9"
        bg_tabela = "#f1f5f9" # Cinza claro para tabela como pedido
        cor_texto_tabela = "#0f172a"

    css_fix = f"""
    <style>
    /* FUNDO GERAL E TEXTO */
    .stApp, [data-testid="stAppViewContainer"], .main {{ background-color: {bg_color} !important; }}
    h1:not(#tmr), h2, h3, h4, h5, h6, p, span, label, div {{ color: {text_color}; }}
    
    /* TODOS OS BOTÕES EM AZUL */
    .stButton>button, button[kind="primary"], button[kind="secondary"], button[data-testid="baseButton-secondary"], div[data-testid="stFormSubmitButton"] > button {{ 
        background-color: #2563eb !important; 
        color: white !important; 
        border: none !important; 
        font-weight: bold !important; 
        border-radius: 6px !important; 
    }} 
    .stButton>button p, button[kind="primary"] p, button[kind="secondary"] p, button[data-testid="baseButton-secondary"] p, div[data-testid="stFormSubmitButton"] > button p {{
        color: white !important;
    }}
    
    /* CORRECAO DAS CAIXAS DE INTERAÇÃO E CHAT */
    div[data-baseweb="input"] > div, div[data-baseweb="textarea"] > div, div[data-baseweb="select"] > div, [data-testid="stChatInput"] > div {{
        background-color: {input_bg} !important;
        border: 1px solid {metric_border} !important;
    }}
    input, textarea, div[data-baseweb="select"] span {{
        color: {text_color} !important;
        -webkit-text-fill-color: {text_color} !important;
    }}
    
    /* O SEGREDO PARA AS OPÇÕES DO SELECTBOX NÃO SUMIREM */
    [data-baseweb="popover"] > div, ul[data-baseweb="menu"] {{
        background-color: {input_bg} !important;
        border: 1px solid {metric_border} !important;
    }}
    ul[data-baseweb="menu"] li {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    ul[data-baseweb="menu"] li:hover {{
        background-color: {menu_hover} !important;
    }}
    
    /* TABELAS COM FUNDO CINZA (st.dataframe e st.table) */
    [data-testid="stDataFrame"] > div, [data-testid="stTable"] {{
        background-color: {bg_tabela} !important;
    }}
    th, td {{
        background-color: {bg_tabela} !important;
        color: {cor_texto_tabela} !important;
        border: 1px solid {metric_border} !important;
    }}
    
    /* ABAS (TABS) - Texto visível */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {{
        color: {text_color} !important;
    }}
    
    /* EXPANDERS E CONTAINERS */
    div[data-testid='stExpander'] {{ border: 1px solid {metric_border} !important; background-color: {metric_bg} !important; border-radius: 8px; }} 
    div[data-testid="metric-container"] {{ background-color: {metric_bg} !important; border: 1px solid {metric_border} !important; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
    
    /* FOTO DE PERFIL E MENU LATERAL */
    .profile-img {{ border-radius: 50%; object-fit: cover; border: 3px solid #2563eb; width: 120px; height: 120px; display: block; margin: 0 auto; }}
    
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {metric_border} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: 12px 16px; border-radius: 12px; margin-bottom: 4px; background-color: transparent; transition: all 0.2s ease; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background-color: {menu_hover} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label p {{ color: {menu_text} !important; font-weight: 500; font-size: 16px; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background-color: #2563eb !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: white !important; font-weight: 600 !important; }}
    </style>
    """
    st.markdown(css_fix, unsafe_allow_html=True)

    if user_settings.get('foto_perfil') and os.path.exists(user_settings['foto_perfil']):
        st.sidebar.markdown(f'<img src="data:image/jpeg;base64,{base64.b64encode(open(user_settings["foto_perfil"], "rb").read()).decode("utf-8")}" class="profile-img">', unsafe_allow_html=True)
        st.sidebar.markdown(f"<h3 style='text-align: center; margin-top: 10px;'>{st.session_state.user_nome}</h3>", unsafe_allow_html=True)
    else: st.sidebar.title(f"👤 {st.session_state.user_nome}")

    st.sidebar.markdown("---")
    if st.sidebar.button("Sair da Conta"):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        st.session_state.clear()
        st.rerun()

    # ==========================================
    # MENU REORGANIZADO
    # ==========================================
    opcoes_menu = [
        "🏠 Dashboard",
        "🗓️ Cronograma IA",
        "🎯 Questões",
        "📚 Registro de Aulas",
        "📅 Agenda de Revisões",
        "✨ AI Tutor & Flashcards",
        "📁 Materiais e Simulados",
        "🏥 Simulados & OSCE",
        "📍 GPS da Aprovação",
        "⏱️ Modo Foco",
        "🧮 Calculadora de Doses",
        "⚙️ Configurações",
        "📱 Instalar App"
    ]
    
    if is_super_admin(st.session_state.user_nome): 
        opcoes_menu.append("👑 Admin")
        
    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ==========================================
    # TELAS DO MENU
    # ==========================================
    if menu == "📱 Instalar App":
        st.header("Transforme o sistema em um Aplicativo Nativo")
        col1, col2 = st.columns(2)
        with col1: st.subheader("🤖 No Android (Chrome)"); st.markdown("1. Toque nos **3 pontinhos**.\n2. Selecione **Adicionar à tela inicial**.\n3. Confirme.")
        with col2: st.subheader("🍎 No iPhone (Safari)"); st.markdown("1. Toque no botão **Compartilhar**.\n2. Selecione **Adicionar à Tela de Início**.\n3. Confirme.")

    # -------------------------------------------------------------------------
    # TELA: CRONOGRAMA INTELIGENTE 
    # -------------------------------------------------------------------------
    elif menu == "🗓️ Cronograma IA":
        st.header("Cronograma Inteligente da Semana")
        
        aba_lista, aba_importar = st.tabs(["✅ Minhas Metas", "📸 Adicionar Cronograma"])
        
        with aba_importar:
            nome_semana = st.text_input("Qual é o nome desta semana? (Ex: Semana 1, Reta Final)")
            col_btn, col_arq = st.columns(2)
            
            colagem_img = None
            with col_btn:
                st.markdown("### 📋 Colar Print Direto")
                st.caption("Você pode copiar (Ctrl+C) seu print e clicar no botão azul abaixo para colar (Ctrl+V).")
                if paste_image_button is not None:
                    paste_result = paste_image_button(
                        label="CLIQUE AQUI E APERTE Ctrl+V",
                        background_color="#2563eb",
                        hover_background_color="#1d4ed8"
                    )
                    if paste_result.image_data is not None:
                        colagem_img = paste_result.image_data
                        st.success("✅ Imagem colada e pronta para extração!")
                        st.image(colagem_img, use_container_width=True)
                else:
                    st.warning("⚠️ Para habilitar o botão de colar mágico, por favor, adicione a linha `streamlit-paste-button` no arquivo `requirements.txt` do seu GitHub.")
                    
            with col_arq:
                st.markdown("### 📂 Enviar Arquivos Tradicional")
                st.caption("Prefere anexar os arquivos? Solte eles aqui.")
                imgs_crono = st.file_uploader("Selecione os arquivos", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")
            
            st.divider()
            
            if (imgs_crono or colagem_img) and nome_semana and st.button("🪄 Extrair Metas com IA", use_container_width=True):
                client_ia = get_ia_client()
                if not client_ia:
                    st.error("IA não conectada. Configure a GROQ_KEY nos Secrets.")
                else:
                    with st.spinner("Visão Computacional analisando cores e metas... Isso pode levar alguns segundos."):
                        try:
                            prompt_visao = """Analise estes prints de cronograma. Extraia todos os dias, as matérias e os temas a serem estudados.
                            MUITO IMPORTANTE: Observe a COR de cada aula/marcação no print e atribua uma "prioridade" (número de 1 a 5) com base na seguinte regra exata:
                            - Se a cor for Azul (Diamante), prioridade = 1
                            - Se a cor for Verde, prioridade = 2
                            - Se a cor for Amarelo, prioridade = 3
                            - Se a cor for Vermelho, prioridade = 4
                            - Se a cor for Roxo, prioridade = 5
                            Se não tiver cor clara ou você não tiver certeza, use 3.
                            Você DEVE retornar APENAS um JSON estrito contendo uma chave "tarefas" com uma lista de dicionários, sem nenhum texto ou explicação adicional:
                            {"tarefas": [{"dia": "Segunda-feira", "materia": "Ginecologia", "tema": "Sangramento Uterino", "prioridade": 1}]}"""
                            
                            conteudo_api = [{"type": "text", "text": prompt_visao}]
                            
                            if imgs_crono:
                                for img in imgs_crono:
                                    img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                    conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
                            
                            if colagem_img:
                                buffered = io.BytesIO()
                                colagem_img.save(buffered, format="PNG")
                                img_b64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
                                conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
                            
                            resposta = client_ia.chat.completions.create(
                                model=MODELO_VISAO, 
                                messages=[{"role": "user", "content": conteudo_api}], 
                                temperature=0.1
                            )
                            
                            texto_json = resposta.choices[0].message.content
                            dados_extraidos = extrair_json_seguro(texto_json)
                            tarefas = dados_extraidos.get("tarefas", [])
                            
                            if not tarefas:
                                st.warning("A IA processou a imagem, mas não encontrou tarefas no formato esperado.")
                            else:
                                batch = db.batch()
                                for t in tarefas:
                                    doc_ref = db.collection("cronogramas").document()
                                    batch.set(doc_ref, {
                                        "usuario_id": u_id,
                                        "semana": nome_semana,
                                        "dia": t.get("dia", "Geral"),
                                        "materia": t.get("materia", ""),
                                        "tema": t.get("tema", ""),
                                        "prioridade": safe_int(t.get("prioridade", 3)),
                                        "concluido": False,
                                        "data_importacao": str(hoje),
                                        "data_conclusao": None
                                    })
                                batch.commit()
                                
                                st.success(f"✅ {len(tarefas)} aulas importadas com sucesso! Vá para a aba 'Minhas Metas'.")
                                invalidar_cache()
                                time.sleep(2)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro na leitura da imagem. Detalhes: {e}")

        with aba_lista:
            meu_crono = dados_cronogramas
            semanas_unicas = sorted(list(set([c.get("semana", "Semana Geral") for c in meu_crono])))
            
            if not meu_crono:
                st.info("Você ainda não tem nenhum cronograma. Vá na aba 'Adicionar Cronograma' para começar!")
            
            for sem in semanas_unicas:
                st.write("---")
                col_titulo, col_del_sem = st.columns([0.7, 0.3])
                with col_titulo:
                    st.subheader(f"📂 {sem}")
                with col_del_sem:
                    if st.button("🗑️ Excluir Semana Toda", key=f"del_sem_{sem}"):
                        batch = db.batch()
                        for t_del in [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]:
                            batch.delete(db.collection("cronogramas").document(t_del['id']))
                        batch.commit()
                        invalidar_cache()
                        st.rerun()

                tarefas_semana = [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]
                
                pendentes = [c for c in tarefas_semana if not c.get("concluido", False)]
                concluidos = [c for c in tarefas_semana if c.get("concluido", False)]
                
                pendentes.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
                
                if pendentes:
                    st.write("Dê um 'check' assim que assistir. Você pode alterar a prioridade manualmente se a IA errar a cor:")
                    for t in pendentes:
                        with st.container(border=True):
                            col1, col2, col3, col4 = st.columns([0.1, 0.55, 0.25, 0.1])
                            with col1:
                                if st.button("✔️", key=f"btn_{t['id']}", help="Marcar Concluída"):
                                    db.collection("cronogramas").document(t['id']).update({
                                        "concluido": True,
                                        "data_conclusao": str(get_agora().date())
                                    })
                                    invalidar_cache()
                                    st.rerun()
                            with col2:
                                st.markdown(f"**{t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
                            with col3:
                                p_val = safe_int(t.get('prioridade', 3))
                                novo_p = st.selectbox(
                                    "Prioridade",
                                    options=[1, 2, 3, 4, 5],
                                    format_func=lambda x: PRIORIDADES.get(x, "🟨 Amarelo"),
                                    index=[1, 2, 3, 4, 5].index(p_val) if p_val in [1, 2, 3, 4, 5] else 2,
                                    key=f"pri_{t['id']}",
                                    label_visibility="collapsed"
                                )
                                if novo_p != p_val:
                                    db.collection("cronogramas").document(t['id']).update({"prioridade": novo_p})
                                    invalidar_cache()
                                    st.rerun()
                            with col4:
                                if st.button("🗑️", key=f"del_p_{t['id']}", help="Excluir Aula"):
                                    db.collection("cronogramas").document(t['id']).delete()
                                    invalidar_cache()
                                    st.rerun()
                else:
                    st.success("🎉 Nenhuma aula pendente nesta semana!")

                if concluidos:
                    st.divider()
                    with st.expander(f"✅ Histórico de Aulas Assistidas ({len(concluidos)})"):
                        st.caption("Aulas concluídas e salvas no histórico.")
                        for t in reversed(concluidos):
                            col_a, col_b, col_c = st.columns([0.7, 0.2, 0.1])
                            data_c = formatar_data_br(t.get('data_conclusao', ''))
                            p_val = safe_int(t.get('prioridade', 3))
                            p_icon = PRIORIDADES.get(p_val, "🟨 Amarelo")
                            
                            col_a.markdown(f"~~[{p_icon}] {t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~ *(Assistida em: {data_c})*")
                            with col_b:
                                if st.button("Desfazer", key=f"undo_{t['id']}"):
                                    db.collection("cronogramas").document(t['id']).update({
                                        "concluido": False,
                                        "data_conclusao": None
                                    })
                                    invalidar_cache()
                                    st.rerun()
                            with col_c:
                                if st.button("🗑️", key=f"del_c_{t['id']}", help="Excluir Definitivamente"):
                                    db.collection("cronogramas").document(t['id']).delete()
                                    invalidar_cache()
                                    st.rerun()

    # ==========================================
    # 🧮 CALCULADORA E OUTRAS ABAS
    # ==========================================
    elif menu == "🧮 Calculadora de Doses":
        st.header("Calculadora Avançada (Diretrizes Nacionais)")
        aba_doses, aba_holliday, aba_obstetricia = st.tabs(["💊 Doses e Condutas", "💧 Hidratação", "🤰 Obstetrícia"])
        with aba_doses:
            col_tipo, col_peso = st.columns(2)
            tipo_paciente = col_tipo.radio("Perfil:", ["Pediatria (Baseado em Peso)", "Adulto (Doses por Peso E Fixas)"])
            peso = col_peso.number_input("Peso do Paciente (kg)", min_value=0.5, value=70.0 if "Adulto" in tipo_paciente else 15.0, step=0.5)
            farmaco = st.selectbox("🔎 Busque a Medicação:", options=sorted(list(MEDICAMENTOS[tipo_paciente].keys())), index=None)
            if farmaco:
                dados = MEDICAMENTOS[tipo_paciente][farmaco]
                st.divider(); st.subheader("📊 Prescrição")
                if 'dose' in dados: 
                    dose_final = min(peso * dados['dose'], dados.get('max', float('inf')))
                    st.markdown(f"**Dose de Diretriz:** `{dados['dose']} {dados['unidade']}`")
                    st.markdown(f"### ➡️ Dose Prescrita: `{dose_final:.1f} mg`")
                elif 'dose_fixa' in dados: 
                    st.markdown(f"### ➡️ Dose Padrão/Ataque: `{dados['dose_fixa']}`")
                st.success(f"**Preparo:** {dados['obs']}")
        with aba_holliday:
            peso_h = st.number_input("Peso da Criança (kg)", min_value=0.5, value=12.0)
            v = peso_h * 100 if peso_h <= 10 else (1000 + (peso_h-10)*50 if peso_h <= 20 else 1500 + (peso_h-20)*20)
            st.info(f"Volume em 24h: **{v:.0f} mL**")
        with aba_obstetricia:
            dum = st.date_input("DUM (Data da Última Menstruação)", format="DD/MM/YYYY")
            dias_g = (hoje - dum).days
            st.success(f"**Idade Gestacional:** {dias_g // 7} semanas e {dias_g % 7} dias.")

    elif menu == "📍 GPS da Aprovação":
        st.header("GPS da Aprovação")
        alvo = st.selectbox("🎯 Especialidade Foco?", ["Medicina Intensiva", "Clínica Médica", "Anestesiologia", "Cardiologia"])
        if dados_simulados:
            notas = [float(s.get('minha_nota', 0)) for s in dados_simulados]
            st.metric("Sua Média", f"{sum(notas)/len(notas):.1f}%")

    elif menu == "🏠 Dashboard":
        st.header("Painel de Desempenho Global")
        qs_sess_all = [dict(q) for q in dados_questoes]
        qs_revs_all = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        
        aba_geral, aba_detalhada = st.tabs(["📊 Resumo Geral", "📈 Análise por Matéria"])
        with aba_geral:
            t_acertos_g = sum(safe_int(q.get('acertos')) for q in qs_sess_all) + sum(safe_int(r.get('acertos')) for r in qs_revs_all)
            t_erros_g = sum(safe_int(q.get('erros')) for q in qs_sess_all) + sum(safe_int(r.get('erros')) for r in qs_revs_all)
            t_questoes_g = t_acertos_g + t_erros_g
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões Totais", t_questoes_g)
            c2.metric("🟢 Acertos", t_acertos_g)
            c3.metric("🔴 Erros", t_erros_g)
            c4.metric("🎯 Taxa de Acerto", f"{(t_acertos_g / t_questoes_g * 100) if t_questoes_g > 0 else 0:.1f}%")
            
            st.divider()
            col_g1, col_g2 = st.columns([1, 1.5])
            with col_g1:
                if t_questoes_g > 0: 
                    fig_pie1 = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_g, t_erros_g], hole=0.6, color_discrete_sequence=["#2563eb", '#ef4444'])
                    fig_pie1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie1, use_container_width=True)
            with col_g2:
                todas_questoes_grafico = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_sess_all] + [{"area": r.get('area_aula'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in qs_revs_all]
                df_r = pd.DataFrame(todas_questoes_grafico).dropna(subset=['area'])
                if not df_r.empty:
                    df_g = df_r.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_g['Taxa'] = (df_g['acertos'] / (df_g['acertos'] + df_g['erros'])) * 100
                    fig_bar1 = px.bar(df_g.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS)
                    fig_bar1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False)
                    st.plotly_chart(fig_bar1, use_container_width=True)

        with aba_detalhada:
            filtro_dash = st.selectbox("Selecione a Especialidade para analisar:", AREAS_MED)
            qs_sess_f = [q for q in qs_sess_all if q.get('area') == filtro_dash]
            qs_revs_f = [r for r in qs_revs_all if r.get('area_aula') == filtro_dash]
            t_acertos_f = sum(safe_int(q.get('acertos')) for q in qs_sess_f) + sum(safe_int(r.get('acertos')) for r in qs_revs_f)
            t_erros_f = sum(safe_int(q.get('erros')) for q in qs_sess_f) + sum(safe_int(r.get('erros')) for r in qs_revs_f)
            t_questoes_f = t_acertos_f + t_erros_f
            
            c1_f, c2_f, c3_f = st.columns(3)
            c1_f.metric(f"Questões ({filtro_dash})", t_questoes_f)
            c2_f.metric("🟢 Acertos", t_acertos_f)
            c3_f.metric("🎯 Aproveitamento", f"{(t_acertos_f / t_questoes_f * 100) if t_questoes_f > 0 else 0:.1f}%")

    elif menu == "📅 Agenda de Revisões":
        st.header("Organizador de Ciclos")
        aba_pendentes, aba_historico = st.tabs(["📝 Pendentes", "✅ Histórico"])
        
        with aba_pendentes:
            c_v, c_o = st.columns(2)
            visao = c_v.radio("Filtro Rápido:", ["📆 Hoje/Atrasadas", "🗓️ Próximos 7 Dias", "♾️ Todas", "🔎 Escolher Data Específica"], horizontal=True)
            ordem = c_o.radio("Prioridade:", ["🚨 Urgência", "🆕 Mais Atuais", "🕰️ Mais Antigas"], horizontal=True)
            
            data_filtro_exata = None
            if visao == "🔎 Escolher Data Específica": data_filtro_exata = st.date_input("Filtrar e exibir lista apenas para o dia:", hoje, format="DD/MM/YYYY")
            
            todas_pendentes = []
            for r_orig in dados_revisoes:
                if str(r_orig.get('status', '')).lower() not in ['pendente', 'pendentes']: continue
                aula_id_limpo = str(r_orig.get('aula_id', '')).strip()
                if aula_id_limpo in mapa_aulas:
                    r = dict(r_orig)
                    r['data_agendada_obj'] = parse_data(r.get('data_agendada'))
                    aula = mapa_aulas[aula_id_limpo]
                    r['tema'] = limpar_texto(aula.get('tema', 'Sem título'))
                    r['area'] = aula.get('area', 'Geral')
                    r['data_aula_obj'] = parse_data(aula.get('data_aula'))
                    todas_pendentes.append(r)
            
            if 'cal_mes_revs' not in st.session_state: st.session_state.cal_mes_revs = hoje.month
            if 'cal_ano_revs' not in st.session_state: st.session_state.cal_ano_revs = hoje.year
            nav_r1, nav_r2, nav_r3 = st.columns([1,2,1])
            with nav_r1:
                if st.button("⬅️ Mês Anterior", key="prev_rev"):
                    if st.session_state.cal_mes_revs == 1: st.session_state.cal_mes_revs, st.session_state.cal_ano_revs = 12, st.session_state.cal_ano_revs - 1
                    else: st.session_state.cal_mes_revs -= 1
                    st.rerun()
            with nav_r2: st.markdown(f"<h3 style='text-align:center; margin:0;'>📅 {MESES_PT[st.session_state.cal_mes_revs]} {st.session_state.cal_ano_revs}</h3>", unsafe_allow_html=True)
            with nav_r3:
                if st.button("Próximo Mês ➡️", key="next_rev"):
                    if st.session_state.cal_mes_revs == 12: st.session_state.cal_mes_revs, st.session_state.cal_ano_revs = 1, st.session_state.cal_ano_revs + 1
                    else: st.session_state.cal_mes_revs += 1
                    st.rerun()

            st.markdown(gerar_calendario_revisoes_html(todas_pendentes, st.session_state.cal_ano_revs, st.session_state.cal_mes_revs), unsafe_allow_html=True)
            st.divider()

            if visao == "🔎 Escolher Data Específica" and data_filtro_exata:
                lista_pendentes = [r for r in todas_pendentes if r['data_agendada_obj'] == data_filtro_exata]
            else:
                lista_pendentes = [r for r in todas_pendentes if not (visao == "📆 Hoje/Atrasadas" and r['data_agendada_obj'] > hoje) and not (visao == "🗓️ Próximos 7 Dias" and r['data_agendada_obj'] > (hoje + timedelta(days=7)))]
            
            if "Atuais" in ordem: lista_pendentes.sort(key=lambda x: x['data_aula_obj'], reverse=True)
            elif "Antigas" in ordem: lista_pendentes.sort(key=lambda x: x['data_aula_obj'])
            else: lista_pendentes.sort(key=lambda x: x['data_agendada_obj'])

            if not lista_pendentes: st.success("🎉 Tudo em dia para os filtros selecionados!")
            for r in lista_pendentes:
                with st.container(border=True):
                    st.markdown(f"<span style='color:{CORES_AREAS.get(r['area'], '#64748b')};'>⬤</span> **{r['tema']}** ({r.get('ciclo','')}) - Alvo: {formatar_data_br(r['data_agendada_obj'])}", unsafe_allow_html=True)
                    with st.expander("Concluir"):
                        with st.form(f"f_{r['id']}", clear_on_submit=True):
                            col1, col2, col3 = st.columns(3)
                            q = col1.number_input("Questões", 0)
                            e = col2.number_input("Erros", 0, max_value=max(q,0))
                            f = col3.number_input("Flashcards", 0)
                            if st.form_submit_button("✅ Marcar Concluída"):
                                db.collection("revisoes").document(r['id']).update({"status": "Concluída", "questoes_feitas": q, "erros": e, "acertos": q-e, "flashcards_feitas": f, "data_conclusao": str(get_agora().date())})
                                invalidar_cache(); st.rerun()

        with aba_historico:
            conc_docs = [d for d in dados_revisoes if str(d.get('status', '')).lower() in ["concluída", "concluida"] and str(d.get('aula_id', '')).strip() in mapa_aulas]
            if conc_docs:
                dados_h = []
                for d in conc_docs:
                    aula_id = str(d.get('aula_id', '')).strip()
                    tema = limpar_texto(mapa_aulas.get(aula_id, {}).get('tema', 'Sem título'))
                    acertos, erros, questoes = safe_int(d.get('acertos')), safe_int(d.get('erros')), safe_int(d.get('questoes_feitas'))
                    if questoes == 0 and (acertos > 0 or erros > 0): questoes = acertos + erros
                    dados_h.append({"ID": d['id'], "Conclusão": d.get('data_conclusao'), "Tema": tema, "Ciclo": d.get('ciclo'), "Questões": questoes, "Acertos": acertos, "Erros": erros, "Cards": safe_int(d.get('flashcards_feitas'))})
                
                df_h = pd.DataFrame(dados_h)
                df_h['Conclusão_dt'] = pd.to_datetime(df_h['Conclusão'], errors='coerce')
                df_h = df_h.dropna(subset=['Conclusão_dt']) 
                
                if not df_h.empty:
                    df_ag = df_h.groupby("Conclusão_dt")[['Acertos', 'Erros', 'Cards']].sum().reset_index()
                    df_ag["Data"] = df_ag["Conclusão_dt"].dt.strftime('%d/%m/%Y')
                    c1g, c2g = st.columns(2)
                    with c1g: 
                        fig1 = px.bar(df_ag, x="Data", y=["Acertos", "Erros"], barmode="group", color_discrete_map={"Acertos":"#22c55e", "Erros":"#ef4444"})
                        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig1, use_container_width=True)
                    with c2g: 
                        fig2 = px.bar(df_ag, x="Data", y="Cards")
                        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                        st.plotly_chart(fig2, use_container_width=True)
                    
                    df_h["Data"] = df_h["Conclusão_dt"].dt.strftime('%d/%m/%Y')
                    df_h = df_h.sort_values(by="Conclusão_dt", ascending=False)
                    st.markdown("### 📋 Detalhamento Diário por Matéria")
                    st.table(df_h[["Data", "Tema", "Ciclo", "Questões", "Acertos", "Erros", "Cards"]])
                    
                    st.divider()
                    with st.expander("⏪ Desfazer Revisão (Voltar para Pendente)"):
                        opcoes_desfazer = {}
                        for _, row in df_h.iterrows():
                            opcoes_desfazer[f"{row['Tema']} - {row['Ciclo']} (Feita em: {row['Data']})"] = row['ID']
                        if opcoes_desfazer:
                            rev_selecionada = st.selectbox("Selecione a revisão para desfazer:", list(opcoes_desfazer.keys()))
                            if st.button("Desfazer Conclusão e Voltar para Pendente", use_container_width=True):
                                db.collection("revisoes").document(opcoes_desfazer[rev_selecionada]).update({"status": "Pendente", "questoes_feitas": 0, "erros": 0, "acertos": 0, "flashcards_feitas": 0, "data_conclusao": None})
                                invalidar_cache(); st.success("Revisão desfeita com sucesso!"); time.sleep(1); st.rerun()

    elif menu == "🎯 Questões":
        aba_reg, aba_erros = st.tabs(["📝 Registrar", "🧠 Caderno de Erros Ativo"])
        with aba_reg:
            with st.form("q_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                a, s, d = c1.selectbox("Área", AREAS_MED), c2.text_input("Subtema"), c3.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2)
                acc, err = ac.number_input("🟢 Acertos", min_value=0), er.number_input("🔴 Erros", min_value=0)
                cc = st.text_input("Conceito Chave (Motivo do erro)")
                if st.form_submit_button("Registrar", use_container_width=True):
                    db.collection("questoes_sessoes").add({"usuario_id": u_id, "data": str(d), "area": a, "subtema": s, "acertos": acc, "erros": err, "conceito_chave": cc})
                    invalidar_cache(); st.rerun()
            
            if dados_questoes: 
                lista_q = [{"Data_obj": parse_data(b.get('data')), "Data": formatar_data_br(b.get('data')), "Área": b.get('area'), "Subtema": limpar_texto(b.get('subtema')), "Acertos": safe_int(b.get('acertos')), "Erros": safe_int(b.get('erros'))} for b in dados_questoes]
                st.table(pd.DataFrame(lista_q).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj"]))
                
        with aba_erros:
            baterias_erros = [b for b in dados_questoes if safe_int(b.get('erros')) > 0 and b.get('conceito_chave')]
            if baterias_erros:
                erro_escolhido = st.selectbox("Escolha um conceito que você errou:", reversed([f"{b.get('area')} - {limpar_texto(b.get('subtema'))}: {b.get('conceito_chave')}" for b in baterias_erros]))
                conceito_alvo = erro_escolhido.split(": ")[1]
                area_alvo = erro_escolhido.split(" - ")[0]
                tema_alvo = erro_escolhido.split(" - ")[1].split(":")[0]

                if st.button("🔥 Gerar Questão Inédita via IA", use_container_width=True):
                    client_ia = get_ia_client()
                    if client_ia:
                        with st.spinner("Construindo caso clínico..."):
                            try:
                                prompt_clonagem = f"[SISTEMA NÍVEL 5] Você é banca de residência médica. O aluno errou o conceito: '{conceito_alvo}'. Crie uma questão INÉDITA de caso clínico para testar isso, com alternativas e gabarito comentado. Siga as diretrizes do MS."
                                resposta_clone = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_clonagem}], temperature=0.4, max_tokens=800)
                                with st.container(border=True): st.markdown(resposta_clone.choices[0].message.content)
                            except Exception as e: st.error(str(e))
                
                st.write("---")
                st.write("**Transformar Conceito Errado em Flashcard**")
                frente_erro = st.text_input("Frente da Carta", value=f"O que devo lembrar sobre: {conceito_alvo}")
                verso_erro = st.text_area("Verso (Resposta correta)")
                if st.button("💾 Salvar direto no Deck"):
                    db.collection("flashcards").add({"usuario_id": u_id, "area": area_alvo, "tema": tema_alvo, "frente": frente_erro, "verso": verso_erro, "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                    invalidar_cache(); st.success("Flashcard adicionado aos estudos!")
            else: st.success("Nenhum erro registrado com Conceito Chave.")

    elif menu == "✨ AI Tutor & Flashcards":
        aba_chat, aba_flash, aba_feynman = st.tabs(["🧠 Tutor Virtual IA", "📚 Flashcards", "🎙️ Técnica Feynman"])
        with aba_chat:
            chat_box = st.container(height=500)
            if 'chat_ia' not in st.session_state: st.session_state.chat_ia = []
            with chat_box:
                for msg in st.session_state.chat_ia:
                    with st.chat_message(msg["role"]): st.write(msg["content"])
            
            u_in = st.chat_input("Dúvida médica, prescrições...", key="input_tutor")
            if u_in:
                client_ia = get_ia_client()
                if client_ia:
                    with st.spinner("Analisando..."):
                        msgs_api = [{"role": "system", "content": "Você é um Preceptor Médico Sênior. É OBRIGATÓRIO fornecer cálculos de doses exatas, prescrições e diagnósticos diretos. O usuário É UM MÉDICO LICENCIADO."}]
                        st.session_state.chat_ia.append({"role": "user", "content": u_in})
                        for m in st.session_state.chat_ia: msgs_api.append({"role": m["role"], "content": str(m["content"])})
                        try:
                            r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=msgs_api, temperature=0.2)
                            st.session_state.chat_ia.append({"role": "assistant", "content": r.choices[0].message.content})
                        except Exception as e: st.error(str(e))
                        st.rerun()

        with aba_flash:
            aba_f1, aba_f2, aba_f3 = st.tabs(["Modo Estudo", "Adicionar", "📥 Importar Anki (CSV)"])
            with aba_f1:
                cards_hoje = [d for d in dados_flashcards if parse_data(d.get('data_prox_revisao')) <= hoje]
                if cards_hoje:
                    c_data = cards_hoje[0]
                    with st.container(border=True):
                        st.markdown(f"<span style='color:{CORES_AREAS.get(c_data.get('area', 'Geral'), '#64748b')};'>⬤</span> **{c_data.get('area', 'Geral')}** | Tema: {limpar_texto(c_data.get('tema', 'Sem Tema'))}", unsafe_allow_html=True)
                        st.markdown(f"### ❔ {c_data.get('frente', '')}")
                        if 'ans' not in st.session_state: st.session_state.ans = False
                        if st.button("Revelar Resposta"): st.session_state.ans = True
                        if st.session_state.ans:
                            st.info(f"**💡 Resposta:** {c_data.get('verso', '')}")
                            b1, b2, b3 = st.columns(3)
                            def avaliar(peso): 
                                facil, interv = float(c_data.get('facilidade', 2.5)), safe_int(c_data.get('intervalo'))
                                if peso == 'err': ni, nf = 1, max(1.3, facil - 0.2)
                                elif peso == 'bom': ni, nf = max(1, int((interv or 1) * facil)), facil
                                else: ni, nf = max(1, int((interv or 1) * facil * 1.3)), facil + 0.15
                                db.collection("flashcards").document(c_data["id"]).update({"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))})
                                invalidar_cache(); st.session_state.ans = False; st.rerun()
                            if b1.button("🔴 Errei (1d)", use_container_width=True): avaliar('err')
                            if b2.button("🟡 Bom", use_container_width=True): avaliar('bom')
                            if b3.button("🟢 Fácil", use_container_width=True): avaliar('facil')
                else: st.success("🎉 Você zerou o deck de hoje. Parabéns!")
            
            with aba_f2:
                with st.form("add_fc", clear_on_submit=True):
                    a, t = st.selectbox("Área", AREAS_MED), st.text_input("Tema")
                    f, v = st.text_input("Frente da Carta"), st.text_area("Verso da Carta")
                    if st.form_submit_button("Salvar no Banco", use_container_width=True):
                        db.collection("flashcards").add({"usuario_id": u_id, "area": a, "tema": t or "Sem Tema", "frente": f, "verso": v, "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                        invalidar_cache(); st.success("Salvo!"); st.rerun()
            
            with aba_f3:
                st.markdown("### 📥 Importação em Massa")
                arq_csv = st.file_uploader("Upload do CSV (Anki)", type=["csv"])
                if arq_csv and st.button("Importar Flashcards", use_container_width=True, type="primary"):
                    try:
                        df_anki = pd.read_csv(arq_csv, sep=None, engine='python') 
                        if all(col in df_anki.columns for col in ['Area', 'Tema', 'Frente', 'Verso']):
                            with st.spinner("Injetando flashcards..."):
                                batch = db.batch()
                                for _, row in df_anki.iterrows():
                                    batch.set(db.collection("flashcards").document(), {"usuario_id": u_id, "area": str(row['Area']).strip(), "tema": str(row['Tema']).strip(), "frente": str(row['Frente']).strip(), "verso": str(row['Verso']).strip(), "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                                batch.commit(); invalidar_cache()
                            st.success("✅ Flashcards importados!"); time.sleep(2); st.rerun()
                    except Exception as e: st.error(f"Erro ao ler o arquivo: {e}")

        with aba_feynman:
            client_ia = get_ia_client()
            if client_ia:
                tema_f = st.text_input("Tema para explicar (Voz):")
                aud_f = st.audio_input("Gravar")
                if tema_f and aud_f:
                    with st.spinner("Avaliando..."):
                        try:
                            transcription = client_ia.audio.transcriptions.create(file=("audio.wav", aud_f.getvalue()), model="whisper-large-v3")
                            r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": "Avalie rigidamente o aluno."},{"role": "user", "content": f"Avalie: '{tema_f}'. Transcrição: '{transcription.text}'."}])
                            st.success(r.choices[0].message.content)
                        except Exception as e: st.error(f"Erro: {e}")

    elif menu == "📚 Registro de Aulas":
        st.header("Biblioteca Pessoal de Conteúdo")
        col_form, col_lista = st.columns([1, 2.5])
        with col_form:
            with st.form("n_aula", clear_on_submit=True):
                st.subheader("➕ Adicionar Aula")
                a = st.selectbox("Especialidade", AREAS_MED)
                t = st.text_input("Assunto da Aula (Tema)")
                d = st.date_input("Data Assistida", hoje, format="DD/MM/YYYY")
                if st.form_submit_button("Registrar e Gerar Ciclo R", use_container_width=True):
                    a_ref = db.collection("aulas").add({"usuario_id": u_id, "area": a, "tema": t or "Aula", "data_aula": str(d)})
                    batch = db.batch()
                    for c, dias in {"R1":1, "R7":7, "R15":15, "R30":30, "R90":90, "R180":180, "R360":360}.items():
                        batch.set(db.collection("revisoes").document(), {"usuario_id": u_id, "aula_id": a_ref[1].id, "ciclo": c, "data_agendada": str(d + timedelta(days=dias)), "status": "Pendente"})
                    batch.commit()
                    invalidar_cache(); st.rerun()
                    
            with st.expander("🗑️ Excluir Aula do Banco"):
                opcoes_del_dict = {f"{formatar_data_br(a.get('data_aula'))} - {limpar_texto(a.get('tema'))}": a['id'] for a in dados_aulas}
                if opcoes_del_dict:
                    op_del_chave = st.selectbox("Selecione para apagar:", list(opcoes_del_dict.keys()))
                    if st.button("Deletar Aula e Suas Revisões", use_container_width=True) and op_del_chave:
                        id_del = opcoes_del_dict[op_del_chave]
                        batch = db.batch()
                        for rd in db.collection("revisoes").where("aula_id", "==", id_del).get(): batch.delete(rd.reference)
                        batch.delete(db.collection("aulas").document(id_del))
                        batch.commit(); invalidar_cache(); st.rerun()

        with col_lista:
            if 'cal_mes_aulas' not in st.session_state: st.session_state.cal_mes_aulas = hoje.month
            if 'cal_ano_aulas' not in st.session_state: st.session_state.cal_ano_aulas = hoje.year
            nav_a1, nav_a2, nav_a3 = st.columns([1,2,1])
            with nav_a1:
                if st.button("⬅️ Mês Anterior", key="prev_aula"):
                    if st.session_state.cal_mes_aulas == 1: st.session_state.cal_mes_aulas, st.session_state.cal_ano_aulas = 12, st.session_state.cal_ano_aulas - 1
                    else: st.session_state.cal_mes_aulas -= 1
                    st.rerun()
            with nav_a2: st.markdown(f"<h3 style='text-align:center; margin:0;'>📅 {MESES_PT[st.session_state.cal_mes_aulas]} {st.session_state.cal_ano_aulas}</h3>", unsafe_allow_html=True)
            with nav_a3:
                if st.button("Próximo Mês ➡️", key="next_aula"):
                    if st.session_state.cal_mes_aulas == 12: st.session_state.cal_mes_aulas, st.session_state.cal_ano_aulas = 1, st.session_state.cal_ano_aulas + 1
                    else: st.session_state.cal_mes_aulas += 1
                    st.rerun()
            
            st.markdown(gerar_calendario_html(list(dados_aulas), st.session_state.cal_ano_aulas, st.session_state.cal_mes_aulas), unsafe_allow_html=True)
            
            col_f1, col_f2 = st.columns([3, 2])
            with col_f1: st.subheader("Linha do Tempo")
            with col_f2: filtrar_data_aula = st.checkbox("🔎 Filtrar por Data")
            
            aulas_exibir = list(dados_aulas)
            if filtrar_data_aula:
                data_alvo = st.date_input("Escolha a data exata", hoje, format="DD/MM/YYYY")
                aulas_exibir = [a for a in dados_aulas if parse_data(a.get('data_aula')) == data_alvo]

            aulas_exibir.sort(key=lambda x: parse_data(x.get('data_aula')), reverse=True)
            for al in aulas_exibir:
                with st.container(border=True):
                    st.markdown(f"#### <span style='color:{CORES_AREAS.get(al.get('area'), '#64748b')};'>⬤</span> {limpar_texto(al.get('tema', 'Aula sem título'))}", unsafe_allow_html=True)
                    st.caption(f"{al.get('area', '')} | Data: {formatar_data_br(al.get('data_aula'))}")

    elif menu == "⏱️ Modo Foco":
        st.header("Concentração Pomodoro")
        sessoes_hoje = [s for s in dados_focus if parse_data(s.get('data_sessao')) == hoje]
        c1, c2, c3 = st.columns(3)
        c1.metric("Ciclos Hoje", len(sessoes_hoje)); c2.metric("Minutos Focados", sum(safe_int(s.get('minutos_foco')) for s in sessoes_hoje)); c3.metric("Questões no Foco", sum(safe_int(s.get('questoes_feitas')) for s in sessoes_hoje))
        st.divider()
        tf = st.selectbox("Duração do Foco (Minutos)", [25, 30, 45, 50, 60, 90], index=3)
        if 'foco_iniciado' not in st.session_state: st.session_state.foco_iniciado = False
        
        if not st.session_state.foco_iniciado:
            if st.button("🚀 Ativar Módulo de Isolamento", use_container_width=True):
                st.session_state.foco_iniciado, st.session_state.foco_min, st.session_state.foco_fim = True, tf, get_agora() + timedelta(minutes=tf); st.rerun()
        else:
            t_seg = int((st.session_state.foco_fim - get_agora()).total_seconds())
            if t_seg > 0:
                components.html(f"""<div style="text-align:center;"><h1 id="tmr" style="font-size:80px;color:#2563eb;">--:--</h1></div><script>var d={t_seg}*1000,el=document.getElementById("tmr");function upd(){{if(d<=0){{el.innerHTML="00:00";return;}}var m=Math.floor(d/60000),s=Math.floor((d%60000)/1000);el.innerHTML=(m<10?"0"+m:m)+":"+(s<10?"0"+s:s);d-=1000;}}upd();setInterval(upd,1000);</script>""", height=120)
                if st.button("❌ Cancelar"): st.session_state.foco_iniciado = False; st.rerun()
            else:
                st.success("✅ Concluído!")
                if st.button("Gravar Sessão"): 
                    db.collection("focus_sessoes").add({"usuario_id": u_id, "data_sessao": str(hoje), "minutos_foco": st.session_state.foco_min})
                    invalidar_cache(); st.session_state.foco_iniciado = False; st.rerun()

    elif menu == "📁 Materiais e Simulados":
        arq = st.file_uploader("Upload PDF")
        if arq and st.button("Salvar na Nuvem"):
            db.collection("materiais").add({"usuario_id": u_id, "titulo": arq.name, "data_upload": str(hoje)})
            invalidar_cache(); st.success("Salvo!")
        if dados_materiais: 
            st.table(pd.DataFrame([{"Título": m.get('titulo'), "Data": formatar_data_br(m.get('data_upload'))} for m in dados_materiais]))

    elif menu == "🏥 Simulados & OSCE":
        st.header("Simulador Interativo")
        aba_p, aba_simulado, aba_osce = st.tabs(["📝 Notas", "🤖 Simulado IA", "🗣️ Consultório OSCE"])
        
        with aba_p:
            with st.form("sim_f", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                ins, an, dt = c1.selectbox("Instituição", INSTITUICOES), c2.text_input("Ano da Prova"), c3.date_input("Data de Resolução", hoje, format="DD/MM/YYYY")
                co, no = st.columns(2)
                cor, notl = co.number_input("Nota de Corte (Alvo)", min_value=0.0), no.number_input("Sua Nota Líquida", min_value=0.0)
                if st.form_submit_button("Inserir Nota no Gráfico", use_container_width=True):
                    db.collection("simulados").add({"usuario_id": u_id, "instituicao": ins, "ano": an, "data_realizacao": str(dt), "nota_corte": cor, "minha_nota": notl})
                    invalidar_cache(); st.rerun()
            if len(dados_simulados) >= 3:
                dfs = pd.DataFrame([{"D": parse_data(s.get('data_realizacao')), "N": float(s.get('minha_nota',0)), "C": float(s.get('nota_corte',0))} for s in dados_simulados])
                dfs['DU'] = pd.to_numeric(pd.to_datetime(dfs['D']))
                if len(dfs['DU'].unique()) > 1:
                    m = LinearRegression().fit(dfs[['DU']], dfs['N'])
                    fut = [dfs['D'].max() + timedelta(days=30*i) for i in range(1, 4)]
                    p = m.predict(pd.to_numeric(pd.to_datetime(fut)).values.reshape(-1, 1))
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=dfs['D'], y=dfs['N'], name="Sua Evolução Real", line=dict(color="#2563eb", width=3)))
                    fig.add_trace(go.Scatter(x=fut, y=p, name="Projeção IA", line=dict(color="#ef4444", dash='dot')))
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True)

        with aba_simulado:
            col_sim1, col_sim2 = st.columns(2)
            colagem_img_sim = None
            with col_sim1:
                imgs_prova = st.file_uploader("🖼️ Múltiplas Imagens da Prova", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
                if paste_image_button is not None:
                    paste_result_sim = paste_image_button(label="Colar print de questão (Ctrl+V)", background_color="#2563eb", hover_background_color="#1d4ed8", key="paste_sim")
                    if paste_result_sim.image_data is not None: colagem_img_sim = paste_result_sim.image_data; st.success("Print colado!")
            with col_sim2: arq_pdf = st.file_uploader("📄 Ou anexe o PDF Completo", type=['pdf'])
            
            if (arq_pdf or imgs_prova or colagem_img_sim) and st.button("🚀 Iniciar Motor de Prova Interativo", use_container_width=True):
                client_ia = get_ia_client()
                if client_ia:
                    todas_imagens_b64 = []
                    with st.spinner("Empacotando arquivos para envio..."):
                        if arq_pdf:
                            try:
                                from pdf2image import convert_from_bytes
                                imagens_paginas = convert_from_bytes(arq_pdf.read())
                                for img in imagens_paginas:
                                    buf = io.BytesIO(); img.save(buf, format="JPEG"); todas_imagens_b64.append(base64.b64encode(buf.getvalue()).decode('utf-8'))
                            except Exception as e_pdf: st.error(f"Erro no PDF: {e_pdf}")
                        if imgs_prova:
                            for img in imgs_prova: todas_imagens_b64.append(base64.b64encode(img.getvalue()).decode('utf-8'))
                        if colagem_img_sim:
                            buf = io.BytesIO(); colagem_img_sim.save(buf, format="PNG"); todas_imagens_b64.append(base64.b64encode(buf.getvalue()).decode('utf-8'))

                    if todas_imagens_b64:
                        st.session_state.prova_ativa = []
                        st.session_state.respostas_usuario = {}
                        barra_progresso = st.progress(0)
                        
                        for i in range(len(todas_imagens_b64)):
                            img_b64 = todas_imagens_b64[i]
                            prompt = """Extraia TODAS as questões da imagem. Retorne JSON: {"questoes": [{"num": 1, "texto": "Enunciado...", "opcoes": {"A": "...", "B": "..."}, "correta": "B", "comentario": "..."}]}"""
                            try:
                                resposta = client_ia.chat.completions.create(model=MODELO_VISAO, messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}], temperature=0.1)
                                questoes_lote = extrair_json_seguro(resposta.choices[0].message.content).get("questoes", [])
                                for q in questoes_lote: q['imagem_fonte'] = img_b64
                                st.session_state.prova_ativa.extend(questoes_lote)
                            except Exception as e: st.warning(f"Erro na página {i+1}: {e}")
                            barra_progresso.progress((i + 1) / len(todas_imagens_b64))
                            time.sleep(1.5)
                        st.success("🎉 Extração concluída!"); time.sleep(1); st.rerun()

            if "prova_ativa" in st.session_state and st.session_state.prova_ativa:
                st.divider(); st.subheader("📝 Resolvendo Simulado")
                for i, q in enumerate(st.session_state.prova_ativa):
                    with st.container(border=True):
                        st.markdown(f"**Questão {q.get('num', i+1)}**")
                        if q.get('imagem_fonte'):
                            with st.expander("🖼️ Ver Imagem"): st.image(base64.b64decode(q['imagem_fonte']), use_container_width=True)
                        st.write(q.get('texto', ''))
                        opcoes_dict = q.get('opcoes', {})
                        if opcoes_dict: st.session_state.respostas_usuario[i] = st.radio("Selecione:", options=list(opcoes_dict.keys()), format_func=lambda x: f"{x}) {opcoes_dict.get(x, '')}", key=f"q_radio_{i}", index=None)

                if st.button("🏁 Finalizar e Ver Gabarito", use_container_width=True):
                    acertos = 0
                    for idx, questao in enumerate(st.session_state.prova_ativa):
                        resp_user = st.session_state.respostas_usuario.get(idx)
                        correta = questao.get('correta', '')
                        st.write("---")
                        if resp_user == correta and correta != '': st.success(f"Questão {questao.get('num', idx+1)}: ACERTOU! ({resp_user})"); acertos += 1
                        else: st.error(f"Questão {questao.get('num', idx+1)}: ERROU. (Sua resposta: {resp_user} | Correta: {correta})")
                        with st.expander("Comentário"): st.write(questao.get('comentario', 'Sem comentário.'))
                    
                    nota_final = (acertos / len(st.session_state.prova_ativa)) * 100 if len(st.session_state.prova_ativa) > 0 else 0
                    st.balloons(); st.metric("Nota Líquida", f"{nota_final:.1f}%")
                    db.collection("simulados").add({"usuario_id": u_id, "data_realizacao": str(hoje), "minha_nota": nota_final, "instituicao": "Simulado IA", "nota_corte": 0})
                    invalidar_cache()
                    
                if st.button("Limpar Prova Atual"): st.session_state.pop("prova_ativa"); st.session_state.pop("respostas_usuario"); st.rerun()

        with aba_osce:
            client_ia = get_ia_client()
            if client_ia:
                modo_osce = st.radio("Cenário", ["🎯 Doença Específica", "🎲 Surpresa"])
                if modo_osce == "🎯 Doença Específica": doenca_alvo = st.text_input("Doença (Ex: Infarto com supra)")
                else:
                    col_m, col_t = st.columns(2)
                    mat_alvo, tema_alvo = col_m.selectbox("Área", AREAS_MED), col_t.text_input("Tema")

                if st.button("▶️ Abrir Consultório"):
                    st.session_state.osce_hist, st.session_state.osce_active, st.session_state.osce_finished = [], True, False
                    base_p = f"""Você é paciente num OSCE de Medicina. Não diga o diagnóstico de cara. Fale os sintomas. Se o médico pedir um exame dessa lista [{", ".join(BANCO_IMAGENS_OSCE.keys())}], responda com a tag [EXAME: nome_do_exame]."""
                    st.session_state.osce_sys_prompt = f"{base_p}\nDoença: {doenca_alvo}." if modo_osce == "🎯 Doença Específica" else f"{base_p}\nSorteie para: {mat_alvo} - {tema_alvo}."
                    st.rerun()

                if getattr(st.session_state, 'osce_active', False):
                    chat_box = st.container(height=450)
                    with chat_box:
                        for msg in st.session_state.osce_hist:
                            with st.chat_message(msg["role"]):
                                if msg["role"] == "assistant": renderizar_mensagem_osce(msg["content"])
                                else: st.write(msg["content"])
                    
                    if not getattr(st.session_state, 'osce_finished', False):
                        col_t, col_a = st.columns([4, 1])
                        texto_medico = col_t.chat_input("Fale ou prescreva...", key="input_osce")
                        audio_medico = col_a.audio_input("Voz", label_visibility="collapsed")
                        prescricao_final = st.text_area("📝 Receituário Final:")

                        if st.button("🛑 Chamar Preceptor", use_container_width=True):
                            st.session_state.osce_finished = True
                            with st.spinner("Corrigindo conduta..."):
                                try:
                                    r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": st.session_state.osce_sys_prompt}] + st.session_state.osce_hist + [{"role": "user", "content": f"O aluno prescreveu: {prescricao_final}. Avalie de 0 a 10 e aponte os erros baseados nas diretrizes."}], temperature=0.3)
                                    st.session_state.osce_eval = r.choices[0].message.content; st.rerun()
                                except Exception as e: st.error(str(e))
                        
                        entrada_final = texto_medico
                        if audio_medico:
                            with st.spinner("Transcrevendo..."):
                                try: entrada_final = client_ia.audio.transcriptions.create(file=("audio.wav", audio_medico.getvalue()), model="whisper-large-v3").text
                                except Exception as e: st.error(f"Erro no áudio: {e}")
                        
                        if entrada_final:
                            st.session_state.osce_hist.append({"role": "user", "content": entrada_final})
                            with st.spinner("Paciente respondendo..."):
                                try:
                                    r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": st.session_state.osce_sys_prompt}] + st.session_state.osce_hist, temperature=0.6)
                                    st.session_state.osce_hist.append({"role": "assistant", "content": r.choices[0].message.content})
                                except Exception as e: st.error(f"Erro IA: {e}")
                                st.rerun()

                    if getattr(st.session_state, 'osce_finished', False):
                        st.divider(); st.markdown("### 📋 Avaliação"); st.info(st.session_state.osce_eval)

    elif menu == "⚙️ Configurações":
        st.header("Controle de Perfil")
        uf = st.file_uploader("Foto de Perfil", type=['jpg', 'png'])
        if uf and st.button("Confirmar Foto", use_container_width=True):
            p = os.path.join("fotos_perfil", f"{u_id}.jpg")
            with open(p, "wb") as f: f.write(uf.getbuffer())
            db.collection("usuarios").document(u_id).update({"foto_perfil": p})
            st.session_state.user_settings["foto_perfil"] = p; st.rerun()

    elif is_super_admin(st.session_state.user_nome) and menu == "👑 Admin":
        st.header("Painel de Administração Global (Firebase)")
        try:
            usuarios_todos = db.collection("usuarios").get()
            st.write(f"**Contas Ativas:** {len(usuarios_todos)}")
            df_u = pd.DataFrame([{"ID Nuvem": u.id, "Nome": u.to_dict().get('nome')} for u in usuarios_todos])
            st.table(df_u)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                edit_u = st.selectbox("Alterar Nome:", [f"{u.id} | {u.to_dict().get('nome')}" for u in usuarios_todos])
                nn = st.text_input("Novo Nome")
                if st.button("✏️ Mudar Nome", use_container_width=True): db.collection("usuarios").document(edit_u.split(" | ")[0]).update({"nome": nn}); invalidar_cache(); st.rerun()
            with c2:
                res_u = st.selectbox("Reset de Senha:", [f"{u.id} | {u.to_dict().get('nome')}" for u in usuarios_todos])
                ns = st.text_input("Nova Senha")
                if st.button("🔄 Forçar Nova Senha", use_container_width=True): db.collection("usuarios").document(res_u.split(" | ")[0]).update({"senha": hash_senha(ns)}); invalidar_cache(); st.rerun()
            with c3:
                del_u = st.selectbox("Banir:", [f"{u.id} | {u.to_dict().get('nome')}" for u in usuarios_todos])
                if st.button("🚫 Apagar Conta", use_container_width=True):
                    uid = del_u.split(" | ")[0]
                    if uid != u_id:
                        for col in ["aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "focus_sessoes", "materiais", "cronogramas"]:
                            for doc in db.collection(col).where("usuario_id", "==", uid).get(): db.collection(col).document(doc.id).delete()
                        db.collection("usuarios").document(uid).delete(); invalidar_cache(); st.rerun()
        except Exception as e: st.error(f"Erro Admin: {e}")
