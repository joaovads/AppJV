import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date, timezone
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
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
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

try:
    from streamlit_paste_button import paste_image_button
except ImportError:
    paste_image_button = None

# ==========================================
# CONFIGURAÇÃO GERAL DA PÁGINA E MODELOS
# ==========================================
st.set_page_config(page_title="Residência PRO", page_icon="🏥", layout="wide")

# Modelos atualizados de produção (Blindado: usando o modelo instantâneo mais estável da Groq)
MODELO_VISAO = "llama-3.2-11b-vision-preview"
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
# FUNÇÃO MESTRE DE ESTILIZAÇÃO CSS
# ==========================================
def aplicar_css_tema(modo):
    if modo == "Escuro":
        bg_color = "#0e1117"
        text_color = "#f8fafc"
        metric_bg = "#1e293b"
        metric_border = "#334155"
        sidebar_bg = "#11151c"
        input_bg = "#1e293b"
        input_text = "#f8fafc"
        menu_text = "#94a3b8"
        menu_hover = "#334155"
        bg_tabela = "#334155"
        th_bg = "#1e293b"
        cor_texto_tabela = "#f8fafc"
        shadow = "0 4px 6px rgba(0, 0, 0, 0.3)"
        blue_accent = "#3b82f6"
    else:
        bg_color = "#f8f9fa"
        text_color = "#0f172a"
        metric_bg = "#ffffff"
        metric_border = "#cbd5e1"
        sidebar_bg = "#ffffff"
        input_bg = "#ffffff"
        input_text = "#0f172a"
        menu_text = "#64748b"
        menu_hover = "#f1f5f9"
        bg_tabela = "#ffffff"
        th_bg = "#f1f5f9"
        cor_texto_tabela = "#0f172a"
        shadow = "0 4px 12px rgba(0, 0, 0, 0.05)"
        blue_accent = "#2563eb"

    css_str = f"""
    <style>
    @keyframes fadein {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .main {{ animation: fadein 0.4s ease-out; }}
    
    .stApp, [data-testid="stAppViewContainer"], .main {{ background-color: {bg_color} !important; }}
    h1:not(#tmr), h2, h3, h4, h5, h6, .stMarkdown p, label {{ color: {text_color} !important; font-family: 'Inter', sans-serif; }}
    
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div, [data-baseweb="select"] > div, [data-testid="stFileUploadDropzone"] {{
        background-color: {input_bg} !important; 
        border: 1px solid {metric_border} !important;
        border-radius: 8px !important;
    }}
    input, textarea, div[data-baseweb="select"] span {{ color: {input_text} !important; -webkit-text-fill-color: {input_text} !important; }}
    
    [data-baseweb="popover"] > div, ul[data-baseweb="menu"] {{ background-color: {input_bg} !important; border: 1px solid {metric_border} !important; border-radius: 8px; box-shadow: {shadow}; }}
    ul[data-baseweb="menu"] li {{ background-color: transparent !important; color: {input_text} !important; padding: 10px; transition: background 0.2s; }}
    ul[data-baseweb="menu"] li:hover {{ background-color: {menu_hover} !important; }}
    ul[data-baseweb="menu"] span {{ color: {input_text} !important; }}
    
    [data-testid="stChatInput"] {{ background-color: {bg_color} !important; padding-bottom: 20px; }}
    [data-testid="stChatInput"] > div {{ background-color: {input_bg} !important; border: 1px solid {metric_border} !important; border-radius: 20px !important; }}
    
    button[kind="primary"], button[kind="secondary"], button[kind="formSubmit"], button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"], button[data-testid="baseButton-formSubmit"], div[data-testid="stFormSubmitButton"] > button {{
        background-color: {blue_accent} !important; 
        border: none !important; 
        border-radius: 8px !important;
        transition: transform 0.1s ease, box-shadow 0.2s ease !important;
    }}
    .stButton > button {{ border-radius: 8px !important; background-color: {blue_accent} !important; color: white !important; border: none !important; }}
    button p, button span, button div {{ color: white !important; font-weight: 600 !important; letter-spacing: 0.3px; }}
    
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {{ color: {text_color} !important; font-weight: 500 !important; transition: color 0.3s; }}
    
    [data-testid="stDataFrame"] > div, [data-testid="stTable"] > div {{ background-color: {bg_tabela} !important; border-radius: 10px; overflow: hidden; box-shadow: {shadow}; }}
    [data-testid="stDataFrame"] th, [data-testid="stTable"] th {{ background-color: {th_bg} !important; color: {cor_texto_tabela} !important; padding: 12px !important; border-bottom: 2px solid {metric_border} !important; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; text-align: left; }}
    [data-testid="stDataFrame"] td, [data-testid="stTable"] td {{ background-color: {bg_tabela} !important; color: {cor_texto_tabela} !important; padding: 12px !important; border-bottom: 1px solid {metric_border} !important; border-right: none !important; border-left: none !important; }}
    
    div[data-testid='stExpander'] {{ border: 1px solid {metric_border} !important; background-color: {metric_bg} !important; border-radius: 12px; transition: box-shadow 0.3s ease; }}
    div[data-testid="metric-container"] {{ background-color: {metric_bg} !important; border: 1px solid {metric_border} !important; padding: 20px; border-radius: 12px; box-shadow: {shadow}; transition: transform 0.2s ease; }}
    
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {metric_border} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: 10px 14px; border-radius: 10px; margin-bottom: 6px; background-color: transparent; transition: all 0.2s ease; cursor: pointer; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background-color: {menu_hover} !important; padding-left: 20px; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label p {{ color: {menu_text} !important; font-weight: 500; font-size: 15px; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background-color: {blue_accent} !important; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3); }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: white !important; font-weight: 600 !important; }}
    
    .profile-img {{ border-radius: 50%; object-fit: cover; border: 4px solid {blue_accent}; width: 130px; height: 130px; display: block; margin: 0 auto; box-shadow: 0 4px 10px rgba(0,0,0,0.15); transition: transform 0.3s ease; }}
    </style>
    """
    st.markdown(css_str, unsafe_allow_html=True)


# ==========================================
# CHAVES DE ACESSO E CONEXÃO FIREBASE
# ==========================================
try:
    CHAVE_GROQ_FIXA = st.secrets.get("GROQ_KEY", st.secrets.get("GROQ_API_KEY", "")) 
except Exception:
    CHAVE_GROQ_FIXA = ""

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

for d in ["materiais_estudo", "imagens_flashcards"]:
    if not os.path.exists(d): os.makedirs(d)

# ==========================================
# FUNÇÕES DE BANCO OTIMIZADAS (ZERO LATÊNCIA)
# ==========================================
def db_add(col_name, state_key, data):
    doc_ref = db.collection(col_name).document()
    doc_ref.set(data)
    data["id"] = doc_ref.id
    if state_key in st.session_state.dados:
        st.session_state.dados[state_key].append(data)
    return doc_ref

def db_update(col_name, state_key, doc_id, updates):
    # Cópia enviada para o Firebase Cloud
    db.collection(col_name).document(doc_id).update(updates)
    
    # Sincroniza a memória local blindada contra objetos Sentinel do Google
    if state_key in st.session_state.dados:
        for item in st.session_state.dados[state_key]:
            if str(item.get("id")) == str(doc_id):
                for k, v in updates.items():
                    if 'Sentinel' in str(type(v)):
                        item.pop(k, None)
                    else:
                        item[k] = v
                break

def db_delete(col_name, state_key, doc_id):
    db.collection(col_name).document(doc_id).delete()
    if state_key in st.session_state.dados:
        st.session_state.dados[state_key] = [i for i in st.session_state.dados[state_key] if str(i.get("id")) != str(doc_id)]

def invalidar_cache(colecoes=None):
    if colecoes and 'dados' in st.session_state:
        if isinstance(colecoes, str): colecoes = [colecoes]
        for colecao in colecoes:
            col_db = colecao
            if colecao == "questoes": col_db = "questoes_sessoes"
            elif colecao == "focus": col_db = "focus_sessoes"
            st.session_state.dados[colecao] = get_user_docs(col_db, st.session_state.user_id)
    else:
        st.session_state.pop('dados', None)
        st.session_state.user_data_loaded = False

# ==========================================
# COMPRESSOR E EXTRATOR SEGURO DE JSON E IA
# ==========================================
def otimizar_imagem_para_api(img_data, max_size=500):
    if Image is None:
        try:
            if isinstance(img_data, bytes): return base64.b64encode(img_data).decode('utf-8')
            if hasattr(img_data, 'getvalue'): return base64.b64encode(img_data.getvalue()).decode('utf-8')
            if hasattr(img_data, 'read'): return base64.b64encode(img_data.read()).decode('utf-8')
        except: pass
        return ""
        
    try:
        # Processamento inteligente detectando a verdadeira classe do objeto
        if isinstance(img_data, Image.Image):
            img = img_data.copy()
        elif isinstance(img_data, bytes):
            img = Image.open(io.BytesIO(img_data))
        elif hasattr(img_data, 'getvalue'):
            img = Image.open(io.BytesIO(img_data.getvalue()))
        elif hasattr(img_data, 'read'):
            img_data.seek(0)
            img = Image.open(io.BytesIO(img_data.read()))
        else:
            img = Image.open(img_data)
            
        if img.mode != 'RGB': 
            img = img.convert('RGB')
            
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=65)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except Exception:
        # Fallback de sobrevivência final
        try:
            if isinstance(img_data, Image.Image):
                buf = io.BytesIO()
                img_data.save(buf, format="PNG")
                return base64.b64encode(buf.getvalue()).decode('utf-8')
            if isinstance(img_data, bytes): return base64.b64encode(img_data).decode('utf-8')
            if hasattr(img_data, 'getvalue'): return base64.b64encode(img_data.getvalue()).decode('utf-8')
            if hasattr(img_data, 'read'):
                img_data.seek(0)
                return base64.b64encode(img_data.read()).decode('utf-8')
        except: pass
        return ""

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
    t = str(texto)
    # Limpeza nuclear de pensamento da IA
    t = re.sub(r'<think>.*?</think>', '', t, flags=re.DOTALL)
    t = re.sub(r'<think>.*', '', t, flags=re.DOTALL)
    
    # Remoção de crases de markdown
    crases = chr(96) * 3
    t = t.replace(crases + "json", "").replace(crases, "").strip()
    
    # Isolar escopo JSON e ignorar textos inúteis que a IA fala antes ou depois
    start_obj = t.find('{')
    start_arr = t.find('[')
    
    if start_obj == -1 and start_arr == -1:
        return {}
        
    is_obj = start_obj != -1 and (start_arr == -1 or start_obj < start_arr)
    t = t[start_obj:] if is_obj else t[start_arr:]
    
    try:
        parsed = json.loads(t)
        if isinstance(parsed, list): return {"tarefas": parsed, "questoes": parsed}
        return parsed
    except: pass
    
    # Isolar do lado direito se houver lixo
    end_idx = t.rfind('}') if is_obj else t.rfind(']')
    if end_idx != -1:
        try:
            parsed = json.loads(t[:end_idx+1])
            if isinstance(parsed, list): return {"tarefas": parsed, "questoes": parsed}
            return parsed
        except: pass
        
    # Auto-Reparo: Fechar chaves pendentes caso a Groq API decepe a string por tokens
    fix = t
    if fix.count('"') % 2 != 0: fix += '"'
    fix = fix.strip()
    if fix.endswith(','): fix = fix[:-1]
    
    faltando_chaves = fix.count('{') - fix.count('}')
    faltando_colchetes = fix.count('[') - fix.count(']')
    
    if faltando_colchetes > 0: fix += ']' * faltando_colchetes
    if faltando_chaves > 0: fix += '}' * faltando_chaves
    
    try:
        parsed = json.loads(fix)
        if isinstance(parsed, list): return {"tarefas": parsed, "questoes": parsed}
        return parsed
    except:
        fix_alt = t
        if fix_alt.count('"') % 2 != 0: fix_alt += '"'
        fix_alt = fix_alt.strip()
        if fix_alt.endswith(','): fix_alt = fix_alt[:-1]
        if faltando_chaves > 0: fix_alt += '}' * faltando_chaves
        if faltando_colchetes > 0: fix_alt += ']' * faltando_colchetes
        try:
            parsed = json.loads(fix_alt)
            if isinstance(parsed, list): return {"tarefas": parsed, "questoes": parsed}
            return parsed
        except Exception:
            return {}

# ==========================================
# CONSTANTES E CORES
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
SUB_CM = ["Geral", "Cardiologia", "Nefrologia", "Endocrinologia", "Pneumologia", "Gastroenterologia", "Reumatologia", "Hematologia", "Infectologia", "Neurologia"]
SUB_CG = ["Geral", "Cirurgia do Trauma", "Cirurgia Vascular", "Cirurgia Plástica", "Cirurgia Torácica", "Cirurgia Pediátrica", "Urologia", "Neurocirurgia", "Ortopedia", "Cirurgia Oncológica", "Cirurgia Cabeça e Pescoço"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#3b82f6", "Pediatria": "#ec4899", "Ginecologia e Obstetrícia": "#a855f7", "Medicina Preventiva": "#22c55e", "Cirurgia Geral": "#ef4444", "Geral": "#64748b"}
PRIORIDADES = {1: "💎 Azul", 2: "🟩 Verde", 3: "🟨 Amarelo", 4: "🟥 Vermelho", 5: "🟪 Roxo"}

BANCO_IMAGENS_OSCE = {
    "ecg_normal": "https://upload.wikimedia.org/wikipedia/commons/b/b6/12_lead_normal_ECG.png",
    "ecg_infarto_supra": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/12-lead_ECG_showing_inferior_STEMI.png/1024px-12-lead_ECG_showing_inferior_STEMI.png",
    "rx_torax_normal": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png",
    "rx_torax_pneumonia": "https://upload.wikimedia.org/wikipedia/commons/e/e0/Pneumonia_Chest_X-ray.jpg",
    "tc_cranio_normal": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Normal_CT_of_the_brain.jpg"
}

def renderizar_mensagem_osce(texto):
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    bg_osce = "#1e293b" if modo == "Escuro" else "#ffffff"
    bd_osce = "#334155" if modo == "Escuro" else "#cbd5e1"
    
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
                <div style="border: 1px solid {bd_osce}; border-radius: 12px; padding: 15px; margin: 15px 0; background-color: {bg_osce}; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <p style="color: #2563eb; font-weight: bold; margin-bottom: 10px; font-size: 16px;">📎 Laudo Anexo: {chave.replace('_', ' ').title()}</p>
                    <img src="{img_url}" style="width: 100%; border-radius: 8px;">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"*(O paciente entrega um laudo correspondente a {chave}, porém sem imagem disponível no banco)*")

# ==========================================
# FUNÇÕES GERAIS E DATA
# ==========================================
def get_agora(): 
    return datetime.now(timezone.utc) - timedelta(hours=3)

def hash_senha(senha): return hashlib.sha256(str.encode(senha)).hexdigest()
def is_super_admin(nome): return str(nome).lower().strip() in ['joao', 'joão', 'joao victor']

def parse_data(d):
    """
    Motor O(1) de conversão de datas super otimizado para evitar travamentos
    e sobrecarga de CPU na renderização do aplicativo Streamlit.
    """
    if not d: return get_agora().date()
    if isinstance(d, datetime): return d.date()
    if isinstance(d, date): return d
    if isinstance(d, str):
        d_str = d.strip()[:10]
        if len(d_str) == 10:
            if d_str[4] == '-' and d_str[7] == '-':
                try: return date(int(d_str[0:4]), int(d_str[5:7]), int(d_str[8:10]))
                except: pass
            elif d_str[2] == '/' and d_str[5] == '/':
                try: return date(int(d_str[6:10]), int(d_str[3:5]), int(d_str[0:2]))
                except: pass
        
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

def limpar_texto(texto):
    if not texto: return "Sem título"
    return re.sub(r'^[A-Za-z0-9_-]{10,40}\s*\|\s*', '', str(texto)).strip()

def get_user_docs(collection_name, user_id):
    try:
        todos_docs = db.collection(collection_name).where(filter=FieldFilter("usuario_id", "==", str(user_id))).get()
        return [{"id": d.id, **d.to_dict()} for d in todos_docs]
    except Exception as e:
        return []

def gerar_calendario_html(aulas_lista, ano, mes):
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    if modo == "Escuro":
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#1e293b", "#334155", "#0f172a", "#1e212b", "#94a3b8", "#f8fafc", "#475569"
    else:
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#ffffff", "#e2e8f0", "#f8fafc", "#ffffff", "#475569", "#0f172a", "#94a3b8"
        
    cal = calendar.monthcalendar(ano, mes)
    aulas_dict = {}
    for a in aulas_lista:
        d = parse_data(a.get('data_aula'))
        if d.year == ano and d.month == mes: aulas_dict.setdefault(d.day, []).append(a)
        
    html_code = f"<div style='background-color:{bg_ct}; padding:20px; border-radius:12px; margin-bottom:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:8px; color:{tc_th}; background-color: transparent !important; border: none !important; font-size:14px;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_em} !important; border-radius:4px;'></td>"
            else:
                if day in aulas_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(a.get('area'), '#64748b')}; color:white !important; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(a.get('tema', '')))}'>{html.escape(limpar_texto(a.get('tema', '')))}</div>" for a in aulas_dict[day]])
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px; transition: transform 0.2s;' onmouseover=\"this.style.transform='scale(1.02)'\" onmouseout=\"this.style.transform='scale(1)'\"><strong style='color:{tc_st} !important; font-size:14px;'>{day}</strong><div style='margin-top:8px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px;'><strong style='color:{tc_em} !important; font-size:14px;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

def gerar_calendario_revisoes_html(revisoes_lista, ano, mes):
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    if modo == "Escuro":
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#1e293b", "#334155", "#0f172a", "#1e212b", "#94a3b8", "#f8fafc", "#475569"
    else:
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#ffffff", "#e2e8f0", "#f8fafc", "#ffffff", "#475569", "#0f172a", "#94a3b8"

    cal = calendar.monthcalendar(ano, mes)
    revs_dict = {}
    for r in revisoes_lista:
        d = parse_data(r.get('data_agendada_obj') if 'data_agendada_obj' in r else r.get('data_agendada'))
        if d and d.year == ano and d.month == mes: revs_dict.setdefault(d.day, []).append(r)
        
    html_code = f"<div style='background-color:{bg_ct}; padding:20px; border-radius:12px; margin-bottom:25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:8px; color:{tc_th}; background-color: transparent !important; border: none !important; font-size:14px;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_em} !important; border-radius:4px;'></td>"
            else:
                if day in revs_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(r.get('area'), '#64748b')}; color:white !important; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})'>{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})</div>" for r in revs_dict[day]])
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px; transition: transform 0.2s;' onmouseover=\"this.style.transform='scale(1.02)'\" onmouseout=\"this.style.transform='scale(1)'\"><strong style='color:{tc_st} !important; font-size:14px;'>{day}</strong><div style='margin-top:8px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px;'><strong style='color:{tc_em} !important; font-size:14px;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

def render_toolbar():
    """
    Componente seguro em JS que permite formatar o texto SELECIONADO
    dentro de qualquer Text Area do Streamlit sem recarregar a tela.
    """
    toolbar_html = """
    <div style="display: flex; gap: 8px; margin-bottom: 0px; align-items: center;">
        <span style="color: #94a3b8; font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600;">Formatador Rápido:</span>
        <button class="fmt-btn" onclick="formatText('**', '**')" style="padding: 4px 10px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; font-weight: bold; font-family: sans-serif;">B</button>
        <button class="fmt-btn" onclick="formatText('<u>', '</u>')" style="padding: 4px 10px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; text-decoration: underline; font-family: sans-serif;">U</button>
        <button class="fmt-btn" onclick="formatText('<mark>', '</mark>')" style="padding: 4px 10px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; font-family: sans-serif;">🖍️ Grifar</button>
        <button class="fmt-btn" onclick="formatText('\\n- ', '')" style="padding: 4px 10px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; font-family: sans-serif;">📋 Tópico</button>
    </div>
    <script>
    document.querySelectorAll('.fmt-btn').forEach(btn => {
        btn.addEventListener('mousedown', function(e) {
            e.preventDefault(); 
        });
    });
    
    function formatText(tagStart, tagEnd) {
        const parentDoc = window.parent.document;
        const textareas = parentDoc.querySelectorAll('textarea');
        if (textareas.length === 0) return;
        
        let ta = null;
        if (parentDoc.activeElement && parentDoc.activeElement.tagName === 'TEXTAREA') {
            ta = parentDoc.activeElement;
        } else {
            for(let i=textareas.length-1; i>=0; i--){
                let label = textareas[i].getAttribute('aria-label');
                if(label && (label.includes('Pontos') || label.includes('Anotação') || label.includes('Resumo') || label.includes('Tópicos'))) {
                    ta = textareas[i];
                    break;
                }
            }
            if(!ta) ta = textareas[textareas.length - 1];
        }

        if(ta) {
            const start = ta.selectionStart;
            const end = ta.selectionEnd;
            const text = ta.value;
            const selectedText = text.substring(start, end);
            
            const newText = text.substring(0, start) + tagStart + selectedText + tagEnd + text.substring(end);
            
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
            nativeInputValueSetter.call(ta, newText);
            
            const event = new Event('input', { bubbles: true });
            ta.dispatchEvent(event);
            
            ta.focus();
            ta.setSelectionRange(start + tagStart.length, start + tagStart.length + selectedText.length);
        }
    }
    </script>
    """
    components.html(toolbar_html, height=35)

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
    if "temp_theme" not in st.session_state: st.session_state.temp_theme = "Escuro"
    aplicar_css_tema(st.session_state.temp_theme)
    
    st.title("🏥 Residência PRO ⚡")
    st.session_state.temp_theme = st.radio("Tema Visual:", ["Escuro", "Claro"], horizontal=True, index=0 if st.session_state.temp_theme == "Escuro" else 1)
    
    aba_l, aba_c = st.tabs(["🔑 Acesso VIP", "📝 Nova Conta"])
    with aba_l:
        if cookie_controller is None: st.warning("⚠️ Biblioteca 'streamlit-cookies-controller' não detectada.")
        with st.form("login_form"):
            u, p, lembrar = st.text_input("Usuário"), st.text_input("Senha", type="password"), st.checkbox("Manter-me conectado")
            if st.form_submit_button("Entrar no Sistema", use_container_width=True):
                try:
                    logou = False
                    u_limpo = u.strip()
                    p_limpo = p.strip()
                    for doc in db.collection("usuarios").get():
                        nome_banco = str(doc.to_dict().get("nome", "")).strip()
                        if nome_banco.lower() == u_limpo.lower():
                            if doc.to_dict().get("senha") == hash_senha(p) or doc.to_dict().get("senha") == hash_senha(p_limpo):
                                st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                                logou = True
                                if lembrar and cookie_controller:
                                    novo_token = str(uuid.uuid4())
                                    db.collection("usuarios").document(doc.id).update({"token_sessao": novo_token})
                                    cookie_controller.set('mr_token', novo_token, max_age=30*24*60*60, path='/')
                                    time.sleep(1) # Sincronização do Websocket para gravar o cookie com segurança
                                st.rerun()
                    if not logou: st.error("Usuário ou senha incorretos.")
                except Exception as e: st.error(f"🚨 Erro no Firebase: {e}")
    with aba_c:
        with st.form("cadastro_form"):
            nu, np = st.text_input("Novo Usuário"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar", use_container_width=True):
                nu_limpo = nu.strip()
                np_limpo = np.strip()
                existe = False
                for doc in db.collection("usuarios").get():
                    if str(doc.to_dict().get("nome", "")).strip().lower() == nu_limpo.lower():
                        existe = True
                        break
                if existe: st.error("Usuário já existe.")
                else:
                    db.collection("usuarios").add({"nome": nu_limpo, "senha": hash_senha(np_limpo), "tema_modo": st.session_state.temp_theme})
                    st.toast("✅ Conta criada com sucesso!", icon="🎉")

# ==========================================
# APLICATIVO LOGADO
# ==========================================
else:
    u_id, hoje = str(st.session_state.user_id), get_agora().date()
    
    if 'dados' not in st.session_state:
        st.session_state.dados = {
            "aulas": [], "revisoes": [], "flashcards": [], 
            "questoes": [], "simulados": [], "focus": [], 
            "materiais": [], "cronogramas": [], "anotacoes": [],
            "questoes_hiit": [], "revisoes_hiit": [], "anotacoes_hiit": []
        }

    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Carregando seus dados da nuvem..."):
            try:
                user_doc = db.collection("usuarios").document(u_id).get()
                st.session_state.user_settings = user_doc.to_dict() if user_doc.exists else {}
                
                aulas_recuperadas = get_user_docs("aulas", u_id)
                revisoes_recuperadas = get_user_docs("revisoes", u_id)
                questoes_hiit_recuperadas = get_user_docs("questoes_hiit", u_id)
                revisoes_hiit_recuperadas = get_user_docs("revisoes_hiit", u_id)
                anotacoes_hiit_recuperadas = get_user_docs("anotacoes_hiit", u_id)

                st.session_state.dados = {
                    "aulas": aulas_recuperadas,
                    "revisoes": revisoes_recuperadas,
                    "flashcards": get_user_docs("flashcards", u_id),
                    "questoes": get_user_docs("questoes_sessoes", u_id),
                    "simulados": get_user_docs("simulados", u_id),
                    "focus": get_user_docs("focus_sessoes", u_id),
                    "materiais": get_user_docs("materiais", u_id),
                    "cronogramas": get_user_docs("cronogramas", u_id),
                    "anotacoes": get_user_docs("anotacoes", u_id),
                    "questoes_hiit": questoes_hiit_recuperadas,
                    "revisoes_hiit": revisoes_hiit_recuperadas,
                    "anotacoes_hiit": anotacoes_hiit_recuperadas
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
    mapa_aulas = {str(a.get("id")).strip(): a for a in dados_aulas} 
    dados_revisoes = _dados_cache.get("revisoes", [])
    dados_questoes = _dados_cache.get("questoes", [])
    dados_flashcards = _dados_cache.get("flashcards", [])
    dados_simulados = _dados_cache.get("simulados", [])
    dados_focus = _dados_cache.get("focus", [])
    dados_materiais = _dados_cache.get("materiais", [])
    dados_cronogramas = _dados_cache.get("cronogramas", [])
    dados_anotacoes = _dados_cache.get("anotacoes", [])
    dados_questoes_hiit = _dados_cache.get("questoes_hiit", [])
    dados_revisoes_hiit = _dados_cache.get("revisoes_hiit", [])
    dados_anotacoes_hiit = _dados_cache.get("anotacoes_hiit", [])

    # APLICA O TEMA DO USUARIO LOGADO
    modo_atual = user_settings.get("tema_modo", "Escuro")
    aplicar_css_tema(modo_atual)

    # BARRA LATERAL (PROFILE)
    if user_settings.get('foto_perfil_b64'):
        st.sidebar.markdown(f'<img src="data:image/jpeg;base64,{user_settings["foto_perfil_b64"]}" class="profile-img">', unsafe_allow_html=True)
        st.sidebar.markdown(f"<h3 style='text-align: center; margin-top: 15px; margin-bottom: 25px; letter-spacing: 0.5px;'>{st.session_state.user_nome}</h3>", unsafe_allow_html=True)
    else: st.sidebar.title(f"👤 {st.session_state.user_nome}")

    if st.sidebar.button("🚪 Sair da Conta", use_container_width=True):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        time.sleep(0.5)
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown("---")

    # ==========================================
    # MENU REORGANIZADO
    # ==========================================
    opcoes_menu = [
        "🏠 Dashboard",
        "🗓️ Cronograma IA",
        "⚡ Revisão HIIT",
        "🎯 Questões",
        "📚 Registro de Aulas",
        "📝 Anotações Rápidas",
        "📅 Agenda de Revisões",
        "✨ AI Tutor & Flashcards",
        "📁 Materiais e Simulados",
        "🏥 Simulados & OSCE",
        "📍 GPS da Aprovação",
        "⏱️ Modo Foco",
        "⚙️ Configurações",
        "📱 Instalar App"
    ]
    
    if is_super_admin(st.session_state.user_nome): 
        opcoes_menu.append("👑 Admin")
        
    menu = st.sidebar.radio("Navegação Principal", opcoes_menu)

    # ==========================================
    # TELAS
    # ==========================================
    if menu == "🏠 Dashboard":
        st.header("Painel de Desempenho Global")
        
        # --- ALERTA NÍTIDO DE REVISÕES NO DASHBOARD ---
        revs_pendentes_dash = [r for r in dados_revisoes + dados_revisoes_hiit if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
        revs_hoje_lista = [r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) <= hoje]
        prox_revs_lista = sorted([r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
        data_prox_dash = formatar_data_br(prox_revs_lista[0].get('data_agendada')) if prox_revs_lista else "Nenhuma agendada"
        
        st.info(f"📅 **Sua Próxima Revisão Futura será em:** {data_prox_dash}")
        if revs_hoje_lista:
            st.warning(f"🚨 **Atenção:** Você tem **{len(revs_hoje_lista)}** revisões para fazer HOJE. Vá na aba de Revisões.")
        else:
            st.success("✅ Você não tem revisões para fazer hoje. Tudo em dia!")
        st.divider()
        # --------------------------------------------------------
        
        qs_sess_all = [dict(q) for q in dados_questoes]
        qs_revs_all = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        
        qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
        revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        
        aba_geral, aba_detalhada = st.tabs(["📊 Resumo Geral", "📈 Análise por Matéria"])
        with aba_geral:
            t_acertos_g = sum(safe_int(q.get('acertos')) for q in qs_sess_all) + sum(safe_int(r.get('acertos')) for r in qs_revs_all) + sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
            t_erros_g = sum(safe_int(q.get('erros')) for q in qs_sess_all) + sum(safe_int(r.get('erros')) for r in qs_revs_all) + sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
            t_questoes_g = t_acertos_g + t_erros_g
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões Totais", t_questoes_g)
            c2.metric("🟢 Acertos", t_acertos_g)
            c3.metric("🔴 Erros", t_erros_g)
            c4.metric("🎯 Taxa de Acerto", f"{(t_acertos_g / t_questoes_g * 100) if t_questoes_g > 0 else 0:.1f}%")
            
            st.divider()
            col_g1, col_g2 = st.columns([1, 1.5])
            
            modo_grafico_font = "#f8fafc" if st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' else "#0f172a"
            
            with col_g1:
                if t_questoes_g > 0: 
                    fig_pie1 = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_g, t_erros_g], hole=0.6, color_discrete_sequence=["#2563eb", '#ef4444'])
                    fig_pie1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie1, use_container_width=True, config={'displayModeBar': False}, theme=None)
            with col_g2:
                todas_questoes_grafico = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_sess_all] + [{"area": r.get('area_aula', r.get('area')), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in qs_revs_all] + [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_hiit_all] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in revs_hiit_all]
                df_r = pd.DataFrame(todas_questoes_grafico).dropna(subset=['area'])
                if not df_r.empty:
                    df_g = df_r.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_g['Taxa'] = (df_g['acertos'] / (df_g['acertos'] + df_g['erros'])) * 100
                    fig_bar1 = px.bar(df_g.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS)
                    fig_bar1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_bar1, use_container_width=True, config={'displayModeBar': False}, theme=None)

        with aba_detalhada:
            filtro_dash = st.selectbox("Selecione a Especialidade para analisar:", AREAS_MED)
            qs_sess_f = [q for q in qs_sess_all if q.get('area') == filtro_dash]
            qs_revs_f = [r for r in qs_revs_all if r.get('area_aula', r.get('area')) == filtro_dash]
            qs_hiit_f = [q for q in qs_hiit_all if q.get('area') == filtro_dash]
            revs_hiit_f = [r for r in revs_hiit_all if r.get('area') == filtro_dash]
            
            t_acertos_f = sum(safe_int(q.get('acertos')) for q in qs_sess_f) + sum(safe_int(r.get('acertos')) for r in qs_revs_f) + sum(safe_int(q.get('acertos')) for q in qs_hiit_f) + sum(safe_int(r.get('acertos')) for r in revs_hiit_f)
            t_erros_f = sum(safe_int(q.get('erros')) for q in qs_sess_f) + sum(safe_int(r.get('erros')) for r in qs_revs_f) + sum(safe_int(q.get('erros')) for q in qs_hiit_f) + sum(safe_int(r.get('erros')) for r in revs_hiit_f)
            t_questoes_f = t_acertos_f + t_erros_f
            
            c1_f, c2_f, c3_f = st.columns(3)
            c1_f.metric(f"Questões ({filtro_dash})", t_questoes_f)
            c2_f.metric("🟢 Acertos", t_acertos_f)
            c3_f.metric("🎯 Aproveitamento", f"{(t_acertos_f / t_questoes_f * 100) if t_questoes_f > 0 else 0:.1f}%")

    elif menu == "📱 Instalar App":
        st.header("Transforme o sistema em um Aplicativo Nativo")
        col1, col2 = st.columns(2)
        with col1: 
            with st.container(border=True):
                st.subheader("🤖 No Android (Chrome)"); st.markdown("1. Toque nos **3 pontinhos**.\n2. Selecione **Adicionar à tela inicial**.\n3. Confirme.")
        with col2: 
            with st.container(border=True):
                st.subheader("🍎 No iPhone (Safari)"); st.markdown("1. Toque no botão **Compartilhar**.\n2. Selecione **Adicionar à Tela de Início**.\n3. Confirme.")

    elif menu == "🗓️ Cronograma IA":
        st.header("Cronograma Inteligente da Semana")
        
        if 'prints_colados' not in st.session_state: st.session_state.prints_colados = []
        
        aba_lista, aba_importar, aba_manual = st.tabs(["✅ Minhas Metas", "📸 Extrair com IA", "➕ Adicionar Manualmente"])
        
        with aba_importar:
            nome_semana = st.text_input("Qual é o nome desta semana? (Ex: Semana 1, Reta Final)")
            col_btn, col_arq = st.columns(2)
            
            with col_btn:
                st.markdown("### 📋 Colar Prints (Suporta Múltiplos)")
                st.caption("Clique no botão azul abaixo e aperte Ctrl+V várias vezes para colar vários prints seguidos.")
                if paste_image_button is not None:
                    paste_result = paste_image_button(
                        label="CLIQUE AQUI E APERTE Ctrl+V",
                        background_color="#2563eb",
                        hover_background_color="#1d4ed8",
                        key="paste_crono"
                    )
                    if paste_result.image_data is not None:
                        img = paste_result.image_data
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        img_hash = hashlib.md5(buf.getvalue()).hexdigest()
                        
                        if not any(item['hash'] == img_hash for item in st.session_state.prints_colados):
                            st.session_state.prints_colados.append({'hash': img_hash, 'img': img, 'bytes': buf.getvalue()})
                            st.rerun()
                else:
                    st.warning("⚠️ Para habilitar o botão de colar mágico, adicione `streamlit-paste-button` no requirements.txt.")
                
                if st.session_state.prints_colados:
                    st.toast(f"{len(st.session_state.prints_colados)} print(s) na fila para extração.", icon="📸")
                    if st.button("Limpar Fila de Prints"):
                        st.session_state.prints_colados = []
                        st.rerun()
                        
            with col_arq:
                st.markdown("### 📂 Enviar Arquivos Tradicional")
                st.caption("Ou anexe múltiplos arquivos de imagem aqui.")
                imgs_crono = st.file_uploader("Selecione os arquivos", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")
            
            st.divider()
            
            if (imgs_crono or st.session_state.prints_colados) and nome_semana and st.button("🪄 Extrair Metas com IA", use_container_width=True):
                client_ia = get_ia_client()
                if not client_ia: st.error("IA não conectada. Configure a GROQ_KEY nos Secrets.")
                else:
                    with st.spinner("Visão Computacional analisando imagens uma a uma para evitar bloqueios de limite..."):
                        
                        todas_imagens_b64 = []
                        if imgs_crono:
                            for img in imgs_crono:
                                todas_imagens_b64.append(otimizar_imagem_para_api(img, max_size=720))
                        
                        if st.session_state.prints_colados:
                            for item in st.session_state.prints_colados:
                                todas_imagens_b64.append(otimizar_imagem_para_api(item['img'], max_size=720))
                        
                        tarefas_totais = []
                        if todas_imagens_b64:
                            barra_progresso = st.progress(0)
                            prompt_visao = """[SISTEMA NÍVEL 5] Extraia RIGOROSAMENTE TODAS as tarefas visíveis na imagem, do início ao fim (não pule nenhuma). 
                            Crie um objeto JSON com formato: {"tarefas": [{"materia": "...", "tema": "...", "cor": "..."}]}
                            MUITO IMPORTANTE: Para economizar limite da API, retorne APENAS o JSON puro MINIFICADO (sem quebras de linha e sem espaços). PROIBIDO usar <think> ou explicar."""
                            
                            for idx_img, img_b64 in enumerate(todas_imagens_b64):
                                conteudo_api = [
                                    {"type": "text", "text": prompt_visao},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
                                ]
                                try:
                                    try:
                                        resposta = client_ia.chat.completions.create(
                                            model=MODELO_VISAO, 
                                            messages=[{"role": "user", "content": conteudo_api}], 
                                            temperature=0.1,
                                            max_tokens=2500
                                        )
                                    except Exception as e_api:
                                        if "rate" in str(e_api).lower() or "429" in str(e_api) or "413" in str(e_api):
                                            time.sleep(12) 
                                            resposta = client_ia.chat.completions.create(
                                                model=MODELO_VISAO, 
                                                messages=[{"role": "user", "content": conteudo_api}], 
                                                temperature=0.1,
                                                max_tokens=2500
                                            )
                                        else:
                                            raise e_api
                                    
                                    tarefas_lote = extrair_json_seguro(resposta.choices[0].message.content).get("tarefas", [])
                                    tarefas_totais.extend(tarefas_lote)
                                except Exception as e:
                                    st.warning(f"Aviso na imagem {idx_img+1}: {e}")
                                barra_progresso.progress((idx_img + 1) / len(todas_imagens_b64))
                        
                        if not tarefas_totais:
                            st.warning("A IA processou as imagens, mas não encontrou tarefas no formato esperado.")
                        else:
                            batch = db.batch()
                            
                            for t in tarefas_totais:
                                c = str(t.get("cor", "")).lower()
                                p = 3
                                if "azul" in c: p = 1
                                elif "verde" in c: p = 2
                                elif "amarelo" in c: p = 3
                                elif "vermelho" in c: p = 4
                                elif "roxo" in c: p = 5
                                t["prioridade"] = p
                                
                            tarefas_totais.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
                            dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
                            
                            for i, t in enumerate(tarefas_totais):
                                dia_idx = (i // 4) % len(dias_semana)
                                t_dia = dias_semana[dia_idx]
                                
                                doc_ref = db.collection("cronogramas").document()
                                nova_tarefa = {
                                    "usuario_id": u_id,
                                    "semana": nome_semana,
                                    "dia": t_dia,
                                    "materia": t.get("materia", ""),
                                    "tema": t.get("tema", ""),
                                    "prioridade": safe_int(t.get("prioridade", 3)),
                                    "concluido": False,
                                    "data_importacao": str(hoje),
                                    "data_conclusao": None
                                }
                                batch.set(doc_ref, nova_tarefa)
                                nova_tarefa["id"] = doc_ref.id
                                st.session_state.dados["cronogramas"].append(nova_tarefa)
                            batch.commit()
                            
                            st.session_state.prints_colados = []
                            st.toast(f"✅ {len(tarefas_totais)} metas importadas e distribuídas!", icon="🎉")
                            time.sleep(1)
                            st.rerun()

        with aba_manual:
            st.markdown("### ➕ Inserir Aula Manualmente no Cronograma")
            c3, c4 = st.columns(2)
            m_materia = c3.selectbox("Matéria", AREAS_MED + ["Outra"], key="crono_mat")
            sub_m = ""
            if m_materia == "Clínica Médica":
                sub_m = c4.selectbox("Subespecialidade", SUB_CM, key="crono_sub_cm")
            elif m_materia == "Cirurgia Geral":
                sub_m = c4.selectbox("Subespecialidade", SUB_CG, key="crono_sub_cg")
                
            with st.form("form_crono_manual", clear_on_submit=True):
                c1, c2 = st.columns(2)
                m_semana = c1.text_input("Nome da Semana (Ex: Semana 1)")
                m_dia = c2.selectbox("Dia da Semana", ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"])
                
                m_tema = st.text_input("Tema da Aula")
                m_prio = st.selectbox("Prioridade (Cor)", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x))
                
                if st.form_submit_button("Adicionar Meta ao Cronograma", use_container_width=True):
                    if not m_semana or not m_tema:
                        st.error("Preencha a Semana e o Tema para adicionar.")
                    else:
                        tema_final = f"{sub_m} - {m_tema}" if sub_m and sub_m != "Geral" else m_tema
                        db_add("cronogramas", "cronogramas", {
                            "usuario_id": u_id,
                            "semana": m_semana,
                            "dia": m_dia,
                            "materia": m_materia,
                            "tema": tema_final,
                            "prioridade": m_prio,
                            "concluido": False,
                            "data_importacao": str(hoje),
                            "data_conclusao": None
                        })
                        st.toast("✅ Meta adicionada com sucesso!", icon="🎯")
                        time.sleep(0.5)
                        st.rerun()

        with aba_lista:
            meu_crono = dados_cronogramas
            
            def sort_key_week(sem):
                dates = [parse_data(c.get("data_importacao", str(hoje))) for c in meu_crono if c.get("semana", "Semana Geral") == sem]
                max_d = max(dates) if dates else parse_data(None)
                nums = re.findall(r'\d+', sem)
                num = int(nums[0]) if nums else 0
                return (max_d, num)
                
            semanas_unicas = sorted(list(set([c.get("semana", "Semana Geral") for c in meu_crono])), key=sort_key_week, reverse=True)
            
            if not meu_crono: 
                st.info("Você ainda não tem nenhum cronograma. Vá na aba 'Adicionar Cronograma' para começar!")
            else:
                termo_pesquisa = st.text_input("🔍 Pesquisar aula, tema ou matéria...", "")
            
            for sem in semanas_unicas:
                tarefas_semana = [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]
                
                if termo_pesquisa:
                    termo_pesquisa_lower = termo_pesquisa.lower()
                    tarefas_semana = [c for c in tarefas_semana if termo_pesquisa_lower in str(c.get('tema', '')).lower() or termo_pesquisa_lower in str(c.get('materia', '')).lower()]
                
                if termo_pesquisa and not tarefas_semana:
                    continue

                st.write("---")
                col_titulo, col_del_sem = st.columns([0.7, 0.3])
                with col_titulo: st.subheader(f"📂 {sem}")
                with col_del_sem:
                    if st.button("🗑️ Excluir Semana Toda", key=f"del_sem_{sem}"):
                        batch = db.batch()
                        ids_del = []
                        for t_del in [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]: 
                            t_id = str(t_del.get('id', '0'))
                            if t_id != '0':
                                batch.delete(db.collection("cronogramas").document(t_id))
                                ids_del.append(t_id)
                        batch.commit()
                        st.session_state.dados["cronogramas"] = [c for c in st.session_state.dados["cronogramas"] if str(c.get('id')) not in ids_del]
                        st.rerun()

                pendentes = [c for c in tarefas_semana if not c.get("concluido", False)]
                concluidos = [c for c in tarefas_semana if c.get("concluido", False)]
                pendentes.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
                
                if pendentes:
                    for t in pendentes:
                        t_id = str(t.get('id', uuid.uuid4()))
                        with st.container(border=True):
                            col1, col2, col3, col4 = st.columns([0.1, 0.55, 0.25, 0.1])
                            with col1:
                                if st.button("✔️", key=f"btn_{t_id}"):
                                    db_update("cronogramas", "cronogramas", t_id, {"concluido": True, "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")})
                                    st.toast("Mandou bem! Mais uma concluída.", icon="🔥")
                                    st.rerun()
                            with col2: st.markdown(f"**{t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
                            with col3:
                                p_val = safe_int(t.get('prioridade', 3))
                                novo_p = st.selectbox("Prioridade", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x, "🟨 Amarelo"), index=[1,2,3,4,5].index(p_val) if p_val in [1,2,3,4,5] else 2, key=f"pri_{t_id}", label_visibility="collapsed")
                                if novo_p != p_val: 
                                    db_update("cronogramas", "cronogramas", t_id, {"prioridade": novo_p})
                                    st.rerun()
                            with col4:
                                if st.button("🗑️", key=f"del_p_{t_id}"): 
                                    db_delete("cronogramas", "cronogramas", t_id)
                                    st.rerun()
                elif not termo_pesquisa:
                    st.success("🎉 Nenhuma aula pendente nesta semana!")

                if concluidos:
                    st.divider()
                    with st.expander(f"✅ Histórico ({len(concluidos)})"):
                        for t in reversed(concluidos):
                            dc = t.get('data_conclusao', '')
                            try:
                                if len(str(dc)) > 10:
                                    dc_fmt = datetime.strptime(str(dc), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M")
                                else:
                                    dc_fmt = formatar_data_br(dc)
                            except:
                                dc_fmt = formatar_data_br(dc)
                            st.markdown(f"~~[{PRIORIDADES.get(safe_int(t.get('prioridade', 3)), '')}] {t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~ *(Check: {dc_fmt})*")

    elif menu == "⚡ Revisão HIIT":
        st.header("⚡ Revisão Intensiva (HIIT MedCof)")
        aba_dash_hiit, aba_reg_hiit, aba_cal_hiit, aba_notas_hiit = st.tabs(["⚡ Dashboard HIIT", "📝 Registrar Questões", "📅 Calendário", "📓 Anotações HIIT"])

        with aba_dash_hiit:
            st.markdown("### ⚡ Desempenho Exclusivo HIIT")
            
            qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
            revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
            
            t_acertos_h = sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
            t_erros_h = sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
            t_questoes_h = t_acertos_h + t_erros_h
            
            c1_h, c2_h, c3_h, c4_h = st.columns(4)
            c1_h.metric("Questões HIIT", t_questoes_h)
            c2_h.metric("🟢 Acertos", t_acertos_h)
            c3_h.metric("🔴 Erros", t_erros_h)
            c4_h.metric("🎯 Taxa HIIT", f"{(t_acertos_h / t_questoes_h * 100) if t_questoes_h > 0 else 0:.1f}%")
            
            st.divider()
            col_gh1, col_gh2 = st.columns([1, 1.5])
            
            modo_grafico_font = "#f8fafc" if st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' else "#0f172a"
            
            with col_gh1:
                if t_questoes_h > 0: 
                    fig_pie_h = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_h, t_erros_h], hole=0.6, color_discrete_sequence=["#2563eb", '#ef4444'])
                    fig_pie_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie_h, use_container_width=True, config={'displayModeBar': False}, theme=None)
            with col_gh2:
                todas_questoes_hiit_grafico = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_hiit_all] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in revs_hiit_all]
                df_rh = pd.DataFrame(todas_questoes_hiit_grafico).dropna(subset=['area'])
                if not df_rh.empty:
                    df_gh = df_rh.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_gh['Taxa'] = (df_gh['acertos'] / (df_gh['acertos'] + df_gh['erros'])) * 100
                    fig_bar_h = px.bar(df_gh.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS)
                    fig_bar_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_bar_h, use_container_width=True, config={'displayModeBar': False}, theme=None)

        with aba_reg_hiit:
            col_a, col_sub = st.columns(2)
            a = col_a.selectbox("Área", AREAS_MED, key="hiit_area")
            sub_q = ""
            if a == "Clínica Médica":
                sub_q = col_sub.selectbox("Subespecialidade", SUB_CM, key="hiit_sub_cm")
            elif a == "Cirurgia Geral":
                sub_q = col_sub.selectbox("Subespecialidade", SUB_CG, key="hiit_sub_cg")

            with st.form("hiit_form", clear_on_submit=True):
                st.info("Registre o desempenho do seu bloco HIIT. As revisões serão agendadas num calendário totalmente isolado do sistema tradicional.")
                c1, c2 = st.columns(2)
                s = c1.text_input("Tema da Revisão HIIT")
                d = c2.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2)
                acc, err = ac.number_input("🟢 Acertos", min_value=0), er.number_input("🔴 Erros", min_value=0)
                
                if st.form_submit_button("Registrar e Agendar HIIT", use_container_width=True):
                    s_final = f"{sub_q} - {s}" if sub_q and sub_q != "Geral" else s
                    db_add("questoes_hiit", "questoes_hiit", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": s_final, "acertos": acc, "erros": err})
                    
                    total_q = acc + err
                    if total_q > 0:
                        taxa_acerto = acc / total_q
                        if taxa_acerto < 0.60:
                            ciclo_nome = "🔴 HIIT Alerta (7d)"
                            dias_prox = 7
                        elif taxa_acerto < 0.80:
                            ciclo_nome = "🟡 HIIT Reforço (14d)"
                            dias_prox = 14
                        else:
                            ciclo_nome = "🟢 HIIT Domínio (30d)"
                            dias_prox = 30
                            
                        nova_data = parse_data(str(d)) + timedelta(days=dias_prox)
                        
                        batch = db.batch()
                        ids_del = set()
                        for r_pend in st.session_state.dados.get("revisoes_hiit", []):
                            if str(r_pend.get('status')).lower() in ['pendente', 'pendentes'] and str(r_pend.get('tema')) == s_final:
                                batch.delete(db.collection("revisoes_hiit").document(r_pend['id']))
                                ids_del.add(r_pend['id'])
                        
                        doc_rev = db.collection("revisoes_hiit").document()
                        nova_rev = {
                            "usuario_id": u_id,
                            "area": a,
                            "tema": s_final,
                            "ciclo": ciclo_nome,
                            "data_agendada": str(nova_data),
                            "status": "Pendente"
                        }
                        batch.set(doc_rev, nova_rev)
                        batch.commit()
                        
                        st.session_state.dados["revisoes_hiit"] = [r for r in st.session_state.dados.get("revisoes_hiit", []) if r['id'] not in ids_del]
                        nova_rev['id'] = doc_rev.id
                        st.session_state.dados["revisoes_hiit"].append(nova_rev)
                        
                        st.toast(f"Revisão HIIT agendada para {formatar_data_br(nova_data)}!", icon="⚡")
                    st.rerun()

            if dados_questoes_hiit:
                st.write("---")
                st.markdown("#### Histórico de Sessões HIIT")
                lista_hiit = []
                for b in dados_questoes_hiit:
                    acertos = safe_int(b.get('acertos'))
                    erros = safe_int(b.get('erros'))
                    total = acertos + erros
                    porcentagem = f"{(acertos / total * 100):.1f}%" if total > 0 else "0.0%"
                    lista_hiit.append({
                        "Data_obj": parse_data(b.get('data')),
                        "Data": formatar_data_br(b.get('data')),
                        "Área": b.get('area'),
                        "Subtema": limpar_texto(b.get('subtema')),
                        "Acertos": acertos,
                        "Erros": erros,
                        "% Acertos": porcentagem
                    })
                df_h = pd.DataFrame(lista_hiit).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj"], errors='ignore')
                
                def colorir_porcentagem_hiit(val):
                    try:
                        num = float(str(val).replace('%', ''))
                        if num > 80: return 'color: #22c55e !important; font-weight: bold !important;'
                        elif num >= 60: return 'color: #eab308 !important; font-weight: bold !important;'
                        else: return 'color: #ef4444 !important; font-weight: bold !important;'
                    except: return ''

                if hasattr(df_h.style, "map"):
                    st.table(df_h.style.map(colorir_porcentagem_hiit, subset=['% Acertos']))
                else:
                    st.table(df_h.style.applymap(colorir_porcentagem_hiit, subset=['% Acertos']))

        with aba_cal_hiit:
            todas_pendentes_hiit_cru = [r for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
            atrasadas_h = [r for r in todas_pendentes_hiit_cru if parse_data(r.get('data_agendada')) < hoje]
            hoje_h = [r for r in todas_pendentes_hiit_cru if parse_data(r.get('data_agendada')) == hoje]
            futuras_h = sorted([r for r in todas_pendentes_hiit_cru if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
            
            col_h1, col_h2, col_h3 = st.columns(3)
            with col_h1: st.metric("🚨 HIITs Atrasados", len(atrasadas_h))
            with col_h2: st.metric("🎯 HIITs Para Hoje", len(hoje_h))
            with col_h3: st.metric("📅 Próximo HIIT", formatar_data_br(futuras_h[0].get('data_agendada')) if futuras_h else "Nenhum")

            if atrasadas_h:
                if st.button("🧹 Limpar HIITs Atrasados (Recomeçar a partir de Hoje)", type="primary", use_container_width=True):
                    with st.spinner("Limpando..."):
                        batch = db.batch()
                        ids_del = set()
                        for r in atrasadas_h:
                            batch.delete(db.collection("revisoes_hiit").document(r['id']))
                            ids_del.add(r['id'])
                        batch.commit()
                        st.session_state.dados["revisoes_hiit"] = [r for r in st.session_state.dados.get("revisoes_hiit", []) if r['id'] not in ids_del]
                        st.rerun()
            st.divider()

            c_v_h, c_o_h = st.columns(2)
            visao_h = c_v_h.radio("Filtro:", ["📆 Para Hoje", "🗓️ Próximos 7 Dias", "♾️ Todas Futuras"], horizontal=True, key="vh")
            ordem_h = c_o_h.radio("Ordem:", ["🚨 Urgência", "🆕 Mais Atuais", "🕰️ Mais Antigas"], horizontal=True, key="oh")

            todas_pendentes_hiit = []
            for r_orig in dados_revisoes_hiit:
                if str(r_orig.get('status', '')).lower() not in ['pendente', 'pendentes']: continue
                r = dict(r_orig)
                r['data_agendada_obj'] = parse_data(r.get('data_agendada'))
                r['tema'] = limpar_texto(r.get('tema', 'Sem título'))
                r['area'] = r.get('area', 'Geral')
                todas_pendentes_hiit.append(r)

            if 'cal_mes_hiit' not in st.session_state: st.session_state.cal_mes_hiit = hoje.month
            if 'cal_ano_hiit' not in st.session_state: st.session_state.cal_ano_hiit = hoje.year
            nav_r1, nav_r2, nav_r3 = st.columns([1,2,1])
            with nav_r1:
                if st.button("⬅️ Mês Anterior", key="prev_hiit"):
                    if st.session_state.cal_mes_hiit == 1: st.session_state.cal_mes_hiit, st.session_state.cal_ano_hiit = 12, st.session_state.cal_ano_hiit - 1
                    else: st.session_state.cal_mes_hiit -= 1
                    st.rerun()
            with nav_r2: st.markdown(f"<h3 style='text-align:center; margin:0;'>📅 {MESES_PT[st.session_state.cal_mes_hiit]} {st.session_state.cal_ano_hiit}</h3>", unsafe_allow_html=True)
            with nav_r3:
                if st.button("Próximo Mês ➡️", key="next_hiit"):
                    if st.session_state.cal_mes_hiit == 12: st.session_state.cal_mes_hiit, st.session_state.cal_ano_hiit = 1, st.session_state.cal_ano_hiit + 1
                    else: st.session_state.cal_mes_hiit += 1
                    st.rerun()

            st.markdown(gerar_calendario_revisoes_html(todas_pendentes_hiit, st.session_state.cal_ano_hiit, st.session_state.cal_mes_hiit), unsafe_allow_html=True)
            st.divider()

            if visao_h == "📆 Para Hoje":
                lista_pendentes_h = [r for r in todas_pendentes_hiit if r['data_agendada_obj'] == hoje]
            elif visao_h == "🗓️ Próximos 7 Dias":
                lista_pendentes_h = [r for r in todas_pendentes_hiit if hoje <= r['data_agendada_obj'] <= (hoje + timedelta(days=7))]
            else:
                lista_pendentes_h = [r for r in todas_pendentes_hiit if r['data_agendada_obj'] >= hoje]
            
            if "Urgência" in ordem_h: lista_pendentes_h.sort(key=lambda x: x['data_agendada_obj'])
            else: lista_pendentes_h.sort(key=lambda x: x['data_agendada_obj'], reverse=("Atuais" in ordem_h))

            if not lista_pendentes_h: st.success("🎉 Tudo em dia no seu projeto HIIT!")
            for r in lista_pendentes_h:
                with st.container(border=True):
                    st.markdown(f"**<span style='color:{CORES_AREAS.get(r['area'], '#64748b')};'>⬤</span> {r['tema']}**", unsafe_allow_html=True)
                    st.caption(f"Status: {r.get('ciclo','')} | Agendado: {formatar_data_br(r['data_agendada_obj'])}")
                    with st.expander("✅ Marcar HIIT como Feito"):
                        if st.button("Concluir Sessão", key=f"hiit_btn_{r['id']}", use_container_width=True):
                            db_update("revisoes_hiit", "revisoes_hiit", r['id'], {"status": "Concluída", "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")})
                            st.toast("✅ HIIT Concluído!", icon="🚀")
                            time.sleep(0.5)
                            st.rerun()

        with aba_notas_hiit:
            if 'hiit_nota_imgs_temp' not in st.session_state: st.session_state.hiit_nota_imgs_temp = []
            if st.session_state.get('limpar_nova_nota_hiit', False):
                st.session_state.hiit_nota_imgs_temp = []
                st.session_state.limpar_nova_nota_hiit = False
                
            aba_hn1, aba_hn2 = st.tabs(["➕ Novo Resumo HIIT", "📖 Cadernos HIIT"])
            with aba_hn1:
                col_b, col_i = st.columns([1, 2])
                with col_b:
                    st.markdown("### 🖼️ Colar Imagem")
                    if paste_image_button is not None:
                        res_paste_hiit = paste_image_button(
                            label="Colar Imagem (Ctrl+V)",
                            background_color="#2563eb", hover_background_color="#1d4ed8",
                            key="paste_hiit_nota"
                        )
                        if res_paste_hiit.image_data is not None:
                            ib64 = otimizar_imagem_para_api(res_paste_hiit.image_data, max_size=1024)
                            if ib64 and ib64 not in st.session_state.hiit_nota_imgs_temp:
                                st.session_state.hiit_nota_imgs_temp.append(ib64)
                                st.rerun()
                with col_i:
                    if st.session_state.hiit_nota_imgs_temp:
                        cols = st.columns(3)
                        for idx, img_b64 in enumerate(st.session_state.hiit_nota_imgs_temp):
                            with cols[idx % 3]:
                                if isinstance(img_b64, str) and len(img_b64)>50:
                                    try: st.image(base64.b64decode(img_b64), use_container_width=True)
                                    except: pass
                                if st.button("🗑️", key=f"rm_hiit_img_{idx}"):
                                    st.session_state.hiit_nota_imgs_temp.pop(idx)
                                    st.rerun()
                
                st.markdown("### ✍️ Escrever Resumo")
                col_ah, col_sh = st.columns(2)
                area_h = col_ah.selectbox("Grande Área", AREAS_MED, key="sel_bloco_hiit")
                sub_ah = ""
                if area_h == "Clínica Médica":
                    sub_ah = col_sh.selectbox("Subespecialidade", SUB_CM, key="hiit_sub_cm_nota")
                elif area_h == "Cirurgia Geral":
                    sub_ah = col_sh.selectbox("Subespecialidade", SUB_CG, key="hiit_sub_cg_nota")

                with st.form("form_hiit_nota", clear_on_submit=True):
                    sub_h = st.text_input("Tema / Assunto")
                    render_toolbar()
                    txt_h = st.text_area("Anotação / Tópicos Chaves", height=200)
                    if st.form_submit_button("💾 Salvar Resumo HIIT", use_container_width=True):
                        if sub_h and txt_h:
                            s_final_h = f"{sub_ah} - {sub_h}" if sub_ah and sub_ah != "Geral" else sub_h
                            db_add("anotacoes_hiit", "anotacoes_hiit", {
                                "usuario_id": u_id, "area": area_h, "subtema": s_final_h, "pontos_chave": txt_h,
                                "imagens_b64": st.session_state.hiit_nota_imgs_temp, "data_criacao": str(hoje)
                            })
                            st.session_state.limpar_nova_nota_hiit = True
                            st.toast("✅ Anotação salva no Caderno HIIT!", icon="📝")
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error("Preencha o tema e a anotação.")
                            
            with aba_hn2:
                if not dados_anotacoes_hiit:
                    st.info("Nenhum resumo HIIT cadastrado.")
                else:
                    pesq_h = st.text_input("🔍 Pesquisar...", key="pesq_hiit")
                    notas_h_exibir = list(dados_anotacoes_hiit)
                    if pesq_h:
                        t_low = pesq_h.lower()
                        notas_h_exibir = [n for n in notas_h_exibir if t_low in str(n.get('subtema','')).lower() or t_low in str(n.get('pontos_chave','')).lower()]
                    notas_h_exibir.sort(key=lambda x: parse_data(x.get('data_criacao')), reverse=True)
                    
                    blocos_presentes = sorted(list(set([n.get('area', 'Clínica Médica') for n in notas_h_exibir])))
                    if not notas_h_exibir:
                        st.warning("Nada encontrado.")
                    else:
                        abas_b = st.tabs(blocos_presentes)
                        for i, bl in enumerate(blocos_presentes):
                            with abas_b[i]:
                                for nh in [x for x in notas_h_exibir if x.get('area') == bl]:
                                    id_nh = str(nh.get('id', '00'))
                                    with st.expander(f"📝 {limpar_texto(nh.get('subtema'))} - {formatar_data_br(nh.get('data_criacao'))}"):
                                        c_d1, c_d2 = st.columns([0.85, 0.15])
                                        with c_d2:
                                            if st.button("🗑️ Excluir", key=f"del_h_{id_nh}", use_container_width=True):
                                                db_delete("anotacoes_hiit", "anotacoes_hiit", id_nh)
                                                st.toast("Anotação excluída!", icon="🗑️")
                                                time.sleep(0.5)
                                                st.rerun()
                                                
                                        st.markdown(f"<div style='border-left: 3px solid #2563eb; padding-left: 15px; margin-top: 10px; margin-bottom: 20px;'>\n\n{nh.get('pontos_chave', '')}\n\n</div>", unsafe_allow_html=True)
                                        
                                        imgs_exibir = list(nh.get('imagens_b64', []))
                                        if imgs_exibir:
                                            st.write("") 
                                            cols_view = st.columns(max(1, min(len(imgs_exibir), 4)))
                                            for idx_v, img_b64_v in enumerate(imgs_exibir):
                                                with cols_view[idx_v % 4]:
                                                    if isinstance(img_b64_v, str) and len(img_b64_v) > 50:
                                                        try: st.image(base64.b64decode(img_b64_v), use_container_width=True)
                                                        except: pass

                                        st.divider()
                                        
                                        with st.container(border=True):
                                            st.markdown("#### 🧠 Gerar Revisão Ativa (IA)")
                                            col_ia1, col_ia2 = st.columns(2)
                                            with col_ia1:
                                                if st.button("🪄 Extrair Flashcards Atômicos", key=f"fc_ia_{id_nh}", use_container_width=True):
                                                    client_ia = get_ia_client()
                                                    if client_ia:
                                                        with st.spinner("Gerando flashcards atômicos..."):
                                                            try:
                                                                prompt_fc = f"""[SISTEMA NÍVEL 5] Extraia estritamente os fatos atômicos, decorebas e critérios diagnósticos deste resumo. Crie um objeto JSON: {{"flashcards": [{{"frente": "...", "verso": "..."}}]}}
                                                                Retorne APENAS o JSON puro. Não explique.
                                                                Resumo: {nh.get('pontos_chave', '')}"""
                                                                r_fc = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_fc}], temperature=0.1, max_tokens=1500)
                                                                fcs = extrair_json_seguro(r_fc.choices[0].message.content).get("flashcards", [])
                                                                if fcs:
                                                                    batch = db.batch()
                                                                    for fc in fcs:
                                                                        doc_ref = db.collection("flashcards").document()
                                                                        n_fc = {"usuario_id": u_id, "area": nh.get('area'), "tema": limpar_texto(nh.get('subtema')), "frente": fc.get('frente'), "verso": fc.get('verso'), "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                                                                        batch.set(doc_ref, n_fc)
                                                                        n_fc["id"] = doc_ref.id
                                                                        st.session_state.dados["flashcards"].append(n_fc)
                                                                    batch.commit()
                                                                    st.success(f"✅ {len(fcs)} Flashcards gerados e adicionados ao deck!")
                                                                else:
                                                                    st.warning("IA não conseguiu extrair cartões válidos.")
                                                            except Exception as e: st.error(f"Erro IA: {e}")
                                            with col_ia2:
                                                if st.button("🔥 Criar Bateria de Questões", key=f"q_ia_{id_nh}", use_container_width=True):
                                                    client_ia = get_ia_client()
                                                    if client_ia:
                                                        with st.spinner("Construindo caso clínico estilo banca..."):
                                                            try:
                                                                prompt_q = f"[SISTEMA NÍVEL 5] Você é banca de residência médica. Use os conceitos DESTE resumo para criar um mini-simulado de 3 questões de caso clínico. Inclua alternativas e gabarito comentado focado em explicar o conceito.\nResumo: {nh.get('pontos_chave', '')}"
                                                                r_q = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_q}], temperature=0.4, max_tokens=3000)
                                                                st.session_state[f"q_gerada_{id_nh}"] = r_q.choices[0].message.content
                                                            except Exception as e: st.error(f"Erro IA: {e}")
                                            if st.session_state.get(f"q_gerada_{id_nh}"):
                                                st.markdown(st.session_state[f"q_gerada_{id_nh}"])

                                        st.divider()
                                        
                                        # --- BOTÃO DE EDITAR INDIVIDUAL (HIIT) ---
                                        if st.session_state.get('nota_hiit_em_edicao') != id_nh:
                                            if st.button("✏️ Editar esta Anotação", key=f"btn_abrir_edit_h_{id_nh}"):
                                                st.session_state.nota_hiit_em_edicao = id_nh
                                                st.rerun()
                                        else:
                                            if st.button("❌ Cancelar Edição", key=f"btn_cancel_edit_h_{id_nh}"):
                                                st.session_state.nota_hiit_em_edicao = None
                                                st.rerun()
                                                
                                            st.markdown("#### 🖼️ Imagens da Anotação")
                                            col_ebtn, col_eimg = st.columns([1, 2])
                                            with col_ebtn:
                                                st.markdown("➕ **Adicionar Mais Imagens:**")
                                                if paste_image_button is not None:
                                                    res_paste_edit = paste_image_button(
                                                        label="Colar Imagem (Ctrl+V)",
                                                        background_color="#2563eb",
                                                        hover_background_color="#1d4ed8",
                                                        key=f"paste_edit_h_{id_nh}" 
                                                    )
                                                    if res_paste_edit.image_data is not None:
                                                        img_eb64 = otimizar_imagem_para_api(res_paste_edit.image_data, max_size=1024)
                                                        if img_eb64 and img_eb64 not in imgs_exibir:
                                                            imgs_exibir.append(img_eb64)
                                                            db_update("anotacoes_hiit", "anotacoes_hiit", id_nh, {"imagens_b64": imgs_exibir})
                                                            st.rerun()
                                            with col_eimg:
                                                if imgs_exibir:
                                                    cols_e = st.columns(max(1, min(len(imgs_exibir), 3)))
                                                    for idx_e, img_b64_e in enumerate(imgs_exibir):
                                                        with cols_e[idx_e % 3]:
                                                            if isinstance(img_b64_e, str) and len(img_b64_e) > 50:
                                                                try: st.image(base64.b64decode(img_b64_e), use_container_width=True)
                                                                except: pass
                                                            if st.button("🗑️ Remover", key=f"rmv_medit_h_{id_nh}_{idx_e}"):
                                                                imgs_exibir.pop(idx_e)
                                                                db_update("anotacoes_hiit", "anotacoes_hiit", id_nh, {"imagens_b64": imgs_exibir})
                                                                st.rerun()

                                            st.markdown("#### ✍️ Editar Texto")
                                            
                                            col_eah, col_esh = st.columns(2)
                                            edit_ah = col_eah.selectbox("Grande Área", AREAS_MED, index=AREAS_MED.index(nh.get('area')) if nh.get('area') in AREAS_MED else 0, key=f"ea_h_{id_nh}")
                                            sub_eah = ""
                                            if edit_ah == "Clínica Médica":
                                                sub_eah = col_esh.selectbox("Subespecialidade", SUB_CM, key=f"sub_eah_cm_{id_nh}")
                                            elif edit_ah == "Cirurgia Geral":
                                                sub_eah = col_esh.selectbox("Subespecialidade", SUB_CG, key=f"sub_eah_cg_{id_nh}")

                                            s_puro_h = nh.get('subtema', '')
                                            if " - " in s_puro_h and s_puro_h.split(" - ")[0] in SUB_CM:
                                                s_puro_h = " - ".join(s_puro_h.split(" - ")[1:])
                                            elif " - " in s_puro_h and s_puro_h.split(" - ")[0] in SUB_CG:
                                                s_puro_h = " - ".join(s_puro_h.split(" - ")[1:])
                                                
                                            with st.form(f"form_edicao_h_{id_nh}", clear_on_submit=False):
                                                edit_sh = st.text_input("Subtema", value=s_puro_h)
                                                render_toolbar()
                                                edit_ph = st.text_area("Anotação / Tópicos Chaves", value=nh.get('pontos_chave', ''), height=200)
                                                
                                                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                                    if edit_sh and edit_ph:
                                                        edit_sh_final = f"{sub_eah} - {edit_sh}" if sub_eah and sub_eah != "Geral" else edit_sh
                                                        db_update("anotacoes_hiit", "anotacoes_hiit", id_nh, {"area": edit_ah, "subtema": edit_sh_final, "pontos_chave": edit_ph})
                                                        st.session_state.nota_hiit_em_edicao = None
                                                        st.toast("✅ Anotação atualizada!", icon="📝")
                                                        time.sleep(0.5)
                                                        st.rerun()
                                                    else:
                                                        st.error("Preencha o subtema e a anotação para salvar.")

    elif menu == "🎯 Questões":
        aba_reg, aba_erros, aba_alvos = st.tabs(["📝 Registrar & Agendar Revisão", "🧠 Caderno de Erros Ativo", "🚨 Alvos Críticos"])
        
        with aba_reg:
            col_a, col_sub = st.columns(2)
            a = col_a.selectbox("Área", AREAS_MED, key="q_area")
            sub_q = ""
            if a == "Clínica Médica":
                sub_q = col_sub.selectbox("Subespecialidade", SUB_CM, key="q_sub_cm")
            elif a == "Cirurgia Geral":
                sub_q = col_sub.selectbox("Subespecialidade", SUB_CG, key="q_sub_cg")
                
            with st.form("q_form", clear_on_submit=True):
                st.info("Ao registrar suas questões, o sistema irá recalcular o seu desempenho e reagendar a sua próxima revisão automaticamente.")
                c1, c2 = st.columns(2)
                s = c1.text_input("Subtema (Ex: Insuficiência Cardíaca)")
                d = c2.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2)
                acc, err = ac.number_input("🟢 Acertos", min_value=0), er.number_input("🔴 Erros", min_value=0)
                cc = st.text_input("Conceito Chave (Motivo de algum erro)")
                
                if st.form_submit_button("Registrar e Agendar Revisão Inteligente", use_container_width=True):
                    s_final = f"{sub_q} - {s}" if sub_q and sub_q != "Geral" else s
                    db_add("questoes_sessoes", "questoes", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": s_final, "acertos": acc, "erros": err, "conceito_chave": cc})
                    
                    # --- NOVO MOTOR DE REPETIÇÃO ESPAÇADA ADAPTATIVA ---
                    total_q = acc + err
                    if total_q > 0:
                        taxa_acerto = acc / total_q
                        if taxa_acerto < 0.60:
                            ciclo_nome = "🔴 Crítico (Rever em 1d)"
                            dias_prox = 1
                        elif taxa_acerto < 0.80:
                            ciclo_nome = "🟡 Reforço (Rever em 7d)"
                            dias_prox = 7
                        else:
                            ciclo_nome = "🟢 Domínio (Rever em 15d)"
                            dias_prox = 15
                            
                        nova_data = parse_data(str(d)) + timedelta(days=dias_prox)
                        
                        batch = db.batch()
                        ids_del = set()
                        for r_pend in st.session_state.dados["revisoes"]:
                            if str(r_pend.get('status')).lower() in ['pendente', 'pendentes'] and str(r_pend.get('tema')) == s_final:
                                batch.delete(db.collection("revisoes").document(r_pend['id']))
                                ids_del.add(r_pend['id'])
                        
                        doc_rev = db.collection("revisoes").document()
                        nova_rev = {
                            "usuario_id": u_id,
                            "area": a,
                            "tema": s_final,
                            "ciclo": ciclo_nome,
                            "data_agendada": str(nova_data),
                            "status": "Pendente"
                        }
                        batch.set(doc_rev, nova_rev)
                        batch.commit()
                        
                        st.session_state.dados["revisoes"] = [r for r in st.session_state.dados["revisoes"] if r['id'] not in ids_del]
                        nova_rev['id'] = doc_rev.id
                        st.session_state.dados["revisoes"].append(nova_rev)
                        
                        st.toast(f"Revisão agendada para {formatar_data_br(nova_data)}!", icon="📅")
                    # -------------------------------------------------------------------
                    
                    st.toast("Questões registradas!", icon="✅")
                    time.sleep(1)
                    st.rerun()
            
            if dados_questoes: 
                lista_q = []
                for b in dados_questoes:
                    acertos = safe_int(b.get('acertos'))
                    erros = safe_int(b.get('erros'))
                    total = acertos + erros
                    porcentagem = f"{(acertos / total * 100):.1f}%" if total > 0 else "0.0%"
                    
                    lista_q.append({
                        "Data_obj": parse_data(b.get('data')),
                        "Data": formatar_data_br(b.get('data')),
                        "Área": b.get('area'),
                        "Subtema": limpar_texto(b.get('subtema')),
                        "Acertos": acertos,
                        "Erros": erros,
                        "% Acertos": porcentagem,
                        "ID": b.get('id')
                    })
                df_q = pd.DataFrame(lista_q).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj", "ID"], errors='ignore')
                
                def colorir_porcentagem(val):
                    try:
                        num = float(str(val).replace('%', ''))
                        if num > 80:
                            return 'color: #22c55e !important; font-weight: bold !important;'
                        elif num >= 70:
                            return 'color: #eab308 !important; font-weight: bold !important;'
                        elif num >= 60:
                            return 'color: #3b82f6 !important; font-weight: bold !important;'
                        else:
                            return 'color: #ef4444 !important; font-weight: bold !important;'
                    except:
                        return ''

                if hasattr(df_q.style, "map"):
                    st.table(df_q.style.map(colorir_porcentagem, subset=['% Acertos']))
                else:
                    st.table(df_q.style.applymap(colorir_porcentagem, subset=['% Acertos']))
                
                st.write("---")
                with st.expander("✏️ Editar ou Excluir Registro de Questões"):
                    opcoes_edicao = {}
                    for q_item in dados_questoes:
                        data_formatada = formatar_data_br(q_item.get('data'))
                        q_id = str(q_item.get('id', '0000'))
                        chave = f"{data_formatada} | {q_item.get('area')} - {limpar_texto(q_item.get('subtema'))} (ID: {q_id[:4]})"
                        opcoes_edicao[chave] = q_item
                        
                    if opcoes_edicao:
                        q_selec = st.selectbox("Selecione o registro que deseja alterar:", list(opcoes_edicao.keys()))
                        q_dados = opcoes_edicao[q_selec]
                        q_id_alvo = str(q_dados.get('id', '0000'))
                        
                        col_e1, col_e2 = st.columns(2)
                        novo_ac = col_e1.number_input("Editar Acertos", min_value=0, value=safe_int(q_dados.get('acertos')), key=f"ac_{q_id_alvo}")
                        novo_er = col_e2.number_input("Editar Erros", min_value=0, value=safe_int(q_dados.get('erros')), key=f"er_{q_id_alvo}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button("💾 Salvar Alterações", use_container_width=True, key=f"sv_{q_id_alvo}"):
                            if q_dados.get('id'):
                                db_update("questoes_sessoes", "questoes", q_id_alvo, {"acertos": novo_ac, "erros": novo_er})
                                st.toast("Registro atualizado com sucesso!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Erro: Registro sem ID.")
                            
                        if col_btn2.button("🗑️ Excluir Registro", use_container_width=True, key=f"dl_{q_id_alvo}"):
                            if q_dados.get('id'):
                                db_delete("questoes_sessoes", "questoes", q_id_alvo)
                                st.toast("Registro excluído!", icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("Erro: Registro sem ID.")
                
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
                                resposta_clone = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_clonagem}], temperature=0.4, max_tokens=2500)
                                with st.container(border=True): st.markdown(resposta_clone.choices[0].message.content)
                            except Exception as e: st.error(str(e))
                
                st.write("---")
                st.write("**Transformar Conceito Errado em Flashcard**")
                frente_erro = st.text_input("Frente da Carta", value=f"O que devo lembrar sobre: {conceito_alvo}")
                verso_erro = st.text_area("Verso (Resposta correta)")
                if st.button("💾 Salvar direto no Deck"):
                    db_add("flashcards", "flashcards", {"usuario_id": u_id, "area": area_alvo, "tema": tema_alvo, "frente": frente_erro, "verso": verso_erro, "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                    st.toast("Flashcard adicionado aos estudos!", icon="🧠")
            else: st.success("Nenhum erro registrado com Conceito Chave.")

        with aba_alvos:
            st.markdown("### ⚠️ Mapeamento de Pontos Cegos")
            st.caption("O sistema calcula a sua média nas últimas 3 baterias de questões de cada subtema. Abaixo de 60%, o tema entra na zona vermelha e a IA pode intervir.")
            
            historico_dict = {}
            for q in sorted(dados_questoes, key=lambda x: parse_data(x.get('data')), reverse=True):
                t_str = f"{q.get('area')} - {limpar_texto(q.get('subtema'))}"
                if t_str not in historico_dict: historico_dict[t_str] = []
                if len(historico_dict[t_str]) < 3:
                    historico_dict[t_str].append({"ac": safe_int(q.get('acertos')), "er": safe_int(q.get('erros'))})
            
            alvos_criticos = []
            for t_str, sessoes in historico_dict.items():
                t_ac = sum(s['ac'] for s in sessoes)
                t_er = sum(s['er'] for s in sessoes)
                t_total = t_ac + t_er
                if t_total > 0:
                    media = t_ac / t_total
                    if media < 0.6:
                        alvos_criticos.append({"Tema": t_str, "Média": media, "Total": t_total})
                        
            if not alvos_criticos:
                st.success("🎉 Você não tem nenhum Alvo Crítico no momento. Seu desempenho está excelente!")
            else:
                alvos_criticos.sort(key=lambda x: x['Média'])
                df_alvos = pd.DataFrame([{"Subtema Analisado": a["Tema"], "Desempenho Recente": f"{a['Média']*100:.1f}%", "Questões Base": a["Total"]} for a in alvos_criticos])
                st.table(df_alvos)
                
                st.write("---")
                if st.button("🔥 Gerar Simulado de Recuperação com IA", use_container_width=True):
                    client_ia = get_ia_client()
                    if client_ia:
                        piores_3 = [a['Tema'] for a in alvos_criticos[:3]]
                        prompt_recup = f"[SISTEMA NÍVEL 5] Você é um tutor médico focado em recuperação. O aluno está com desempenho crítico (abaixo de 60%) nos seguintes temas: {', '.join(piores_3)}. Crie um mini-simulado com 1 questão de caso clínico rigoroso (estilo residência) para cada um desses temas, com alternativas e gabarito comentado focado em explicar o conceito-chave. Não escreva introduções."
                        with st.spinner("Convocando o Tutor IA para montar seu plano de recuperação. Aguarde..."):
                            try:
                                resposta_recup = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_recup}], temperature=0.3, max_tokens=3000)
                                with st.container(border=True):
                                    st.markdown(resposta_recup.choices[0].message.content)
                            except Exception as e:
                                st.error(f"Erro ao gerar simulado: {e}")

    elif menu == "✨ AI Tutor & Flashcards":
        aba_chat, aba_flash, aba_feynman = st.tabs(["🧠 Tutor Virtual IA", "📚 Flashcards", "🎙️ Técnica Feynman"])
        with aba_chat:
            chat_box = st.container(height=500)
            if 'chat_ia' not in st.session_state: st.session_state.chat_ia = []
            with chat_box:
                for msg in st.session_state.chat_ia:
                    with st.chat_message(msg.get("role", "user")): st.write(msg.get("content", ""))
            
            u_in = st.chat_input("Dúvida médica, prescrições...", key="input_tutor")
            if u_in:
                client_ia = get_ia_client()
                if client_ia:
                    with st.spinner("Analisando..."):
                        msgs_api = [{"role": "system", "content": "Você é um Preceptor Médico Sênior. É OBRIGATÓRIO fornecer cálculos de doses exatas, prescrições e diagnósticos diretos. O usuário É UM MÉDICO LICENCIADO."}]
                        st.session_state.chat_ia.append({"role": "user", "content": u_in})
                        for m in st.session_state.chat_ia: msgs_api.append({"role": m["role"], "content": str(m["content"])})
                        try:
                            r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=msgs_api, temperature=0.2, max_tokens=2500)
                            st.session_state.chat_ia.append({"role": "assistant", "content": r.choices[0].message.content})
                        except Exception as e: st.error(str(e))
                        st.rerun()

        with aba_flash:
            aba_f1, aba_f2, aba_f3 = st.tabs(["Modo Estudo", "Adicionar", "📥 Importar Anki (CSV)"])
            with aba_f1:
                cards_hoje = [d for d in dados_flashcards if parse_data(d.get('data_prox_revisao')) <= hoje]
                if cards_hoje:
                    c_data = cards_hoje[0]
                    c_data_id = str(c_data.get("id", "000"))
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
                                db_update("flashcards", "flashcards", c_data_id, {"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))})
                                st.session_state.ans = False; st.rerun()
                            if b1.button("🔴 Errei (1d)", use_container_width=True): avaliar('err')
                            if b2.button("🟡 Bom", use_container_width=True): avaliar('bom')
                            if b3.button("🟢 Fácil", use_container_width=True): avaliar('facil')
                else: st.success("🎉 Você zerou o deck de hoje. Parabéns!")
            
            with aba_f2:
                col_a, col_t = st.columns(2)
                a = col_a.selectbox("Área", AREAS_MED, key="fc_area")
                sub_f = ""
                if a == "Clínica Médica":
                    sub_f = col_t.selectbox("Subespecialidade", SUB_CM, key="fc_sub_cm")
                elif a == "Cirurgia Geral":
                    sub_f = col_t.selectbox("Subespecialidade", SUB_CG, key="fc_sub_cg")
                    
                with st.form("add_fc", clear_on_submit=True):
                    t = st.text_input("Tema")
                    f = st.text_input("Frente da Carta")
                    v = st.text_area("Verso da Carta")
                    if st.form_submit_button("Salvar no Banco", use_container_width=True):
                        t_final = f"{sub_f} - {t}" if sub_f and sub_f != "Geral" else t
                        db_add("flashcards", "flashcards", {"usuario_id": u_id, "area": a, "tema": t_final or "Sem Tema", "frente": f, "verso": v, "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                        st.toast("Flashcard salvo!", icon="📚")
                        time.sleep(0.5)
                        st.rerun()
            
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
                                    doc_ref = db.collection("flashcards").document()
                                    n_fc = {"usuario_id": u_id, "area": str(row['Area']).strip(), "tema": str(row['Tema']).strip(), "frente": str(row['Frente']).strip(), "verso": str(row['Verso']).strip(), "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                                    batch.set(doc_ref, n_fc)
                                    n_fc["id"] = doc_ref.id
                                    st.session_state.dados["flashcards"].append(n_fc)
                                batch.commit()
                            st.toast("✅ Flashcards importados com sucesso!")
                            st.rerun()
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
                            r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": "Avalie rigidamente o aluno."}, {"role": "user", "content": f"Avalie: '{tema_f}'. Transcrição: '{transcription.text}'."}], temperature=0.2, max_tokens=2500)
                            st.success(r.choices[0].message.content)
                        except Exception as e: st.error(f"Erro: {e}")

    elif menu == "📚 Registro de Aulas":
        st.header("Biblioteca Pessoal de Conteúdo")
        col_form, col_lista = st.columns([1, 2.5])
        with col_form:
            st.subheader("➕ Adicionar Aula")
            st.caption("Aulas não geram mais revisões automáticas (Apenas questões). O registro aqui serve apenas para seu histórico.")
            c_area, c_sub = st.columns(2)
            a = c_area.selectbox("Especialidade", AREAS_MED, key="aula_area")
            sub_al = ""
            if a == "Clínica Médica":
                sub_al = c_sub.selectbox("Subespecialidade", SUB_CM, key="aula_sub_cm")
            elif a == "Cirurgia Geral":
                sub_al = c_sub.selectbox("Subespecialidade", SUB_CG, key="aula_sub_cg")
                
            with st.form("n_aula", clear_on_submit=True):
                t = st.text_input("Assunto da Aula (Tema)")
                d = st.date_input("Data Assistida", hoje, format="DD/MM/YYYY")
                if st.form_submit_button("Registrar Aula no Histórico", use_container_width=True):
                    doc_a = db.collection("aulas").document()
                    t_final = f"{sub_al} - {t}" if sub_al and sub_al != "Geral" else t
                    n_aula = {"usuario_id": u_id, "area": a, "tema": t_final or "Aula", "data_aula": str(d)}
                    doc_a.set(n_aula)
                    n_aula["id"] = doc_a.id
                    st.session_state.dados["aulas"].append(n_aula)
                    st.toast("Aula registrada com sucesso!", icon="📚")
                    time.sleep(0.5)
                    st.rerun()
                    
            with st.expander("🗑️ Excluir Aula do Banco"):
                opcoes_del_dict = {f"{formatar_data_br(a.get('data_aula'))} - {limpar_texto(a.get('tema'))}": a.get('id') for a in dados_aulas}
                if opcoes_del_dict:
                    op_del_chave = st.selectbox("Selecione para apagar:", list(opcoes_del_dict.keys()))
                    if st.button("Deletar Aula", use_container_width=True) and op_del_chave:
                        id_del = str(opcoes_del_dict[op_del_chave])
                        db.collection("aulas").document(id_del).delete()
                        st.session_state.dados["aulas"] = [au for au in st.session_state.dados["aulas"] if str(au.get("id")) != id_del]
                        st.toast("Aula apagada.", icon="🗑️")
                        time.sleep(0.5)
                        st.rerun()

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
                    db_add("focus_sessoes", "focus", {"usuario_id": u_id, "data_sessao": str(hoje), "minutos_foco": st.session_state.foco_min})
                    st.session_state.foco_iniciado = False; st.rerun()

    elif menu == "📁 Materiais e Simulados":
        st.header("Gerenciador de PDFs")
        arq = st.file_uploader("Upload PDF de Estudo", type=['pdf'])
        if arq and st.button("Salvar na Nuvem", use_container_width=True):
            caminho = os.path.join("materiais_estudo", arq.name)
            with open(caminho, "wb") as f: f.write(arq.getbuffer())
            db_add("materiais", "materiais", {"usuario_id": u_id, "titulo": arq.name, "path": caminho, "data_upload": str(hoje)})
            st.toast("Salvo com sucesso!", icon="📄")
            
        if dados_materiais: 
            st.write("---")
            st.subheader("Meus Arquivos")
            for mat in dados_materiais:
                mat_id = str(mat.get('id', '0000'))
                with st.container(border=True):
                    col_t, col_d, col_v, col_del = st.columns([4, 1, 1, 1])
                    col_t.markdown(f"**{mat.get('titulo')}**")
                    col_d.caption(f"Data: {formatar_data_br(mat.get('data_upload'))}")
                    
                    if os.path.exists(mat.get('path', '')):
                        with open(mat['path'], "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            col_v.download_button("📥 Baixar", data=pdf_bytes, file_name=mat.get('titulo'), key=f"dl_{mat_id}")
                    else:
                        col_v.warning("Arquivo perdido.")
                        
                    if col_del.button("🗑️ Excluir", key=f"del_{mat_id}"):
                        db_delete("materiais", "materiais", mat_id)
                        if os.path.exists(mat.get('path', '')): os.remove(mat['path'])
                        st.rerun()

    elif menu == "🏥 Simulados & OSCE":
        st.header("Simulador Interativo")
        aba_p, aba_simulado, aba_sim_pdf, aba_osce = st.tabs(["📝 Notas", "🤖 Simulado IA (Imagens)", "📄 Simulado de PDF", "🗣️ Consultório OSCE"])
        
        with aba_p:
            with st.form("sim_f", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                ins, an, dt = c1.selectbox("Instituição", INSTITUICOES), c2.text_input("Ano da Prova"), c3.date_input("Data de Resolução", hoje, format="DD/MM/YYYY")
                co, no = st.columns(2)
                cor, notl = co.number_input("Nota de Corte (Alvo)", min_value=0.0), no.number_input("Sua Nota Líquida", min_value=0.0)
                if st.form_submit_button("Inserir Nota no Gráfico", use_container_width=True):
                    db_add("simulados", "simulados", {"usuario_id": u_id, "instituicao": ins, "ano": an, "data_realizacao": str(dt), "nota_corte": cor, "minha_nota": notl})
                    st.rerun()
            if len(dados_simulados) >= 3:
                dfs = pd.DataFrame([{"D": parse_data(s.get('data_realizacao')), "N": float(s.get('minha_nota',0)), "C": float(s.get('nota_corte',0))} for s in dados_simulados])
                dfs['DU'] = pd.to_numeric(pd.to_datetime(dfs['D']))
                if len(dfs['DU'].unique()) > 1:
                    x_vals = dfs['DU'].values
                    y_vals = dfs['N'].values
                    coefs = np.polyfit(x_vals, y_vals, 1)
                    poly_func = np.poly1d(coefs)
                    
                    fut = [dfs['D'].max() + timedelta(days=30*i) for i in range(1, 4)]
                    fut_x = pd.to_numeric(pd.to_datetime(fut)).values
                    p = poly_func(fut_x)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=dfs['D'], y=dfs['N'], name="Sua Evolução Real", line=dict(color="#2563eb", width=3)))
                    fig.add_trace(go.Scatter(x=fut, y=p, name="Projeção IA", line=dict(color="#ef4444", dash='dot')))
                    
                    modo_grafico_font = "#f8fafc" if st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' else "#0f172a"
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, theme=None)

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
                                    buf_p = io.BytesIO(); img.save(buf_p, format="JPEG")
                                    todas_imagens_b64.append(otimizar_imagem_para_api(buf_p.getvalue(), max_size=500))
                            except Exception as e_pdf: st.error(f"Erro no PDF: {e_pdf}")
                        if imgs_prova:
                            for img in imgs_prova: 
                                todas_imagens_b64.append(otimizar_imagem_para_api(img, max_size=500))
                        if colagem_img_sim:
                            buf = io.BytesIO(); colagem_img_sim.save(buf, format="PNG")
                            todas_imagens_b64.append(otimizar_imagem_para_api(buf.getvalue(), max_size=500))

                    if todas_imagens_b64:
                        st.session_state.prova_ativa = []
                        st.session_state.respostas_usuario = {}
                        barra_progresso = st.progress(0)
                        
                        for i in range(len(todas_imagens_b64)):
                            img_b64 = todas_imagens_b64[i]
                            prompt = """Extraia as questões da imagem e retorne um JSON no formato {"questoes": [{"num": 1, "texto": "Enunciado...", "opcoes": {"A": "...", "B": "..."}, "correta": "B", "comentario": "..."}]}
                            Retorne apenas o JSON. Não pense, não explique e não use tags markdown."""
                            try:
                                msg_api = [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]}]
                                resposta = client_ia.chat.completions.create(model=MODELO_VISAO, messages=msg_api, temperature=0.1, max_tokens=1200)
                                questoes_lote = extrair_json_seguro(resposta.choices[0].message.content).get("questoes", [])
                                for q in questoes_lote: q['imagem_fonte'] = img_b64
                                st.session_state.prova_ativa.extend(questoes_lote)
                            except Exception as e: st.warning(f"Erro na página {i+1}: {e}")
                            barra_progresso.progress((i + 1) / len(todas_imagens_b64))
                        st.toast("🎉 Extração concluída!")
                        st.rerun()

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
                    db_add("simulados", "simulados", {"usuario_id": u_id, "data_realizacao": str(hoje), "minha_nota": nota_final, "instituicao": "Simulado IA", "nota_corte": 0})
                    
                if st.button("Limpar Prova Atual"): st.session_state.pop("prova_ativa"); st.session_state.pop("respostas_usuario"); st.rerun()

        with aba_sim_pdf:
            st.subheader("Gerar Simulado baseado em seus Materiais (PDF)")
            if not dados_materiais:
                st.warning("Você não tem PDFs salvos na aba 'Materiais e Simulados'.")
            else:
                mat_escolhido = st.selectbox("Escolha o PDF de Estudo:", [m['titulo'] for m in dados_materiais])
                qtd_q = st.slider("Quantidade de Questões", 5, 100, 10)
                st.caption("Atenção: PDFs muito extensos podem ser cortados pela IA devido ao limite de leitura.")
                
                if st.button("Gerar Simulado Exclusivo", use_container_width=True):
                    client_ia = get_ia_client()
                    if client_ia and PyPDF2:
                        caminho_pdf = next(m['path'] for m in dados_materiais if m['titulo'] == mat_escolhido)
                        if os.path.exists(caminho_pdf):
                            with st.spinner(f"Lendo o material e estruturando {qtd_q} questões..."):
                                try:
                                    reader = PyPDF2.PdfReader(caminho_pdf)
                                    texto_pdf = ""
                                    for page in reader.pages: texto_pdf += page.extract_text() + "\n"
                                    texto_pdf = texto_pdf[:20000] # Limite de segurança de tokens da IA
                                    
                                    prompt = f"""Baseado no material fornecido, crie um simulado de {qtd_q} questões. Retorne um JSON no formato: {{"questoes": [{{"num": 1, "texto": "...", "opcoes": {{"A": "...", "B": "..."}}, "correta": "A", "comentario": "..."}}]}}
                                    Material: {texto_pdf}"""
                                    
                                    resposta = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=2500)
                                    questoes_pdf = extrair_json_seguro(resposta.choices[0].message.content).get("questoes", [])
                                    
                                    if questoes_pdf:
                                        st.session_state.prova_ativa = questoes_pdf
                                        st.session_state.respostas_usuario = {}
                                        st.toast("Simulado gerado! Acesse a aba 'Simulado IA'", icon="🎉")
                                    else:
                                        pass # O erro já foi mostrado na função extrair_json_seguro
                                except Exception as e:
                                    st.error(f"Erro ao analisar PDF: {e}")
                        else:
                            st.error("Arquivo PDF não encontrado no servidor físico.")

        with aba_osce:
            client_ia = get_ia_client()
            if client_ia:
                modo_osce = st.radio("Cenário", ["🎯 Doença Específica", "🎲 Surpresa"])
                if modo_osce == "🎯 Doença Específica": doenca_alvo = st.text_input("Doença (Ex: Infarto com supra)")
                else:
                    col_m, col_t = st.columns(2)
                    mat_alvo = col_m.selectbox("Área", AREAS_MED, key="osce_mat")
                    sub_o = ""
                    if mat_alvo == "Clínica Médica":
                        sub_o = col_t.selectbox("Subespecialidade", SUB_CM, key="osce_sub_cm")
                    elif mat_alvo == "Cirurgia Geral":
                        sub_o = col_t.selectbox("Subespecialidade", SUB_CG, key="osce_sub_cg")
                    tema_alvo = st.text_input("Tema", key="osce_tema")

                if st.button("▶️ Abrir Consultório"):
                    st.session_state.osce_hist, st.session_state.osce_active, st.session_state.osce_finished = [], True, False
                    base_p = f"""Você é paciente num OSCE de Medicina. Não diga o diagnóstico de cara. Fale os sintomas. Se o médico pedir um exame dessa lista [{", ".join(BANCO_IMAGENS_OSCE.keys())}], responda com a tag [EXAME: nome_do_exame]."""
                    tema_final = f"{sub_o} - {tema_alvo}" if modo_osce == "🎲 Surpresa" and sub_o and sub_o != "Geral" else (tema_alvo if modo_osce == "🎲 Surpresa" else "")
                    st.session_state.osce_sys_prompt = f"{base_p}\nDoença: {doenca_alvo}." if modo_osce == "🎯 Doença Específica" else f"{base_p}\nSorteie para: {mat_alvo} - {tema_final}."
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
                                    r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": st.session_state.osce_sys_prompt}] + st.session_state.osce_hist + [{"role": "user", "content": f"O aluno prescreveu: {prescricao_final}. Avalie de 0 a 10 e aponte os erros baseados nas diretrizes."}], temperature=0.3, max_tokens=2500)
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
                                    r = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "system", "content": st.session_state.osce_sys_prompt}] + st.session_state.osce_hist, temperature=0.6, max_tokens=1000)
                                    st.session_state.osce_hist.append({"role": "assistant", "content": r.choices[0].message.content})
                                except Exception as e: st.error(f"Erro IA: {e}")
                                st.rerun()

                    if getattr(st.session_state, 'osce_finished', False):
                        st.divider(); st.markdown("### 📋 Avaliação"); st.info(st.session_state.osce_eval)

    elif menu == "⚙️ Configurações":
        st.header("Controle de Perfil")
        uf = st.file_uploader("Foto de Perfil", type=['jpg', 'png'])
        if uf and st.button("Confirmar Foto", use_container_width=True):
            b64_img = base64.b64encode(uf.read()).decode("utf-8")
            db.collection("usuarios").document(u_id).update({"foto_perfil_b64": b64_img})
            st.session_state.user_settings["foto_perfil_b64"] = b64_img
            st.rerun()

        with st.form("tema_form"):
            mo = st.radio("Cores do Sistema", ["Escuro", "Claro"], index=0 if user_settings.get("tema_modo") == "Escuro" else 1)
            if st.form_submit_button("Aplicar Estilo Global", use_container_width=True):
                db.collection("usuarios").document(u_id).update({"tema_modo": mo})
                st.session_state.user_settings["tema_modo"] = mo
                st.rerun()

    elif is_super_admin(st.session_state.user_nome) and menu == "👑 Admin":
        st.header("Painel de Administração Global (Firebase)")
        try:
            usuarios_todos = db.collection("usuarios").get()
            st.write(f"**Contas Ativas:** {len(usuarios_todos)}")
            df_u = pd.DataFrame([{"ID Nuvem": u.id, "Nome": u.to_dict().get('nome')} for u in usuarios_todos])
            st.dataframe(df_u, use_container_width=True, column_config={"ID Nuvem": None})
            
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
                        for col in ["aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "focus_sessoes", "materiais", "cronogramas", "anotacoes", "questoes_hiit", "revisoes_hiit", "anotacoes_hiit"]:
                            for doc in db.collection(col).where(filter=FieldFilter("usuario_id", "==", uid)).get(): db.collection(col).document(doc.id).delete()
                        db.collection("usuarios").document(uid).delete(); invalidar_cache(); st.rerun()
                    else: st.warning("Você não pode banir a si mesmo.")
            
            st.divider()
            st.subheader("📦 Exportação de Backup em Nuvem")
            if st.button("Baixar Dados (JSON)"):
                with st.spinner("Coletando tudo..."):
                    backup_data = {colecao: {d.id: d.to_dict() for d in db.collection(colecao).get()} for colecao in ["usuarios", "aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "cronogramas", "anotacoes", "questoes_hiit", "revisoes_hiit", "anotacoes_hiit"]}
                    st.download_button(label="📥 Baixar snapshot_nuvem.json", data=json.dumps(backup_data, default=str, indent=4), file_name="snapshot_nuvem.json", mime="application/json")
        except Exception as e:
            st.error(f"Erro Admin: {e}")
