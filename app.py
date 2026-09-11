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
st.set_page_config(page_title="Residência PRO 2.0", page_icon="🏥", layout="wide")

MODELO_TEXTO = "qwen/qwen3.6-27b"
MODELO_VISAO = "qwen/qwen3.6-27b"
MODELOS_TEXTO_FALLBACK = ["qwen/qwen3.6-27b", "openai/gpt-oss-20b"]
MODELOS_VISAO_FALLBACK = ["qwen/qwen3.6-27b"]

def ativar_pwa():
    pwa_html = """
    <script>
        if (!document.getElementById('pwa-manifest')) {
            const manifest = {
                "name": "Residência PRO",
                "short_name": "Residência",
                "theme_color": "#000000",
                "background_color": "#ffffff",
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
# DESIGN SYSTEM PREMIUM 2.0 (FLUID & LIGHT)
# ==========================================
def aplicar_css_tema(modo):
    if modo == "Escuro":
        bg_color, text_color, metric_bg, metric_border = "#0A0A0A", "#EDEDED", "#171717", "#2E2E2E"
        sidebar_bg, input_bg, input_text, menu_text = "#0A0A0A", "#1A1A1A", "#EDEDED", "#888888"
        menu_hover, bg_tabela, th_bg, cor_texto_tabela = "#242424", "#171717", "#0A0A0A", "#E0E0E0"
        shadow = "0 8px 30px rgba(0,0,0,0.4)"
        shadow_hover = "0 10px 40px rgba(0,0,0,0.6)"
        btn_bg, btn_text, btn_hover = "#EDEDED", "#0A0A0A", "#FFFFFF"
    else:
        bg_color, text_color, metric_bg, metric_border = "#FAFAFA", "#111827", "#FFFFFF", "#E5E7EB"
        sidebar_bg, input_bg, input_text, menu_text = "#FFFFFF", "#F3F4F6", "#111827", "#6B7280"
        menu_hover, bg_tabela, th_bg, cor_texto_tabela = "#F3F4F6", "#FFFFFF", "#FAFAFA", "#374151"
        shadow = "0 4px 12px rgba(0, 0, 0, 0.03)"
        shadow_hover = "0 10px 20px rgba(0, 0, 0, 0.08)"
        btn_bg, btn_text, btn_hover = "#111827", "#FFFFFF", "#000000"

    css_str = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"], .stApp, .main, p, h1, h2, h3, h4, h5, h6, span, label {{ font-family: 'Inter', sans-serif !important; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .main {{ animation: fadeIn 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); }}
    
    /* Cores Globais */
    .stApp, [data-testid="stAppViewContainer"], .main {{ background-color: {bg_color} !important; }}
    h1:not(#tmr), h2, h3, h4, h5, h6, .stMarkdown p, label {{ color: {text_color} !important; }}
    
    /* Esconder Rodapé e Menu Extra do Streamlit */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{background-color: transparent !important;}}
    
    /* Inputs Fluidos */
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div, [data-baseweb="select"] > div {{
        background-color: {input_bg} !important; 
        border: 1px solid {metric_border} !important; 
        border-radius: 12px !important; 
        transition: all 0.2s ease;
    }}
    [data-baseweb="input"] > div:focus-within, [data-baseweb="textarea"] > div:focus-within, [data-baseweb="select"] > div:focus-within {{
        border-color: {btn_bg} !important; 
        box-shadow: 0 0 0 2px rgba(0,0,0,0.1) !important;
    }}
    input, textarea, div[data-baseweb="select"] span {{ color: {input_text} !important; -webkit-text-fill-color: {input_text} !important; }}
    
    /* Botões Premium Apple-style */
    button[kind="primary"], button[kind="secondary"], button[kind="formSubmit"], div[data-testid="stFormSubmitButton"] > button {{
        background-color: {btn_bg} !important; 
        color: {btn_text} !important;
        border: none !important; 
        border-radius: 10px !important; 
        font-weight: 600 !important;
        transition: transform 0.1s ease, box-shadow 0.2s ease, background-color 0.2s ease !important;
    }}
    button[kind="primary"]:hover, button[kind="secondary"]:hover, button[kind="formSubmit"]:hover {{
        background-color: {btn_hover} !important;
        transform: scale(0.98);
        box-shadow: {shadow_hover} !important;
    }}
    button p, button span, button div {{ color: {btn_text} !important; font-weight: 600 !important; }}
    
    /* Abas Modernas (Segmented Control) */
    [data-baseweb="tab-list"] {{ background-color: {input_bg} !important; border-radius: 12px; padding: 4px; border: 1px solid {metric_border}; gap: 4px; }}
    button[data-baseweb="tab"] {{ border-radius: 8px !important; border: none !important; background: transparent !important; padding: 8px 16px !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ background: {metric_bg} !important; box-shadow: {shadow} !important; }}
    button[data-baseweb="tab"] p {{ color: {menu_text} !important; font-weight: 500 !important; transition: color 0.2s; }}
    button[data-baseweb="tab"][aria-selected="true"] p {{ color: {text_color} !important; font-weight: 600 !important; }}
    
    /* Containers Elevados (Cards) */
    [data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 16px !important; border: 1px solid {metric_border} !important; background-color: {metric_bg} !important; box-shadow: {shadow} !important; transition: transform 0.2s ease, box-shadow 0.2s ease !important; }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover {{ transform: translateY(-2px); box-shadow: {shadow_hover} !important; }}
    div[data-testid='stExpander'] {{ border: 1px solid {metric_border} !important; background-color: {metric_bg} !important; border-radius: 12px; transition: all 0.2s ease; }}
    
    /* Métricas Minimalistas */
    [data-testid="stMetric"] {{ background-color: {metric_bg} !important; border: 1px solid {metric_border} !important; padding: 24px !important; border-radius: 16px !important; box-shadow: {shadow} !important; }}
    [data-testid="stMetricValue"] {{ font-weight: 700 !important; font-size: 2.2rem !important; color: {text_color} !important; }}
    [data-testid="stMetricLabel"] {{ font-weight: 500 !important; color: {menu_text} !important; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; }}

    /* Dataframes/Table Hover Fluid */
    [data-testid="stDataFrame"] > div, [data-testid="stTable"] > div {{ background-color: {bg_tabela} !important; border-radius: 12px; border: 1px solid {metric_border}; box-shadow: {shadow}; }}
    [data-testid="stDataFrame"] th {{ background-color: {th_bg} !important; color: {menu_text} !important; font-weight: 600; font-size: 12px; text-transform: uppercase; border-bottom: 1px solid {metric_border} !important; }}
    [data-testid="stDataFrame"] td {{ background-color: {bg_tabela} !important; color: {cor_texto_tabela} !important; font-size: 14px; border-bottom: 1px solid {metric_border} !important; }}
    
    /* Sidebar Premium */
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {metric_border} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: 10px 16px; border-radius: 10px; margin-bottom: 4px; background-color: transparent; transition: all 0.2s ease; cursor: pointer; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background-color: {menu_hover} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label p {{ color: {menu_text} !important; font-weight: 500; font-size: 14.5px; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background-color: {input_bg} !important; box-shadow: {shadow}; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: {text_color} !important; font-weight: 600 !important; }}
    
    .profile-img {{ border-radius: 50%; object-fit: cover; border: 2px solid {metric_border}; width: 120px; height: 120px; display: block; margin: 0 auto; box-shadow: {shadow}; transition: transform 0.3s ease; }}
    .profile-img:hover {{ transform: scale(1.05); }}
    </style>
    """
    st.markdown(css_str, unsafe_allow_html=True)
    st.session_state["graph_font"] = text_color
    st.session_state["modo_tema"] = modo

# ==========================================
# CONEXÃO FIREBASE SEGURA
# ==========================================
try: CHAVE_GROQ_FIXA = st.secrets.get("GROQ_KEY", st.secrets.get("GROQ_API_KEY", "")) 
except: CHAVE_GROQ_FIXA = ""

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            schema = dict(st.secrets["textkey"])
            if "private_key" in schema:
                schema["private_key"] = schema["private_key"].strip().replace('"', '').replace("'", "").replace("\\n", "\n")
            cred = credentials.Certificate(schema)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro no Firebase: {e}"); st.stop()
    return firestore.client()

db = init_firebase()
for d in ["materiais_estudo", "imagens_flashcards"]:
    if not os.path.exists(d): os.makedirs(d)

def db_add(col_name, state_key, data):
    doc_ref = db.collection(col_name).document()
    doc_ref.set(data)
    data["id"] = doc_ref.id
    if state_key in st.session_state.dados: st.session_state.dados[state_key].append(data)
    return doc_ref

def db_update(col_name, state_key, doc_id, updates):
    db.collection(col_name).document(doc_id).update(updates)
    if state_key in st.session_state.dados:
        for item in st.session_state.dados[state_key]:
            if str(item.get("id")) == str(doc_id):
                for k, v in updates.items():
                    if 'Sentinel' in str(type(v)): item.pop(k, None)
                    else: item[k] = v
                break

def db_delete(col_name, state_key, doc_id):
    db.collection(col_name).document(doc_id).delete()
    if state_key in st.session_state.dados:
        st.session_state.dados[state_key] = [i for i in st.session_state.dados[state_key] if str(i.get("id")) != str(doc_id)]

def invalidar_cache(colecoes=None):
    if colecoes and 'dados' in st.session_state:
        colecoes = [colecoes] if isinstance(colecoes, str) else colecoes
        for colecao in colecoes:
            col_db = "questoes_sessoes" if colecao == "questoes" else "focus_sessoes" if colecao == "focus" else colecao
            st.session_state.dados[colecao] = get_user_docs(col_db, st.session_state.user_id)
    else:
        st.session_state.pop('dados', None); st.session_state.user_data_loaded = False

# ==========================================
# MOTOR IA MULTIMODAL E EXTRATOR SEGURO
# ==========================================
def otimizar_imagem_para_api(img_data, max_size=500):
    if Image is None: return ""
    try:
        if isinstance(img_data, Image.Image): img = img_data.copy()
        elif isinstance(img_data, bytes): img = Image.open(io.BytesIO(img_data))
        elif hasattr(img_data, 'read'): img_data.seek(0); img = Image.open(io.BytesIO(img_data.read()))
        else: img = Image.open(img_data)
        if img.mode != 'RGB': img = img.convert('RGB')
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=65)
        return base64.b64encode(buf.getvalue()).decode('utf-8')
    except: return ""

def get_ia_client():
    if "model_ia" not in st.session_state:
        st.session_state.model_ia = Groq(api_key=CHAVE_GROQ_FIXA) if Groq and CHAVE_GROQ_FIXA else None
    return st.session_state.model_ia

def chamar_ia(client, *, modelo, **kwargs):
    if not client: raise RuntimeError("IA não conectada.")
    candidatos = MODELOS_VISAO_FALLBACK if modelo == MODELO_VISAO else MODELOS_TEXTO_FALLBACK
    for mod in candidatos:
        try:
            call_kwargs = dict(kwargs)
            if "qwen3.6" in mod: call_kwargs.update({"reasoning_effort": "none", "include_reasoning": False})
            elif "openai" in mod: call_kwargs.update({"include_reasoning": False})
            call_kwargs.pop("response_format", None)
            return client.chat.completions.create(model=mod, **call_kwargs)
        except Exception as exc:
            if any(t in str(exc).lower() for t in ("model_not_found", "does not exist", "404", "403")): continue
            raise
    raise RuntimeError("Nenhum modelo disponível.")

def chamar_ia_json_estrito(client, *, modelo, messages, max_completion_tokens=2000, **kwargs):
    return chamar_ia(client, modelo=modelo, messages=messages, temperature=0.1, max_completion_tokens=max_completion_tokens)

def extrair_json_seguro(texto):
    if not texto: return {}
    t = re.sub(r'<think>.*?</think>', '', str(texto), flags=re.DOTALL)
    t = t.replace("```json", "").replace("```", "").strip()
    s_obj, s_arr = t.find('{'), t.find('[')
    if s_obj == -1 and s_arr == -1: return {}
    is_obj = s_obj != -1 and (s_arr == -1 or s_obj < s_arr)
    t = t[s_obj:] if is_obj else t[s_arr:]
    try:
        p = json.loads(t)
        return {"tarefas": p, "questoes": p} if isinstance(p, list) else p
    except: pass
    end_idx = t.rfind('}') if is_obj else t.rfind(']')
    if end_idx != -1:
        try:
            p = json.loads(t[:end_idx+1])
            return {"tarefas": p, "questoes": p} if isinstance(p, list) else p
        except: pass
    return {}

# ==========================================
# CONSTANTES DE DOMÍNIO MÉDICO
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
SUB_CM = ["Geral", "Cardiologia", "Nefrologia", "Endocrinologia", "Pneumologia", "Gastroenterologia", "Reumatologia", "Hematologia", "Infectologia", "Neurologia"]
SUB_CG = ["Geral", "Cirurgia do Trauma", "Cirurgia Vascular", "Cirurgia Plástica", "Cirurgia Torácica", "Cirurgia Pediátrica", "Urologia", "Neurocirurgia", "Ortopedia", "Cirurgia Oncológica", "Cirurgia Cabeça e Pescoço"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#2563eb", "Pediatria": "#db2777", "Ginecologia e Obstetrícia": "#9333ea", "Medicina Preventiva": "#059669", "Cirurgia Geral": "#dc2626", "Geral": "#4b5563"}
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
    bd_osce = "#334155" if modo == "Escuro" else "#e2e8f0"
    partes = re.split(r"(?i)\[EXAME:\s*([^\]]+)\]", str(texto))
    for i, p in enumerate(partes):
        if i % 2 == 0:
            if p.strip(): st.write(p)
        else:
            ch = p.strip().lower().replace(" ", "_") # Correção definitiva do bug de espaço nos exames
            if ch in BANCO_IMAGENS_OSCE: 
                st.markdown(f'<div style="border:1px solid {bd_osce}; border-radius:12px; padding:15px; margin:15px 0; background:{bg_osce};"><p style="font-weight:600; margin-bottom:10px;">📎 Laudo: {ch.replace("_", " ").title()}</p><img src="{BANCO_IMAGENS_OSCE[ch]}" style="width:100%; border-radius:8px;"></div>', unsafe_allow_html=True)
            else: st.info(f"*(Laudo '{ch}' sem imagem correspondente no banco de dados)*")

# ==========================================
# UTILITÁRIOS E DATAS
# ==========================================
def get_agora(): return datetime.now(timezone.utc) - timedelta(hours=3)
def hash_senha(senha): return hashlib.sha256(str.encode(senha)).hexdigest()
def is_super_admin(n): return str(n).lower().strip() in ['joao', 'joão', 'joao victor']

def parse_data(d):
    if not d: return get_agora().date()
    if isinstance(d, datetime): return d.date()
    if isinstance(d, date): return d
    try: return datetime.strptime(str(d).strip()[:10], "%Y-%m-%d").date()
    except:
        try: return datetime.strptime(str(d).strip()[:10], "%d/%m/%Y").date()
        except: return get_agora().date()

def formatar_data_br(d): return parse_data(d).strftime("%d/%m/%Y") if d else "-"
def safe_int(valor):
    try: return int(float(valor)) if valor else 0
    except: return 0
def limpar_texto(texto): return re.sub(r'^[A-Za-z0-9_-]{10,40}\s*\|\s*', '', str(texto)).strip() if texto else "Sem título"

def get_user_docs(col, uid):
    try: return [{"id": d.id, **d.to_dict()} for d in db.collection(col).where(filter=FieldFilter("usuario_id", "==", str(uid))).get()]
    except: return []

# ==========================================
# CALENDÁRIOS HTML PURO E RÁPIDO
# ==========================================
def gerar_calendario_html(aulas_lista, ano, mes):
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = ("#0A0A0A", "#2E2E2E", "#000000", "#171717", "#888888", "#EDEDED", "#555555") if modo == "Escuro" else ("#FFFFFF", "#E5E7EB", "#FAFAFA", "#FFFFFF", "#6B7280", "#111827", "#9CA3AF")
    cal = calendar.monthcalendar(ano, mes)
    ad = {}
    for a in aulas_lista:
        d = parse_data(a.get('data_aula'))
        if d.year == ano and d.month == mes: ad.setdefault(d.day, []).append(a)
    h = f"<div style='background:{bg_ct}; padding:20px; border-radius:16px; border: 1px solid {bd_cl}; margin-bottom:20px;'><table style='width:100%; border-collapse:separate; border-spacing:4px; table-layout:fixed;'><tr>"
    for ds in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]: h += f"<th style='text-align:center; padding:8px; color:{tc_th}; font-size:12px; text-transform:uppercase;'>{ds}</th>"
    h += "</tr>"
    for w in cal:
        h += "<tr>"
        for d in w:
            if d == 0: h += f"<td style='border:1px dashed {bd_cl}; padding:8px; background:{bg_em}; border-radius:8px;'></td>"
            else:
                if d in ad:
                    tms = "".join([f"<div style='background:{CORES_AREAS.get(a.get('area'),'#64748b')}; color:white; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(limpar_texto(a.get('tema')))}</div>" for a in ad[d]])
                    h += f"<td style='border:1px solid {bd_cl}; padding:8px; background:{bg_cl}; vertical-align:top; height:90px; border-radius:8px;'><strong style='color:{tc_st}; font-size:13px;'>{d}</strong><div style='margin-top:6px;'>{tms}</div></td>"
                else: h += f"<td style='border:1px solid {bd_cl}; padding:8px; background:{bg_cl}; vertical-align:top; height:90px; border-radius:8px;'><strong style='color:{tc_em}; font-size:13px;'>{d}</strong></td>"
        h += "</tr>"
    return h + "</table></div>"

def gerar_calendario_revisoes_html(revisoes_lista, ano, mes):
    modo = st.session_state.get("user_settings", {}).get("tema_modo", "Escuro")
    bg_ct, bd_cl, bg_em, bg_cl, tc_th, tc_st, tc_em = ("#0A0A0A", "#2E2E2E", "#000000", "#171717", "#888888", "#EDEDED", "#555555") if modo == "Escuro" else ("#FFFFFF", "#E5E7EB", "#FAFAFA", "#FFFFFF", "#6B7280", "#111827", "#9CA3AF")
    cal = calendar.monthcalendar(ano, mes)
    rd = {}
    for r in revisoes_lista:
        d = parse_data(r.get('data_agendada_obj') if 'data_agendada_obj' in r else r.get('data_agendada'))
        if d and d.year == ano and d.month == mes: rd.setdefault(d.day, []).append(r)
    h = f"<div style='background:{bg_ct}; padding:20px; border-radius:16px; border: 1px solid {bd_cl}; margin-bottom:20px;'><table style='width:100%; border-collapse:separate; border-spacing:4px; table-layout:fixed;'><tr>"
    for ds in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]: h += f"<th style='text-align:center; padding:8px; color:{tc_th}; font-size:12px; text-transform:uppercase;'>{ds}</th>"
    h += "</tr>"
    for w in cal:
        h += "<tr>"
        for d in w:
            if d == 0: h += f"<td style='border:1px dashed {bd_cl}; padding:8px; background:{bg_em}; border-radius:8px;'></td>"
            else:
                if d in rd:
                    tms = "".join([f"<div style='background:{CORES_AREAS.get(r.get('area'),'#64748b')}; color:white; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;'>{html.escape(limpar_texto(r.get('tema')))} <span style='opacity:0.7'>({str(r.get('ciclo') or '').split(' ')[0]})</span></div>" for r in rd[d]])
                    h += f"<td style='border:1px solid {bd_cl}; padding:8px; background:{bg_cl}; vertical-align:top; height:90px; border-radius:8px;'><strong style='color:{tc_st}; font-size:13px;'>{d}</strong><div style='margin-top:6px;'>{tms}</div></td>"
                else: h += f"<td style='border:1px solid {bd_cl}; padding:8px; background:{bg_cl}; vertical-align:top; height:90px; border-radius:8px;'><strong style='color:{tc_em}; font-size:13px;'>{d}</strong></td>"
        h += "</tr>"
    return h + "</table></div>"

def render_toolbar():
    """ Barra Fixa Clean e Responsiva. Sem gambiarras JS que quebram a navegação. """
    toolbar_html = """
    <div style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 4px 0px; margin-bottom: 6px;">
        <button class="fmt-btn" onclick="formatTextLocal('**', '**')" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db; background: transparent; color: inherit; cursor: pointer; font-weight: 700; transition: 0.1s;">B</button>
        <button class="fmt-btn" onclick="formatTextLocal('<u>', '</u>')" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db; background: transparent; color: inherit; cursor: pointer; text-decoration: underline; transition: 0.1s;">U</button>
        <button class="fmt-btn" onclick="formatTextLocal('<mark>', '</mark>')" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db; background: transparent; color: inherit; cursor: pointer; transition: 0.1s;">🖍️ Grifar</button>
        <button class="fmt-btn" onclick="formatTextLocal('\\n- ', '')" style="padding: 6px 12px; border-radius: 8px; border: 1px solid #d1d5db; background: transparent; color: inherit; cursor: pointer; transition: 0.1s;">📋 Tópico</button>
    </div>
    <script>
    function formatTextLocal(tagStart, tagEnd) {
        const pDoc = window.parent.document;
        const tas = pDoc.querySelectorAll('textarea');
        if (tas.length === 0) return;
        let ta = pDoc.activeElement && pDoc.activeElement.tagName === 'TEXTAREA' ? pDoc.activeElement : tas[tas.length - 1];
        if(ta) {
            const start = ta.selectionStart, end = ta.selectionEnd, txt = ta.value, sel = txt.substring(start, end);
            const newTxt = txt.substring(0, start) + tagStart + sel + tagEnd + txt.substring(end);
            Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set.call(ta, newTxt);
            ta.dispatchEvent(new Event('input', { bubbles: true }));
            ta.focus(); ta.setSelectionRange(start + tagStart.length, start + tagStart.length + sel.length);
        }
    }
    document.querySelectorAll('.fmt-btn').forEach(btn => {
        const action = (e) => { e.preventDefault(); formatTextLocal(btn.getAttribute('onclick').match(/'([^']*)'/g)[0].replace(/'/g, '').replace('\\\\n', '\\n'), btn.getAttribute('onclick').match(/'([^']*)'/g)[1].replace(/'/g, '')); };
        btn.removeAttribute('onclick'); btn.addEventListener('mousedown', action); btn.addEventListener('touchstart', action, {passive: false});
    });
    </script>
    """
    components.html(toolbar_html, height=45)

# ==========================================
# GESTÃO DE LOGIN E SEGURANÇA
# ==========================================
if 'logado' not in st.session_state: 
    st.session_state.logado = False
    st.session_state.user_id = None
    st.session_state.user_nome = ""

saved_token = None
if hasattr(st, "context") and hasattr(st.context, "cookies"): saved_token = st.context.cookies.get("mr_token")
if not saved_token and cookie_controller:
    try: saved_token = cookie_controller.get("mr_token")
    except: pass

if not st.session_state.logado and saved_token:
    try:
        for doc in db.collection("usuarios").get():
            if doc.to_dict().get("token_sessao") == saved_token:
                st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                st.rerun()
    except: pass 

if not st.session_state.logado:
    if "temp_theme" not in st.session_state: st.session_state.temp_theme = "Claro"
    aplicar_css_tema(st.session_state.temp_theme)
    
    with st.container():
        st.markdown("<br><br>", unsafe_allow_html=True)
        col_t1, col_t2, col_t3 = st.columns([1,2,1])
        with col_t2:
            st.markdown("<h1 style='text-align: center; font-weight: 800; font-size: 3.5rem; margin-bottom: 5px;'>Residência PRO <span style='color: #4f46e5;'>2.0</span></h1>", unsafe_allow_html=True)
            st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.1rem; margin-bottom: 30px;'>O Ecossistema Definitivo de Aprovação Médica.</p>", unsafe_allow_html=True)
            
            st.session_state.temp_theme = st.radio("Ambiente:", ["Claro", "Escuro"], horizontal=True, index=0 if st.session_state.temp_theme == "Claro" else 1)
            
            aba_l, aba_c = st.tabs(["🔑 Acesso Inteligente", "📝 Criar Conta"])
            with aba_l:
                if cookie_controller is None: st.warning("⚠️ Biblioteca 'streamlit-cookies-controller' não detectada.")
                with st.form("login_form"):
                    u, p, lembrar = st.text_input("Usuário"), st.text_input("Senha", type="password"), st.checkbox("Manter conectado")
                    if st.form_submit_button("Entrar no Ecossistema", use_container_width=True):
                        try:
                            logou = False
                            for doc in db.collection("usuarios").get():
                                if str(doc.to_dict().get("nome", "")).strip().lower() == u.strip().lower() and (doc.to_dict().get("senha") == hash_senha(p) or doc.to_dict().get("senha") == hash_senha(p.strip())):
                                    st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                                    logou = True
                                    if lembrar and cookie_controller:
                                        nt = str(uuid.uuid4())
                                        db.collection("usuarios").document(doc.id).update({"token_sessao": nt})
                                        cookie_controller.set('mr_token', nt, max_age=30*24*60*60, path='/')
                                        time.sleep(0.5)
                                    st.rerun()
                            if not logou: st.error("Acesso negado.")
                        except Exception as e: st.error(f"Erro Firebase: {e}")
            with aba_c:
                with st.form("cadastro_form"):
                    nu, np = st.text_input("Novo Usuário"), st.text_input("Senha", type="password")
                    if st.form_submit_button("Criar Conta", use_container_width=True):
                        existe = any(str(doc.to_dict().get("nome", "")).strip().lower() == nu.strip().lower() for doc in db.collection("usuarios").get())
                        if existe: st.error("Usuário indisponível.")
                        else:
                            db.collection("usuarios").add({"nome": nu.strip(), "senha": hash_senha(np.strip()), "tema_modo": st.session_state.temp_theme})
                            st.toast("✅ Conta criada!", icon="🎉")

# ==========================================
# APLICATIVO LOGADO
# ==========================================
else:
    u_id, hoje = str(st.session_state.user_id), get_agora().date()
    if 'dados' not in st.session_state:
        st.session_state.dados = {"aulas": [], "revisoes": [], "flashcards": [], "questoes": [], "simulados": [], "focus": [], "materiais": [], "cronogramas": [], "anotacoes": [], "questoes_hiit": [], "revisoes_hiit": [], "anotacoes_hiit": [], "flashcards_hiit": []}

    if not st.session_state.get('user_data_loaded'):
        with st.spinner("Sincronizando Ecossistema..."):
            try:
                user_doc = db.collection("usuarios").document(u_id).get()
                st.session_state.user_settings = user_doc.to_dict() if user_doc.exists else {}
                st.session_state.dados = {
                    "aulas": get_user_docs("aulas", u_id), "revisoes": get_user_docs("revisoes", u_id), "flashcards": get_user_docs("flashcards", u_id),
                    "questoes": get_user_docs("questoes_sessoes", u_id), "simulados": get_user_docs("simulados", u_id), "focus": get_user_docs("focus_sessoes", u_id),
                    "materiais": get_user_docs("materiais", u_id), "cronogramas": get_user_docs("cronogramas", u_id), "anotacoes": get_user_docs("anotacoes", u_id),
                    "questoes_hiit": get_user_docs("questoes_hiit", u_id), "revisoes_hiit": get_user_docs("revisoes_hiit", u_id), "anotacoes_hiit": get_user_docs("anotacoes_hiit", u_id), "flashcards_hiit": get_user_docs("flashcards_hiit", u_id)
                }
                if 'model_ia' not in st.session_state: st.session_state.model_ia = get_ia_client()
                st.session_state.user_data_loaded = True 
            except Exception as e: st.error(f"Erro Crítico: {e}"); st.stop()

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
    dados_flashcards_hiit = _dados_cache.get("flashcards_hiit", [])

    aplicar_css_tema(user_settings.get("tema_modo", "Claro"))

    if user_settings.get('foto_perfil_b64'):
        st.sidebar.markdown(f'<img src="data:image/jpeg;base64,{user_settings["foto_perfil_b64"]}" class="profile-img">', unsafe_allow_html=True)
        st.sidebar.markdown(f"<h3 style='text-align: center; margin-top: 15px; margin-bottom: 25px; font-weight: 700;'>{st.session_state.user_nome}</h3>", unsafe_allow_html=True)
    else: st.sidebar.markdown(f"<h2 style='text-align: center; font-weight: 800;'>👤 {st.session_state.user_nome}</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🚪 Encerrar Sessão", use_container_width=True):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        st.session_state.clear(); st.rerun()
    st.sidebar.markdown("---")

    opcoes_menu = ["🏠 Dashboard", "🗓️ Cronograma IA", "⚡ Revisão HIIT", "🎯 Questões", "📚 Registro de Aulas", "📝 Anotações Rápidas", "📅 Agenda de Revisões", "✨ AI Tutor & Flashcards", "📁 Materiais e Simulados", "🏥 Simulados & OSCE", "📍 GPS da Aprovação", "⏱️ Modo Foco", "⚙️ Configurações", "📱 Instalar App"]
    if is_super_admin(st.session_state.user_nome): opcoes_menu.append("👑 Admin")
    menu = st.sidebar.radio("Navegação Principal", opcoes_menu)

    # ---------------------------------------------------------
    # TELAS DO APLICATIVO
    # ---------------------------------------------------------
    if menu == "🏠 Dashboard":
        st.header("Inteligência e Desempenho")
        
        revs_pendentes_dash = [r for r in dados_revisoes + dados_revisoes_hiit if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
        revs_hoje_lista = [r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) <= hoje]
        prox_revs_lista = sorted([r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
        data_prox_dash = formatar_data_br(prox_revs_lista[0].get('data_agendada')) if prox_revs_lista else "Nenhuma agendada"
        
        with st.container(border=True):
            st.markdown(f"**Próxima Revisão Algorítmica:** {data_prox_dash}")
            if revs_hoje_lista: st.markdown(f"<p style='color: #ef4444; font-weight: bold;'>Você tem {len(revs_hoje_lista)} revisões pendentes hoje.</p>", unsafe_allow_html=True)
            else: st.markdown("<p style='color: #10b981; font-weight: bold;'>Todas as revisões em dia.</p>", unsafe_allow_html=True)
        
        qs_sess_all = [dict(q) for q in dados_questoes]
        qs_revs_all = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
        revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        
        aba_geral, aba_detalhada = st.tabs(["📊 Visão Global", "📈 Especialidades"])
        with aba_geral:
            t_acertos_g = sum(safe_int(q.get('acertos')) for q in qs_sess_all) + sum(safe_int(r.get('acertos')) for r in qs_revs_all) + sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
            t_erros_g = sum(safe_int(q.get('erros')) for q in qs_sess_all) + sum(safe_int(r.get('erros')) for r in qs_revs_all) + sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
            t_questoes_g = t_acertos_g + t_erros_g
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões Resolvidas", t_questoes_g)
            c2.metric("Acertos Absolutos", t_acertos_g)
            c3.metric("Erros Mapeados", t_erros_g)
            c4.metric("Precisão Global", f"{(t_acertos_g / t_questoes_g * 100) if t_questoes_g > 0 else 0:.1f}%")
            
            st.divider()
            col_g1, col_g2 = st.columns([1, 1.5])
            modo_grafico_font = st.session_state.get("graph_font", "#0f172a")
            
            with col_g1:
                if t_questoes_g > 0: 
                    fig_pie1 = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_g, t_erros_g], hole=0.7, color_discrete_sequence=["#10b981", '#ef4444'])
                    fig_pie1.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='rgba(0,0,0,0)', width=0)))
                    fig_pie1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                    st.plotly_chart(fig_pie1, use_container_width=True, config={'displayModeBar': False})
            with col_g2:
                todas_questoes_grafico = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_sess_all] + [{"area": r.get('area_aula', r.get('area')), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in qs_revs_all] + [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_hiit_all] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in revs_hiit_all]
                df_r = pd.DataFrame(todas_questoes_grafico).dropna(subset=['area'])
                if not df_r.empty:
                    df_g = df_r.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_g['Taxa'] = (df_g['acertos'] / (df_g['acertos'] + df_g['erros'])) * 100
                    fig_bar1 = px.bar(df_g.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS, text_auto='.1f')
                    fig_bar1.update_traces(textposition="outside", cliponaxis=False)
                    fig_bar1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, showlegend=False, margin=dict(t=0, b=0, l=0, r=20), xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', zeroline=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_bar1, use_container_width=True, config={'displayModeBar': False})

        with aba_detalhada:
            filtro_dash = st.selectbox("Filtrar Especialidade:", AREAS_MED)
            qs_sess_f = [q for q in qs_sess_all if q.get('area') == filtro_dash]
            qs_revs_f = [r for r in qs_revs_all if r.get('area_aula', r.get('area')) == filtro_dash]
            qs_hiit_f = [q for q in qs_hiit_all if q.get('area') == filtro_dash]
            revs_hiit_f = [r for r in revs_hiit_all if r.get('area') == filtro_dash]
            t_acertos_f = sum(safe_int(q.get('acertos')) for q in qs_sess_f) + sum(safe_int(r.get('acertos')) for r in qs_revs_f) + sum(safe_int(q.get('acertos')) for q in qs_hiit_f) + sum(safe_int(r.get('acertos')) for r in revs_hiit_f)
            t_erros_f = sum(safe_int(q.get('erros')) for q in qs_sess_f) + sum(safe_int(r.get('erros')) for r in qs_revs_f) + sum(safe_int(q.get('erros')) for q in qs_hiit_f) + sum(safe_int(r.get('erros')) for r in revs_hiit_f)
            t_questoes_f = t_acertos_f + t_erros_f
            c1_f, c2_f, c3_f = st.columns(3)
            c1_f.metric(f"Base de Questões", t_questoes_f)
            c2_f.metric("Acertos", t_acertos_f)
            c3_f.metric("Aproveitamento", f"{(t_acertos_f / t_questoes_f * 100) if t_questoes_f > 0 else 0:.1f}%")

    elif menu == "📱 Instalar App":
        st.header("Aplicativo Nativo")
        col1, col2 = st.columns(2)
        with col1: 
            with st.container(border=True):
                st.subheader("🤖 Android"); st.write("1. Menu do Chrome.\n2. Adicionar à tela inicial.\n3. Instalar.")
        with col2: 
            with st.container(border=True):
                st.subheader("🍎 iOS"); st.write("1. Botão Compartilhar do Safari.\n2. Adicionar à Tela de Início.\n3. Confirmar.")

    elif menu == "🗓️ Cronograma IA":
        st.header("Cronograma de Elite")
        if 'prints_colados' not in st.session_state: st.session_state.prints_colados = []
        aba_lista, aba_importar, aba_manual = st.tabs(["Minhas Metas", "Extração Visual (IA)", "Cadastro Manual"])
        
        with aba_importar:
            nome_semana = st.text_input("Identificador da Semana (Ex: Reta Final S1)")
            col_btn, col_arq = st.columns(2)
            with col_btn:
                st.markdown("#### Captura Instantânea")
                if paste_image_button is not None:
                    paste_result = paste_image_button(label="Colar Print (Ctrl+V)", background_color="#4f46e5", hover_background_color="#4338ca", key="paste_crono")
                    if paste_result.image_data is not None:
                        img, buf = paste_result.image_data, io.BytesIO(); img.save(buf, format="PNG")
                        img_hash = hashlib.md5(buf.getvalue()).hexdigest()
                        if not any(item['hash'] == img_hash for item in st.session_state.prints_colados):
                            st.session_state.prints_colados.append({'hash': img_hash, 'img': img, 'bytes': buf.getvalue()}); st.rerun()
                if st.session_state.prints_colados:
                    st.toast(f"{len(st.session_state.prints_colados)} imagens na fila.", icon="📸")
                    if st.button("Limpar Cache"): st.session_state.prints_colados = []; st.rerun()
            with col_arq:
                st.markdown("#### Upload em Lote")
                imgs_crono = st.file_uploader("Arquivos", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")
            st.divider()
            if (imgs_crono or st.session_state.prints_colados) and nome_semana and st.button("Processar com IA Multimodal", use_container_width=True, type="primary"):
                client_ia = get_ia_client()
                if not client_ia: st.error("Motor IA Offline.")
                else:
                    with st.spinner("Decodificando cronograma..."):
                        todas_imagens_b64 = [otimizar_imagem_para_api(img, max_size=720) for img in imgs_crono] if imgs_crono else []
                        if st.session_state.prints_colados: todas_imagens_b64.extend([otimizar_imagem_para_api(item['img'], max_size=720) for item in st.session_state.prints_colados])
                        tarefas_totais = []
                        if todas_imagens_b64:
                            barra_progresso = st.progress(0)
                            prompt_visao = """[SISTEMA NÍVEL 5] Extraia TODAS as tarefas visíveis. JSON estrito: {"tarefas": [{"materia": "...", "tema": "...", "cor": "..."}]}. NENHUM texto extra. Não use crases."""
                            for idx_img, img_b64 in enumerate(todas_imagens_b64):
                                conteudo_api = [{"type": "text", "text": prompt_visao}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}]
                                try:
                                    try: resposta = chamar_ia(client_ia, modelo=MODELO_VISAO, messages=[{"role": "user", "content": conteudo_api}], temperature=0.1, max_tokens=2500)
                                    except Exception as e_api:
                                        if "rate" in str(e_api).lower() or "429" in str(e_api): time.sleep(12); resposta = chamar_ia(client_ia, modelo=MODELO_VISAO, messages=[{"role": "user", "content": conteudo_api}], temperature=0.1, max_tokens=2500)
                                        else: raise e_api
                                    tarefas_totais.extend(extrair_json_seguro(resposta.choices[0].message.content).get("tarefas", []))
                                except Exception as e: st.warning(f"Erro imagem {idx_img+1}: {e}")
                                barra_progresso.progress((idx_img + 1) / len(todas_imagens_b64))
                        if tarefas_totais:
                            batch = db.batch()
                            for t in tarefas_totais:
                                c = str(t.get("cor", "")).lower(); p = 3
                                if "azul" in c: p = 1
                                elif "verde" in c: p = 2
                                elif "amarelo" in c: p = 3
                                elif "vermelho" in c: p = 4
                                elif "roxo" in c: p = 5
                                t["prioridade"] = p
                            tarefas_totais.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
                            dias_semana = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado"]
                            for i, t in enumerate(tarefas_totais):
                                doc_ref = db.collection("cronogramas").document()
                                nova_tarefa = {"usuario_id": u_id, "semana": nome_semana, "dia": dias_semana[(i // 4) % 6], "materia": t.get("materia", ""), "tema": t.get("tema", ""), "prioridade": safe_int(t.get("prioridade", 3)), "concluido": False, "data_importacao": str(hoje), "data_conclusao": None}
                                batch.set(doc_ref, nova_tarefa); nova_tarefa["id"] = doc_ref.id; st.session_state.dados["cronogramas"].append(nova_tarefa)
                            batch.commit(); st.session_state.prints_colados = []; st.toast("Cronograma injetado!", icon="🚀"); time.sleep(1); st.rerun()

        with aba_manual:
            c3, c4 = st.columns(2)
            m_materia = c3.selectbox("Matéria", AREAS_MED + ["Outra"], key="crono_mat")
            sub_m = c4.selectbox("Subespecialidade", SUB_CM if m_materia == "Clínica Médica" else SUB_CG if m_materia == "Cirurgia Geral" else ["Geral"])
            c1, c2 = st.columns(2)
            m_semana = c1.text_input("Semana", key="cs")
            m_dia = c2.selectbox("Dia", ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"])
            m_tema = st.text_input("Tema da Aula")
            m_prio = st.selectbox("Prioridade", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(safe_int(x)))
            if st.button("Gravar Meta", type="primary"):
                if m_semana and m_tema:
                    db_add("cronogramas", "cronogramas", {"usuario_id": u_id, "semana": m_semana, "dia": m_dia, "materia": m_materia, "tema": f"{sub_m} - {m_tema}" if sub_m and sub_m != "Geral" else m_tema, "prioridade": m_prio, "concluido": False, "data_importacao": str(hoje), "data_conclusao": None})
                    st.toast("Meta gravada!", icon="🎯"); time.sleep(0.5); st.rerun()

        with aba_lista:
            meu_crono = dados_cronogramas
            def sort_key_week(sem):
                dates = [parse_data(c.get("data_importacao", str(hoje))) for c in meu_crono if c.get("semana", "Semana Geral") == sem]
                nums = re.findall(r'\d+', sem)
                return (max(dates) if dates else parse_data(None), int(nums[0]) if nums else 0)
            semanas_unicas = sorted(list(set([c.get("semana", "Semana Geral") for c in meu_crono])), key=sort_key_week, reverse=True)
            termo_pesquisa = st.text_input("🔍 Pesquisar em todo cronograma...", "").lower()
            
            for sem in semanas_unicas:
                tarefas_semana = [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]
                if termo_pesquisa: tarefas_semana = [c for c in tarefas_semana if termo_pesquisa in str(c.get('tema', '')).lower() or termo_pesquisa in str(c.get('materia', '')).lower()]
                if termo_pesquisa and not tarefas_semana: continue

                col_t, col_d = st.columns([0.8, 0.2])
                col_t.subheader(f"📁 {sem}")
                if col_d.button("Excluir Bloco", key=f"dels_{sem}"):
                    batch = db.batch(); ids_del = []
                    for t_del in [c for c in meu_crono if c.get("semana", "Semana Geral") == sem]: 
                        if str(t_del.get('id', '0')) != '0': batch.delete(db.collection("cronogramas").document(str(t_del['id']))); ids_del.append(str(t_del['id']))
                    batch.commit(); st.session_state.dados["cronogramas"] = [c for c in st.session_state.dados["cronogramas"] if str(c.get('id')) not in ids_del]; st.rerun()

                pendentes = sorted([c for c in tarefas_semana if not c.get("concluido", False)], key=lambda x: safe_int(x.get("prioridade", 3)))
                for t in pendentes:
                    t_id = str(t.get('id', uuid.uuid4()))
                    with st.container(border=True):
                        c1, c2, c3, c4 = st.columns([0.1, 0.6, 0.2, 0.1])
                        if c1.button("✅", key=f"ok_{t_id}"): db_update("cronogramas", "cronogramas", t_id, {"concluido": True, "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")}); st.rerun()
                        c2.markdown(f"**{t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
                        if c3.selectbox("Prioridade", [1,2,3,4,5], format_func=lambda x: PRIORIDADES.get(x), index=safe_int(t.get('prioridade',3))-1, key=f"p_{t_id}", label_visibility="collapsed") != safe_int(t.get('prioridade',3)): db_update("cronogramas", "cronogramas", t_id, {"prioridade": st.session_state[f"p_{t_id}"]}); st.rerun()
                        if c4.button("🗑️", key=f"rm_{t_id}"): db_delete("cronogramas", "cronogramas", t_id); st.rerun()
                
                concluidos = [c for c in tarefas_semana if c.get("concluido", False)]
                if concluidos:
                    with st.expander(f"✅ Histórico Concluído ({len(concluidos)})"):
                        for t in reversed(concluidos):
                            dc = t.get('data_conclusao', '')
                            dc_fmt = datetime.strptime(str(dc), "%Y-%m-%d %H:%M:%S").strftime("%d/%m %H:%M") if len(str(dc)) > 10 else formatar_data_br(dc)
                            st.markdown(f"~~[{PRIORIDADES.get(safe_int(t.get('prioridade', 3)), '')}] {t.get('materia')} - {t.get('tema')}~~ *(Check: {dc_fmt})*")
                st.divider()

    elif menu == "⚡ Revisão HIIT":
        st.header("Algoritmo de Revisão HIIT")
        aba_dash_hiit, aba_reg_hiit, aba_cal_hiit, aba_notas_hiit, aba_fc_hiit = st.tabs(["Métricas", "Lançar Desempenho", "Agenda", "Resumos Rápidos", "Flashcards Atomizados"])

        with aba_dash_hiit:
            qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
            revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
            t_acertos_h = sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
            t_erros_h = sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
            t_questoes_h = t_acertos_h + t_erros_h
            
            c1_h, c2_h, c3_h, c4_h = st.columns(4)
            c1_h.metric("Questões Base", t_questoes_h)
            c2_h.metric("Acertos", t_acertos_h)
            c3_h.metric("Erros", t_erros_h)
            c4_h.metric("Aproveitamento", f"{(t_acertos_h / t_questoes_h * 100) if t_questoes_h > 0 else 0:.1f}%")
            
            st.divider()
            col_gh1, col_gh2 = st.columns([1, 1.5])
            modo_grafico_font = st.session_state.get("graph_font", "#0f172a")
            with col_gh1:
                if t_questoes_h > 0: 
                    fig_pie_h = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_h, t_erros_h], hole=0.7, color_discrete_sequence=["#10b981", '#ef4444'])
                    fig_pie_h.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color='rgba(0,0,0,0)', width=0)))
                    fig_pie_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0), showlegend=False)
                    st.plotly_chart(fig_pie_h, use_container_width=True, config={'displayModeBar': False})
            with col_gh2:
                df_rh = pd.DataFrame([{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_hiit_all] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in revs_hiit_all]).dropna(subset=['area'])
                if not df_rh.empty:
                    df_gh = df_rh.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_gh['Taxa'] = (df_gh['acertos'] / (df_gh['acertos'] + df_gh['erros'])) * 100
                    fig_bar_h = px.bar(df_gh.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS, text_auto='.1f')
                    fig_bar_h.update_traces(textposition="outside", cliponaxis=False)
                    fig_bar_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, showlegend=False, margin=dict(t=0, b=0, l=0, r=20), xaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.1)', zeroline=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_bar_h, use_container_width=True, config={'displayModeBar': False})

        with aba_reg_hiit:
            col_a, col_sub = st.columns(2)
            a = col_a.selectbox("Área", AREAS_MED, key="h_a")
            sub_q = col_sub.selectbox("Subespecialidade", SUB_CM if a == "Clínica Médica" else SUB_CG if a == "Cirurgia Geral" else ["Geral"], key="h_s")
            with st.form("h_f", clear_on_submit=True):
                st.info("Registre o bloco. A repetição espaçada (SRS) é calculada isoladamente.")
                c1, c2 = st.columns(2)
                s, d = c1.text_input("Tema"), c2.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2)
                acc, err = ac.number_input("Acertos", min_value=0), er.number_input("Erros", min_value=0)
                if st.form_submit_button("Gerar Ciclo HIIT", use_container_width=True, type="primary"):
                    s_f = f"{sub_q} - {s}" if sub_q and sub_q != "Geral" else s
                    db_add("questoes_hiit", "questoes_hiit", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": s_f, "acertos": acc, "erros": err})
                    if acc + err > 0:
                        taxa = acc / (acc + err)
                        c_nome, d_p = ("🔴 HIIT Alerta (7d)", 7) if taxa < 0.6 else ("🟡 HIIT Reforço (14d)", 14) if taxa < 0.8 else ("🟢 HIIT Domínio (30d)", 30)
                        n_data = parse_data(str(d)) + timedelta(days=d_p)
                        batch = db.batch(); ids_del = set()
                        for r_p in st.session_state.dados.get("revisoes_hiit", []):
                            if str(r_p.get('status')).lower() in ['pendente', 'pendentes'] and str(r_p.get('tema')) == s_f: batch.delete(db.collection("revisoes_hiit").document(r_p['id'])); ids_del.add(r_p['id'])
                        doc_r = db.collection("revisoes_hiit").document(); n_r = {"usuario_id": u_id, "area": a, "tema": s_f, "ciclo": c_nome, "data_agendada": str(n_data), "status": "Pendente"}
                        batch.set(doc_r, n_r); batch.commit()
                        st.session_state.dados["revisoes_hiit"] = [r for r in st.session_state.dados.get("revisoes_hiit", []) if r['id'] not in ids_del]
                        n_r['id'] = doc_r.id; st.session_state.dados["revisoes_hiit"].append(n_r); st.toast(f"Revisão ({c_nome}) gerada!", icon="⚡")
                    st.rerun()

            if dados_questoes_hiit:
                st.write("---"); st.subheader("Histórico Bruto")
                df_h = pd.DataFrame([{"Data": formatar_data_br(b.get('data')), "Data_obj": parse_data(b.get('data')), "Área": b.get('area'), "Subtema": limpar_texto(b.get('subtema')), "Acertos": safe_int(b.get('acertos')), "Erros": safe_int(b.get('erros')), "%": f"{(safe_int(b.get('acertos')) / (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) * 100):.1f}%" if safe_int(b.get('acertos')) + safe_int(b.get('erros')) > 0 else "0.0%"} for b in dados_questoes_hiit]).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj"])
                st.dataframe(df_h, use_container_width=True, hide_index=True)
                with st.expander("Modificar Histórico"):
                    op_h = {f"{formatar_data_br(q.get('data'))} | {limpar_texto(q.get('subtema'))}": q for q in dados_questoes_hiit}
                    if op_h:
                        qh_sel = st.selectbox("Registro:", list(op_h.keys()))
                        c_e1, c_e2 = st.columns(2)
                        n_ac = c_e1.number_input("Acertos", value=safe_int(op_h[qh_sel].get('acertos')), min_value=0)
                        n_er = c_e2.number_input("Erros", value=safe_int(op_h[qh_sel].get('erros')), min_value=0)
                        cb1, cb2 = st.columns(2)
                        if cb1.button("Salvar Edição", use_container_width=True): db_update("questoes_hiit", "questoes_hiit", op_h[qh_sel]['id'], {"acertos": n_ac, "erros": n_er}); st.rerun()
                        if cb2.button("Excluir", use_container_width=True): db_delete("questoes_hiit", "questoes_hiit", op_h[qh_sel]['id']); st.rerun()

        with aba_cal_hiit:
            todas_pendentes_hiit = [dict(r, data_agendada_obj=parse_data(r.get('data_agendada')), tema=limpar_texto(r.get('tema')), area=r.get('area', 'Geral')) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
            col_h1, col_h2, col_h3 = st.columns(3)
            col_h1.metric("Atrasos Críticos", len([r for r in todas_pendentes_hiit if r['data_agendada_obj'] < hoje]))
            col_h2.metric("Missões de Hoje", len([r for r in todas_pendentes_hiit if r['data_agendada_obj'] == hoje]))
            fut = sorted([r for r in todas_pendentes_hiit if r['data_agendada_obj'] > hoje], key=lambda x: x['data_agendada_obj'])
            col_h3.metric("Ponto Futuro", formatar_data_br(fut[0]['data_agendada_obj']) if fut else "-")

            if 'cal_mes_hiit' not in st.session_state: st.session_state.cal_mes_hiit = hoje.month
            if 'cal_ano_hiit' not in st.session_state: st.session_state.cal_ano_hiit = hoje.year
            n1, n2, n3 = st.columns([1,2,1])
            if n1.button("⬅️", key="p_h"): st.session_state.cal_mes_hiit, st.session_state.cal_ano_hiit = (12, st.session_state.cal_ano_hiit - 1) if st.session_state.cal_mes_hiit == 1 else (st.session_state.cal_mes_hiit - 1, st.session_state.cal_ano_hiit); st.rerun()
            n2.markdown(f"<h3 style='text-align:center; margin:0;'>{MESES_PT[st.session_state.cal_mes_hiit]} {st.session_state.cal_ano_hiit}</h3>", unsafe_allow_html=True)
            if n3.button("➡️", key="n_h"): st.session_state.cal_mes_hiit, st.session_state.cal_ano_hiit = (1, st.session_state.cal_ano_hiit + 1) if st.session_state.cal_mes_hiit == 12 else (st.session_state.cal_mes_hiit + 1, st.session_state.cal_ano_hiit); st.rerun()
            st.markdown(gerar_calendario_revisoes_html(todas_pendentes_hiit, st.session_state.cal_ano_hiit, st.session_state.cal_mes_hiit), unsafe_allow_html=True)
            
            v_h, o_h = st.columns(2)
            f_vh = v_h.radio("Perspectiva:", ["Hoje", "Próx 7 Dias", "Todas"], horizontal=True)
            f_oh = o_h.radio("Filtragem:", ["Urgência", "Recentes"], horizontal=True)
            
            l_p_h = [r for r in todas_pendentes_hiit if r['data_agendada_obj'] == hoje] if f_vh == "Hoje" else [r for r in todas_pendentes_hiit if hoje <= r['data_agendada_obj'] <= (hoje + timedelta(days=7))] if f_vh == "Próx 7 Dias" else [r for r in todas_pendentes_hiit if r['data_agendada_obj'] >= hoje]
            l_p_h.sort(key=lambda x: x['data_agendada_obj'], reverse=(f_oh == "Recentes"))
            
            for r in l_p_h:
                with st.container(border=True):
                    st.markdown(f"**<span style='color:{CORES_AREAS.get(r['area'], '#64748b')};'>⬤</span> {r['tema']}**", unsafe_allow_html=True)
                    st.caption(f"{r.get('ciclo','')} | Agendado: {formatar_data_br(r['data_agendada_obj'])}")
                    with st.expander("Lançar Ciclo"):
                        cf1, cf2 = st.columns(2)
                        a_h = cf1.number_input("Acertos", 0, key=f"ah_{r['id']}")
                        e_h = cf2.number_input("Erros", 0, key=f"eh_{r['id']}")
                        if st.button("Finalizar Ciclo e Evoluir SRS", key=f"fch_{r['id']}", type="primary", use_container_width=True):
                            db_update("revisoes_hiit", "revisoes_hiit", r['id'], {"status": "Concluída", "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S"), "acertos": a_h, "erros": e_h})
                            if a_h + e_h > 0:
                                t = a_h / (a_h + e_h)
                                c_n, d_p = ("🔴 HIIT Alerta (7d)", 7) if t < 0.6 else ("🟡 HIIT Reforço (14d)", 14) if t < 0.8 else ("🟢 HIIT Domínio (30d)", 30)
                                n_d = parse_data(str(get_agora().date())) + timedelta(days=d_p)
                                dr = db.collection("revisoes_hiit").document(); nr = {"usuario_id": u_id, "area": r['area'], "tema": r['tema'], "ciclo": c_n, "data_agendada": str(n_d), "status": "Pendente"}
                                dr.set(nr); nr['id'] = dr.id; st.session_state.dados["revisoes_hiit"].append(nr); st.toast(f"Evoluído para {formatar_data_br(n_d)}", icon="🚀")
                            st.rerun()

        with aba_notas_hiit:
            aba_nh1, aba_nh2 = st.tabs(["Construtor de Resumos", "Arquivo Morto"])
            with aba_nh1:
                col_i, col_f = st.columns([1, 2])
                with col_i:
                    if 'hiit_nota_imgs_temp' not in st.session_state: st.session_state.hiit_nota_imgs_temp = []
                    st.markdown("#### 🖼️ Evidências Visuais")
                    if paste_image_button:
                        res = paste_image_button(label="Colar da Área de Transferência", background_color=st.session_state.get("graph_font", "#0f172a"), hover_background_color=CORES_AREAS["Clínica Médica"], key="paste_hiit")
                        if res.image_data:
                            b64 = otimizar_imagem_para_api(res.image_data, 1024)
                            if b64 and b64 not in st.session_state.hiit_nota_imgs_temp: st.session_state.hiit_nota_imgs_temp.append(b64); st.rerun()
                    for idx, img in enumerate(st.session_state.hiit_nota_imgs_temp):
                        if isinstance(img, str) and len(img)>50: st.image(base64.b64decode(img), use_container_width=True)
                        if st.button("Remover", key=f"rm_h_{idx}"): st.session_state.hiit_nota_imgs_temp.pop(idx); st.rerun()
                
                with col_f:
                    st.markdown("#### ✍️ Estruturação")
                    c_ah, c_sh = st.columns(2)
                    ah = c_ah.selectbox("Área", AREAS_MED, key="ah_s")
                    sh = c_sh.selectbox("Especialidade", SUB_CM if ah == "Clínica Médica" else SUB_CG if ah == "Cirurgia Geral" else ["Geral"], key="sh_s")
                    th = st.text_input("Conceito Central", key="anotacao_subtema_hiit")
                    render_toolbar()
                    ph = st.text_area("Núcleo do Resumo", height=250, key="anotacao_resumo_hiit")
                    if st.button("Homologar Anotação", type="primary", use_container_width=True):
                        if th and ph:
                            db_add("anotacoes_hiit", "anotacoes_hiit", {"usuario_id": u_id, "area": ah, "subtema": f"{sh} - {th}" if sh and sh != "Geral" else th, "pontos_chave": ph, "imagens_b64": st.session_state.hiit_nota_imgs_temp, "data_criacao": str(hoje)})
                            st.session_state.anotacao_subtema_hiit, st.session_state.anotacao_resumo_hiit, st.session_state.hiit_nota_imgs_temp = "", "", []
                            st.toast("Anotação imortalizada no banco!", icon="🧠"); time.sleep(0.5); st.rerun()
                            
            with aba_nh2:
                if not dados_anotacoes_hiit: st.info("Arquivo limpo.")
                else:
                    pesq = st.text_input("Filtrar arquivos...", key="ph").lower()
                    n_ex = [n for n in dados_anotacoes_hiit if pesq in str(n.get('subtema','')).lower() or pesq in str(n.get('pontos_chave','')).lower()]
                    n_ex.sort(key=lambda x: parse_data(x.get('data_criacao')), reverse=True)
                    bp = sorted(list(set([n.get('area', 'Geral') for n in n_ex])))
                    
                    if bp:
                        abas = st.tabs(bp)
                        for i, b in enumerate(bp):
                            with abas[i]:
                                for nh in [x for x in n_ex if x.get('area') == b]:
                                    with st.expander(f"{limpar_texto(nh.get('subtema'))} ({formatar_data_br(nh.get('data_criacao'))})"):
                                        if st.button("Excluir", key=f"d_nh_{nh['id']}"): db_delete("anotacoes_hiit", "anotacoes_hiit", nh['id']); st.rerun()
                                        st.markdown(f"<div style='border-left: 3px solid {CORES_AREAS.get(b, '#000')}; padding-left: 15px; margin: 15px 0;'>{nh.get('pontos_chave', '')}</div>", unsafe_allow_html=True)
                                        for img in nh.get('imagens_b64', []): st.image(base64.b64decode(img), use_container_width=True)
                                        if st.button("🪄 IA: Atomizar em Flashcards", key=f"ia_nh_{nh['id']}"):
                                            cli = get_ia_client()
                                            if cli:
                                                with st.spinner("Fragmentando..."):
                                                    try:
                                                        res = chamar_ia_json_estrito(cli, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": f"""Extraia flashcards precisos deste resumo. Responda APENAS JSON: {{"flashcards": [{{"frente": "...", "verso": "..."}}]}}\nResumo: {nh.get('pontos_chave', '')}"""}])
                                                        fcs = extrair_json_seguro(res.choices[0].message.content).get("flashcards", [])
                                                        if fcs:
                                                            bat = db.batch()
                                                            for fc in fcs:
                                                                dr = db.collection("flashcards_hiit").document(); nfc = {"usuario_id": u_id, "area": b, "tema": limpar_texto(nh.get('subtema')), "frente": fc.get('frente'), "verso": fc.get('verso'), "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                                                                bat.set(dr, nfc); nfc['id'] = dr.id; st.session_state.dados["flashcards_hiit"].append(nfc)
                                                            bat.commit(); st.success(f"{len(fcs)} cartões gerados!")
                                                    except Exception as e: st.error(str(e))

        with aba_fc_hiit:
            cv = [d for d in dados_flashcards_hiit if parse_data(d.get('data_prox_revisao')) <= hoje]
            if not cv: st.success("Deck zerado.")
            else:
                d_o = {}
                for c in cv:
                    a, t = c.get('area', 'Geral'), limpar_texto(c.get('tema', 'Tema'))
                    d_o.setdefault(a, {}).setdefault(t, []).append(c)
                ap = sorted(list(d_o.keys()))
                abas_f = st.tabs(ap)
                for idx, area in enumerate(ap):
                    with abas_f[idx]:
                        tms = sorted(list(d_o[area].keys()))
                        c_a = d_o[area][tms[0]][0]
                        st.caption(f"**{tms[0]}** - {sum(len(d_o[area][t]) for t in tms)} cartões na área.")
                        with st.container(border=True):
                            st.markdown(f"### {c_a.get('frente', '')}")
                            if st.session_state.get(f"ans_h_{c_a['id']}"):
                                st.info(c_a.get('verso', ''))
                                b1, b2, b3 = st.columns(3)
                                def avaliar(peso):
                                    facil, interv = float(c_a.get('facilidade', 2.5)), safe_int(c_a.get('intervalo'))
                                    ni, nf = (1, max(1.3, facil-0.2)) if peso == 'err' else (max(1, int((interv or 1)*facil)), facil) if peso == 'bom' else (max(1, int((interv or 1)*facil*1.3)), facil+0.15)
                                    db_update("flashcards_hiit", "flashcards_hiit", c_a['id'], {"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))})
                                    st.session_state[f"ans_h_{c_a['id']}"] = False
                                if b1.button("🔴 Errei (1d)", key=f"e_{c_a['id']}"): avaliar('err'); st.rerun()
                                if b2.button("🟡 Bom", key=f"b_{c_a['id']}"): avaliar('bom'); st.rerun()
                                if b3.button("🟢 Fácil", key=f"f_{c_a['id']}"): avaliar('facil'); st.rerun()
                            elif st.button("Revelar Resposta", key=f"rev_{c_a['id']}"): st.session_state[f"ans_h_{c_a['id']}"] = True; st.rerun()

    elif menu == "🎯 Questões":
        aba_reg, aba_erros, aba_alvos = st.tabs(["Registro Cirúrgico", "Caderno de Erros IA", "Mapeamento Crítico"])
        with aba_reg:
            col_a, col_sub = st.columns(2)
            a = col_a.selectbox("Área", AREAS_MED, key="q_area")
            sub_q = col_sub.selectbox("Subespecialidade", SUB_CM if a == "Clínica Médica" else SUB_CG if a == "Cirurgia Geral" else ["Geral"], key="q_sub")
            with st.form("q_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                s = c1.text_input("Módulo")
                d = c2.date_input("Data Base", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2)
                acc, err = ac.number_input("Acertos", min_value=0), er.number_input("Erros", min_value=0)
                cc = st.text_input("Gatilho de Erro (Conceito Chave)")
                if st.form_submit_button("Inserir no Motor de Performance", use_container_width=True, type="primary"):
                    s_f = f"{sub_q} - {s}" if sub_q and sub_q != "Geral" else s
                    db_add("questoes_sessoes", "questoes", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": s_f, "acertos": acc, "erros": err, "conceito_chave": cc})
                    if acc + err > 0:
                        taxa = acc / (acc + err)
                        c_n, d_p = ("🔴 Crítico (1d)", 1) if taxa < 0.6 else ("🟡 Reforço (7d)", 7) if taxa < 0.8 else ("🟢 Domínio (15d)", 15)
                        n_d = parse_data(str(d)) + timedelta(days=d_p)
                        batch = db.batch(); ids_del = set()
                        for r_p in st.session_state.dados["revisoes"]:
                            if str(r_p.get('status')).lower() in ['pendente', 'pendentes'] and str(r_p.get('tema')) == s_f: batch.delete(db.collection("revisoes").document(r_p['id'])); ids_del.add(r_p['id'])
                        doc_r = db.collection("revisoes").document(); nr = {"usuario_id": u_id, "area": a, "tema": s_f, "ciclo": c_n, "data_agendada": str(n_d), "status": "Pendente"}
                        batch.set(doc_r, nr); batch.commit()
                        st.session_state.dados["revisoes"] = [r for r in st.session_state.dados["revisoes"] if r['id'] not in ids_del]; nr['id'] = doc_r.id; st.session_state.dados["revisoes"].append(nr)
                    st.toast("Motor atualizado!", icon="⚙️"); time.sleep(0.5); st.rerun()
            if dados_questoes:
                st.write("---")
                df_q = pd.DataFrame([{"Data": formatar_data_br(b.get('data')), "Área": b.get('area'), "Módulo": limpar_texto(b.get('subtema')), "A": safe_int(b.get('acertos')), "E": safe_int(b.get('erros')), "%": f"{(safe_int(b.get('acertos')) / (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) * 100):.1f}%" if safe_int(b.get('acertos')) + safe_int(b.get('erros')) > 0 else "0.0%", "Data_obj": parse_data(b.get('data'))} for b in dados_questoes]).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj"])
                st.dataframe(df_q, use_container_width=True, hide_index=True)

        with aba_erros:
            be = [b for b in dados_questoes if safe_int(b.get('erros')) > 0 and b.get('conceito_chave')]
            if be:
                esc = st.selectbox("Mapeamento de Lacuna:", reversed([f"{b.get('area')} - {limpar_texto(b.get('subtema'))}: {b.get('conceito_chave')}" for b in be]))
                if st.button("Invocar IA: Clonar Questão", type="primary"):
                    cli = get_ia_client()
                    if cli:
                        with st.spinner("Forjando..."):
                            try:
                                res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": f"[SISTEMA] Crie uma questão INÉDITA de caso clínico simulando banca para testar este erro: '{esc.split(': ')[1]}'."}], temperature=0.4, max_tokens=2500)
                                with st.container(border=True): st.markdown(res.choices[0].message.content)
                            except Exception as e: st.error(str(e))
            else: st.success("Nenhuma lacuna detectada.")

        with aba_alvos:
            hd = {}
            for q in sorted(dados_questoes, key=lambda x: parse_data(x.get('data')), reverse=True):
                ts = f"{q.get('area')} - {limpar_texto(q.get('subtema'))}"
                hd.setdefault(ts, []).append({"ac": safe_int(q.get('acertos')), "er": safe_int(q.get('erros'))})
            ac = [{"Tema": ts, "Média": sum(s['ac'] for s[:3]) / sum(s['ac']+s['er'] for s[:3])} for ts, s in hd.items() if len(s) >= 3 and sum(s['ac']+s['er'] for s[:3]) > 0 and (sum(s['ac'] for s[:3]) / sum(s['ac']+s['er'] for s[:3])) < 0.6]
            if not ac: st.success("Monitoramento Verde. Sem alvos de baixo rendimento.")
            else:
                st.dataframe(pd.DataFrame([{"Zonas Críticas (<60%)": a["Tema"], "Desempenho": f"{a['Média']*100:.1f}%"} for a in sorted(ac, key=lambda x: x['Média'])]), use_container_width=True, hide_index=True)

    elif menu == "📝 Anotações Rápidas":
        st.header("Workspace de Conteúdo")
        aba_nova, aba_lista = st.tabs(["Construtor", "Repositório"])
        
        with aba_nova:
            col_i, col_f = st.columns([1, 2])
            with col_i:
                if 'nota_imgs_temp' not in st.session_state: st.session_state.nota_imgs_temp = []
                st.markdown("#### 🖼️ Camada Visual")
                if paste_image_button:
                    res = paste_image_button(label="Colar Área de Transferência", background_color=st.session_state.get("graph_font", "#111827"), hover_background_color=CORES_AREAS["Clínica Médica"], key="paste_nota_nova")
                    if res.image_data:
                        b64 = otimizar_imagem_para_api(res.image_data, 1024)
                        if b64 and b64 not in st.session_state.nota_imgs_temp: st.session_state.nota_imgs_temp.append(b64); st.rerun()
                for idx, img in enumerate(st.session_state.nota_imgs_temp):
                    if isinstance(img, str) and len(img)>50: st.image(base64.b64decode(img), use_container_width=True)
                    if st.button("Remover", key=f"rm_img_{idx}"): st.session_state.nota_imgs_temp.pop(idx); st.rerun()
            
            with col_f:
                st.markdown("#### ✍️ Estruturação")
                c_a, c_s = st.columns(2)
                a = c_a.selectbox("Domínio", AREAS_MED, key="n_a")
                sub_a = c_s.selectbox("Subdomínio", SUB_CM if a == "Clínica Médica" else SUB_CG if a == "Cirurgia Geral" else ["Geral"], key="n_s")
                s = st.text_input("Tema Central", key="anotacao_subtema")
                render_toolbar()
                p = st.text_area("Bloco de Código Mentais", height=250, key="anotacao_resumo")
                if st.button("Registrar no Cofre", type="primary", use_container_width=True):
                    if s and p:
                        db_add("anotacoes", "anotacoes", {"usuario_id": u_id, "area": a, "subtema": f"{sub_a} - {s}" if sub_a and sub_a != "Geral" else s, "pontos_chave": p, "imagens_b64": st.session_state.nota_imgs_temp, "data_criacao": str(hoje)})
                        st.session_state.anotacao_subtema, st.session_state.anotacao_resumo, st.session_state.nota_imgs_temp = "", "", []
                        st.toast("Salvo com Integridade!", icon="🛡️"); time.sleep(0.5); st.rerun()
        
        with aba_lista:
            if not dados_anotacoes: st.info("Repositório Vazio.")
            else:
                pesq = st.text_input("Buscar blocos...", key="pb").lower()
                n_ex = [n for n in dados_anotacoes if pesq in str(n.get('subtema','')).lower() or pesq in str(n.get('pontos_chave','')).lower()]
                n_ex.sort(key=lambda x: parse_data(x.get('data_criacao')), reverse=True)
                bp = sorted(list(set([n.get('area', 'Geral') for n in n_ex])))
                if bp:
                    abas = st.tabs(bp)
                    for i, b in enumerate(bp):
                        with abas[i]:
                            for n in [x for x in n_ex if x.get('area') == b]:
                                with st.expander(f"{limpar_texto(n.get('subtema'))} ({formatar_data_br(n.get('data_criacao'))})"):
                                    if st.button("Eliminar", key=f"d_n_{n['id']}"): db_delete("anotacoes", "anotacoes", n['id']); st.rerun()
                                    st.markdown(f"<div style='border-left: 3px solid {CORES_AREAS.get(b, '#000')}; padding-left: 15px; margin: 15px 0;'>{n.get('pontos_chave', '')}</div>", unsafe_allow_html=True)
                                    for img in n.get('imagens_b64', []): st.image(base64.b64decode(img), use_container_width=True)

    elif menu == "📅 Agenda de Revisões":
        st.header("Cronologia Adaptativa")
        t_p = [dict(r, data_agendada_obj=parse_data(r.get('data_agendada')), tema=limpar_texto(r.get('tema') or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('tema', 'Sem título')), area=r.get('area') or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('area', 'Geral')) for r in dados_revisoes if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
        
        aba_pend, aba_hist = st.tabs(["Missões Críticas", "Auditoria de Conclusão"])
        with aba_pend:
            st.markdown(gerar_calendario_revisoes_html(t_p, hoje.year, hoje.month), unsafe_allow_html=True)
            v_p, o_p = st.columns(2)
            f_vp = v_p.radio("Alvo:", ["Hoje", "Futuras"], horizontal=True)
            f_op = o_p.radio("Timeline:", ["Urgência", "Recentes"], horizontal=True)
            l_p = [r for r in t_p if r['data_agendada_obj'] == hoje] if f_vp == "Hoje" else [r for r in t_p if r['data_agendada_obj'] >= hoje]
            l_p.sort(key=lambda x: x['data_agendada_obj'], reverse=(f_op == "Recentes"))
            for r in l_p:
                with st.container(border=True):
                    st.markdown(f"**<span style='color:{CORES_AREAS.get(r['area'], '#64748b')};'>⬤</span> {r['tema']}**", unsafe_allow_html=True)
                    st.caption(f"{r.get('ciclo','')} | Data: {formatar_data_br(r['data_agendada_obj'])}")
                    with st.expander("Sinalizar Conclusão"):
                        c1, c2, c3 = st.columns(3)
                        q = c1.number_input("Qtd", 0, key=f"q_{r['id']}")
                        e = c2.number_input("Err", 0, key=f"e_{r['id']}")
                        if st.button("Finalizar", key=f"f_{r['id']}", type="primary"): db_update("revisoes", "revisoes", r['id'], {"status": "Concluída", "questoes_feitas": q, "erros": e, "acertos": q-e, "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")}); st.rerun()
        
        with aba_hist:
            ch = [d for d in dados_revisoes if str(d.get('status', '')).lower() in ["concluída", "concluida"]]
            if ch:
                dh = pd.DataFrame([{"Data": d.get('data_conclusao', '')[:10], "Tema": limpar_texto(d.get('tema') or mapa_aulas.get(str(d.get('aula_id', '')).strip(), {}).get('tema')), "Acertos": safe_int(d.get('acertos')), "Erros": safe_int(d.get('erros'))} for d in ch]).sort_values(by="Data", ascending=False)
                st.dataframe(dh, use_container_width=True, hide_index=True)

    elif menu == "✨ AI Tutor & Flashcards":
        aba_chat, aba_flash = st.tabs(["🧠 Preceptor IA", "📚 Engine de Flashcards"])
        with aba_chat:
            cb = st.container(height=450)
            if 'chat_ia' not in st.session_state: st.session_state.chat_ia = []
            with cb:
                for m in st.session_state.chat_ia: st.chat_message(m["role"]).write(m["content"])
            ui = st.chat_input("Dúvida de conduta...")
            if ui:
                cli = get_ia_client()
                if cli:
                    st.session_state.chat_ia.append({"role": "user", "content": ui})
                    msgs = [{"role": "system", "content": "Você é um Preceptor Médico rigoroso e cirúrgico."}] + st.session_state.chat_ia
                    try:
                        res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=msgs, temperature=0.2, max_tokens=2500)
                        st.session_state.chat_ia.append({"role": "assistant", "content": res.choices[0].message.content})
                    except Exception as e: st.error(str(e))
                    st.rerun()

        with aba_flash:
            cv = [d for d in dados_flashcards if parse_data(d.get('data_prox_revisao')) <= hoje]
            if not cv: st.success("Motor zerado. Bom descanso.")
            else:
                do = {}
                for c in cv: do.setdefault(c.get('area', 'Geral'), {}).setdefault(limpar_texto(c.get('tema', 'Tema')), []).append(c)
                ap = sorted(list(do.keys()))
                abf = st.tabs(ap)
                for idx, area in enumerate(ap):
                    with abf[idx]:
                        tms = sorted(list(do[area].keys()))
                        ca = do[area][tms[0]][0]
                        st.markdown(f"#### {ca.get('frente', '')}")
                        if st.session_state.get(f"a_{ca['id']}"):
                            st.info(ca.get('verso', ''))
                            b1, b2, b3 = st.columns(3)
                            def aval(p):
                                f, i = float(ca.get('facilidade', 2.5)), safe_int(ca.get('intervalo'))
                                ni, nf = (1, max(1.3, f-0.2)) if p == 'err' else (max(1, int((i or 1)*f)), f) if p == 'bom' else (max(1, int((i or 1)*f*1.3)), f+0.15)
                                db_update("flashcards", "flashcards", ca['id'], {"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))})
                                st.session_state[f"a_{ca['id']}"] = False
                            if b1.button("Errei", key=f"e_{ca['id']}"): aval('err'); st.rerun()
                            if b2.button("Bom", key=f"b_{ca['id']}"): aval('bom'); st.rerun()
                            if b3.button("Fácil", key=f"f_{ca['id']}"): aval('facil'); st.rerun()
                        elif st.button("Revelar", key=f"r_{ca['id']}", type="primary"): st.session_state[f"a_{ca['id']}"] = True; st.rerun()

    elif menu == "📚 Registro de Aulas":
        st.header("Biblioteca Pessoal")
        c1, c2 = st.columns([1, 2])
        with c1:
            a = st.selectbox("Área", AREAS_MED, key="ra_a")
            sub = st.selectbox("Sub", SUB_CM if a == "Clínica Médica" else SUB_CG if a == "Cirurgia Geral" else ["Geral"], key="ra_s")
            t = st.text_input("Tema", key="ra_t")
            d = st.date_input("Data", hoje, key="ra_d")
            if st.button("Registrar Aula", type="primary", use_container_width=True):
                db_add("aulas", "aulas", {"usuario_id": u_id, "area": a, "tema": f"{sub} - {t}" if sub and sub != "Geral" else t, "data_aula": str(d)})
                st.toast("Aula Indexada."); st.rerun()
        with c2:
            st.markdown(gerar_calendario_html(list(dados_aulas), hoje.year, hoje.month), unsafe_allow_html=True)
            df_a = pd.DataFrame([{"Data": formatar_data_br(a.get('data_aula')), "Área": a.get('area'), "Tema": limpar_texto(a.get('tema'))} for a in dados_aulas])
            if not df_a.empty: st.dataframe(df_a, use_container_width=True, hide_index=True)

    elif menu == "📁 Materiais e Simulados":
        st.header("Nuvem de Arquivos")
        arq = st.file_uploader("Subir PDF", type=['pdf'])
        if arq and st.button("Upload", type="primary"):
            c = os.path.join("materiais_estudo", arq.name)
            with open(c, "wb") as f: f.write(arq.getbuffer())
            db_add("materiais", "materiais", {"usuario_id": u_id, "titulo": arq.name, "path": c, "data_upload": str(hoje)}); st.rerun()
        df_m = pd.DataFrame([{"Arquivo": m.get('titulo'), "Data": formatar_data_br(m.get('data_upload'))} for m in dados_materiais])
        if not df_m.empty: st.dataframe(df_m, use_container_width=True, hide_index=True)

    elif menu == "🏥 Simulados & OSCE":
        st.header("Centro de Simulação Clínica")
        aba_p, aba_osce = st.tabs(["Evolução Simulada", "Consultório IA (OSCE)"])
        with aba_p:
            if len(dados_simulados) >= 2:
                dfs = pd.DataFrame([{"D": parse_data(s.get('data_realizacao')), "N": float(s.get('minha_nota',0))} for s in dados_simulados])
                fig = px.line(dfs, x='D', y='N', line_shape='spline')
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=st.session_state.get("graph_font", "#0f172a"))
                st.plotly_chart(fig, use_container_width=True)
        with aba_osce:
            cli = get_ia_client()
            if cli:
                da = st.text_input("Gabarito (Diagnóstico)")
                if st.button("Iniciar Estação"):
                    st.session_state.osce_hist, st.session_state.osce_active = [], True
                    st.session_state.osce_sys = f"Você é o paciente. Responda sintomas. Diagnóstico oculto: {da}. Para exames, envie [EXAME: ecg_normal]."
                    st.rerun()
                if st.session_state.get('osce_active'):
                    for m in st.session_state.osce_hist:
                        with st.chat_message(m["role"]):
                            if m["role"] == "assistant": renderizar_mensagem_osce(m["content"])
                            else: st.write(m["content"])
                    u_in = st.chat_input("Fale com o paciente...")
                    if u_in:
                        st.session_state.osce_hist.append({"role": "user", "content": u_in})
                        res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role": "system", "content": st.session_state.osce_sys}] + st.session_state.osce_hist, temperature=0.6, max_tokens=1000)
                        st.session_state.osce_hist.append({"role": "assistant", "content": res.choices[0].message.content}); st.rerun()

    elif menu == "📍 GPS da Aprovação":
        st.header("Métricas Avançadas")
        st.metric("Total Simulados", len(dados_simulados))

    elif menu == "⏱️ Modo Foco":
        st.header("Isolamento Pomodoro")
        tf = st.selectbox("Duração", [25, 50, 90])
        if not st.session_state.get('foco_iniciado'):
            if st.button("Iniciar"): st.session_state.foco_iniciado, st.session_state.foco_fim = True, get_agora() + timedelta(minutes=tf); st.rerun()
        else:
            t_seg = int((st.session_state.foco_fim - get_agora()).total_seconds())
            if t_seg > 0: components.html(f"<h1 style='font-size:80px; text-align:center; font-family:sans-serif;'>{t_seg//60:02d}:{t_seg%60:02d}</h1>", height=120)
            else: st.success("Tempo esgotado!")
            if st.button("Encerrar"): st.session_state.foco_iniciado = False; st.rerun()

    elif menu == "⚙️ Configurações":
        st.header("Ajustes")
        mo = st.radio("Tema", ["Claro", "Escuro"], index=0 if user_settings.get("tema_modo") == "Claro" else 1)
        if st.button("Salvar Tema", type="primary"): db_update("usuarios", "user_settings", u_id, {"tema_modo": mo}); st.session_state.user_settings["tema_modo"] = mo; st.rerun()

    elif is_super_admin(st.session_state.user_nome) and menu == "👑 Admin":
        st.header("Terminal de Controle")
        df_u = pd.DataFrame([{"Nome": u.to_dict().get('nome')} for u in db.collection("usuarios").get()])
        st.dataframe(df_u, hide_index=True)
