import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date, timezone
import os, time, hashlib, uuid, base64, json, calendar, re, io
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
                "theme_color": "#4f46e5",
                "background_color": "#0f172a",
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
# FUNÇÃO MESTRE DE ESTILIZAÇÃO CSS (V 2.0 PREMIUM)
# ==========================================
def aplicar_css_tema(modo):
    if modo == "Escuro":
        bg_color = "#0f172a"          
        text_color = "#f8fafc"        
        metric_bg = "#1e293b"         
        metric_border = "#334155"     
        sidebar_bg = "#0f172a"
        input_bg = "#1e293b"
        input_text = "#f8fafc"
        menu_text = "#94a3b8"
        menu_hover = "#1e293b"
        bg_tabela = "#1e293b"
        th_bg = "#0f172a"
        cor_texto_tabela = "#e2e8f0"
        shadow = "0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.3)"
        shadow_hover = "0 20px 25px -5px rgba(0, 0, 0, 0.6), 0 8px 10px -6px rgba(0, 0, 0, 0.4)"
        blue_accent = "#4f46e5"       
        blue_hover = "#4338ca"
    else:
        bg_color = "#f8fafc"          
        text_color = "#0f172a"        
        metric_bg = "#ffffff"         
        metric_border = "#e2e8f0"     
        sidebar_bg = "#ffffff"
        input_bg = "#f1f5f9"          
        input_text = "#0f172a"
        menu_text = "#64748b"
        menu_hover = "#f1f5f9"
        bg_tabela = "#ffffff"
        th_bg = "#f8fafc"
        cor_texto_tabela = "#334155"
        shadow = "0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)"
        shadow_hover = "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)"
        blue_accent = "#4f46e5"       
        blue_hover = "#4338ca"

    css_str = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Protegendo a fonte Inter apenas onde importa, sem quebrar os ícones do Streamlit (keyboard_double) */
    .stApp, [data-testid="stAppViewContainer"], .main {{ 
        background-color: {bg_color} !important; 
        color: {text_color} !important; 
        font-family: 'Inter', sans-serif; 
    }}
    h1, h2, h3, h4, h5, h6, p, .stMarkdown, label {{ 
        font-family: 'Inter', sans-serif !important; 
        color: {text_color} !important; 
    }}
    
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {metric_border}; border-radius: 10px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
    
    [data-baseweb="input"] > div, [data-baseweb="textarea"] > div, [data-baseweb="select"] > div, [data-testid="stFileUploadDropzone"] {{
        background-color: {input_bg} !important; 
        border: 1px solid {metric_border} !important;
        border-radius: 12px !important;
        transition: all 0.3s ease;
    }}
    [data-baseweb="input"] > div:focus-within, [data-baseweb="textarea"] > div:focus-within, [data-baseweb="select"] > div:focus-within {{
        border-color: {blue_accent} !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.2) !important;
    }}
    input, textarea, div[data-baseweb="select"] span {{ 
        color: {input_text} !important; 
        -webkit-text-fill-color: {input_text} !important; 
    }}
    
    button[kind="primary"], button[kind="secondary"], button[kind="formSubmit"], div[data-testid="stFormSubmitButton"] > button {{
        background-color: {blue_accent} !important; 
        border: none !important; 
        border-radius: 10px !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 6px rgba(79, 70, 229, 0.25) !important;
    }}
    button[kind="primary"]:hover, button[kind="formSubmit"]:hover {{
        background-color: {blue_hover} !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(79, 70, 229, 0.35) !important;
    }}
    .stButton > button {{ 
        border-radius: 10px !important; 
        background-color: {blue_accent} !important; 
        color: white !important; 
        border: none !important; 
        transition: all 0.2s ease !important; 
    }}
    .stButton > button:hover {{ transform: translateY(-2px); }}
    
    [data-baseweb="tab-list"] {{
        background-color: {input_bg} !important;
        border-radius: 14px;
        padding: 6px;
        border: 1px solid {metric_border};
    }}
    button[data-baseweb="tab"] {{ border-radius: 10px !important; border: none !important; background: transparent !important; padding: 8px !important; }}
    button[data-baseweb="tab"][aria-selected="true"] {{ background: {metric_bg} !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important; }}
    
    [data-testid="stVerticalBlockBorderWrapper"], [data-testid="stMetric"] {{ 
        background-color: {metric_bg} !important; 
        border: 1px solid {metric_border} !important; 
        border-radius: 16px !important; 
        box-shadow: {shadow} !important; 
        transition: transform 0.2s ease !important; 
    }}
    [data-testid="stVerticalBlockBorderWrapper"]:hover, [data-testid="stMetric"]:hover {{ transform: translateY(-3px); }}
    
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; border-right: 1px solid {metric_border} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{ padding: 12px 16px; border-radius: 12px; margin-bottom: 8px; transition: all 0.2s ease; cursor: pointer; border: 1px solid transparent; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background-color: {menu_hover} !important; transform: translateX(4px); border-color: {metric_border}; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background-color: {blue_accent} !important; box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4); border-color: {blue_accent}; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color: white !important; font-weight: 700 !important; }}
    
    .profile-img {{ border-radius: 50%; object-fit: cover; border: 4px solid {blue_accent}; width: 140px; height: 140px; display: block; margin: 0 auto; box-shadow: 0 8px 20px rgba(0,0,0,0.25); }}
    </style>
    """
    st.markdown(css_str, unsafe_allow_html=True)
    st.session_state["graph_bg"] = bg_color
    st.session_state["graph_font"] = text_color

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
            firebase_secrets = dict(st.secrets["textkey"])
            if "private_key" in firebase_secrets:
                firebase_secrets["private_key"] = firebase_secrets["private_key"].strip().replace('"', '').replace("'", "").replace("\\n", "\n")
            cred = credentials.Certificate(firebase_secrets)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao conectar ao Firebase: {e}")
            st.stop()
    return firestore.client()

db = init_firebase()

for d in ["materiais_estudo", "imagens_flashcards"]:
    if not os.path.exists(d): 
        os.makedirs(d)

# ==========================================
# FUNÇÕES DE BANCO OTIMIZADAS
# ==========================================
def db_add(col_name, state_key, data):
    doc_ref = db.collection(col_name).document()
    doc_ref.set(data)
    data["id"] = doc_ref.id
    if state_key in st.session_state.dados:
        st.session_state.dados[state_key].append(data)
    return doc_ref

def db_update(col_name, state_key, doc_id, updates):
    db.collection(col_name).document(doc_id).update(updates)
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
        if isinstance(colecoes, str): 
            colecoes = [colecoes]
        for colecao in colecoes:
            col_db = "questoes_sessoes" if colecao == "questoes" else ("focus_sessoes" if colecao == "focus" else colecao)
            st.session_state.dados[colecao] = get_user_docs(col_db, st.session_state.user_id)
    else:
        st.session_state.pop('dados', None)
        st.session_state.user_data_loaded = False

def otimizar_imagem_para_api(img_data, max_size=500):
    if Image is None: return ""
    try:
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
        return ""

def get_ia_client():
    if "model_ia" not in st.session_state:
        if Groq and CHAVE_GROQ_FIXA:
            st.session_state.model_ia = Groq(api_key=CHAVE_GROQ_FIXA)
        else:
            st.session_state.model_ia = None
    return st.session_state.model_ia

def chamar_ia(client, *, modelo, **kwargs):
    candidatos = MODELOS_VISAO_FALLBACK if modelo == MODELO_VISAO else MODELOS_TEXTO_FALLBACK
    for m in candidatos:
        try:
            call_kwargs = dict(kwargs)
            if "qwen3.6-27b" in m:
                call_kwargs.update({"reasoning_effort": "none", "include_reasoning": False})
            call_kwargs.pop("response_format", None)
            return client.chat.completions.create(model=m, **call_kwargs)
        except Exception as exc:
            if any(token in str(exc).lower() for token in ("model_not_found", "not exist", "access", "404", "403")): 
                continue
            raise
    raise RuntimeError("Nenhum modelo Groq disponível.")

def extrair_json_seguro(texto):
    if not texto: return {}
    t = str(texto)
    t = re.sub(r'<think>.*?</think>', '', t, flags=re.DOTALL)
    t = re.sub(r'<think>.*', '', t, flags=re.DOTALL)
    t = t.replace("```json", "").replace("```", "").strip()
    
    start_obj = t.find('{')
    start_arr = t.find('[')
    
    if start_obj == -1 and start_arr == -1: return {}
    
    is_obj = start_obj != -1 and (start_arr == -1 or start_obj < start_arr)
    t = t[start_obj:] if is_obj else t[start_arr:]
    
    try:
        parsed = json.loads(t)
        return {"tarefas": parsed, "questoes": parsed} if isinstance(parsed, list) else parsed
    except: pass
    
    fix = t
    if fix.count('"') % 2 != 0: fix += '"'
    fix = fix.strip().rstrip(',')
    fix += ']' * (fix.count('[') - fix.count(']')) + '}' * (fix.count('{') - fix.count('}'))
    
    try:
        parsed = json.loads(fix)
        return {"tarefas": parsed, "questoes": parsed} if isinstance(parsed, list) else parsed
    except: return {}

# ==========================================
# CONSTANTES E CORES
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
SUB_CM = ["Geral", "Cardiologia", "Nefrologia", "Endocrinologia", "Pneumologia", "Gastroenterologia", "Reumatologia", "Hematologia", "Infectologia", "Neurologia"]
SUB_CG = ["Geral", "Cirurgia do Trauma", "Cirurgia Vascular", "Cirurgia Plástica", "Cirurgia Torácica", "Cirurgia Pediátrica", "Urologia", "Neurocirurgia", "Ortopedia", "Cirurgia Oncológica", "Cirurgia Cabeça e Pescoço"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#4f46e5", "Pediatria": "#ec4899", "Ginecologia e Obstetrícia": "#8b5cf6", "Medicina Preventiva": "#10b981", "Cirurgia Geral": "#ef4444", "Geral": "#64748b"}
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
                <div style="border: 1px solid {bd_osce}; border-radius: 16px; padding: 20px; margin: 15px 0; background-color: {bg_osce}; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
                    <p style="color: #4f46e5; font-weight: 700; margin-bottom: 12px; font-size: 16px; display: flex; align-items: center; gap: 8px;">📎 Laudo Anexo: {chave.replace('_', ' ').title()}</p>
                    <img src="{img_url}" style="width: 100%; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"*(O paciente entrega um laudo correspondente a {chave}, porém sem imagem disponível no banco)*")

def get_agora(): return datetime.now(timezone.utc) - timedelta(hours=3)
def hash_senha(senha): return hashlib.sha256(str.encode(senha)).hexdigest()
def is_super_admin(nome): return str(nome).lower().strip() in ['joao', 'joão', 'joao victor']

def safe_int(valor):
    try: return int(float(valor)) if valor else 0
    except: return 0

def limpar_texto(texto):
    if not texto: return "Sem título"
    return re.sub(r'^[A-Za-z0-9_-]{10,40}\s*\|\s*', '', str(texto)).strip()

def parse_data(d):
    if not d: return get_agora().date()
    if isinstance(d, datetime): return d.date()
    if isinstance(d, date): return d
    if isinstance(d, str):
        d_str = d.strip()[:10]
        try:
            if '-' in d_str: 
                return datetime.strptime(d_str, "%Y-%m-%d" if len(d_str.split('-')[0])==4 else "%d-%m-%Y").date()
            if '/' in d_str: 
                return datetime.strptime(d_str, "%Y/%m/%d" if len(d_str.split('/')[0])==4 else "%d/%m/%Y").date()
        except: pass
    return get_agora().date()

def formatar_data_br(d): 
    return parse_data(d).strftime("%d/%m/%Y") if d else "-"

def get_user_docs(collection_name, user_id):
    try: 
        return [{"id": d.id, **d.to_dict()} for d in db.collection(collection_name).where(filter=FieldFilter("usuario_id", "==", str(user_id))).get()]
    except Exception: return []

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
        
    html_code = f"<div style='background-color:{bg_ct}; padding:25px; border-radius:16px; margin-bottom:20px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'><table style='width:100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:10px 8px; color:{tc_th}; background-color: transparent !important; border: none !important; font-size:13px; text-transform: uppercase; letter-spacing: 0.5px;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_em} !important; border-radius:8px;'></td>"
            else:
                if day in aulas_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(a.get('area'), '#64748b')}; color:white !important; padding:6px 8px; border-radius:6px; font-size:11px; font-weight: 500; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(a.get('tema', '')))}'>{html.escape(limpar_texto(a.get('tema', '')))}</div>" for a in aulas_dict[day]])
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_cl} !important; vertical-align:top; height:100px; border-radius:8px; transition: all 0.2s;' onmouseover=\"this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'\" onmouseout=\"this.style.transform='translateY(0)'; this.style.boxShadow='none'\"><strong style='color:{tc_st} !important; font-size:15px;'>{day}</strong><div style='margin-top:10px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_cl} !important; vertical-align:top; height:100px; border-radius:8px;'><strong style='color:{tc_em} !important; font-size:15px;'>{day}</strong></td>"
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
        
    html_code = f"<div style='background-color:{bg_ct}; padding:25px; border-radius:16px; margin-bottom:25px; box-shadow: 0 4px 10px rgba(0,0,0,0.05);'><table style='width:100%; border-collapse: separate; border-spacing: 4px; table-layout: fixed;'>"
    html_code += "<tr>"
    for dia_sem in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]:
        html_code += f"<th style='text-align:center; padding:10px 8px; color:{tc_th}; background-color: transparent !important; border: none !important; font-size:13px; text-transform: uppercase; letter-spacing: 0.5px;'>{dia_sem}</th>"
    html_code += "</tr>"
    
    for week in cal:
        html_code += "<tr>"
        for day in week:
            if day == 0: 
                html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_em} !important; border-radius:8px;'></td>"
            else:
                if day in revs_dict:
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(r.get('area'), '#64748b')}; color:white !important; padding:6px 8px; border-radius:6px; font-size:11px; font-weight: 500; margin-bottom:6px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})'>{html.escape(limpar_texto(r.get('tema', '')))} <span style='opacity: 0.8; font-size: 9px;'>({r.get('ciclo').split(' ')[0]})</span></div>" for r in revs_dict[day]])
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_cl} !important; vertical-align:top; height:100px; border-radius:8px; transition: all 0.2s;' onmouseover=\"this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0,0,0,0.1)'\" onmouseout=\"this.style.transform='translateY(0)'; this.style.boxShadow='none'\"><strong style='color:{tc_st} !important; font-size:15px;'>{day}</strong><div style='margin-top:10px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:10px; background-color:{bg_cl} !important; vertical-align:top; height:100px; border-radius:8px;'><strong style='color:{tc_em} !important; font-size:15px;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

def render_toolbar():
    """
    A Barra Fixa Otimizada.
    Sem barra flutuante rodando no fundo. Leve, responsiva e com auto-save silencioso no navegador.
    """
    toolbar_html = """
    <div id="inline-toolbar" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; background: rgba(30, 41, 59, 0.5); padding: 10px 15px; border-radius: 12px; border: 1px solid #334155; width: 100%; box-sizing: border-box; margin-bottom: 10px;">
        <span style="color: #f8fafc; font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; margin-right: 5px;">🪄 Formatador:</span>
        <button class="inline-fmt-btn" data-t1="**" data-t2="**" style="padding: 6px 12px; border-radius: 8px; border: none; background: #4f46e5; color: white; cursor: pointer; font-weight: bold; transition: transform 0.1s, background 0.2s;">B</button>
        <button class="inline-fmt-btn" data-t1="<u>" data-t2="</u>" style="padding: 6px 12px; border-radius: 8px; border: none; background: #4f46e5; color: white; cursor: pointer; text-decoration: underline; transition: transform 0.1s, background 0.2s;">U</button>
        <button class="inline-fmt-btn" data-t1="<mark>" data-t2="</mark>" style="padding: 6px 12px; border-radius: 8px; border: none; background: #4f46e5; color: white; cursor: pointer; transition: transform 0.1s, background 0.2s;">🖍️ Grifar</button>
        <button class="inline-fmt-btn" data-t1="\\n- " data-t2="" style="padding: 6px 12px; border-radius: 8px; border: none; background: #4f46e5; color: white; cursor: pointer; transition: transform 0.1s, background 0.2s;">📋 Tópico</button>
        <button class="inline-fmt-btn" data-t1="PASTE" data-t2="" style="padding: 6px 12px; border-radius: 8px; border: none; background: #10b981; color: white; cursor: pointer; font-weight: bold; transition: transform 0.1s, background 0.2s; margin-left: auto;">📸 Colar Imagem</button>
    </div>
    
    <script>
    function formatTextLocal(tagStart, tagEnd) {
        const parentDoc = window.parent.document;
        const textareas = parentDoc.querySelectorAll('textarea');
        if (textareas.length === 0) return;
        
        let ta = null;
        if (parentDoc.activeElement && parentDoc.activeElement.tagName === 'TEXTAREA') {
            ta = parentDoc.activeElement;
        } else {
            for(let i=textareas.length-1; i>=0; i--){
                let label = textareas[i].getAttribute('aria-label') || '';
                if(label.includes('Pontos') || label.includes('Anotação') || label.includes('Resumo') || label.includes('Tópicos') || label.includes('Chaves') || label.includes('Verso')) {
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
            ta.dispatchEvent(new Event('input', { bubbles: true })); 
            
            ta.focus();
            ta.setSelectionRange(start + tagStart.length, start + tagStart.length + selectedText.length);
        }
    }

    function focusPasteLocal() {
        const parentDoc = window.parent.document;
        const pasteFrames = parentDoc.querySelectorAll('iframe[title*="paste"]');
        if (pasteFrames.length > 0) {
            const target = pasteFrames[pasteFrames.length - 1];
            target.focus();
            target.scrollIntoView({behavior: 'smooth', block: 'center'});
            const container = target.closest('div[data-testid="stElementContainer"]');
            if (container) {
                container.style.transition = 'box-shadow 0.3s, transform 0.3s';
                container.style.boxShadow = '0 0 25px 8px rgba(16, 185, 129, 0.5)';
                container.style.transform = 'scale(1.02)';
                setTimeout(() => {
                    container.style.boxShadow = 'none';
                    container.style.transform = 'scale(1)';
                }, 1200);
            }
        } else {
            alert("⚠️ Área de colagem de imagem não encontrada.");
        }
    }

    // Configuração dos botões anti-perda-de-foco
    document.querySelectorAll('.inline-fmt-btn').forEach(btn => {
        if (!btn.dataset.bound) {
            btn.dataset.bound = "true";
            const action = (e) => {
                e.preventDefault(); 
                btn.style.transform = 'scale(0.92)';
                setTimeout(() => btn.style.transform = 'scale(1)', 100);
                
                let t1 = btn.getAttribute('data-t1');
                let t2 = btn.getAttribute('data-t2');
                
                if (t1 === "PASTE") {
                    focusPasteLocal();
                } else {
                    formatTextLocal(t1, t2);
                }
            };
            btn.addEventListener('mousedown', action);
            btn.addEventListener('touchstart', action, {passive: false});
        }
    });

    // Auto-Save super leve no LocalStorage
    setTimeout(() => {
        const textareas = window.parent.document.querySelectorAll('textarea');
        textareas.forEach((ta, index) => {
            if (ta.dataset.asaveBound) return; 
            ta.dataset.asaveBound = "true";
            
            const label = ta.getAttribute('aria-label') || '';
            if(label.includes('Pontos') || label.includes('Anotação') || label.includes('Resumo') || label.includes('Tópicos') || label.includes('Chaves')) {
                const storageKey = 'autosave_nota_' + label.replace(/\\s+/g, '_') + '_' + index;
                
                const savedText = window.parent.localStorage.getItem(storageKey);
                if (savedText && ta.value === "") {
                    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                    nativeInputValueSetter.call(ta, savedText);
                    ta.dispatchEvent(new Event('input', { bubbles: true }));
                }

                ta.addEventListener('input', function() {
                    window.parent.localStorage.setItem(storageKey, ta.value);
                });
            }
        });
    }, 1000);
    </script>
    """
    components.html(toolbar_html, height=75)

# ==========================================
# INÍCIO - LOGIN
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
    
    st.markdown("<h1 style='text-align:center; font-weight:800; font-size:3rem;'>🏥 Residência PRO <span style='color:#4f46e5;'>2.0</span></h1>", unsafe_allow_html=True)
    st.session_state.temp_theme = st.radio("Tema Visual:", ["Escuro", "Claro"], horizontal=True, index=0 if st.session_state.temp_theme == "Escuro" else 1)
    
    aba_l, aba_c = st.tabs(["🔑 Acesso VIP", "📝 Nova Conta"])
    with aba_l:
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
                                    time.sleep(1)
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
                        existe = True; break
                if existe: st.error("Usuário já existe.")
                else:
                    db.collection("usuarios").add({"nome": nu_limpo, "senha": hash_senha(np_limpo), "tema_modo": st.session_state.temp_theme})
                    st.toast("✅ Conta criada com sucesso!", icon="🎉")# ==========================================
# APLICATIVO LOGADO
# ==========================================
else:
    u_id, hoje = str(st.session_state.user_id), get_agora().date()
    if 'dados' not in st.session_state:
        st.session_state.dados = {"aulas": [], "revisoes": [], "flashcards": [], "questoes": [], "simulados": [], "focus": [], "materiais": [], "cronogramas": [], "anotacoes": [], "questoes_hiit": [], "revisoes_hiit": [], "anotacoes_hiit": [], "flashcards_hiit": []}

    if not st.session_state.get('user_data_loaded'):
        with st.spinner("Carregando dados da nuvem..."):
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
            except Exception as e:
                st.error(f"🚨 Falha de conexão: {str(e)}"); st.stop()

    us = st.session_state.user_settings
    dcache = st.session_state.dados
    mapa_aulas = {str(a.get("id")).strip(): a for a in dcache["aulas"]} 

    aplicar_css_tema(us.get("tema_modo", "Escuro"))

    if us.get('foto_perfil_b64'):
        st.sidebar.markdown(f'<img src="data:image/jpeg;base64,{us["foto_perfil_b64"]}" class="profile-img"><h3 style="text-align: center; margin-top: 15px; margin-bottom: 25px;">{st.session_state.user_nome}</h3>', unsafe_allow_html=True)
    else: 
        st.sidebar.markdown(f"<h2 style='text-align:center;'>👤 {st.session_state.user_nome}</h2>", unsafe_allow_html=True)

    if st.sidebar.button("🚪 Sair da Conta", use_container_width=True):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        time.sleep(0.5); st.session_state.clear(); st.rerun()
    st.sidebar.markdown("---")

    opcoes_menu = ["🏠 Dashboard", "🗓️ Cronograma IA", "⚡ Revisão HIIT", "🎯 Questões", "📚 Registro de Aulas", "📝 Anotações Rápidas", "📅 Agenda de Revisões", "✨ AI Tutor & Flashcards", "📁 Materiais e Simulados", "🏥 Simulados & OSCE", "📍 GPS da Aprovação", "⏱️ Modo Foco", "⚙️ Configurações", "📱 Instalar App"]
    if is_super_admin(st.session_state.user_nome): opcoes_menu.append("👑 Admin")
    menu = st.sidebar.radio("Navegação Principal", opcoes_menu)
    
    if menu == "🏠 Dashboard":
        st.header("Painel Global 2.0")
        rp = [r for r in dcache["revisoes"] + dcache["revisoes_hiit"] if str(r.get('status','')).lower() in ['pendente', 'pendentes']]
        rhoje = [r for r in rp if parse_data(r.get('data_agendada')) <= hoje]
        rfut = sorted([r for r in rp if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
        st.info(f"📅 **Sua Próxima Revisão Futura será em:** {formatar_data_br(rfut[0].get('data_agendada')) if rfut else '-'}")
        if rhoje: st.warning(f"🚨 **Atenção:** Você tem **{len(rhoje)}** revisões para fazer HOJE. Vá na aba de Revisões.")
        else: st.success("✅ Você não tem revisões para fazer hoje. Tudo em dia!")
        st.divider()
        
        a1, a2 = st.tabs(["📊 Resumo Geral", "📈 Análise por Matéria"])
        with a1:
            ac_g = sum(safe_int(q.get('acertos')) for q in dcache["questoes"] + dcache["questoes_hiit"] + [r for r in dcache["revisoes"]+dcache["revisoes_hiit"] if r.get('status')=='Concluída'])
            er_g = sum(safe_int(q.get('erros')) for q in dcache["questoes"] + dcache["questoes_hiit"] + [r for r in dcache["revisoes"]+dcache["revisoes_hiit"] if r.get('status')=='Concluída'])
            tg = ac_g + er_g
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Questões Totais", tg); c2.metric("🟢 Acertos", ac_g); c3.metric("🔴 Erros", er_g); c4.metric("🎯 Taxa de Acerto", f"{(ac_g/tg*100) if tg>0 else 0:.1f}%")
            col1, col2 = st.columns([1, 1.5])
            modo_g_font = st.session_state.get("graph_font", "#f8fafc")
            modo_g_bg = st.session_state.get("graph_bg", "#0f172a")
            with col1:
                if tg > 0:
                    fig = px.pie(names=['Acertos', 'Erros'], values=[ac_g, er_g], hole=0.65, color_discrete_sequence=["#10b981", '#ef4444'])
                    fig.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color=modo_g_bg, width=3)))
                    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, margin=dict(t=30,b=10,l=0,r=0), showlegend=False, title_text="Precisão Global", title_x=0.5)
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
            with col2:
                ld = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in dcache["questoes"]+dcache["questoes_hiit"]+[r for r in dcache["revisoes"]+dcache["revisoes_hiit"] if r.get('status')=='Concluída']]
                df = pd.DataFrame(ld).dropna(subset=['area'])
                if not df.empty:
                    dfg = df.groupby('area')[['acertos','erros']].sum().reset_index()
                    dfg['Taxa'] = (dfg['acertos'] / (dfg['acertos']+dfg['erros'])) * 100
                    fig2 = px.bar(dfg.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS, text_auto='.1f')
                    fig2.update_traces(textposition="outside", cliponaxis=False)
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, showlegend=False, margin=dict(t=30,b=0,l=0,r=20), title_text="Desempenho por Matéria", title_x=0.5, xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar':False})
        with a2:
            f = st.selectbox("Selecione a Especialidade:", AREAS_MED)
            ac_f = sum(safe_int(q.get('acertos')) for q in dcache["questoes"]+dcache["questoes_hiit"]+[r for r in dcache["revisoes"]+dcache["revisoes_hiit"] if r.get('status')=='Concluída'] if q.get('area')==f)
            er_f = sum(safe_int(q.get('erros')) for q in dcache["questoes"]+dcache["questoes_hiit"]+[r for r in dcache["revisoes"]+dcache["revisoes_hiit"] if r.get('status')=='Concluída'] if q.get('area')==f)
            t_f = ac_f + er_f
            c1, c2, c3 = st.columns(3); c1.metric(f"Questões ({f})", t_f); c2.metric("🟢 Acertos", ac_f); c3.metric("🎯 Aproveitamento", f"{(ac_f/t_f*100) if t_f>0 else 0:.1f}%")

    elif menu == "🗓️ Cronograma IA":
        st.header("Cronograma Inteligente da Semana")
        if 'p_cols' not in st.session_state: st.session_state.p_cols = []
        aba_lista, aba_importar, aba_manual = st.tabs(["✅ Minhas Metas", "📸 Extrair com IA", "➕ Adicionar Manualmente"])
        with aba_importar:
            ns = st.text_input("Qual é o nome desta semana? (Ex: Semana 1, Reta Final)")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("### 📋 Colar Prints (Suporta Múltiplos)")
                if paste_image_button is not None:
                    rp = paste_image_button("CLIQUE AQUI E APERTE Ctrl+V", "#4f46e5", "#4338ca", "paste_crono")
                    if rp.image_data is not None:
                        buf = io.BytesIO(); rp.image_data.save(buf, format="PNG")
                        img_hash = hashlib.md5(buf.getvalue()).hexdigest()
                        if not any(item['hash'] == img_hash for item in st.session_state.p_cols):
                            st.session_state.p_cols.append({'hash': img_hash, 'img': rp.image_data, 'bytes': buf.getvalue()}); st.rerun()
                if st.session_state.p_cols:
                    st.toast(f"{len(st.session_state.p_cols)} print(s) na fila para extração.", icon="📸")
                    if st.button("Limpar Fila"): st.session_state.p_cols = []; st.rerun()
            with c2:
                st.markdown("### 📂 Enviar Arquivos")
                imgs_crono = st.file_uploader("Selecione os arquivos", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True, label_visibility="collapsed")
            st.divider()
            if (imgs_crono or st.session_state.p_cols) and ns and st.button("🪄 Extrair Metas com IA", use_container_width=True):
                cli = get_ia_client()
                if cli:
                    with st.spinner("Visão Computacional analisando imagens..."):
                        t_imgs = [otimizar_imagem_para_api(i, 720) for i in imgs_crono] + [otimizar_imagem_para_api(i['img'], 720) for i in st.session_state.p_cols]
                        tot = []
                        pb = st.progress(0)
                        for i, ib in enumerate(t_imgs):
                            p = """Extraia TODAS as tarefas visíveis. Retorne JSON puro: {"tarefas": [{"materia": "...", "tema": "...", "cor": "..."}]} Sem markdown, sem texto extra."""
                            try:
                                res = chamar_ia(cli, modelo=MODELO_VISAO, messages=[{"role": "user", "content": [{"type": "text", "text": p}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{ib}"}}]}], temperature=0.1, max_tokens=2500)
                                tot.extend(extrair_json_seguro(res.choices[0].message.content).get("tarefas", []))
                            except Exception as e: st.warning(f"Aviso na imagem {i+1}: {e}")
                            pb.progress((i + 1) / len(t_imgs))
                        if tot:
                            b = db.batch()
                            for t in tot:
                                c = str(t.get("cor", "")).lower(); p_val = 1 if "azul" in c else (2 if "verde" in c else (4 if "vermelho" in c else (5 if "roxo" in c else 3)))
                                t["prioridade"] = p_val
                            for i, t in enumerate(sorted(tot, key=lambda x: x.get("prioridade", 3))):
                                ref = db.collection("cronogramas").document()
                                nt = {"usuario_id": u_id, "semana": ns, "dia": ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado"][i%6], "materia": t.get("materia", ""), "tema": t.get("tema", ""), "prioridade": t.get("prioridade", 3), "concluido": False, "data_importacao": str(hoje), "data_conclusao": None}
                                b.set(ref, nt); nt["id"] = ref.id; dcache["cronogramas"].append(nt)
                            b.commit()
                            st.session_state.p_cols = []; st.toast(f"✅ {len(tot)} metas importadas!", icon="🎉"); time.sleep(1); st.rerun()
                        else: st.warning("A IA não encontrou tarefas no formato esperado.")
        with aba_manual:
            st.markdown("### ➕ Inserir Manualmente")
            c3, c4 = st.columns(2)
            m_materia = c3.selectbox("Matéria", AREAS_MED + ["Outra"], key="c_mat")
            sub_m = c4.selectbox("Subespecialidade", SUB_CM, key="c_sub") if m_materia == "Clínica Médica" else (c4.selectbox("Subespecialidade", SUB_CG, key="c_sub_cg") if m_materia == "Cirurgia Geral" else "")
            with st.form("cm", clear_on_submit=True):
                c1, c2 = st.columns(2); ms = c1.text_input("Semana"); md = c2.selectbox("Dia", ["Segunda","Terça","Quarta","Quinta","Sexta","Sábado","Domingo"])
                mt = st.text_input("Tema"); mp = st.selectbox("Prioridade", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x))
                if st.form_submit_button("Adicionar", use_container_width=True) and ms and mt:
                    db_add("cronogramas", "cronogramas", {"usuario_id": u_id, "semana": ms, "dia": md, "materia": m_materia, "tema": f"{sub_m} - {mt}" if sub_m and sub_m != "Geral" else mt, "prioridade": mp, "concluido": False, "data_importacao": str(hoje), "data_conclusao": None})
                    st.toast("Adicionado!", icon="🎯"); time.sleep(0.5); st.rerun()
        with aba_lista:
            def sk(sem):
                ds = [parse_data(c.get("data_importacao", str(hoje))) for c in dcache["cronogramas"] if c.get("semana", "Semana Geral") == sem]
                ns = re.findall(r'\d+', sem)
                return (max(ds) if ds else parse_data(None), int(ns[0]) if ns else 0)
            su = sorted(list(set(c.get("semana", "Semana Geral") for c in dcache["cronogramas"])), key=sk, reverse=True)
            if not dcache["cronogramas"]: st.info("Nenhum cronograma.")
            else:
                tp = st.text_input("🔍 Pesquisar...", "").lower()
                for sem in su:
                    ts = [c for c in dcache["cronogramas"] if c.get("semana", "Semana Geral") == sem]
                    if tp: ts = [c for c in ts if tp in str(c.get('tema','')).lower() or tp in str(c.get('materia','')).lower()]
                    if tp and not ts: continue
                    st.write("---")
                    c_t, c_d = st.columns([0.7, 0.3])
                    c_t.subheader(f"📂 {sem}")
                    if c_d.button("🗑️ Excluir Semana", key=f"ds_{sem}"):
                        b = db.batch(); d_ids = []
                        for td in [c for c in dcache["cronogramas"] if c.get("semana", "Semana Geral") == sem]:
                            if td.get('id'): b.delete(db.collection("cronogramas").document(td['id'])); d_ids.append(td['id'])
                        b.commit(); dcache["cronogramas"] = [c for c in dcache["cronogramas"] if c.get('id') not in d_ids]; st.rerun()
                    
                    pdts = sorted([c for c in ts if not c.get("concluido")], key=lambda x: safe_int(x.get("prioridade", 3)))
                    conc = [c for c in ts if c.get("concluido")]
                    
                    for t in pdts:
                        tid = str(t.get('id', uuid.uuid4()))
                        with st.container(border=True):
                            c1, c2, c3, c4 = st.columns([0.1, 0.55, 0.25, 0.1])
                            if c1.button("✔️", key=f"b_{tid}"): db_update("cronogramas", "cronogramas", tid, {"concluido": True, "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")}); st.rerun()
                            c2.markdown(f"**{t.get('dia','')}**: {t.get('materia','')} - {t.get('tema','')}")
                            pv = safe_int(t.get('prioridade', 3))
                            nv = c3.selectbox("Prioridade", options=[1, 2, 3, 4, 5], format_func=lambda x: PRIORIDADES.get(x), index=[1,2,3,4,5].index(pv) if pv in [1,2,3,4,5] else 2, key=f"p_{tid}", label_visibility="collapsed")
                            if nv != pv: db_update("cronogramas", "cronogramas", tid, {"prioridade": nv}); st.rerun()
                            if c4.button("🗑️", key=f"dp_{tid}"): db_delete("cronogramas", "cronogramas", tid); st.rerun()
                    if conc:
                        st.divider()
                        with st.expander(f"✅ Histórico ({len(conc)})"):
                            for t in reversed(conc):
                                dc = t.get('data_conclusao', '')
                                dcf = datetime.strptime(str(dc), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y às %H:%M") if len(str(dc)) > 10 else formatar_data_br(dc)
                                st.markdown(f"~~[{PRIORIDADES.get(safe_int(t.get('prioridade', 3)), '')}] {t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~ *(Check: {dcf})*")

    elif menu == "⚡ Revisão HIIT":
        st.header("⚡ Revisão Intensiva (HIIT MedCof)")
        aba_dash_hiit, aba_reg_hiit, aba_cal_hiit, aba_notas_hiit, aba_fc_hiit = st.tabs(["⚡ Dashboard HIIT", "📝 Registrar Questões", "📅 Calendário", "📓 Anotações HIIT", "📚 Flashcards HIIT"])
        with aba_dash_hiit:
            st.markdown("### ⚡ Desempenho Exclusivo HIIT")
            t_acertos_h = sum(safe_int(q.get('acertos')) for q in dcache["questoes_hiit"]) + sum(safe_int(r.get('acertos')) for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída")
            t_erros_h = sum(safe_int(q.get('erros')) for q in dcache["questoes_hiit"]) + sum(safe_int(r.get('erros')) for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída")
            t_questoes_h = t_acertos_h + t_erros_h
            c1_h, c2_h, c3_h, c4_h = st.columns(4)
            c1_h.metric("Questões HIIT", t_questoes_h); c2_h.metric("🟢 Acertos", t_acertos_h); c3_h.metric("🔴 Erros", t_erros_h); c4_h.metric("🎯 Taxa HIIT", f"{(t_acertos_h / t_questoes_h * 100) if t_questoes_h > 0 else 0:.1f}%")
            st.divider(); col_gh1, col_gh2 = st.columns([1, 1.5])
            modo_g_font, modo_g_bg = st.session_state.get("graph_font", "#f8fafc"), st.session_state.get("graph_bg", "#0f172a")
            with col_gh1:
                if t_questoes_h > 0: 
                    fig_pie_h = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_h, t_erros_h], hole=0.65, color_discrete_sequence=["#10b981", '#ef4444'])
                    fig_pie_h.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color=modo_g_bg, width=3)))
                    fig_pie_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, margin=dict(t=30, b=10, l=0, r=0), showlegend=False, title_text="Precisão HIIT", title_x=0.5)
                    st.plotly_chart(fig_pie_h, use_container_width=True, config={'displayModeBar': False})
            with col_gh2:
                th_graf = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in dcache["questoes_hiit"]] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída"]
                df_rh = pd.DataFrame(th_graf).dropna(subset=['area'])
                if not df_rh.empty:
                    df_gh = df_rh.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_gh['Taxa'] = (df_gh['acertos'] / (df_gh['acertos'] + df_gh['erros'])) * 100
                    fig_bar_h = px.bar(df_gh.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS, text_auto='.1f')
                    fig_bar_h.update_traces(textposition="outside", cliponaxis=False)
                    fig_bar_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, showlegend=False, margin=dict(t=30, b=0, l=0, r=20), title_text="Desempenho por Matéria", title_x=0.5, xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_bar_h, use_container_width=True, config={'displayModeBar': False})
        with aba_reg_hiit:
            c_a, c_sub = st.columns(2)
            a = c_a.selectbox("Área", AREAS_MED, key="h_a")
            sq = c_sub.selectbox("Subespecialidade", SUB_CM, key="h_cm") if a == "Clínica Médica" else (c_sub.selectbox("Subespecialidade", SUB_CG, key="h_cg") if a == "Cirurgia Geral" else "")
            with st.form("h_f", clear_on_submit=True):
                c1, c2 = st.columns(2); s = c1.text_input("Tema"); d = c2.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2); acc, err = ac.number_input("🟢 Acertos", min_value=0), er.number_input("🔴 Erros", min_value=0)
                if st.form_submit_button("Registrar e Agendar", use_container_width=True) and s:
                    sf = f"{sq} - {s}" if sq and sq != "Geral" else s
                    db_add("questoes_hiit", "questoes_hiit", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": sf, "acertos": acc, "erros": err})
                    tq = acc + err
                    if tq > 0:
                        tx = acc / tq; cn, dp = ("🔴 HIIT Alerta (7d)", 7) if tx < 0.6 else (("🟡 HIIT Reforço (14d)", 14) if tx < 0.8 else ("🟢 HIIT Domínio (30d)", 30))
                        nd = parse_data(str(d)) + timedelta(days=dp)
                        b = db.batch(); ids_d = set()
                        for r in dcache["revisoes_hiit"]:
                            if str(r.get('status')).lower() == 'pendente' and str(r.get('tema')) == sf:
                                b.delete(db.collection("revisoes_hiit").document(r['id'])); ids_d.add(r['id'])
                        nr = {"usuario_id": u_id, "area": a, "tema": sf, "ciclo": cn, "data_agendada": str(nd), "status": "Pendente"}
                        dr = db.collection("revisoes_hiit").document(); b.set(dr, nr); b.commit()
                        dcache["revisoes_hiit"] = [r for r in dcache["revisoes_hiit"] if r['id'] not in ids_d]; nr['id'] = dr.id; dcache["revisoes_hiit"].append(nr)
                        st.toast(f"Agendado para {formatar_data_br(nd)}!", icon="⚡")
                    st.rerun()
            if dcache["questoes_hiit"]:
                l_h = [{"Data_obj": parse_data(b.get('data')), "Data": formatar_data_br(b.get('data')), "Área": b.get('area'), "Subtema": limpar_texto(b.get('subtema')), "Acertos": safe_int(b.get('acertos')), "Erros": safe_int(b.get('erros')), "% Acertos": f"{(safe_int(b.get('acertos')) / (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) * 100):.1f}%" if (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) > 0 else "0.0%", "ID": b.get('id')} for b in dcache["questoes_hiit"]]
                st.dataframe(pd.DataFrame(l_h).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj", "ID"], errors='ignore'), use_container_width=True, hide_index=True)
                with st.expander("✏️ Editar Histórico"):
                    oe_h = {f"{formatar_data_br(q.get('data'))} | {q.get('area')} - {limpar_texto(q.get('subtema'))}": q for q in dcache["questoes_hiit"]}
                    if oe_h:
                        qhs = st.selectbox("Registro:", list(oe_h.keys()))
                        qhd = oe_h[qhs]; qhi = str(qhd.get('id', '0'))
                        ce1, ce2 = st.columns(2); na = ce1.number_input("Acertos", min_value=0, value=safe_int(qhd.get('acertos'))); ne = ce2.number_input("Erros", min_value=0, value=safe_int(qhd.get('erros')))
                        cb1, cb2 = st.columns(2)
                        if cb1.button("Salvar", use_container_width=True): db_update("questoes_hiit", "questoes_hiit", qhi, {"acertos": na, "erros": ne}); st.rerun()
                        if cb2.button("Excluir", use_container_width=True): db_delete("questoes_hiit", "questoes_hiit", qhi); st.rerun()elif menu == "⚡ Revisão HIIT":
        st.header("⚡ Revisão Intensiva (HIIT MedCof)")
        aba_dash_hiit, aba_reg_hiit, aba_cal_hiit, aba_notas_hiit, aba_fc_hiit = st.tabs(["⚡ Dashboard HIIT", "📝 Registrar Questões", "📅 Calendário", "📓 Anotações HIIT", "📚 Flashcards HIIT"])
        
        with aba_dash_hiit:
            st.markdown("### ⚡ Desempenho Exclusivo HIIT")
            t_acertos_h = sum(safe_int(q.get('acertos')) for q in dcache["questoes_hiit"]) + sum(safe_int(r.get('acertos')) for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída")
            t_erros_h = sum(safe_int(q.get('erros')) for q in dcache["questoes_hiit"]) + sum(safe_int(r.get('erros')) for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída")
            t_questoes_h = t_acertos_h + t_erros_h
            c1_h, c2_h, c3_h, c4_h = st.columns(4)
            c1_h.metric("Questões HIIT", t_questoes_h); c2_h.metric("🟢 Acertos", t_acertos_h); c3_h.metric("🔴 Erros", t_erros_h); c4_h.metric("🎯 Taxa HIIT", f"{(t_acertos_h / t_questoes_h * 100) if t_questoes_h > 0 else 0:.1f}%")
            st.divider(); col_gh1, col_gh2 = st.columns([1, 1.5])
            modo_g_font, modo_g_bg = st.session_state.get("graph_font", "#f8fafc"), st.session_state.get("graph_bg", "#0f172a")
            with col_gh1:
                if t_questoes_h > 0: 
                    fig_pie_h = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_h, t_erros_h], hole=0.65, color_discrete_sequence=["#10b981", '#ef4444'])
                    fig_pie_h.update_traces(textposition='inside', textinfo='percent+label', marker=dict(line=dict(color=modo_g_bg, width=3)))
                    fig_pie_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, margin=dict(t=30, b=10, l=0, r=0), showlegend=False, title_text="Precisão HIIT", title_x=0.5)
                    st.plotly_chart(fig_pie_h, use_container_width=True, config={'displayModeBar': False})
            with col_gh2:
                th_graf = [{"area": q.get('area'), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in dcache["questoes_hiit"]] + [{"area": r.get('area'), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() == "concluída"]
                df_rh = pd.DataFrame(th_graf).dropna(subset=['area'])
                if not df_rh.empty:
                    df_gh = df_rh.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_gh['Taxa'] = (df_gh['acertos'] / (df_gh['acertos'] + df_gh['erros'])) * 100
                    fig_bar_h = px.bar(df_gh.sort_values('Taxa'), x='Taxa', y='area', orientation='h', color='area', color_discrete_map=CORES_AREAS, text_auto='.1f')
                    fig_bar_h.update_traces(textposition="outside", cliponaxis=False)
                    fig_bar_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_g_font, showlegend=False, margin=dict(t=30, b=0, l=0, r=20), title_text="Desempenho por Matéria", title_x=0.5, xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False), yaxis=dict(showgrid=False))
                    st.plotly_chart(fig_bar_h, use_container_width=True, config={'displayModeBar': False})
        
        with aba_reg_hiit:
            c_a, c_sub = st.columns(2)
            a = c_a.selectbox("Área", AREAS_MED, key="h_a")
            sq = c_sub.selectbox("Subespecialidade", SUB_CM, key="h_cm") if a == "Clínica Médica" else (c_sub.selectbox("Subespecialidade", SUB_CG, key="h_cg") if a == "Cirurgia Geral" else "")
            with st.form("h_f", clear_on_submit=True):
                c1, c2 = st.columns(2); s = c1.text_input("Tema"); d = c2.date_input("Data", hoje, format="DD/MM/YYYY")
                ac, er = st.columns(2); acc, err = ac.number_input("🟢 Acertos", min_value=0), er.number_input("🔴 Erros", min_value=0)
                if st.form_submit_button("Registrar e Agendar", use_container_width=True) and s:
                    sf = f"{sq} - {s}" if sq and sq != "Geral" else s
                    db_add("questoes_hiit", "questoes_hiit", {"usuario_id": u_id, "data": str(d), "area": a, "subtema": sf, "acertos": acc, "erros": err})
                    tq = acc + err
                    if tq > 0:
                        tx = acc / tq; cn, dp = ("🔴 HIIT Alerta (7d)", 7) if tx < 0.6 else (("🟡 HIIT Reforço (14d)", 14) if tx < 0.8 else ("🟢 HIIT Domínio (30d)", 30))
                        nd = parse_data(str(d)) + timedelta(days=dp)
                        b = db.batch(); ids_d = set()
                        for r in dcache["revisoes_hiit"]:
                            if str(r.get('status')).lower() == 'pendente' and str(r.get('tema')) == sf:
                                b.delete(db.collection("revisoes_hiit").document(r['id'])); ids_d.add(r['id'])
                        nr = {"usuario_id": u_id, "area": a, "tema": sf, "ciclo": cn, "data_agendada": str(nd), "status": "Pendente"}
                        dr = db.collection("revisoes_hiit").document(); b.set(dr, nr); b.commit()
                        dcache["revisoes_hiit"] = [r for r in dcache["revisoes_hiit"] if r['id'] not in ids_d]; nr['id'] = dr.id; dcache["revisoes_hiit"].append(nr)
                        st.toast(f"Agendado para {formatar_data_br(nd)}!", icon="⚡")
                    st.rerun()
            if dcache["questoes_hiit"]:
                l_h = [{"Data_obj": parse_data(b.get('data')), "Data": formatar_data_br(b.get('data')), "Área": b.get('area'), "Subtema": limpar_texto(b.get('subtema')), "Acertos": safe_int(b.get('acertos')), "Erros": safe_int(b.get('erros')), "% Acertos": f"{(safe_int(b.get('acertos')) / (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) * 100):.1f}%" if (safe_int(b.get('acertos')) + safe_int(b.get('erros'))) > 0 else "0.0%", "ID": b.get('id')} for b in dcache["questoes_hiit"]]
                st.dataframe(pd.DataFrame(l_h).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj", "ID"], errors='ignore'), use_container_width=True, hide_index=True)
                with st.expander("✏️ Editar Histórico"):
                    oe_h = {f"{formatar_data_br(q.get('data'))} | {q.get('area')} - {limpar_texto(q.get('subtema'))}": q for q in dcache["questoes_hiit"]}
                    if oe_h:
                        qhs = st.selectbox("Registro:", list(oe_h.keys()))
                        qhd = oe_h[qhs]; qhi = str(qhd.get('id', '0'))
                        ce1, ce2 = st.columns(2); na = ce1.number_input("Acertos", min_value=0, value=safe_int(qhd.get('acertos'))); ne = ce2.number_input("Erros", min_value=0, value=safe_int(qhd.get('erros')))
                        cb1, cb2 = st.columns(2)
                        if cb1.button("Salvar", use_container_width=True): db_update("questoes_hiit", "questoes_hiit", qhi, {"acertos": na, "erros": ne}); st.rerun()
                        if cb2.button("Excluir", use_container_width=True): db_delete("questoes_hiit", "questoes_hiit", qhi); st.rerun()
        
        with aba_cal_hiit:
            tph = [r for r in dcache["revisoes_hiit"] if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
            atr = [r for r in tph if parse_data(r.get('data_agendada')) < hoje]; hj = [r for r in tph if parse_data(r.get('data_agendada')) == hoje]; fut = sorted([r for r in tph if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
            ch1, ch2, ch3 = st.columns(3); ch1.metric("Atrasados", len(atr)); ch2.metric("Para Hoje", len(hj)); ch3.metric("Próximo", formatar_data_br(fut[0].get('data_agendada')) if fut else "Nenhum")
            if atr and st.button("🧹 Limpar Atrasados", type="primary", use_container_width=True):
                b = db.batch(); d_i = set()
                for r in atr: b.delete(db.collection("revisoes_hiit").document(r['id'])); d_i.add(r['id'])
                b.commit(); dcache["revisoes_hiit"] = [r for r in dcache["revisoes_hiit"] if r['id'] not in d_i]; st.rerun()
            st.divider(); cv, co = st.columns(2)
            vh = cv.radio("Filtro:", ["📆 Para Hoje", "🗓️ Próximos 7 Dias", "♾️ Todas Futuras"], horizontal=True)
            oh = co.radio("Ordem:", ["🚨 Urgência", "🆕 Mais Atuais", "🕰️ Mais Antigas"], horizontal=True)
            for r in tph: r['data_agendada_obj'] = parse_data(r.get('data_agendada')); r['tema'] = limpar_texto(r.get('tema', '')); r['area'] = r.get('area', 'Geral')
            if 'c_m_h' not in st.session_state: st.session_state.c_m_h = hoje.month
            if 'c_a_h' not in st.session_state: st.session_state.c_a_h = hoje.year
            n1, n2, n3 = st.columns([1,2,1])
            if n1.button("⬅️ Mês", key="ph"): st.session_state.c_m_h, st.session_state.c_a_h = (12, st.session_state.c_a_h-1) if st.session_state.c_m_h==1 else (st.session_state.c_m_h-1, st.session_state.c_a_h); st.rerun()
            with n2: st.markdown(f"<h3 style='text-align:center;'>📅 {MESES_PT[st.session_state.c_m_h]} {st.session_state.c_a_h}</h3>", unsafe_allow_html=True)
            if n3.button("Mês ➡️", key="nh"): st.session_state.c_m_h, st.session_state.c_a_h = (1, st.session_state.c_a_h+1) if st.session_state.c_m_h==12 else (st.session_state.c_m_h+1, st.session_state.c_a_h); st.rerun()
            st.markdown(gerar_calendario_revisoes_html(tph, st.session_state.c_a_h, st.session_state.c_m_h), unsafe_allow_html=True); st.divider()
            
            lph = [r for r in tph if r['data_agendada_obj'] == hoje] if vh == "📆 Para Hoje" else ([r for r in tph if hoje <= r['data_agendada_obj'] <= (hoje + timedelta(days=7))] if vh == "🗓️ Próximos 7 Dias" else [r for r in tph if r['data_agendada_obj'] >= hoje])
            lph.sort(key=lambda x: x['data_agendada_obj'], reverse=("Atuais" in oh)) if "Urgência" not in oh else lph.sort(key=lambda x: x['data_agendada_obj'])
            
            if not lph: st.success("🎉 Tudo em dia!")
            for r in lph:
                with st.container(border=True):
                    st.markdown(f"**<span style='color:{CORES_AREAS.get(r['area'], '#64748b')};'>⬤</span> {r['tema']}**", unsafe_allow_html=True); st.caption(f"Status: {r.get('ciclo','')} | Agendado: {formatar_data_br(r['data_agendada_obj'])}")
                    with st.expander("Concluir"):
                        with st.form(f"fch_{r['id']}", clear_on_submit=True):
                            ca, ce = st.columns(2); ah = ca.number_input("Acertos", 0); eh = ce.number_input("Erros", 0)
                            if st.form_submit_button("Marcar Concluída", use_container_width=True):
                                db_update("revisoes_hiit", "revisoes_hiit", r['id'], {"status": "Concluída", "data_conclusao": str(get_agora()), "acertos": ah, "erros": eh})
                                th = ah + eh
                                if th > 0:
                                    cn, dp = ("🔴 HIIT Alerta (7d)", 7) if ah/th < 0.6 else (("🟡 HIIT Reforço (14d)", 14) if ah/th < 0.8 else ("🟢 HIIT Domínio (30d)", 30))
                                    nd = parse_data(str(get_agora().date())) + timedelta(days=dp)
                                    nr = {"usuario_id": u_id, "area": r['area'], "tema": r['tema'], "ciclo": cn, "data_agendada": str(nd), "status": "Pendente"}
                                    db_add("revisoes_hiit", "revisoes_hiit", nr)
                                st.rerun()
        
        with aba_notas_hiit:
            if 'h_img_tmp' not in st.session_state: st.session_state.h_img_tmp = []
            if st.session_state.get('limpa_h_n', False): st.session_state.h_img_tmp = []; st.session_state.limpa_h_n = False; components.html("<script>Object.keys(window.parent.localStorage).forEach(k => { if(k.startsWith('autosave_nota_')) window.parent.localStorage.removeItem(k); });</script>", height=0); st.toast("✅ Salvo!", icon="📝")
            an1, an2 = st.tabs(["➕ Novo Resumo", "📖 Cadernos"])
            with an1:
                with st.container(border=True):
                    cb, ci = st.columns([1, 2])
                    with cb:
                        if paste_image_button:
                            rp = paste_image_button("📸 Colar Imagem", "#4f46e5", "#4338ca", "p_h_n")
                            if rp.image_data: 
                                ib = otimizar_imagem_para_api(rp.image_data, 1024)
                                if ib and ib not in st.session_state.h_img_tmp: st.session_state.h_img_tmp.append(ib); st.rerun()
                    with ci:
                        if st.session_state.h_img_tmp:
                            cc = st.columns(3)
                            for idx, img in enumerate(st.session_state.h_img_tmp):
                                with cc[idx % 3]:
                                    st.image(base64.b64decode(img)); 
                                    if st.button("🗑️", key=f"rm_h_{idx}"): st.session_state.h_img_tmp.pop(idx); st.rerun()
                cah, csh = st.columns(2); ah = cah.selectbox("Área", AREAS_MED, key="s_a_h")
                sh = csh.selectbox("Sub", SUB_CM, key="s_cm_h") if ah == "Clínica Médica" else (csh.selectbox("Sub", SUB_CG, key="s_cg_h") if ah == "Cirurgia Geral" else "")
                th = st.text_input("Tema", key="h_t")
                with st.container(border=True):
                    render_toolbar(); txh = st.text_area("Anotação", height=200, key="d_h_txt")
                if st.button("💾 Salvar", type="primary", use_container_width=True) and th and txh:
                    db_add("anotacoes_hiit", "anotacoes_hiit", {"usuario_id": u_id, "area": ah, "subtema": f"{sh} - {th}" if sh and sh != "Geral" else th, "pontos_chave": txh, "imagens_b64": st.session_state.h_img_tmp, "data_criacao": str(hoje)})
                    st.session_state.limpa_h_n = True; st.rerun()
            with an2:
                nh = dcache["anotacoes_hiit"]
                if not nh: st.info("Nenhum resumo.")
                else:
                    pq = st.text_input("🔍 Buscar...").lower()
                    nhe = [n for n in nh if pq in str(n.get('subtema','')).lower() or pq in str(n.get('pontos_chave','')).lower()] if pq else list(nh)
                    nhe.sort(key=lambda x: parse_data(x.get('data_criacao')), reverse=True)
                    bp = sorted(list(set([n.get('area', 'Clínica Médica') for n in nhe])))
                    if not nhe: st.warning("Nada encontrado.")
                    else:
                        ab = st.tabs(bp)
                        for i, b in enumerate(bp):
                            with ab[i]:
                                for n in [x for x in nhe if x.get('area') == b]:
                                    idn = str(n.get('id', '0'))
                                    with st.expander(f"📝 {limpar_texto(n.get('subtema'))} - {formatar_data_br(n.get('data_criacao'))}"):
                                        cd1, cd2 = st.columns([0.85, 0.15])
                                        if cd2.button("🗑️", key=f"del_hn_{idn}"): db_delete("anotacoes_hiit", "anotacoes_hiit", idn); st.rerun()
                                        st.markdown(f"<div style='border-left: 3px solid #4f46e5; padding-left: 15px; margin-top: 10px; margin-bottom: 20px;'>\n\n{n.get('pontos_chave', '')}\n\n</div>", unsafe_allow_html=True)
                                        ie = list(n.get('imagens_b64', []))
                                        if ie:
                                            cv = st.columns(max(1, min(len(ie), 4)))
                                            for ix, im in enumerate(ie):
                                                with cv[ix % 4]: st.image(base64.b64decode(im))
                                        st.divider()
                                        with st.container(border=True):
                                            ci1, ci2 = st.columns(2)
                                            if ci1.button("🪄 Extrair Flashcards", key=f"fc_ia_{idn}", use_container_width=True):
                                                cli = get_ia_client()
                                                if cli:
                                                    with st.spinner("Gerando..."):
                                                        res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": f"Transforme a anotação em flashcards. Retorne JSON: {{\"flashcards\": [{{\"frente\": \"...\", \"verso\": \"...\"}}]}} Resumo: {n.get('pontos_chave','')}"}], max_tokens=2000)
                                                        fcs = extrair_json_seguro(res.choices[0].message.content).get("flashcards", [])
                                                        if fcs:
                                                            ba = db.batch()
                                                            for fc in fcs:
                                                                dr = db.collection("flashcards_hiit").document()
                                                                nf = {"usuario_id": u_id, "area": n.get('area'), "tema": limpar_texto(n.get('subtema')), "frente": fc.get('frente'), "verso": fc.get('verso'), "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                                                                ba.set(dr, nf); nf["id"] = dr.id; dcache["flashcards_hiit"].append(nf)
                                                            ba.commit(); st.success(f"✅ {len(fcs)} Cards gerados!")
                                            if ci2.button("🔥 Criar Bateria", key=f"q_ia_{idn}", use_container_width=True):
                                                cli = get_ia_client()
                                                if cli:
                                                    with st.spinner("Construindo..."):
                                                        res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": f"Crie 3 questões de caso clínico baseadas no resumo com alternativas e gabarito comentado.\nResumo: {n.get('pontos_chave','')}"}], temperature=0.4, max_tokens=3000)
                                                        st.session_state[f"qg_{idn}"] = res.choices[0].message.content
                                            if st.session_state.get(f"qg_{idn}"): st.markdown(st.session_state[f"qg_{idn}"])
                                        st.divider()
                                        if st.session_state.get('nhe_e') != idn:
                                            if st.button("✏️ Editar", key=f"be_{idn}"): st.session_state.nhe_e = idn; st.rerun()
                                        else:
                                            if st.button("❌ Cancelar", key=f"bc_{idn}"): st.session_state.nhe_e = None; st.rerun()
                                            ceb, cei = st.columns([1, 2])
                                            with ceb:
                                                if paste_image_button:
                                                    rp = paste_image_button("📸 Adicionar", "#4f46e5", "#4338ca", f"pe_{idn}")
                                                    if rp.image_data:
                                                        ib = otimizar_imagem_para_api(rp.image_data, 1024)
                                                        if ib and ib not in ie: ie.append(ib); db_update("anotacoes_hiit", "anotacoes_hiit", idn, {"imagens_b64": ie}); st.rerun()
                                            with cei:
                                                if ie:
                                                    cle = st.columns(max(1, min(len(ie), 3)))
                                                    for ix, im in enumerate(ie):
                                                        with cle[ix % 3]:
                                                            st.image(base64.b64decode(im))
                                                            if st.button("🗑️", key=f"rme_{idn}_{ix}"): ie.pop(ix); db_update("anotacoes_hiit", "anotacoes_hiit", idn, {"imagens_b64": ie}); st.rerun()
                                            cea, ces = st.columns(2)
                                            eda = cea.selectbox("Área", AREAS_MED, index=AREAS_MED.index(n.get('area')) if n.get('area') in AREAS_MED else 0, key=f"ea_{idn}")
                                            eds = ces.selectbox("Sub", SUB_CM, key=f"es_cm_{idn}") if eda == "Clínica Médica" else (ces.selectbox("Sub", SUB_CG, key=f"es_cg_{idn}") if eda == "Cirurgia Geral" else "")
                                            sp = n.get('subtema', '')
                                            if " - " in sp and sp.split(" - ")[0] in SUB_CM + SUB_CG: sp = " - ".join(sp.split(" - ")[1:])
                                            with st.form(f"fe_{idn}", clear_on_submit=False):
                                                ed_s = st.text_input("Subtema", value=sp)
                                                with st.container(border=True):
                                                    render_toolbar(); ed_p = st.text_area("Anotação", value=n.get('pontos_chave', ''), height=200)
                                                if st.form_submit_button("Salvar Alterações", use_container_width=True) and ed_s and ed_p:
                                                    db_update("anotacoes_hiit", "anotacoes_hiit", idn, {"area": eda, "subtema": f"{eds} - {ed_s}" if eds and eds != "Geral" else ed_s, "pontos_chave": ed_p})
                                                    st.session_state.nhe_e = None; st.rerun()
        
        with aba_fc_hiit:
            st.markdown("### 📚 Modo Estudo - Flashcards HIIT")
            cvs = [d for d in dcache["flashcards_hiit"] if parse_data(d.get('data_prox_revisao')) <= hoje]
            if not cvs: st.success("🎉 Deck zerado!")
            else:
                do = {}
                for c in cvs:
                    a, t = c.get('area', 'Geral'), limpar_texto(c.get('tema', 'Sem Tema'))
                    do.setdefault(a, {}).setdefault(t, []).append(c)
                aps = sorted(list(do.keys()))
                abas = st.tabs(aps)
                for ix, aa in enumerate(aps):
                    with abas[ix]:
                        st.markdown(f"#### <span style='color:{CORES_AREAS.get(aa, '#64748b')};'>⬤</span> Cartões de {aa}", unsafe_allow_html=True)
                        ta = sorted(list(do[aa].keys()))[0]; cd = do[aa][ta][0]; cdi = str(cd.get("id", "0"))
                        st.caption(f"**Progresso na Área:** Restam {sum(len(do[aa][t]) for t in do[aa])} cartões hoje.")
                        with st.container(border=True):
                            st.markdown(f"**Tema:** {ta}"); st.markdown(f"### ❔ {cd.get('frente', '')}")
                            ka = f"ah_{cdi}"
                            if ka not in st.session_state: st.session_state[ka] = False
                            if st.button("Revelar Resposta", key=f"rr_{cdi}"): st.session_state[ka] = True; st.rerun()
                            if st.session_state[ka]:
                                st.info(f"**💡 Resposta:** {cd.get('verso', '')}")
                                b1, b2, b3 = st.columns(3)
                                def ah(p, i=cdi, d=cd, k=ka): 
                                    f, iv = float(d.get('facilidade', 2.5)), safe_int(d.get('intervalo'))
                                    if p=='e': ni, nf = 1, max(1.3, f - 0.2)
                                    elif p=='b': ni, nf = max(1, int((iv or 1) * f)), f
                                    else: ni, nf = max(1, int((iv or 1) * f * 1.3)), f + 0.15
                                    db_update("flashcards_hiit", "flashcards_hiit", i, {"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))}); st.session_state[k] = False
                                if b1.button("🔴 Errei", use_container_width=True, key=f"e_{cdi}"): ah('e'); st.rerun()
                                if b2.button("🟡 Bom", use_container_width=True, key=f"b_{cdi}"): ah('b'); st.rerun()
                                if b3.button("🟢 Fácil", use_container_width=True, key=f"f_{cdi}"): ah('f'); st.rerun()
                with st.expander("Gerenciar"):
                    if dcache["flashcards_hiit"]:
                        st.dataframe(pd.DataFrame(dcache["flashcards_hiit"])[['area', 'tema', 'frente', 'data_prox_revisao']], use_container_width=True, hide_index=True)
                        dfc = st.selectbox("Excluir:", [f"{f.get('id')} | {f.get('frente')[:30]}..." for f in dcache["flashcards_hiit"]])
                        if st.button("🗑️ Excluir Flashcard"): db_delete("flashcards_hiit", "flashcards_hiit", dfc.split(" | ")[0]); st.rerun()

    elif menu == "📝 Anotações Rápidas":
        st.header("Cadernos de Resumos")
        if 'ntmp' not in st.session_state: st.session_state.ntmp = []
        if st.session_state.get('limpa_n', False): st.session_state.ntmp = []; st.session_state.limpa_n = False; components.html("<script>Object.keys(window.parent.localStorage).forEach(k => { if(k.startsWith('autosave_nota_')) window.parent.localStorage.removeItem(k); });</script>", height=0); st.toast("✅ Salvo!", icon="📝")
        a1, a2 = st.tabs(["➕ Nova", "📖 Resumos"])
        with a1:
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if paste_image_button:
                        rp = paste_image_button("📸 Colar", "#4f46e5", "#4338ca", "pn")
                        if rp.image_data: st.session_state.ntmp.append(otimizar_imagem_para_api(rp.image_data, 1024)); st.rerun()
                with c2:
                    if st.session_state.ntmp:
                        cc = st.columns(3)
                        for i, img in enumerate(st.session_state.ntmp):
                            with cc[i%3]:
                                st.image(base64.b64decode(img)); 
                                if st.button("Remover", key=f"rn_{i}"): st.session_state.ntmp.pop(i); st.rerun()
            ca, cs = st.columns(2); ar = ca.selectbox("Área", AREAS_MED, key="na"); tm = st.text_input("Tema", key="ntm")
            with st.container(border=True):
                render_toolbar(); txt = st.text_area("Texto", height=200, key="ntxt")
            if st.button("💾 Salvar", type="primary", use_container_width=True) and tm and txt:
                db_add("anotacoes", "anotacoes", {"usuario_id":u_id, "area":ar, "subtema":tm, "pontos_chave":txt, "imagens_b64":st.session_state.ntmp, "data_criacao":str(hoje)})
                st.session_state.limpa_n = True; st.rerun()
        with a2:
            for n in sorted(dcache["anotacoes"], key=lambda x: parse_data(x.get('data_criacao')), reverse=True):
                with st.expander(f"📝 {n.get('subtema')} - {formatar_data_br(n.get('data_criacao'))}"):
                    st.markdown(n.get('pontos_chave'))
                    for img in n.get('imagens_b64',[]): st.image(base64.b64decode(img))
                    if st.button("Excluir", key=f"dn_{n['id']}"): db_delete("anotacoes", "anotacoes", n['id']); st.rerun()

    elif menu == "🎯 Questões":
        st.header("Sessões & Erros")
        a1, a2, a3 = st.tabs(["Registrar", "Histórico", "Alvos"])
        with a1:
            with st.form("qf", clear_on_submit=True):
                ca, cs = st.columns(2); ar = ca.selectbox("Área", AREAS_MED); sub = cs.selectbox("Sub", SUB_CM) if ar == "Clínica Médica" else (cs.selectbox("Sub", SUB_CG) if ar == "Cirurgia Geral" else "")
                tm = st.text_input("Tema"); dt = st.date_input("Data", hoje); c1, c2 = st.columns(2); ac = c1.number_input("Acertos", 0); er = c2.number_input("Erros", 0); cc = st.text_input("Conceito Chave (Erro)")
                if st.form_submit_button("Salvar") and tm:
                    tf = f"{sub} - {tm}" if sub and sub != "Geral" else tm
                    db_add("questoes_sessoes", "questoes", {"usuario_id":u_id, "data":str(dt), "area":ar, "subtema":tf, "acertos":ac, "erros":er, "conceito_chave":cc})
                    tq = ac+er
                    if tq>0:
                        tx = ac/tq; cn, dp = ("🔴 Crítico (1d)", 1) if tx<0.6 else (("🟡 Reforço (7d)", 7) if tx<0.8 else ("🟢 Domínio (15d)", 15))
                        nd = parse_data(str(dt)) + timedelta(days=dp)
                        b = db.batch(); dids = set()
                        for r in dcache["revisoes"]:
                            if str(r.get('status')).lower() == 'pendente' and str(r.get('tema')) == tf: b.delete(db.collection("revisoes").document(r['id'])); dids.add(r['id'])
                        nr = {"usuario_id":u_id, "area":ar, "tema":tf, "ciclo":cn, "data_agendada":str(nd), "status":"Pendente"}
                        dr = db.collection("revisoes").document(); b.set(dr, nr); b.commit()
                        dcache["revisoes"] = [r for r in dcache["revisoes"] if r['id'] not in dids]; nr['id'] = dr.id; dcache["revisoes"].append(nr)
                    st.rerun()
        with a2:
            if dcache["questoes"]: st.dataframe(pd.DataFrame(dcache["questoes"])[['data','area','subtema','acertos','erros','conceito_chave']], hide_index=True, use_container_width=True)
        with a3:
            hd = {}
            for q in sorted(dcache["questoes"], key=lambda x: parse_data(x.get('data')), reverse=True):
                ts = f"{q.get('area')} - {limpar_texto(q.get('subtema'))}"
                hd.setdefault(ts, [])
                if len(hd[ts]) < 3: hd[ts].append({"ac": safe_int(q.get('acertos')), "er": safe_int(q.get('erros'))})
            acrit = []
            for ts, ss in hd.items():
                tac = sum(s['ac'] for s in ss); ter = sum(s['er'] for s in ss); ttot = tac + ter
                if ttot > 0 and tac/ttot < 0.6: acrit.append({"Tema": ts, "Média": tac/ttot, "Total": ttot})
            if not acrit: st.success("Nenhum Alvo Crítico!")
            else:
                acrit.sort(key=lambda x: x['Média'])
                st.dataframe(pd.DataFrame([{"Tema": a["Tema"], "Desempenho": f"{a['Média']*100:.1f}%", "Base": a["Total"]} for a in acrit]), use_container_width=True, hide_index=True)
                if st.button("🔥 Simulado de Recuperação"):
                    cli = get_ia_client()
                    if cli:
                        with st.spinner("Gerando..."):
                            try:
                                res = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": f"Crie um mini-simulado rigoroso para: {', '.join([a['Tema'] for a in acrit[:3]])}. Com alternativas e gabarito comentado."}], max_tokens=3000)
                                with st.container(border=True): st.markdown(res.choices[0].message.content)
                            except Exception as e: st.error(str(e))

    elif menu == "📅 Agenda de Revisões":
        st.header("Agenda SRS")
        p = [r for r in dcache["revisoes"] if r.get('status')=='Pendente']
        for r in p:
            r['data_agendada_obj'] = parse_data(r.get('data_agendada')); r['tema'] = r.get('tema') or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('tema', ''); r['area'] = r.get('area') or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('area', 'Geral')
        if 'cmr' not in st.session_state: st.session_state.cmr = hoje.month
        if 'car' not in st.session_state: st.session_state.car = hoje.year
        n1, n2, n3 = st.columns([1,2,1])
        if n1.button("⬅️ Mês", key="pr"): st.session_state.cmr, st.session_state.car = (12, st.session_state.car-1) if st.session_state.cmr==1 else (st.session_state.cmr-1, st.session_state.car); st.rerun()
        with n2: st.markdown(f"<h3 style='text-align:center;'>📅 {MESES_PT[st.session_state.cmr]} {st.session_state.car}</h3>", unsafe_allow_html=True)
        if n3.button("Mês ➡️", key="nr"): st.session_state.cmr, st.session_state.car = (1, st.session_state.car+1) if st.session_state.cmr==12 else (st.session_state.cmr+1, st.session_state.car); st.rerun()
        st.markdown(gerar_calendario_revisoes_html(p, st.session_state.car, st.session_state.cmr), unsafe_allow_html=True)
        cv, co = st.columns(2); vr = cv.radio("Filtro:", ["📆 Hoje", "🗓️ 7 Dias", "♾️ Futuras"], horizontal=True); orr = co.radio("Ordem:", ["🚨 Urgência", "🆕 Atuais", "🕰️ Antigas"], horizontal=True)
        lp = [r for r in p if r['data_agendada_obj'] == hoje] if vr == "📆 Hoje" else ([r for r in p if hoje <= r['data_agendada_obj'] <= (hoje + timedelta(days=7))] if vr == "🗓️ 7 Dias" else [r for r in p if r['data_agendada_obj'] >= hoje])
        lp.sort(key=lambda x: x['data_agendada_obj'], reverse=("Atuais" in orr)) if "Urgência" not in orr else lp.sort(key=lambda x: x['data_agendada_obj'])
        if not lp: st.success("Tudo em dia!")
        for r in lp:
            with st.container(border=True):
                st.markdown(f"**{r['tema']}** ({r.get('ciclo','')})")
                with st.expander("Concluir"):
                    with st.form(f"fr_{r['id']}", clear_on_submit=True):
                        c1, c2 = st.columns(2); a = c1.number_input("Acertos", 0); e = c2.number_input("Erros", 0)
                        if st.form_submit_button("Salvar"): db_update("revisoes", "revisoes", r['id'], {"status":"Concluída", "acertos":a, "erros":e, "data_conclusao":str(get_agora())}); st.rerun()

    elif menu == "✨ AI Tutor & Flashcards":
        st.header("IA & Cards")
        a1, a2, a3 = st.tabs(["Flashcards", "Tutor", "Feynman"])
        with a1:
            venc = [c for c in dcache["flashcards"] if parse_data(c.get('data_prox_revisao')) <= hoje]
            if not venc: st.success("Deck zerado!")
            else:
                c = venc[0]; cid = c['id']
                with st.container(border=True):
                    st.markdown(f"**{c.get('frente')}**")
                    if st.button("Revelar", key=f"r_{cid}"): st.session_state[f"a_{cid}"] = True; st.rerun()
                    if st.session_state.get(f"a_{cid}"):
                        st.info(c.get('verso')); c1, c2, c3 = st.columns(3)
                        def av(p):
                            f, i = float(c.get('facilidade',2.5)), safe_int(c.get('intervalo',0))
                            if p=='e': ni, nf = 1, max(1.3, f-0.2)
                            elif p=='b': ni, nf = max(1, int(max(1,i)*f)), f
                            else: ni, nf = max(1, int(max(1,i)*f*1.3)), f+0.15
                            db_update("flashcards", "flashcards", cid, {"intervalo":ni, "facilidade":nf, "data_prox_revisao":str(get_agora().date()+timedelta(days=ni))}); st.session_state[f"a_{cid}"] = False
                        if c1.button("Errei", key="e"): av('e'); st.rerun()
                        if c2.button("Bom", key="b"): av('b'); st.rerun()
                        if c3.button("Fácil", key="f"): av('f'); st.rerun()
        with a2:
            if 'chat' not in st.session_state: st.session_state.chat = []
            for m in st.session_state.chat: st.chat_message(m["role"]).write(m["content"])
            if u := st.chat_input("Dúvida?"):
                st.session_state.chat.append({"role":"user","content":u})
                cli = get_ia_client()
                if cli:
                    try:
                        r = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role":"system","content":"Tutor médico."}]+st.session_state.chat, max_tokens=1000)
                        st.session_state.chat.append({"role":"assistant","content":r.choices[0].message.content})
                    except Exception as e: st.error(str(e))
                    st.rerun()
        with a3:
            cli = get_ia_client()
            if cli:
                tmf = st.text_input("Tema:")
                aud = st.audio_input("Gravar")
                if tmf and aud:
                    with st.spinner("Avaliando..."):
                        try:
                            tr = cli.audio.transcriptions.create(file=("a.wav", aud.getvalue()), model="whisper-large-v3")
                            r = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role":"system","content":"Avalie rigidamente."}, {"role":"user","content":f"Avalie: '{tmf}'. Transcrição: '{tr.text}'."}], max_tokens=2500)
                            st.success(r.choices[0].message.content)
                        except Exception as e: st.error(str(e))

    elif menu == "📚 Registro de Aulas":
        with st.form("fa"):
            a = st.selectbox("Área", AREAS_MED); t = st.text_input("Tema"); d = st.date_input("Data", hoje)
            if st.form_submit_button("Salvar") and t: db_add("aulas", "aulas", {"usuario_id":u_id, "area":a, "tema":t, "data_aula":str(d)}); st.rerun()
        if 'cma' not in st.session_state: st.session_state.cma = hoje.month
        if 'caa' not in st.session_state: st.session_state.caa = hoje.year
        n1, n2, n3 = st.columns([1,2,1])
        if n1.button("⬅️ Mês", key="pa"): st.session_state.cma, st.session_state.caa = (12, st.session_state.caa-1) if st.session_state.cma==1 else (st.session_state.cma-1, st.session_state.caa); st.rerun()
        with n2: st.markdown(f"<h3 style='text-align:center;'>📅 {MESES_PT[st.session_state.cma]} {st.session_state.caa}</h3>", unsafe_allow_html=True)
        if n3.button("Mês ➡️", key="na"): st.session_state.cma, st.session_state.caa = (1, st.session_state.caa+1) if st.session_state.cma==12 else (st.session_state.cma+1, st.session_state.caa); st.rerun()
        st.markdown(gerar_calendario_html(dcache["aulas"], st.session_state.caa, st.session_state.cma), unsafe_allow_html=True)
        if dcache["aulas"]: st.dataframe(pd.DataFrame(dcache["aulas"])[['data_aula','area','tema']], hide_index=True, use_container_width=True)

    elif menu == "🏥 Simulados & OSCE":
        a1, a2 = st.tabs(["OSCE", "Simulados Salvos"])
        with a1:
            cli = get_ia_client()
            if cli:
                d = st.text_input("Doença (Ex: Infarto)")
                if st.button("Iniciar"): st.session_state.oh = []; st.session_state.oa = True; st.session_state.op = f"Paciente OSCE. Fale sintomas. Se pedir exame [{','.join(BANCO_IMAGENS_OSCE.keys())}], use [EXAME: nome]. Doença: {d}."; st.rerun()
                if st.session_state.get("oa"):
                    for m in st.session_state.oh: 
                        with st.chat_message(m["role"]): 
                            if m["role"]=="assistant": renderizar_mensagem_osce(m["content"])
                            else: st.write(m["content"])
                    if i := st.chat_input("Fale..."):
                        st.session_state.oh.append({"role":"user","content":i})
                        try:
                            r = chamar_ia(cli, modelo=MODELO_TEXTO, messages=[{"role":"system","content":st.session_state.op}]+st.session_state.oh, max_tokens=1000)
                            st.session_state.oh.append({"role":"assistant","content":r.choices[0].message.content})
                        except Exception as e: st.error(str(e))
                        st.rerun()
        with a2:
            if dcache["simulados"]: st.dataframe(pd.DataFrame(dcache["simulados"])[['data_realizacao','instituicao','minha_nota']], hide_index=True)

    elif menu == "📁 Materiais e Simulados":
        arq = st.file_uploader("Upload PDF", type=['pdf'])
        if arq and st.button("Salvar"):
            p = os.path.join("materiais_estudo", arq.name); open(p,"wb").write(arq.getbuffer())
            db_add("materiais", "materiais", {"usuario_id":u_id, "titulo":arq.name, "path":p, "data_upload":str(hoje)}); st.rerun()
        if dcache["materiais"]: st.dataframe(pd.DataFrame(dcache["materiais"])[['data_upload','titulo']], hide_index=True, use_container_width=True)

    elif menu == "📍 GPS da Aprovação":
        ns = [float(s.get('minha_nota',0)) for s in dcache["simulados"]]
        st.metric("Média Geral Simulados", f"{sum(ns)/len(ns):.1f}%" if ns else "0%")

    elif menu == "⏱️ Modo Foco":
        st.header("Pomodoro")
        if 'fc_i' not in st.session_state: st.session_state.fc_i = False
        if not st.session_state.fc_i:
            if st.button("Iniciar 25 min", use_container_width=True): st.session_state.fc_i, st.session_state.fc_f = True, get_agora()+timedelta(minutes=25); st.rerun()
        else:
            ts = int((st.session_state.fc_f - get_agora()).total_seconds())
            if ts>0: components.html(f"<h1 style='text-align:center;color:#4f46e5;'>Foco Ativo: {ts//60}:{ts%60:02d}</h1>", height=100)
            else:
                st.success("Fim!"); 
                if st.button("Gravar"): db_add("focus_sessoes", "focus", {"usuario_id":u_id, "data_sessao":str(hoje), "minutos_foco":25}); st.session_state.fc_i=False; st.rerun()
            if st.button("Cancelar"): st.session_state.fc_i=False; st.rerun()

    elif menu == "⚙️ Configurações":
        st.header("Perfil")
        uf = st.file_uploader("Foto", type=['jpg','png'])
        if uf and st.button("Salvar"): db.collection("usuarios").document(u_id).update({"foto_perfil_b64": base64.b64encode(uf.read()).decode("utf-8")}); st.rerun()
        with st.form("t_f"):
            mo = st.radio("Tema", ["Escuro", "Claro"], index=0 if us.get("tema_modo")=="Escuro" else 1)
            if st.form_submit_button("Aplicar"): db.collection("usuarios").document(u_id).update({"tema_modo": mo}); st.session_state.user_settings["tema_modo"]=mo; st.rerun()

    elif menu == "📱 Instalar App":
        st.header("Transforme o sistema em um Aplicativo Nativo")
        col1, col2 = st.columns(2)
        with col1: 
            with st.container(border=True): st.subheader("🤖 Android"); st.markdown("1. Toque nos **3 pontinhos**.\n2. **Adicionar à tela inicial**.")
        with col2: 
            with st.container(border=True): st.subheader("🍎 iPhone"); st.markdown("1. Botão **Compartilhar**.\n2. **Adicionar à Tela de Início**.")

    elif is_super_admin(st.session_state.user_nome) and menu == "👑 Admin":
        st.dataframe(pd.DataFrame([{"ID":u.id, "Nome":u.to_dict().get('nome')} for u in db.collection("usuarios").get()]), hide_index=True, use_container_width=True)
