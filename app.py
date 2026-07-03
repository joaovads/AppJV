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
        bg_tabela = "#334155" # Cinza chumbo escuro para tabela não ficar preta
        th_bg = "#1e293b"
        cor_texto_tabela = "#f8fafc"
        shadow = "0 4px 6px rgba(0, 0, 0, 0.3)"
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
        bg_tabela = "#f1f5f9" # Cinza claro para tabela
        th_bg = "#e2e8f0"
        cor_texto_tabela = "#0f172a"
        shadow = "0 4px 12px rgba(0, 0, 0, 0.05)"

    css_str = f"""
    <style>
    /* ANIMAÇÃO DE ENTRADA SUAVE */
    @keyframes fadein {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .main {{ animation: fadein 0.4s ease-out; }}
    
    .stApp, [data-testid="stAppViewContainer"], .main {{ background-color: {bg_color} !important; }}
    h1:not(#tmr), h2, h3, h4, h5, h6, p, span, label, div {{ color: {text_color}; font-family: 'Inter', sans-serif; }}
    
    /* INPUTS MODERNOS */
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div, [data-baseweb="select"] > div, [data-testid="stFileUploadDropzone"] {{
        background-color: {input_bg} !important; 
        border: 1px solid {metric_border} !important;
        border-radius: 8px !important;
        transition: border-color 0.3s ease;
    }}
    [data-baseweb="input"] > div:focus-within, [data-baseweb="textarea"] > div:focus-within {{
        border-color: #2563eb !important;
        box-shadow: 0 0 0 1px #2563eb !important;
    }}
    input, textarea, div[data-baseweb="select"] span {{ color: {input_text} !important; -webkit-text-fill-color: {input_text} !important; }}
    
    /* CORREÇÃO DEFINITIVA DOS DROPDOWNS E POPOVERS (SEM TEXTO INVISÍVEL) */
    [data-baseweb="popover"] > div, ul[data-baseweb="menu"] {{ background-color: {input_bg} !important; border: 1px solid {metric_border} !important; border-radius: 8px; box-shadow: {shadow}; }}
    ul[data-baseweb="menu"] li {{ background-color: transparent !important; color: {input_text} !important; padding: 10px; transition: background 0.2s; }}
    ul[data-baseweb="menu"] li:hover {{ background-color: {menu_hover} !important; }}
    ul[data-baseweb="menu"] span {{ color: {input_text} !important; }}
    
    /* CHAT IA */
    [data-testid="stChatInput"] {{ background-color: {bg_color} !important; padding-bottom: 20px; }}
    [data-testid="stChatInput"] > div {{ background-color: {input_bg} !important; border: 1px solid {metric_border} !important; border-radius: 20px !important; }}
    
    /* BOTÕES PRO (TODOS EM AZUL COM HOVER EFFECT) */
    button[kind="primary"], button[kind="secondary"], button[kind="formSubmit"], button[data-testid="baseButton-secondary"], button[data-testid="baseButton-primary"], button[data-testid="baseButton-formSubmit"], .stButton > button, div[data-testid="stFormSubmitButton"] > button {{
        background-color: #2563eb !important; 
        border: none !important; 
        border-radius: 8px !important;
        transition: transform 0.1s ease, box-shadow 0.2s ease !important;
    }}
    button[kind="primary"]:hover, button[kind="secondary"]:hover, .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(37, 99, 235, 0.4) !important;
    }}
    button p, button span, button div {{ color: white !important; font-weight: 600 !important; letter-spacing: 0.3px; }}
    
    /* ABAS (TABS) INTERATIVAS */
    button[data-baseweb="tab"] p, button[data-baseweb="tab"] span {{ color: {text_color} !important; font-weight: 500 !important; transition: color 0.3s; }}
    button[data-baseweb="tab"]:hover p {{ color: #2563eb !important; }}
    
    /* ISOLAMENTO DA TABELA (EVITA BUGAR O CALENDÁRIO) */
    [data-testid="stDataFrame"] > div, [data-testid="stTable"] > div {{ background-color: {bg_tabela} !important; border-radius: 10px; overflow: hidden; box-shadow: {shadow}; }}
    [data-testid="stDataFrame"] th, [data-testid="stTable"] th {{ background-color: {th_bg} !important; color: {cor_texto_tabela} !important; padding: 12px !important; border-bottom: 2px solid {metric_border} !important; text-transform: uppercase; font-size: 12px; letter-spacing: 0.5px; text-align: left; }}
    [data-testid="stDataFrame"] td, [data-testid="stTable"] td {{ background-color: {bg_tabela} !important; color: {cor_texto_tabela} !important; padding: 12px !important; border-bottom: 1px solid {metric_border} !important; border-right: none !important; border-left: none !important; }}
    
    /* CONTAINERS INTERATIVOS */
    div[data-testid='stExpander'] {{ border: 1px solid {metric_border} !important; background-color: {metric_bg} !important; border-radius: 12px; transition: box-shadow 0.3s ease; }}
    div[data-testid='stExpander']:hover {{ box-shadow: {shadow}; }}
    
    div[data-testid="metric-container"] {{ background-color: {metric_bg} !important; border: 1px solid {metric_border} !important; padding: 20px; border-radius: 12px; box-shadow: {shadow}; transition: transform 0.2s ease; }}
    div[data-testid="metric-container"]:hover {{ transform: scale(1.02); }}
    
    /* MENU LATERAL */
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {metric_border} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: 10px 14px; border-radius: 10px; margin-bottom: 6px; background-color: transparent; transition: all 0.2s ease; cursor: pointer; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background-color: {menu_hover} !important; padding-left: 20px; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label p {{ color: {menu_text} !important; font-weight: 500; font-size: 15px; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background-color: #2563eb !important; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.3); }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: white !important; font-weight: 600 !important; }}
    
    .profile-img {{ border-radius: 50%; object-fit: cover; border: 4px solid #2563eb; width: 130px; height: 130px; display: block; margin: 0 auto; box-shadow: 0 4px 10px rgba(0,0,0,0.15); transition: transform 0.3s ease; }}
    .profile-img:hover {{ transform: scale(1.05); cursor: pointer; }}
    </style>
    """
    st.markdown(css_str, unsafe_allow_html=True)


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

for d in ["materiais_estudo", "imagens_flashcards"]:
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
    crases = chr(96) + chr(96) + chr(96)
    texto = texto.replace(crases + "json", "").replace(crases, "").strip()
    try:
        return json.loads(texto)
    except:
        try:
            match = re.search(r'(\{.*\})', texto, re.DOTALL)
            if match: return json.loads(match.group(1))
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
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    if modo == "Escuro":
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#1e293b", "#334155", "#0f172a", "#1e212b", "#94a3b8", "#f8fafc", "#475569"
    else:
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#e0f2fe", "#bae6fd", "#f0f9ff", "#ffffff", "#0369a1", "#0f172a", "#64748b"
        
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
        bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = "#e0f2fe", "#bae6fd", "#f0f9ff", "#ffffff", "#0369a1", "#0f172a", "#64748b"

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
                    for doc in db.collection("usuarios").get():
                        if doc.to_dict().get("nome") == u and doc.to_dict().get("senha") == hash_senha(p):
                            st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                            logou = True
                            if lembrar and cookie_controller:
                                novo_token = str(uuid.uuid4())
                                db.collection("usuarios").document(doc.id).update({"token_sessao": novo_token})
                                cookie_controller.set('mr_token', novo_token, max_age=30*24*60*60, path='/')
                                time.sleep(1)
                            st.rerun()
                    if not logou: st.error("Usuário ou senha incorretos.")
                except Exception as e: st.error(f"🚨 Erro no Firebase: {e}")
    with aba_c:
        with st.form("cadastro_form"):
            nu, np = st.text_input("Novo Usuário"), st.text_input("Senha", type="password")
            if st.form_submit_button("Cadastrar", use_container_width=True):
                if db.collection("usuarios").where("nome", "==", nu).get(): st.error("Usuário já existe.")
                else:
                    db.collection("usuarios").add({"nome": nu, "senha": hash_senha(np), "tema_modo": st.session_state.temp_theme})
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
            "materiais": [], "cronogramas": [], "anotacoes": []
        }

    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Sincronizando ambiente de alta performance..."):
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
                    "cronogramas": get_user_docs("cronogramas", u_id),
                    "anotacoes": get_user_docs("anotacoes", u_id)
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
    dados_anotacoes = _dados_cache.get("anotacoes", [])

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
        st.session_state.clear()
        st.rerun()
    st.sidebar.markdown("---")

    # ==========================================
    # MENU REORGANIZADO
    # ==========================================
    opcoes_menu = [
        "🏠 Dashboard",
        "🗓️ Cronograma IA",
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
    if menu == "📱 Instalar App":
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
                    with st.spinner("Visão Computacional analisando cores e metas... Isso pode levar alguns segundos."):
                        try:
                            prompt_visao = """Analise estes prints de cronograma e extraia os dias, matérias e temas. Atribua prioridade: Azul=1, Verde=2, Amarelo=3, Vermelho=4, Roxo=5. Retorne APENAS um JSON: {"tarefas": [{"dia": "Segunda-feira", "materia": "Ginecologia", "tema": "Sangramento Uterino", "prioridade": 1}]}"""
                            conteudo_api = [{"type": "text", "text": prompt_visao}]
                            
                            if imgs_crono:
                                for img in imgs_crono:
                                    conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img.getvalue()).decode('utf-8')}"}})
                            
                            if st.session_state.prints_colados:
                                for item in st.session_state.prints_colados:
                                    conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(item['bytes']).decode('utf-8')}"}})
                            
                            resposta = client_ia.chat.completions.create(
                                model=MODELO_VISAO, 
                                messages=[{"role": "user", "content": conteudo_api}], 
                                temperature=0.1
                            )
                            
                            tarefas = extrair_json_seguro(resposta.choices[0].message.content).get("tarefas", [])
                            
                            if not tarefas:
                                st.warning("A IA processou as imagens, mas não encontrou tarefas no formato esperado.")
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
                                
                                st.session_state.prints_colados = []
                                st.toast(f"✅ {len(tarefas)} aulas importadas com sucesso!", icon="🎉")
                                invalidar_cache()
                                time.sleep(1.5)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Erro na leitura da imagem. Detalhes: {e}")

        with aba_manual:
            st.markdown("### ➕ Inserir Aula Manualmente no Cronograma")
            with st.form("form_crono_manual", clear_on_submit=True):
                c1, c2 = st.columns(2)
                m_semana = c1.text_input("Nome da Semana (Ex: Semana 1)")
                m_dia = c2.selectbox("Dia da Semana", ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"])
                
                c3, c4 = st.columns(2)
                m_materia = c3.selectbox("Matéria", AREAS_MED + ["Outra"])
                m_tema = c4.text_input("Tema da Aula")
                
                m_prio = st.selectbox("Prioridade (Cor)", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x))
                
                if st.form_submit_button("Adicionar Meta ao Cronograma", use_container_width=True):
                    if not m_semana or not m_tema:
                        st.error("Preencha a Semana e o Tema para adicionar.")
                    else:
                        db.collection("cronogramas").add({
                            "usuario_id": u_id,
                            "semana": m_semana,
                            "dia": m_dia,
                            "materia": m_materia,
                            "tema": m_tema,
                            "prioridade": m_prio,
                            "concluido": False,
                            "data_importacao": str(hoje),
                            "data_conclusao": None
                        })
                        invalidar_cache()
                        st.toast("✅ Meta adicionada com sucesso!", icon="🎯")
                        time.sleep(1)
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
                        for t_del in [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]: batch.delete(db.collection("cronogramas").document(t_del['id']))
                        batch.commit(); invalidar_cache(); st.rerun()

                pendentes = [c for c in tarefas_semana if not c.get("concluido", False)]
                concluidos = [c for c in tarefas_semana if c.get("concluido", False)]
                pendentes.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
                
                if pendentes:
                    for t in pendentes:
                        with st.container(border=True):
                            col1, col2, col3, col4 = st.columns([0.1, 0.55, 0.25, 0.1])
                            with col1:
                                if st.button("✔️", key=f"btn_{t['id']}"):
                                    db.collection("cronogramas").document(t['id']).update({"concluido": True, "data_conclusao": str(get_agora().date())})
                                    invalidar_cache(); st.toast("Mandou bem! Mais uma concluída.", icon="🔥"); time.sleep(0.5); st.rerun()
                            with col2: st.markdown(f"**{t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
                            with col3:
                                p_val = safe_int(t.get('prioridade', 3))
                                novo_p = st.selectbox("Prioridade", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x, "🟨 Amarelo"), index=[1,2,3,4,5].index(p_val) if p_val in [1,2,3,4,5] else 2, key=f"pri_{t['id']}", label_visibility="collapsed")
                                if novo_p != p_val: db.collection("cronogramas").document(t['id']).update({"prioridade": novo_p}); invalidar_cache(); st.rerun()
                            with col4:
                                if st.button("🗑️", key=f"del_p_{t['id']}"): db.collection("cronogramas").document(t['id']).delete(); invalidar_cache(); st.rerun()
                elif not termo_pesquisa:
                    st.success("🎉 Nenhuma aula pendente nesta semana!")

                if concluidos:
                    st.divider()
                    with st.expander(f"✅ Histórico ({len(concluidos)})"):
                        for t in reversed(concluidos):
                            st.markdown(f"~~[{PRIORIDADES.get(safe_int(t.get('prioridade', 3)), '')}] {t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~")

    elif menu == "📝 Anotações Rápidas":
        st.header("Caderno de Resumos e Anotações")
        aba_nova, aba_lista = st.tabs(["➕ Nova Anotação", "📖 Meus Resumos"])
        
        with aba_nova:
            with st.form("form_anotacao", clear_on_submit=True):
                col_a, col_s = st.columns(2)
                a = col_a.selectbox("Grande Área", AREAS_MED)
                s = col_s.text_input("Subtema (Ex: Insuficiência Cardíaca)")
                p = st.text_area("Pontos Chave / Tópicos mais cobrados nas questões", height=150, help="Anote aqui os tópicos mais relevantes.")
                
                if st.form_submit_button("Salvar Anotação", use_container_width=True):
                    if s and p:
                        db.collection("anotacoes").add({
                            "usuario_id": u_id,
                            "area": a,
                            "subtema": s,
                            "pontos_chave": p,
                            "data_criacao": str(hoje)
                        })
                        invalidar_cache()
                        st.toast("✅ Anotação salva com sucesso!", icon="📝")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Preencha o subtema e a anotação para salvar.")

        with aba_lista:
            minhas_anotacoes = dados_anotacoes
            if not minhas_anotacoes:
                st.info("Você ainda não tem anotações. Vá na aba 'Nova Anotação' para começar!")
            else:
                pesquisa_nota = st.text_input("🔍 Pesquisar por subtema, área ou palavra-chave...", "")
                
                notas_exibir = list(minhas_anotacoes)
                if pesquisa_nota:
                    termo = pesquisa_nota.lower()
                    notas_exibir = [n for n in notas_exibir if termo in str(n.get('subtema', '')).lower() or termo in str(n.get('area', '')).lower() or termo in str(n.get('pontos_chave', '')).lower()]
                
                notas_exibir.sort(key=lambda x: parse_data(x.get('data_criacao')), reverse=True)
                
                for nota in notas_exibir:
                    with st.container(border=True):
                        c1, c2 = st.columns([0.85, 0.15])
                        with c1:
                            st.markdown(f"### <span style='color:{CORES_AREAS.get(nota.get('area'), '#64748b')};'>⬤</span> {limpar_texto(nota.get('subtema'))}", unsafe_allow_html=True)
                            st.caption(f"**Área:** {nota.get('area', '')} | **Data:** {formatar_data_br(nota.get('data_criacao'))}")
                        with c2:
                            if st.button("🗑️ Excluir", key=f"del_nota_{nota['id']}", use_container_width=True):
                                db.collection("anotacoes").document(nota['id']).delete()
                                invalidar_cache()
                                st.toast("Anotação excluída!", icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()
                        st.markdown(f"<div style='background-color: transparent; padding: 10px; border-left: 3px solid {CORES_AREAS.get(nota.get('area'), '#64748b')}; margin-top: 10px;'>{html.escape(nota.get('pontos_chave', '')).replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
                        
                        with st.expander("✏️ Editar Anotação"):
                            with st.form(f"edit_nota_{nota['id']}", clear_on_submit=False):
                                col_ea, col_es = st.columns(2)
                                edit_a = col_ea.selectbox("Grande Área", AREAS_MED, index=AREAS_MED.index(nota.get('area')) if nota.get('area') in AREAS_MED else 0, key=f"ea_{nota['id']}")
                                edit_s = col_es.text_input("Subtema", value=nota.get('subtema', ''), key=f"es_{nota['id']}")
                                edit_p = st.text_area("Pontos Chave / Resumo", value=nota.get('pontos_chave', ''), height=150, key=f"ep_{nota['id']}")
                                
                                if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                    if edit_s and edit_p:
                                        db.collection("anotacoes").document(nota['id']).update({
                                            "area": edit_a,
                                            "subtema": edit_s,
                                            "pontos_chave": edit_p
                                        })
                                        invalidar_cache()
                                        st.toast("✅ Anotação atualizada!", icon="📝")
                                        time.sleep(0.5)
                                        st.rerun()
                                    else:
                                        st.error("Preencha o subtema e a anotação para salvar.")

    elif menu == "📍 GPS da Aprovação":
        st.header("GPS da Aprovação")
        alvo = st.selectbox("🎯 Especialidade Foco?", ["Medicina Intensiva", "Clínica Médica", "Anestesiologia", "Cardiologia"])
        if dados_simulados:
            notas = [float(s.get('minha_nota', 0)) for s in dados_simulados]
            st.metric("Sua Média Global", f"{sum(notas)/len(notas):.1f}%")

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
                    fig_pie1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' and '#f8fafc' or '#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie1, use_container_width=True, config={'displayModeBar': False})
            with col_g2:
                todas_questoes_grafico = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_sess_all] + [{"area": r.get('area_aula'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in qs_revs_all]
                df_r = pd.DataFrame(todas_questoes_grafico).dropna(subset=['area'])
                if not df_r.empty:
                    df_g = df_r.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_g['Taxa'] = (df_g['acertos'] / (df_g['acertos'] + df_g['erros'])) * 100
                    fig_bar1 = px.bar(df_g.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS)
                    fig_bar1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' and '#f8fafc' or '#0f172a', showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_bar1, use_container_width=True, config={'displayModeBar': False})

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
                                invalidar_cache(); st.toast("✅ Revisão Concluída!", icon="🚀"); time.sleep(0.5); st.rerun()

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
                        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' and '#f8fafc' or '#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})
                    with c2g: 
                        fig2 = px.bar(df_ag, x="Data", y="Cards")
                        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' and '#f8fafc' or '#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False})
                    
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
                                invalidar_cache(); st.toast("Revisão desfeita!", icon="⏪"); time.sleep(1); st.rerun()

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
                    invalidar_cache(); st.toast("Questões registradas!", icon="✅"); time.sleep(0.5); st.rerun()
            
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
                st.table(df_q)
                
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
                        
                        col_e1, col_e2 = st.columns(2)
                        novo_ac = col_e1.number_input("Editar Acertos", min_value=0, value=safe_int(q_dados.get('acertos')))
                        novo_er = col_e2.number_input("Editar Erros", min_value=0, value=safe_int(q_dados.get('erros')))
                        
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button("💾 Salvar Alterações", use_container_width=True):
                            if q_dados.get('id'):
                                db.collection("questoes_sessoes").document(q_dados['id']).update({
                                    "acertos": novo_ac,
                                    "erros": novo_er
                                })
                                invalidar_cache(); st.toast("Registro atualizado com sucesso!", icon="✅"); time.sleep(0.5); st.rerun()
                            else:
                                st.error("Erro: Registro sem ID.")
                            
                        if col_btn2.button("🗑️ Excluir Registro", use_container_width=True):
                            if q_dados.get('id'):
                                db.collection("questoes_sessoes").document(q_dados['id']).delete()
                                invalidar_cache(); st.toast("Registro excluído!", icon="🗑️"); time.sleep(0.5); st.rerun()
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
                                resposta_clone = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_clonagem}], temperature=0.4, max_tokens=800)
                                with st.container(border=True): st.markdown(resposta_clone.choices[0].message.content)
                            except Exception as e: st.error(str(e))
                
                st.write("---")
                st.write("**Transformar Conceito Errado em Flashcard**")
                frente_erro = st.text_input("Frente da Carta", value=f"O que devo lembrar sobre: {conceito_alvo}")
                verso_erro = st.text_area("Verso (Resposta correta)")
                if st.button("💾 Salvar direto no Deck"):
                    db.collection("flashcards").add({"usuario_id": u_id, "area": area_alvo, "tema": tema_alvo, "frente": frente_erro, "verso": verso_erro, "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5})
                    invalidar_cache(); st.toast("Flashcard adicionado aos estudos!", icon="🧠")
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
                        invalidar_cache(); st.toast("Flashcard salvo!", icon="📚"); st.rerun()
            
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
                            st.toast("✅ Flashcards importados com sucesso!"); time.sleep(1.5); st.rerun()
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
                    invalidar_cache(); st.toast("Aula registrada no ciclo!", icon="📚"); time.sleep(0.5); st.rerun()
                    
            with st.expander("🗑️ Excluir Aula do Banco"):
                opcoes_del_dict = {f"{formatar_data_br(a.get('data_aula'))} - {limpar_texto(a.get('tema'))}": a['id'] for a in dados_aulas}
                if opcoes_del_dict:
                    op_del_chave = st.selectbox("Selecione para apagar:", list(opcoes_del_dict.keys()))
                    if st.button("Deletar Aula e Suas Revisões", use_container_width=True) and op_del_chave:
                        id_del = opcoes_del_dict[op_del_chave]
                        batch = db.batch()
                        for rd in db.collection("revisoes").where("aula_id", "==", id_del).get(): batch.delete(rd.reference)
                        batch.delete(db.collection("aulas").document(id_del))
                        batch.commit(); invalidar_cache(); st.toast("Aula apagada.", icon="🗑️"); time.sleep(0.5); st.rerun()

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
        st.header("Gerenciador de PDFs")
        arq = st.file_uploader("Upload PDF de Estudo", type=['pdf'])
        if arq and st.button("Salvar na Nuvem", use_container_width=True):
            caminho = os.path.join("materiais_estudo", arq.name)
            with open(caminho, "wb") as f: f.write(arq.getbuffer())
            db.collection("materiais").add({"usuario_id": u_id, "titulo": arq.name, "path": caminho, "data_upload": str(hoje)})
            invalidar_cache()
            st.toast("Salvo com sucesso!", icon="📄")
            
        if dados_materiais: 
            st.write("---")
            st.subheader("Meus Arquivos")
            for mat in dados_materiais:
                with st.container(border=True):
                    col_t, col_d, col_v, col_del = st.columns([4, 1, 1, 1])
                    col_t.markdown(f"**{mat.get('titulo')}**")
                    col_d.caption(f"Data: {formatar_data_br(mat.get('data_upload'))}")
                    
                    if os.path.exists(mat.get('path', '')):
                        with open(mat['path'], "rb") as pdf_file:
                            pdf_bytes = pdf_file.read()
                            col_v.download_button("📥 Baixar", data=pdf_bytes, file_name=mat.get('titulo'), key=f"dl_{mat['id']}")
                    else:
                        col_v.warning("Arquivo perdido.")
                        
                    if col_del.button("🗑️ Excluir", key=f"del_{mat['id']}"):
                        db.collection("materiais").document(mat['id']).delete()
                        if os.path.exists(mat.get('path', '')): os.remove(mat['path'])
                        invalidar_cache()
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
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' and '#f8fafc' or '#0f172a', margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

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
                        st.toast("🎉 Extração concluída!"); time.sleep(1); st.rerun()

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
                                    
                                    prompt = f"Baseado puramente no seguinte material médico, crie um simulado de {qtd_q} questões de múltipla escolha. Retorne APENAS um JSON válido no formato: {{\"questoes\": [{{\"num\": 1, \"texto\": \"...\", \"opcoes\": {{\"A\": \"...\", \"B\": \"...\"}}, \"correta\": \"A\", \"comentario\": \"...\"}}]}}. \n\nMaterial: {texto_pdf}"
                                    
                                    resposta = client_ia.chat.completions.create(model=MODELO_TEXTO, messages=[{"role": "user", "content": prompt}], temperature=0.2)
                                    questoes_pdf = extrair_json_seguro(resposta.choices[0].message.content).get("questoes", [])
                                    
                                    if questoes_pdf:
                                        st.session_state.prova_ativa = questoes_pdf
                                        st.session_state.respostas_usuario = {}
                                        st.toast("Simulado gerado! Acesse a aba 'Simulado IA'", icon="🎉")
                                    else:
                                        st.error("A IA não conseguiu formatar o PDF.")
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
                        for col in ["aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "focus_sessoes", "materiais", "cronogramas"]:
                            for doc in db.collection(col).where("usuario_id", "==", uid).get(): db.collection(col).document(doc.id).delete()
                        db.collection("usuarios").document(uid).delete(); invalidar_cache(); st.rerun()
                    else: st.warning("Você não pode banir a si mesmo.")
            
            st.divider()
            st.subheader("📦 Exportação de Backup em Nuvem")
            if st.button("Baixar Dados (JSON)"):
                with st.spinner("Coletando tudo..."):
                    backup_data = {colecao: {d.id: d.to_dict() for d in db.collection(colecao).get()} for colecao in ["usuarios", "aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "cronogramas"]}
                    st.download_button(label="📥 Baixar snapshot_nuvem.json", data=json.dumps(backup_data, default=str, indent=4), file_name="snapshot_nuvem.json", mime="application/json")
        except Exception as e:
            st.error(f"Erro Admin: {e}")
