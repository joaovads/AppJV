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
st.set_page_config(page_title="Residência PRO 2.9", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# Modelos atuais da Groq (2026-08)
# Texto: substitui llama-3.1-8b-instant, desligado em 16/08/2026.
# Visão: substitui llama-3.2-11b-vision-preview, desligado em 14/04/2025.
MODELO_TEXTO = "qwen/qwen3.6-27b"
MODELO_VISAO = "qwen/qwen3.6-27b"

# Fallbacks para evitar que uma descontinuação/restrição de modelo derrube a função inteira.
MODELOS_TEXTO_FALLBACK = [
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
]
# Ambos são multimodais; não use um modelo somente-texto como fallback de visão.
MODELOS_VISAO_FALLBACK = [
    "qwen/qwen3.6-27b",
]


def ativar_pwa():
    pwa_html = """
    <script>
        if (!document.getElementById('pwa-manifest')) {
            const manifest = {
                "name": "Residência PRO",
                "short_name": "Residência",
                "theme_color": "#247c75",
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
# DESIGN PREMIUM 2.9 — CAMADA VISUAL NÃO INTRUSIVA
# ==========================================
def aplicar_ui_premium(modo):
    """Residência PRO 2.9 — linguagem visual de produto profissional.
    Camada exclusivamente visual: não altera banco, chaves ou regras de negócio.
    """
    dark = modo == "Escuro"
    if dark:
        bg, surface, surface2, border, border2 = "#0f1115", "#15181d", "#1a1e24", "#292e36", "#22272e"
        text, muted, accent, accent_soft = "#f2f4f5", "#9aa3ad", "#3fa7a0", "rgba(63,167,160,.11)"
        input_bg, hover = "#12151a", "#1d2229"
    else:
        bg, surface, surface2, border, border2 = "#f6f7f5", "#ffffff", "#fbfcfb", "#d9dedb", "#e8ece9"
        text, muted, accent, accent_soft = "#17201d", "#68736e", "#247c75", "rgba(36,124,117,.08)"
        input_bg, hover = "#ffffff", "#f0f3f1"

    css=f"""
    <style>
    :root{{--rp-bg:{bg};--rp-surface:{surface};--rp-surface2:{surface2};--rp-border:{border};--rp-border2:{border2};--rp-text:{text};--rp-muted:{muted};--rp-accent:{accent};--rp-accent-soft:{accent_soft};--rp-input:{input_bg};--rp-hover:{hover};}}

    /* ===== FUNDAMENTO ===== */
    html,body {{ color-scheme:{"dark" if dark else "light"} !important; }}
    html,body,[data-testid="stAppViewContainer"],.stApp,.main {{ background:{bg} !important; color:{text} !important; }}
    [data-testid="stHeader"] {{ background:transparent !important; }}
    .main .block-container {{ max-width:1280px; padding:1.15rem 2rem 3.5rem; }}
    .main .block-container > div {{ gap:.55rem; }}
    *,*::before,*::after {{ box-sizing:border-box; }}
    h1,h2,h3,h4,h5,h6 {{ font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif !important; color:{text} !important; letter-spacing:-.018em !important; }}
    h1 {{ font-size:1.75rem !important; font-weight:720 !important; margin:.15rem 0 .15rem !important; }}
    h2 {{ font-size:1.28rem !important; font-weight:700 !important; }}
    h3 {{ font-size:1.02rem !important; font-weight:680 !important; }}
    p,li,label,.stMarkdown {{ color:{text} !important; }}
    [data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {{ color:{muted} !important; }}
    hr {{ border-color:{border2} !important; margin:.75rem 0 !important; }}

    /* ===== SIDEBAR ===== */
    [data-testid="stSidebar"] {{ background:{surface} !important; border-right:1px solid {border} !important; }}
    [data-testid="stSidebar"] > div:first-child {{ padding:.55rem .45rem 1rem !important; }}
    .rp-brand {{ padding:7px 10px 14px !important; margin:0 4px 10px !important; border-bottom:1px solid {border2}; }}
    .rp-brand-title {{ color:{text} !important; font-size:1rem !important; font-weight:760 !important; letter-spacing:.015em !important; }}
    .rp-brand-sub {{ color:{muted} !important; font-size:.61rem !important; margin-top:4px !important; letter-spacing:.09em !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] {{ gap:2px !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] > label {{
        margin:0 3px !important; padding:7px 9px !important; min-height:35px !important;
        border:1px solid transparent !important; border-radius:6px !important; transition:background .12s,border-color .12s !important;
    }}
    [data-testid="stSidebar"] [role="radiogroup"] > label:hover {{ background:{hover} !important; border-color:{border2} !important; transform:none !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label p {{ color:{muted} !important; font-size:13px !important; font-weight:570 !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {{ background:{accent_soft} !important; border-color:rgba(36,124,117,.18) !important; box-shadow:inset 2px 0 0 {accent} !important; }}
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p {{ color:{accent} !important; font-weight:700 !important; }}
    [data-testid="stSidebar"] hr {{ margin:9px 8px !important; border-color:{border2} !important; }}
    [data-testid="stSidebar"] .stButton > button {{ min-height:34px !important; font-size:.78rem !important; padding:0 9px !important; }}
    .profile-img {{ width:62px !important; height:62px !important; border-radius:8px !important; border:1px solid {border} !important; box-shadow:none !important; }}

    /* ===== MODO CLARO — CONTROLO EXPLÍCITO DOS COMPONENTES NATIVOS ===== */
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stTextArea"] textarea {{
        background-color:{input_bg} !important;
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
        caret-color:{accent} !important;
        opacity:1 !important;
    }}
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stTimeInput"] [data-baseweb="input"],
    [data-testid="stTextArea"] [data-baseweb="textarea"] {{
        background-color:{input_bg} !important;
        color:{text} !important;
    }}
    [data-testid="stTextInput"] [data-baseweb="input"] > div,
    [data-testid="stNumberInput"] [data-baseweb="input"] > div,
    [data-testid="stDateInput"] [data-baseweb="input"] > div,
    [data-testid="stTimeInput"] [data-baseweb="input"] > div,
    [data-testid="stTextArea"] [data-baseweb="textarea"] > div {{
        background-color:{input_bg} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stSelectSlider"] [data-baseweb="select"] > div {{
        background-color:{input_bg} !important;
        color:{text} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] span,
    [data-testid="stMultiSelect"] [data-baseweb="select"] span,
    [data-testid="stSelectSlider"] [data-baseweb="select"] span {{
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
    }}
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [role="listbox"],
    [role="listbox"] > div {{
        background-color:{surface} !important;
        color:{text} !important;
    }}
    [role="option"], [role="option"] * {{
        background-color:transparent !important;
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
    }}
    [role="option"]:hover, [role="option"][aria-selected="true"] {{
        background-color:{hover} !important;
    }}
    [data-testid="stNumberInput"] button {{
        background-color:{surface2} !important;
        color:{text} !important;
        border-color:{border} !important;
    }}
    [data-testid="stNumberInput"] button svg {{
        fill:{text} !important;
    }}
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploadDropzone"] {{
        background-color:{surface} !important;
        color:{text} !important;
        border-color:{border} !important;
    }}
    [data-testid="stFileUploader"] section *,
    [data-testid="stFileUploadDropzone"] * {{
        color:{text} !important;
    }}
    [data-testid="stRadio"] label,
    [data-testid="stCheckbox"] label,
    [data-testid="stToggle"] label {{
        color:{text} !important;
    }}
    [data-testid="stRadio"] label p,
    [data-testid="stCheckbox"] label p,
    [data-testid="stToggle"] label p {{
        color:{text} !important;
    }}
    /* Remove qualquer fundo escuro residual em wrappers de formulário */
    [data-testid="stForm"],
    [data-testid="stForm"] > div,
    [data-testid="stVerticalBlockBorderWrapper"] {{
        color:{text} !important;
    }}

    /* ===== THEME SHIELD — COMPONENTES BASEWEB / STREAMLIT ===== */
    /* O tema do aplicativo nunca deve vazar para os campos nativos. */
    [data-testid="stTextInput"] [data-baseweb="input"],
    [data-testid="stTextInput"] [data-baseweb="input"] > div,
    [data-testid="stTextInput"] [data-baseweb="input"] > div > div,
    [data-testid="stNumberInput"] [data-baseweb="input"],
    [data-testid="stNumberInput"] [data-baseweb="input"] > div,
    [data-testid="stNumberInput"] [data-baseweb="input"] > div > div,
    [data-testid="stDateInput"] [data-baseweb="input"],
    [data-testid="stDateInput"] [data-baseweb="input"] > div,
    [data-testid="stDateInput"] [data-baseweb="input"] > div > div,
    [data-testid="stTimeInput"] [data-baseweb="input"],
    [data-testid="stTimeInput"] [data-baseweb="input"] > div,
    [data-testid="stTimeInput"] [data-baseweb="input"] > div > div,
    [data-testid="stTextArea"] [data-baseweb="textarea"],
    [data-testid="stTextArea"] [data-baseweb="textarea"] > div,
    [data-testid="stTextArea"] [data-baseweb="textarea"] > div > div,
    [data-testid="stSelectbox"] [data-baseweb="select"],
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] > div > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"],
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] > div > div,
    [data-testid="stSelectSlider"] [data-baseweb="select"],
    [data-testid="stSelectSlider"] [data-baseweb="select"] > div,
    [data-testid="stSelectSlider"] [data-baseweb="select"] > div > div {{
        background-color:{input_bg} !important;
        background:{input_bg} !important;
        color:{text} !important;
        border-color:{border} !important;
        box-shadow:none !important;
        opacity:1 !important;
    }}
    [data-testid="stTextInput"] input,
    [data-testid="stNumberInput"] input,
    [data-testid="stDateInput"] input,
    [data-testid="stTimeInput"] input,
    [data-testid="stTextArea"] textarea {{
        background-color:{input_bg} !important;
        background:{input_bg} !important;
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
        opacity:1 !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] span,
    [data-testid="stSelectbox"] [data-baseweb="select"] div,
    [data-testid="stMultiSelect"] [data-baseweb="select"] span,
    [data-testid="stMultiSelect"] [data-baseweb="select"] div,
    [data-testid="stSelectSlider"] [data-baseweb="select"] span,
    [data-testid="stSelectSlider"] [data-baseweb="select"] div {{
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] svg,
    [data-testid="stMultiSelect"] [data-baseweb="select"] svg,
    [data-testid="stSelectSlider"] [data-baseweb="select"] svg {{
        fill:{muted} !important;
        color:{muted} !important;
    }}
    [data-testid="stNumberInput"] button {{
        background:{surface2} !important;
        color:{text} !important;
        border-color:{border} !important;
    }}
    [data-testid="stNumberInput"] button svg {{ fill:{text} !important; color:{text} !important; }}
    [data-testid="stDateInput"] button,
    [data-testid="stTimeInput"] button {{ background:transparent !important; color:{muted} !important; }}
    [data-testid="stDateInput"] button svg,
    [data-testid="stTimeInput"] button svg {{ fill:{muted} !important; }}

    /* Menus e popovers vivem fora do bloco principal no DOM. */
    [data-baseweb="popover"],
    [data-baseweb="popover"] > div,
    [data-baseweb="popover"] [role="listbox"],
    [data-baseweb="popover"] ul,
    ul[data-baseweb="menu"],
    [role="listbox"] {{
        background:{surface} !important;
        background-color:{surface} !important;
        color:{text} !important;
        border-color:{border} !important;
    }}
    [data-baseweb="popover"] [role="option"],
    [data-baseweb="popover"] [role="option"] *,
    ul[data-baseweb="menu"] li,
    ul[data-baseweb="menu"] li * {{
        background:transparent !important;
        color:{text} !important;
        -webkit-text-fill-color:{text} !important;
    }}
    [data-baseweb="popover"] [role="option"]:hover,
    [data-baseweb="popover"] [role="option"][aria-selected="true"],
    ul[data-baseweb="menu"] li:hover {{ background:{hover} !important; }}

    /* Placeholder e texto desabilitado continuam legíveis no modo claro. */
    input::placeholder, textarea::placeholder {{ color:{muted} !important; -webkit-text-fill-color:{muted} !important; opacity:1 !important; }}
    input:disabled, textarea:disabled {{ background:{surface2} !important; color:{muted} !important; -webkit-text-fill-color:{muted} !important; }}

    /* ===== DASHBOARD 2.6 ===== */
    .rp-dash-hero {{
        display:flex; justify-content:space-between; align-items:flex-end; gap:24px;
        padding:4px 0 18px; margin-bottom:18px; border-bottom:1px solid {border};
    }}
    .rp-dash-eyebrow {{ color:{accent}; font-size:.66rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }}
    .rp-dash-title {{ color:{text}; font-size:1.8rem; line-height:1.1; font-weight:760; letter-spacing:-.035em; margin-top:4px; }}
    .rp-dash-sub {{ color:{muted}; font-size:.82rem; margin-top:6px; }}
    .rp-dash-date {{ color:{muted}; font-size:.75rem; white-space:nowrap; padding-bottom:3px; }}
    .rp-dash-alert {{
        border:1px solid {border}; border-left:3px solid {accent}; background:{surface};
        padding:12px 14px; border-radius:7px; margin-bottom:16px;
    }}
    .rp-dash-alert-title {{ color:{text}; font-weight:700; font-size:.82rem; }}
    .rp-dash-alert-sub {{ color:{muted}; font-size:.74rem; margin-top:3px; }}
    .rp-dash-section {{
        display:flex; align-items:center; gap:9px; margin:18px 0 9px;
        color:{text}; font-size:.92rem; font-weight:720;
    }}
    .rp-dash-section::before {{ content:""; width:3px; height:16px; background:{accent}; border-radius:2px; }}
    .rp-chart-title {{ color:{text}; font-size:.82rem; font-weight:700; margin:3px 0 8px; }}

    /* ===== CRONOGRAMA 2.6 ===== */
    .rp-crono-hero {{
        padding:2px 0 16px; border-bottom:1px solid {border}; margin-bottom:16px;
    }}
    .rp-crono-kicker {{ color:{accent}; font-size:.65rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }}
    .rp-crono-title {{ color:{text}; font-size:1.62rem; font-weight:750; letter-spacing:-.03em; margin-top:3px; }}
    .rp-crono-sub {{ color:{muted}; font-size:.79rem; margin-top:4px; max-width:760px; }}
    .rp-crono-stat {{
        background:{surface}; border:1px solid {border}; border-radius:7px; padding:11px 13px;
        min-height:68px;
    }}
    .rp-crono-stat-label {{ color:{muted}; font-size:.68rem; text-transform:uppercase; letter-spacing:.07em; font-weight:700; }}
    .rp-crono-stat-value {{ color:{text}; font-size:1.25rem; font-weight:760; margin-top:3px; }}
    .rp-crono-stat-accent {{ color:{accent}; }}
    .rp-crono-tabs [data-baseweb="tab-list"] {{ gap:3px !important; border-bottom:1px solid {border} !important; }}
    .rp-crono-tabs [data-baseweb="tab"] {{ padding:8px 12px !important; }}


    /* ===== CRONOGRAMA 2.8 — PLANNER PREMIUM ===== */
    .rp-planner-hero {{
        display:flex; align-items:flex-end; justify-content:space-between; gap:24px;
        padding:3px 0 18px; margin-bottom:16px; border-bottom:1px solid {{border}};
    }}
    .rp-planner-kicker {{ color:{{accent}}; font-size:.64rem; font-weight:820; letter-spacing:.13em; text-transform:uppercase; }}
    .rp-planner-title {{ color:{{text}}; font-size:1.82rem; line-height:1.08; font-weight:770; letter-spacing:-.04em; margin-top:4px; }}
    .rp-planner-sub {{ color:{{muted}}; font-size:.8rem; line-height:1.5; margin-top:6px; max-width:760px; }}
    .rp-planner-date {{ color:{{muted}}; font-size:.72rem; white-space:nowrap; padding-bottom:3px; }}
    .rp-planner-progress {{ height:7px; background:{{surface2}}; border:1px solid {{border2}}; border-radius:999px; overflow:hidden; margin-top:11px; }}
    .rp-planner-progress > div {{ height:100%; background:{{accent}}; border-radius:999px; }}
    .rp-planner-kpi {{
        background:{{surface}}; border:1px solid {{border}}; border-radius:9px; padding:12px 14px; min-height:78px;
    }}
    .rp-planner-kpi-label {{ color:{{muted}}; font-size:.65rem; text-transform:uppercase; letter-spacing:.075em; font-weight:760; }}
    .rp-planner-kpi-value {{ color:{{text}}; font-size:1.38rem; font-weight:770; letter-spacing:-.03em; margin-top:4px; }}
    .rp-planner-kpi-note {{ color:{{muted}}; font-size:.68rem; margin-top:2px; }}
    .rp-planner-toolbar {{
        background:{{surface}}; border:1px solid {{border}}; border-radius:9px; padding:12px 14px; margin:13px 0 15px;
    }}
    .rp-planner-toolbar-title {{ color:{{text}}; font-size:.76rem; font-weight:720; margin-bottom:7px; }}
    .rp-week-head {{
        display:flex; align-items:center; justify-content:space-between; gap:12px;
        padding:11px 13px; background:{{surface}}; border:1px solid {{border}}; border-bottom:0;
        border-radius:9px 9px 0 0; margin-top:14px;
    }}
    .rp-week-name {{ color:{{text}}; font-size:.95rem; font-weight:760; letter-spacing:-.015em; }}
    .rp-week-meta {{ color:{{muted}}; font-size:.7rem; white-space:nowrap; }}
    .rp-day-card {{
        background:{{surface}}; border:1px solid {{border}}; border-radius:8px; padding:10px 11px; margin-bottom:9px;
    }}
    .rp-day-card-empty {{ opacity:.72; }}
    .rp-day-head {{ display:flex; align-items:center; justify-content:space-between; gap:8px; padding-bottom:7px; margin-bottom:8px; border-bottom:1px solid {{border2}}; }}
    .rp-day-name {{ color:{{text}}; font-size:.75rem; font-weight:760; }}
    .rp-day-count {{ color:{{muted}}; font-size:.64rem; }}
    .rp-task {{
        display:flex; align-items:center; gap:9px; padding:8px 7px; border:1px solid transparent; border-radius:7px; margin:2px 0;
    }}
    .rp-task:hover {{ background:{{hover}}; border-color:{{border2}}; }}
    .rp-task-dot {{ width:7px; height:7px; min-width:7px; border-radius:50%; }}
    .rp-task-body {{ min-width:0; flex:1; }}
    .rp-task-title {{ color:{{text}}; font-size:.76rem; font-weight:650; line-height:1.3; overflow-wrap:anywhere; }}
    .rp-task-title.done {{ color:{{muted}}; text-decoration:line-through; }}
    .rp-task-meta {{ color:{{muted}}; font-size:.63rem; margin-top:2px; }}
    .rp-task-priority {{ font-size:.61rem; font-weight:700; white-space:nowrap; }}
    .rp-empty {{
        text-align:center; padding:32px 16px; background:{{surface}}; border:1px dashed {{border}}; border-radius:9px; color:{{muted}};
    }}
    .rp-empty strong {{ color:{{text}}; display:block; font-size:.9rem; margin-bottom:4px; }}
    .rp-import-card, .rp-manual-card {{ background:{{surface}}; border:1px solid {{border}}; border-radius:9px; padding:13px 14px; }}
    @media(max-width:760px) {{
        .rp-planner-hero {{ align-items:flex-start; }}
        .rp-planner-date {{ display:none; }}
        .rp-planner-title {{ font-size:1.5rem; }}
        .rp-week-head {{ padding:10px; }}
        .rp-week-meta {{ display:none; }}
        .rp-task {{ padding:7px 4px; }}
        .rp-task-priority {{ display:none; }}
    }}

    /* ===== CRONOGRAMA 2.9 — LEITURA RÁPIDA ===== */
    .rp-simple-crono-head {{ display:flex; align-items:center; justify-content:space-between; gap:20px; padding:3px 0 15px; border-bottom:1px solid {border}; margin-bottom:14px; }}
    .rp-simple-crono-title {{ color:{text}; font-size:1.72rem; font-weight:760; letter-spacing:-.035em; margin-top:3px; }}
    .rp-simple-crono-sub {{ color:{muted}; font-size:.79rem; margin-top:5px; }}
    .rp-simple-crono-progress {{ min-width:110px; text-align:right; }}
    .rp-simple-crono-progress strong {{ display:block; color:{accent}; font-size:1.35rem; }}
    .rp-simple-crono-progress span {{ color:{muted}; font-size:.68rem; }}

    /* ===== TOPO DE MÓDULO ===== */
    .rp-topbar {{ display:flex; align-items:center; justify-content:space-between; gap:20px; padding:2px 0 13px; margin:0 0 18px; border-bottom:1px solid {border}; }}
    .rp-topbar-title {{ color:{text}; font-size:1.42rem; font-weight:730; letter-spacing:-.025em; }}
    .rp-topbar-sub {{ color:{muted}; font-size:.77rem; margin-top:3px; }}
    .rp-status {{ color:{muted}; font-size:.7rem; white-space:nowrap; }}
    .rp-dot {{ display:inline-block; width:6px; height:6px; margin-right:6px; border-radius:50%; background:{accent}; }}
    .rp-kicker {{ color:{accent}; font-size:.66rem; font-weight:760; letter-spacing:.1em; text-transform:uppercase; margin-bottom:3px; }}

    /* ===== FORMULÁRIOS ===== */
    [data-baseweb="input"] > div,[data-baseweb="textarea"] > div,[data-baseweb="select"] > div,[data-testid="stFileUploadDropzone"] {{
        background:{input_bg} !important; border:1px solid {border} !important; border-radius:6px !important; box-shadow:none !important;
    }}
    [data-baseweb="input"] > div:focus-within,[data-baseweb="textarea"] > div:focus-within,[data-baseweb="select"] > div:focus-within {{ border-color:{accent} !important; box-shadow:0 0 0 2px {accent_soft} !important; }}
    input,textarea,[data-baseweb="select"] span {{ color:{text} !important; -webkit-text-fill-color:{text} !important; }}
    [data-baseweb="popover"] > div,ul[data-baseweb="menu"] {{ background:{surface} !important; border:1px solid {border} !important; border-radius:6px !important; box-shadow:0 10px 28px rgba(0,0,0,.12) !important; }}
    ul[data-baseweb="menu"] li:hover {{ background:{hover} !important; }}

    /* Botões: hierarquia, não decoração */
    .stButton > button, div[data-testid="stFormSubmitButton"] > button {{ min-height:39px !important; border-radius:6px !important; border:1px solid {accent} !important; background:{accent} !important; color:#fff !important; box-shadow:none !important; font-weight:650 !important; }}
    .stButton > button:hover,div[data-testid="stFormSubmitButton"] > button:hover {{ filter:brightness(.95); transform:none !important; }}
    .stButton > button:focus-visible,div[data-testid="stFormSubmitButton"] > button:focus-visible {{ box-shadow:0 0 0 3px {accent_soft} !important; }}

    /* ===== CONTAINERS / CARDS ===== */
    div[data-testid="stVerticalBlockBorderWrapper"] {{ background:{surface} !important; border:1px solid {border} !important; border-radius:7px !important; box-shadow:none !important; }}
    div[data-testid="stExpander"] {{ background:{surface} !important; border:1px solid {border} !important; border-radius:6px !important; box-shadow:none !important; }}
    div[data-testid="stExpander"] summary {{ font-weight:650 !important; }}
    [data-testid="stAlert"] {{ border-radius:6px !important; box-shadow:none !important; }}

    /* Métricas com leitura de dashboard, não cartão de marketing */
    div[data-testid="metric-container"] {{ background:{surface} !important; border:1px solid {border} !important; border-radius:7px !important; padding:12px 14px !important; box-shadow:none !important; }}
    div[data-testid="metric-container"] label {{ color:{muted} !important; font-size:.72rem !important; font-weight:620 !important; }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{ color:{text} !important; font-size:1.48rem !important; font-weight:730 !important; letter-spacing:-.035em !important; }}
    div[data-testid="metric-container"] [data-testid="stMetricDelta"] {{ font-size:.72rem !important; }}

    /* ===== ABAS ===== */
    [data-testid="stTabs"] {{ margin-top:.15rem !important; }}
    [data-testid="stTabs"] [role="tablist"] {{ gap:0 !important; border-bottom:1px solid {border} !important; }}
    [data-testid="stTabs"] button[role="tab"] {{ border:0 !important; border-bottom:2px solid transparent !important; border-radius:0 !important; padding:9px 14px 8px !important; color:{muted} !important; font-size:.8rem !important; font-weight:620 !important; background:transparent !important; }}
    [data-testid="stTabs"] button[role="tab"]:hover {{ color:{text} !important; background:{hover} !important; }}
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{ color:{accent} !important; border-bottom-color:{accent} !important; background:transparent !important; }}
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {{ background:{accent} !important; }}

    /* ===== TABELAS / EDITORES ===== */
    [data-testid="stDataFrame"],[data-testid="stTable"] {{ border:1px solid {border} !important; border-radius:6px !important; overflow:hidden !important; box-shadow:none !important; }}
    [data-testid="stDataFrame"] th,[data-testid="stTable"] th {{ background:{surface2} !important; color:{muted} !important; font-size:.74rem !important; font-weight:680 !important; text-transform:none !important; letter-spacing:0 !important; padding:9px !important; border-bottom:1px solid {border} !important; }}
    [data-testid="stDataFrame"] td,[data-testid="stTable"] td {{ padding:9px !important; border-bottom:1px solid {border2} !important; }}

    /* ===== COMPONENTES DE ESTUDO ===== */
    .rp-study-row {{ background:{surface}; border:1px solid {border}; border-radius:6px; padding:10px 12px; }}
    .rp-label {{ color:{muted}; font-size:.68rem; font-weight:700; text-transform:uppercase; letter-spacing:.06em; }}
    .rp-value {{ color:{text}; font-size:.94rem; font-weight:650; margin-top:2px; }}
    .rp-rule {{ height:1px; background:{border2}; margin:10px 0; }}

    /* ===== DASHBOARD 2.4 — visual próprio ===== */
    .dash-head {{ display:flex; align-items:flex-end; justify-content:space-between; gap:20px; padding:2px 0 15px; margin:0 0 14px; border-bottom:1px solid {border}; }}
    .dash-eyebrow {{ color:{accent}; font-size:.62rem; font-weight:800; letter-spacing:.12em; margin-bottom:5px; }}
    .dash-title {{ color:{text}; font-size:1.72rem; font-weight:760; letter-spacing:-.035em; line-height:1.05; }}
    .dash-sub {{ color:{muted}; font-size:.78rem; margin-top:6px; max-width:650px; }}
    .dash-date {{ color:{muted}; font-size:.72rem; white-space:nowrap; }}
    .dash-section-title {{ color:{text}; font-size:.78rem; font-weight:750; margin:14px 0 9px; }}
    @media(max-width:760px) {{ .dash-head {{ align-items:flex-start; }} .dash-date {{ display:none; }} .dash-title {{ font-size:1.48rem; }} }}

    /* ===== CHAT / IA ===== */
    [data-testid="stChatMessage"] {{ background:{surface} !important; border:1px solid {border} !important; border-radius:7px !important; margin-bottom:7px !important; }}
    [data-testid="stChatInput"] > div {{ background:{surface} !important; border:1px solid {border} !important; border-radius:7px !important; box-shadow:none !important; }}

    /* ===== GRÁFICOS ===== */
    .js-plotly-plot .plotly .modebar {{ display:none !important; }}

    @media(max-width:760px) {{
        .main .block-container {{ padding:.85rem .65rem 2.5rem !important; }}
        h1 {{ font-size:1.52rem !important; }}
        .rp-topbar {{ align-items:flex-start; margin-bottom:13px; }}
        .rp-status {{ display:none; }}
        [data-testid="stTabs"] button[role="tab"] {{ padding:9px 10px 8px !important; font-size:.75rem !important; }}
        .stButton > button {{ min-height:43px !important; }}
    }}
    @media(prefers-reduced-motion:reduce) {{ *,*::before,*::after {{ transition:none !important; animation:none !important; }} }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def render_shell(menu, nome, modo):
    """Cabeçalho discreto por módulo; mantém a navegação e as funções intactas."""
    nomes = {
        "🏠 Dashboard": ("Dashboard", "Visão geral do seu desempenho e da rotina de estudos."),
        "🗓️ Cronograma IA": ("Cronograma", "Planejamento e distribuição do estudo."),
        "⚡ Revisão HIIT": ("Revisão HIIT", "Revisões rápidas baseadas no que precisa de atenção."),
        "🎯 Questões": ("Questões", "Registro, desempenho e revisão dos erros."),
        "📚 Registro de Aulas": ("Aulas", "Acompanhe o conteúdo estudado e transforme aulas em progresso."),
        "📝 Anotações Rápidas": ("Anotações", "Seu espaço para registrar e organizar pontos importantes."),
        "📅 Agenda de Revisões": ("Revisões", "Veja o que está previsto e o que precisa ser retomado."),
        "✨ AI Tutor & Flashcards": ("Tutor & Flashcards", "Estudo ativo com tutor, cartões e técnica Feynman."),
        "📁 Materiais e Simulados": ("Materiais", "Organize materiais e simulados em um só lugar."),
        "🏥 Simulados & OSCE": ("Simulados & OSCE", "Treino direcionado para prova e estações práticas."),
        "📍 GPS da Aprovação": ("GPS da Aprovação", "Acompanhe seu caminho e os indicadores de desempenho."),
        "⏱️ Modo Foco": ("Modo Foco", "Sessões de estudo concentradas e sem distrações."),
        "⚙️ Configurações": ("Configurações", "Preferências e controle do seu perfil."),
        "📱 Instalar App": ("Residência PRO", "Acesso rápido ao seu ambiente de estudos."),
        "👑 Admin": ("Administração", "Gerenciamento global do sistema."),
    }
    titulo, subtitulo = nomes.get(menu, ("Residência PRO", "Ambiente de preparação para residência."))
    st.markdown(
        f'<div class="rp-topbar"><div><div class="rp-kicker">RESIDÊNCIA PRO · MÓDULO</div>'
        f'<div class="rp-topbar-title">{titulo}</div>'
        f'<div class="rp-topbar-sub">{subtitulo}</div></div>'
        f'<div class="rp-status"><span class="rp-dot"></span>{nome}</div></div>',
        unsafe_allow_html=True,
    )

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
# IMPORTANTE: não usamos response_format/json_schema nas chamadas;
# todo JSON é validado localmente para evitar HTTP 400 json_validate_failed.
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

def chamar_ia(client, *, modelo, **kwargs):
    """
    Faz a chamada Chat Completions com fallback automático de modelo.
    Mantém a mesma resposta compatível com client.chat.completions.create().
    """
    if client is None:
        raise RuntimeError("Cliente Groq não está conectado.")

    candidatos = MODELOS_VISAO_FALLBACK if modelo == MODELO_VISAO else MODELOS_TEXTO_FALLBACK
    ultimo_erro = None

    for modelo_tentativa in candidatos:
        try:
            call_kwargs = dict(kwargs)
            if modelo_tentativa == "qwen/qwen3.6-27b":
                call_kwargs.setdefault("reasoning_effort", "none")
                call_kwargs.setdefault("include_reasoning", False)
            elif modelo_tentativa in ("openai/gpt-oss-20b", "openai/gpt-oss-120b"):
                call_kwargs.setdefault("include_reasoning", False)
            call_kwargs.pop("response_format", None)
            return client.chat.completions.create(model=modelo_tentativa, **call_kwargs)
        except Exception as exc:
            ultimo_erro = exc
            erro = str(exc).lower()
            # Só troca de modelo quando o problema indica modelo indisponível/permissão.
            if any(token in erro for token in ("model_not_found", "does not exist", "do not have access", "404", "403")):
                continue
            raise

    raise RuntimeError(f"Nenhum modelo Groq disponível para esta operação. Último erro: {ultimo_erro}")


def chamar_ia_json_estrito(client, *, modelo, messages, schema_name=None, schema=None, max_completion_tokens=2000):
    """
    Chamada de IA sem response_format/json_schema.
    O JSON é validado e extraído localmente por extrair_json_seguro().
    Isso evita completamente o erro HTTP 400 json_validate_failed da Groq.
    """
    payload = dict(
        messages=messages,
        temperature=0.1,
        max_completion_tokens=max_completion_tokens,
    )
    # Qwen 3.6 permite desligar o raciocínio para respostas estruturadas simples.
    if modelo == MODELO_VISAO or modelo == MODELO_TEXTO:
        payload["reasoning_effort"] = "none"
        payload["include_reasoning"] = False
    return chamar_ia(client, modelo=modelo, **payload)


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

# Paleta EXCLUSIVA para percentual de acerto. Não reutilizar CORES_AREAS aqui.
def cor_percentual_acerto(valor):
    try:
        pct = float(str(valor).replace("%", "").replace(",", "."))
    except Exception:
        return "#94a3b8"
    if pct > 80:
        return "#22c55e"   # verde = excelente
    if pct >= 70:
        return "#eab308"   # amarelo = bom
    if pct >= 60:
        return "#3b82f6"   # azul = atenção
    return "#ef4444"       # vermelho = baixo
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

def normalizar_area(valor, mapa_aulas=None):
    """Normaliza nomes e códigos antigos de área para os nomes oficiais do app."""
    mapa_aulas = mapa_aulas or {}
    if valor is None:
        return "Geral"
    raw = str(valor).strip()
    if not raw:
        return "Geral"
    # IDs de aulas antigas: resolve primeiro pelo documento relacionado.
    if raw in mapa_aulas:
        aula = mapa_aulas.get(raw, {})
        candidato = aula.get("area") or aula.get("especialidade") or aula.get("materia")
        if candidato:
            return normalizar_area(candidato, {})
    limpo = limpar_texto(raw)
    chave = re.sub(r"[^a-z0-9]+", "", limpo.casefold())
    aliases = {
        "clinicamedica": "Clínica Médica", "cm": "Clínica Médica", "clinica": "Clínica Médica",
        "cirurgiageral": "Cirurgia Geral", "cg": "Cirurgia Geral", "cirurgia": "Cirurgia Geral",
        "pediatria": "Pediatria", "ped": "Pediatria", "peds": "Pediatria",
        "ginecologiaeobstetricia": "Ginecologia e Obstetrícia", "ginecologiaobstetricia": "Ginecologia e Obstetrícia",
        "go": "Ginecologia e Obstetrícia", "gineco": "Ginecologia e Obstetrícia", "obstetricia": "Ginecologia e Obstetrícia",
        "medicinapreventiva": "Medicina Preventiva", "preventiva": "Medicina Preventiva", "mp": "Medicina Preventiva",
        "geral": "Geral", "medicinageral": "Geral"
    }
    if chave in aliases:
        return aliases[chave]
    for area in AREAS_MED:
        if limpo.casefold() == area.casefold() or area.casefold() in limpo.casefold():
            return area
    # Códigos/IDs técnicos não vazam para a interface.
    if re.fullmatch(r"[A-Za-z0-9_-]{6,64}", limpo):
        return "Geral"
    return limpo or "Geral"

def resolver_area_grafico(valor, mapa_aulas=None):
    return normalizar_area(valor, mapa_aulas)

def cor_area(valor, mapa_aulas=None):
    return CORES_AREAS.get(normalizar_area(valor, mapa_aulas), CORES_AREAS["Geral"])

def normalizar_tema_comparacao(valor):
    """Normaliza temas apenas para identificar uma aula correspondente no cronograma."""
    txt = limpar_texto(valor or "")
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^a-z0-9]+", " ", txt.casefold())
    return re.sub(r"\s+", " ", txt).strip()

def remover_aula_do_cronograma(area_aula, tema_aula):
    """Remove do cronograma a meta correspondente à aula recém-registrada."""
    tema_ref = normalizar_tema_comparacao(tema_aula)
    if not tema_ref:
        return 0
    removidos = []
    area_ref = normalizar_area(area_aula, mapa_aulas)
    for item in list(st.session_state.dados.get("cronogramas", [])):
        if bool(item.get("concluido")):
            continue
        tema_crono = normalizar_tema_comparacao(item.get("tema"))
        area_crono = normalizar_area(item.get("materia"), mapa_aulas)
        if not tema_crono:
            continue
        mesma_area = area_crono == area_ref or area_crono == "Geral" or area_ref == "Geral"
        # Aceita correspondência exata ou quando um tema é uma versão expandida do outro.
        mesmo_tema = (tema_crono == tema_ref or tema_crono in tema_ref or tema_ref in tema_crono)
        if mesma_area and mesmo_tema:
            tid = str(item.get("id", "")).strip()
            if tid:
                db.collection("cronogramas").document(tid).delete()
                removidos.append(tid)
    if removidos:
        st.session_state.dados["cronogramas"] = [
            x for x in st.session_state.dados.get("cronogramas", [])
            if str(x.get("id", "")) not in set(removidos)
        ]
    return len(removidos)

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
                    temas = "".join([f"<div style='background-color:{cor_area(a.get('area'), mapa_aulas)}; color:white !important; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(a.get('tema', '')))}'>{html.escape(limpar_texto(a.get('tema', '')))}</div>" for a in aulas_dict[day]])
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
                    temas = "".join([f"<div style='background-color:{CORES_AREAS.get(normalizar_area(r.get('area'), mapa_aulas), '#64748b')}; color:white !important; padding:4px 6px; border-radius:6px; font-size:11px; margin-bottom:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; box-shadow: 0 2px 4px rgba(0,0,0,0.1);' title='{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})'>{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})</div>" for r in revs_dict[day]])
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px; transition: transform 0.2s;' onmouseover=\"this.style.transform='scale(1.02)'\" onmouseout=\"this.style.transform='scale(1)'\"><strong style='color:{tc_st} !important; font-size:14px;'>{day}</strong><div style='margin-top:8px;'>{temas}</div></td>"
                else: 
                    html_code += f"<td style='border:1px solid {bd_cl}; padding:8px; background-color:{bg_cl} !important; vertical-align:top; height:90px; border-radius:6px;'><strong style='color:{tc_em} !important; font-size:14px;'>{day}</strong></td>"
        html_code += "</tr>"
    html_code += "</table></div>"
    return html_code

def render_toolbar():
    """
    Motor definitivo de formatação à prova de mobile e iPad.
    Implementa a barra fixa com flex-wrap (que quebra de linha em telas pequenas)
    e o Real-Time Auto-Save local.
    """
    toolbar_html = """
    <div id="inline-toolbar" style="display: flex; flex-wrap: wrap; gap: 8px; align-items: center; background: #1e293b; padding: 10px 15px; border-radius: 8px; border: 1px solid #334155; width: 100%; box-sizing: border-box;">
        <span style="color: #f8fafc; font-family: 'Inter', sans-serif; font-size: 13px; font-weight: 600; margin-right: 5px;">🪄 Formatador:</span>
        <button class="inline-fmt-btn" data-t1="**" data-t2="**" style="padding: 6px 12px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; font-weight: bold; transition: transform 0.1s;">B</button>
        <button class="inline-fmt-btn" data-t1="<u>" data-t2="</u>" style="padding: 6px 12px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; text-decoration: underline; transition: transform 0.1s;">U</button>
        <button class="inline-fmt-btn" data-t1="<mark>" data-t2="</mark>" style="padding: 6px 12px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; transition: transform 0.1s;">🖍️ Grifar</button>
        <button class="inline-fmt-btn" data-t1="\\n- " data-t2="" style="padding: 6px 12px; border-radius: 6px; border: none; background: #2563eb; color: white; cursor: pointer; transition: transform 0.1s;">📋 Tópico</button>
        <button class="inline-fmt-btn" data-t1="PASTE" data-t2="" style="padding: 6px 12px; border-radius: 6px; border: none; background: #10b981; color: white; cursor: pointer; font-weight: bold; transition: transform 0.1s;">📸 Colar Imagem</button>
    </div>
    
    <script>
    // --- LÓGICA LOCAL PARA A BARRA FIXA (COM SUPORTE A IPAD/MOBILE) ---
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
                container.style.boxShadow = '0 0 20px 5px #10b981';
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

    // Configuração dos botões anti-perda-de-foco (PC + Mobile/iPad)
    document.querySelectorAll('.inline-fmt-btn').forEach(btn => {
        const action = (e) => {
            e.preventDefault(); // Impede a perda de foco da caixa de texto no mobile
            btn.style.transform = 'scale(0.95)';
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
        btn.addEventListener('touchstart', action, {passive: false}); // O segredo para o iPad e Celular
    });

    // --- AUTO-SAVE REAL TIME NO NAVEGADOR ---
    function initAutoSave() {
        const parentDoc = window.parent.document;
        const textareas = parentDoc.querySelectorAll('textarea');
        
        textareas.forEach((ta, index) => {
            const label = ta.getAttribute('aria-label') || '';
            if(label.includes('Pontos') || label.includes('Anotação') || label.includes('Resumo') || label.includes('Tópicos')) {
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
    }
    setTimeout(initAutoSave, 1000);
    </script>
    """
    components.html(toolbar_html, height=85)

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
    aplicar_ui_premium(st.session_state.temp_theme)
    
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
                elif not nu_limpo or not np_limpo:
                    st.error("Preencha o usuário e a senha para criar a conta.")
                else:
                    db.collection("usuarios").add({"nome": nu_limpo, "senha": hash_senha(np_limpo), "tema_modo": st.session_state.temp_theme})
                    st.toast("✅ Conta criada com sucesso!", icon="🎉")

# CORES DE % DE ACERTOS PRESERVADAS: <60 vermelho | 60-69 azul | 70-80 amarelo | >80 verde.
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
            "questoes_hiit": [], "revisoes_hiit": [], "anotacoes_hiit": [], "flashcards_hiit": []
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
                flashcards_hiit_recuperadas = get_user_docs("flashcards_hiit", u_id)

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
                    "anotacoes_hiit": anotacoes_hiit_recuperadas,
                    "flashcards_hiit": flashcards_hiit_recuperadas
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
    dados_flashcards_hiit = _dados_cache.get("flashcards_hiit", [])

    # APLICA O TEMA DO USUARIO LOGADO
    modo_atual = user_settings.get("tema_modo", "Escuro")
    aplicar_css_tema(modo_atual)
    aplicar_ui_premium(modo_atual)

    # BARRA LATERAL — HUB DE NAVEGAÇÃO 2.1
    with st.sidebar:
        st.markdown("<div class='rp-brand'><div class='rp-brand-title'>🏥 RESIDÊNCIA PRO</div><div class='rp-brand-sub'>AMBIENTE DE ESTUDO · 2.8</div></div>", unsafe_allow_html=True)
        if user_settings.get('foto_perfil_b64'):
            st.markdown(f'<img src="data:image/jpeg;base64,{user_settings["foto_perfil_b64"]}" class="profile-img">', unsafe_allow_html=True)
        st.markdown(f'<div style="text-align:center;font-weight:850;font-size:.95rem;color:var(--rp-text);margin-bottom:8px">{st.session_state.user_nome}</div>', unsafe_allow_html=True)
        total_atividade = sum(len(_dados_cache.get(k, [])) for k in ["aulas","revisoes","questoes","flashcards","simulados","focus","materiais","cronogramas","anotacoes"])
        st.markdown(f'<div style="text-align:center;margin-bottom:12px"><span class="rp-chip">● {total_atividade} registros</span></div>', unsafe_allow_html=True)
        if st.button("🚪 Sair da Conta", use_container_width=True):
            db.collection("usuarios").document(u_id).update({"token_sessao": None})
            if cookie_controller: cookie_controller.remove('mr_token')
            time.sleep(0.5)
            st.session_state.clear()
            st.rerun()
        st.markdown("---")

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
        
    st.sidebar.markdown("<div style='font-size:.72rem;font-weight:850;letter-spacing:.08em;color:var(--rp-muted);margin:4px 12px 7px'>ACESSO RÁPIDO</div>", unsafe_allow_html=True)
    q1, q2 = st.sidebar.columns(2)
    with q1:
        if st.button("🏠 Início", use_container_width=True, key="quick_home"):
            st.session_state["menu_navegacao"] = "🏠 Dashboard"
            st.rerun()
    with q2:
        if st.button("🎯 Questões", use_container_width=True, key="quick_q"):
            st.session_state["menu_navegacao"] = "🎯 Questões"
            st.rerun()
    st.sidebar.markdown("<div style='font-size:.72rem;font-weight:850;letter-spacing:.08em;color:var(--rp-muted);margin:12px 12px 7px'>NAVEGAÇÃO</div>", unsafe_allow_html=True)
    menu = st.sidebar.radio("Navegação Principal", opcoes_menu, key="menu_navegacao", label_visibility="collapsed")
    render_shell(menu, st.session_state.user_nome, modo_atual)

    # ==========================================
    # TELAS
    # ==========================================
    if menu == "🏠 Dashboard":
        st.markdown(f"""
        <div class="rp-dash-hero">
            <div>
                <div class="rp-dash-eyebrow">CENTRO DE COMANDO</div>
                <div class="rp-dash-title">Seu desempenho</div>
                <div class="rp-dash-sub">Uma visão objetiva do seu estudo para decidir o próximo passo.</div>
            </div>
            <div class="rp-dash-date">{hoje.strftime('%A, %d/%m/%Y').capitalize()}</div>
        </div>
        """, unsafe_allow_html=True)

        revs_pendentes_dash = [r for r in dados_revisoes + dados_revisoes_hiit if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
        revs_hoje_lista = [r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) <= hoje]
        prox_revs_lista = sorted([r for r in revs_pendentes_dash if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
        data_prox_dash = formatar_data_br(prox_revs_lista[0].get('data_agendada')) if prox_revs_lista else "Nenhuma agendada"

        if revs_hoje_lista:
            st.markdown(f"""<div class="rp-dash-alert"><div class="rp-dash-alert-title">Atenção: {len(revs_hoje_lista)} revisão(ões) pendente(s) hoje</div><div class="rp-dash-alert-sub">Priorize a agenda de revisões antes de iniciar um novo bloco.</div></div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="rp-dash-alert"><div class="rp-dash-alert-title">Tudo em dia</div><div class="rp-dash-alert-sub">Próxima revisão futura: {data_prox_dash}.</div></div>""", unsafe_allow_html=True)

        qs_sess_all = [dict(q) for q in dados_questoes]
        qs_revs_all = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
        revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]

        t_acertos_g = sum(safe_int(q.get('acertos')) for q in qs_sess_all) + sum(safe_int(r.get('acertos')) for r in qs_revs_all) + sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
        t_erros_g = sum(safe_int(q.get('erros')) for q in qs_sess_all) + sum(safe_int(r.get('erros')) for r in qs_revs_all) + sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
        t_questoes_g = t_acertos_g + t_erros_g
        taxa_geral = (t_acertos_g / t_questoes_g * 100) if t_questoes_g else 0

        st.markdown('<div class="rp-dash-section">Visão geral</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões", t_questoes_g)
        c2.metric("🟢 Acertos", t_acertos_g)
        c3.metric("🔴 Erros", t_erros_g)
        c4.metric("Aproveitamento", f"{taxa_geral:.1f}%")

        aba_geral, aba_detalhada = st.tabs(["Desempenho geral", "Por matéria"])
        with aba_geral:
            col_g1, col_g2 = st.columns([0.9, 1.5])
            modo_grafico_font = "#f2f4f5" if modo_atual == "Escuro" else "#17201d"
            with col_g1:
                st.markdown('<div class="rp-chart-title">Acertos x erros</div>', unsafe_allow_html=True)
                if t_questoes_g > 0:
                    fig_pie1 = px.pie(
                        names=['Acertos', 'Erros'], values=[t_acertos_g, t_erros_g], hole=0.68,
                        color_discrete_sequence=["#22c55e", "#ef4444"]
                    )
                    fig_pie1.update_traces(textinfo="percent", textposition="inside", hovertemplate="%{label}: %{value}<extra></extra>")
                    fig_pie1.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color=modo_grafico_font, showlegend=True,
                        legend=dict(orientation="h", y=-0.05), margin=dict(t=10,b=10,l=5,r=5)
                    )
                    st.plotly_chart(fig_pie1, use_container_width=True, config={'displayModeBar': False}, theme=None)
                else:
                    st.info("Registre questões para visualizar seu desempenho.")
            with col_g2:
                st.markdown('<div class="rp-chart-title">Aproveitamento por matéria</div>', unsafe_allow_html=True)
                todas_questoes_grafico = []
                for q in qs_sess_all:
                    todas_questoes_grafico.append({"area": normalizar_area(q.get('area'), mapa_aulas), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))})
                for r in qs_revs_all:
                    todas_questoes_grafico.append({"area": normalizar_area(r.get('area_aula', r.get('area')), mapa_aulas), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))})
                for q in qs_hiit_all:
                    todas_questoes_grafico.append({"area": normalizar_area(q.get('area'), mapa_aulas), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))})
                for r in revs_hiit_all:
                    todas_questoes_grafico.append({"area": normalizar_area(r.get('area'), mapa_aulas), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))})
                df_r = pd.DataFrame(todas_questoes_grafico)
                if not df_r.empty:
                    df_r = df_r[df_r["area"].notna()]
                    df_g = df_r.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_g['Taxa'] = np.where((df_g['acertos'] + df_g['erros']) > 0, df_g['acertos'] / (df_g['acertos'] + df_g['erros']) * 100, 0)
                    df_g = df_g.sort_values('Taxa')
                    # A COR DA BARRA IDENTIFICA A MATÉRIA. A COR DO % IDENTIFICA O DESEMPENHO.
                    # Assim as duas informações permanecem independentes e não se misturam.
                    def cor_taxa(v):
                        return cor_percentual_acerto(v)

                    cores_materias = [CORES_AREAS.get(str(area), "#64748b") for area in df_g['area']]
                    fig_bar1 = go.Figure(go.Bar(
                        x=df_g['Taxa'], y=df_g['area'], orientation='h',
                        marker_color=cores_materias,
                        marker_line_color=cores_materias,
                        marker_line_width=0,
                        hovertemplate="<b>%{y}</b><br>Aproveitamento: %{x:.1f}%<extra></extra>",
                        cliponaxis=False
                    ))
                    # O percentual continua usando a escala de desempenho, sem alterar a cor da matéria.
                    for _, row in df_g.iterrows():
                        taxa = float(row['Taxa'])
                        fig_bar1.add_annotation(
                            x=min(taxa + 2.2, 108), y=row['area'],
                            text=f"<b>{taxa:.1f}%</b>",
                            showarrow=False,
                            xanchor="left", yanchor="middle",
                            font=dict(size=12, color=cor_taxa(taxa)),
                            bgcolor="rgba(0,0,0,0)",
                            borderwidth=0
                        )
                    fig_bar1.update_xaxes(range=[0, 110], ticksuffix="%", gridcolor="rgba(128,128,128,.12)")
                    fig_bar1.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                        font_color=modo_grafico_font, showlegend=False,
                        margin=dict(t=8,b=8,l=8,r=48), height=max(300, 42 * len(df_g))
                    )
                    st.plotly_chart(fig_bar1, use_container_width=True, config={'displayModeBar': False}, theme=None)
                    legenda_materias = " · ".join([
                        f"<span style='color:{CORES_AREAS.get(a, '#64748b')};font-weight:700'>●</span> {a}"
                        for a in AREAS_MED if a in set(df_g['area'])
                    ])
                    st.markdown(
                        f"<div style='font-size:11px;line-height:1.7;margin-top:-4px'>{legenda_materias}</div>"
                        f"<div style='font-size:11px;line-height:1.7;color:{modo_grafico_font};opacity:.82'>"
                        f"% de acertos: <span style='color:#ef4444;font-weight:700'>● &lt;60%</span> · "
                        f"<span style='color:#3b82f6;font-weight:700'>● 60–69%</span> · "
                        f"<span style='color:#eab308;font-weight:700'>● 70–80%</span> · "
                        f"<span style='color:#22c55e;font-weight:700'>● &gt;80%</span></div>",
                        unsafe_allow_html=True
                    )
                else:
                    st.info("Ainda não há dados suficientes por matéria.")

        with aba_detalhada:
            filtro_dash = st.selectbox("Selecione a matéria", AREAS_MED, key="dash_area_filtro")
            qs_sess_f = [q for q in qs_sess_all if normalizar_area(q.get('area'), mapa_aulas) == filtro_dash]
            qs_revs_f = [r for r in qs_revs_all if normalizar_area(r.get('area_aula', r.get('area')), mapa_aulas) == filtro_dash]
            qs_hiit_f = [q for q in qs_hiit_all if normalizar_area(q.get('area'), mapa_aulas) == filtro_dash]
            revs_hiit_f = [r for r in revs_hiit_all if normalizar_area(r.get('area'), mapa_aulas) == filtro_dash]
            t_acertos_f = sum(safe_int(q.get('acertos')) for q in qs_sess_f) + sum(safe_int(r.get('acertos')) for r in qs_revs_f) + sum(safe_int(q.get('acertos')) for q in qs_hiit_f) + sum(safe_int(r.get('acertos')) for r in revs_hiit_f)
            t_erros_f = sum(safe_int(q.get('erros')) for q in qs_sess_f) + sum(safe_int(r.get('erros')) for r in qs_revs_f) + sum(safe_int(q.get('erros')) for q in qs_hiit_f) + sum(safe_int(r.get('erros')) for r in revs_hiit_f)
            t_questoes_f = t_acertos_f + t_erros_f
            taxa_f = (t_acertos_f / t_questoes_f * 100) if t_questoes_f else 0
            c1_f, c2_f, c3_f = st.columns(3)
            c1_f.metric("Questões", t_questoes_f)
            c2_f.metric("🟢 Acertos", t_acertos_f)
            c3_f.metric("Aproveitamento", f"{taxa_f:.1f}%")
            if t_questoes_f:
                st.progress(min(max(taxa_f / 100, 0), 1), text=f"{taxa_f:.1f}% de aproveitamento em {filtro_dash}")
            else:
                st.info("Nenhuma questão registrada para esta matéria ainda.")

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
        # =============================================================
        # CRONOGRAMA 2.9 — PLANEJADOR SIMPLES E DIRETO
        # =============================================================
        meu_crono = list(dados_cronogramas or [])
        total_crono = len(meu_crono)
        concluidos_crono = [t for t in meu_crono if bool(t.get("concluido"))]
        pendentes_crono = [t for t in meu_crono if not bool(t.get("concluido"))]
        taxa_crono = (len(concluidos_crono) / total_crono * 100) if total_crono else 0

        st.markdown(f"""
        <div class="rp-simple-crono-head">
          <div><div class="rp-kicker">PLANEJAMENTO</div>
          <div class="rp-simple-crono-title">Meu cronograma</div>
          <div class="rp-simple-crono-sub">Um lugar para saber exatamente o que estudar hoje e o que vem depois.</div></div>
          <div class="rp-simple-crono-progress"><strong>{taxa_crono:.0f}%</strong><span>concluído</span></div>
        </div>""", unsafe_allow_html=True)

        k1,k2,k3 = st.columns(3)
        k1.metric("Total", total_crono)
        k2.metric("Pendentes", len(pendentes_crono))
        k3.metric("Concluídas", len(concluidos_crono))
        st.progress(min(max(taxa_crono/100,0),1), text=f"Progresso geral · {taxa_crono:.0f}%")

        tab_plano, tab_nova, tab_ia = st.tabs(["📋 Meu plano", "➕ Nova meta", "✨ Importar com IA"])

        with tab_plano:
            if not meu_crono:
                st.info("Seu cronograma está vazio. Crie uma meta ou importe seu cronograma com IA.")
            else:
                # Ordem das semanas: a ÚLTIMA SEMANA INSERIDA aparece primeiro.
                # Usa criado_em quando disponível e data_importacao como fallback para
                # cronogramas antigos. A ordem é calculada por semana, não pela ordem
                # em que o Firestore devolveu os documentos.
                semanas_info = {}
                for c in meu_crono:
                    sem = str(c.get("semana") or "Sem semana").strip() or "Sem semana"
                    bruto = c.get("criado_em") or c.get("data_importacao") or ""
                    try:
                        ordem_dt = pd.to_datetime(bruto, errors="coerce")
                        if pd.isna(ordem_dt): ordem_dt = pd.Timestamp.min
                    except Exception:
                        ordem_dt = pd.Timestamp.min
                    if sem not in semanas_info or ordem_dt > semanas_info[sem]:
                        semanas_info[sem] = ordem_dt

                def chave_semana_num(x):
                    nums = re.findall(r"\d+", x)
                    return int(nums[-1]) if nums else -1

                # Principal: inserção mais recente.
                # Desempate: maior número da semana; depois nome.
                semanas = sorted(
                    semanas_info.keys(),
                    key=lambda x: (semanas_info[x], chave_semana_num(x), x.casefold()),
                    reverse=True
                )
                f1,f2,f3 = st.columns([1.2,1.2,2])
                filtro_sem = f1.selectbox("Semana", ["Todas"]+semanas, key="crono29_sem")
                filtro_status = f2.selectbox("Status", ["Todos","Pendentes","Concluídas"], key="crono29_status")
                busca = f3.text_input("Buscar tema", placeholder="Ex.: insuficiência cardíaca", key="crono29_busca")
                filtradas=meu_crono
                if filtro_sem!="Todas": filtradas=[x for x in filtradas if str(x.get("semana") or "Sem semana")==filtro_sem]
                if filtro_status=="Pendentes": filtradas=[x for x in filtradas if not bool(x.get("concluido"))]
                elif filtro_status=="Concluídas": filtradas=[x for x in filtradas if bool(x.get("concluido"))]
                if busca:
                    q=busca.casefold(); filtradas=[x for x in filtradas if q in str(x.get("tema","")).casefold() or q in normalizar_area(x.get("materia"), mapa_aulas).casefold()]

                if not filtradas:
                    st.warning("Nenhuma meta encontrada com esses filtros.")
                else:
                    dias=["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"]
                    semanas_exibir=semanas if filtro_sem=="Todas" else [filtro_sem]
                    for sem in semanas_exibir:
                        itens_sem=[x for x in filtradas if str(x.get("semana") or "Sem semana")==sem]
                        if not itens_sem: continue
                        done=sum(bool(x.get("concluido")) for x in itens_sem)
                        pct=done/len(itens_sem)*100
                        with st.container(border=True):
                            st.markdown(f"### 📚 {sem}")
                            st.caption(f"{done} de {len(itens_sem)} metas concluídas · {pct:.0f}%")
                            st.progress(pct/100)
                            # Dentro de cada dia, sempre ordenar pela prioridade visual:
                            # Azul -> Verde -> Amarelo -> Vermelho -> Roxo.
                            # Aulas concluídas não permanecem na lista principal do dia:
                            # elas são movidas para o tópico "Aulas assistidas" no fim da semana.
                            ordem_prioridade = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4}
                            for dia in dias:
                                itens=[x for x in itens_sem if str(x.get("dia",""))==dia and not bool(x.get("concluido"))]
                                if not itens: continue
                                itens.sort(key=lambda x: ordem_prioridade.get(safe_int(x.get("prioridade", 3)), 2))
                                st.markdown(f"**{dia}**")
                                for t in itens:
                                    tid=str(t.get("id","")); mat=normalizar_area(t.get("materia"), mapa_aulas); cor=cor_area(mat); tema=html.escape(limpar_texto(t.get("tema","Sem tema")));
                                    a,b,c=st.columns([0.08,3.4,0.8])
                                    with a:
                                        # O botão de check conclui a aula e a move para
                                        # "Aulas assistidas" no final desta semana.
                                        if st.button("✓", key=f"crono29_done_{tid}", help="Marcar aula como assistida"):
                                            agora = get_agora().strftime("%Y-%m-%d %H:%M:%S")
                                            db_update("cronogramas","cronogramas",tid,{"concluido":True,"data_conclusao":agora})
                                            # Mantém o registro no Firestore para preservar o histórico
                                            # e permitir que a aula apareça no tópico de assistidas.
                                            st.toast("Aula assistida! Ela foi movida para o histórico da semana.", icon="✅")
                                            st.rerun()
                                    with b:
                                        st.markdown(f"<div style='padding:5px 0'><span style='color:{cor};font-weight:800'>●</span> <strong>{tema}</strong><br><small style='color:var(--rp-muted)'>{mat}</small></div>", unsafe_allow_html=True)
                                    with c:
                                        p=safe_int(t.get("prioridade",3)); novo=st.selectbox("Prioridade",[1,2,3,4,5],index=max(0,min(4,p-1)),format_func=lambda x: PRIORIDADES.get(x),key=f"crono29_pri_{tid}",label_visibility="collapsed")
                                        if novo!=p: db_update("cronogramas","cronogramas",tid,{"prioridade":novo}); st.rerun()

                            # =====================================================
                            # HISTÓRICO DA SEMANA — aulas que já foram assistidas
                            # =====================================================
                            aulas_assistidas = [x for x in itens_sem if bool(x.get("concluido"))]
                            if filtro_status in ("Todos", "Concluídas") and aulas_assistidas:
                                with st.expander(f"✅ Aulas assistidas · {len(aulas_assistidas)}", expanded=False):
                                    st.caption("As aulas marcadas com ✓ ficam aqui para você visualizar o que já estudou nesta semana.")
                                    aulas_assistidas.sort(
                                        key=lambda x: (
                                            str(x.get("data_conclusao") or ""),
                                            ordem_prioridade.get(safe_int(x.get("prioridade", 3)), 2)
                                        ),
                                        reverse=True
                                    )
                                    for t in aulas_assistidas:
                                        tid=str(t.get("id", ""))
                                        mat=normalizar_area(t.get("materia"), mapa_aulas); cor=cor_area(mat); tema=html.escape(limpar_texto(t.get("tema","Sem tema")))
                                        data_conc=limpar_texto(t.get("data_conclusao", ""))
                                        a,b=st.columns([0.45,4.15])
                                        with a:
                                            # Permite desfazer o check e devolver a aula à lista pendente.
                                            if st.button("↩️", key=f"crono29_uncheck_{tid}", help="Desmarcar como assistida e devolver ao cronograma"):
                                                db_update("cronogramas","cronogramas",tid,{"concluido":False,"data_conclusao":None})
                                                st.toast("Aula devolvida ao cronograma.", icon="↩️")
                                                st.rerun()
                                        with b:
                                            detalhe=f"<small style='color:{cor};font-weight:700'>{html.escape(mat)}</small>"
                                            if data_conc:
                                                detalhe += f"<small style='color:var(--rp-muted)'> · Assistida em {html.escape(data_conc)}</small>"
                                            st.markdown(f"<div style='padding:5px 0'><span style='color:{cor};font-weight:900'>●</span> <span style='color:{cor};font-weight:900'>✅</span> <strong style='text-decoration:line-through'>{tema}</strong><br>{detalhe}</div>", unsafe_allow_html=True)

                            with st.expander("⚙️ Gerenciar semana"):
                                if st.button("Excluir esta semana",key=f"crono29_del_sem_{sem}"):
                                    batch=db.batch(); ids=[]
                                    for t in [x for x in meu_crono if str(x.get("semana") or "Sem semana")==sem]:
                                        tid=str(t.get("id",""))
                                        if tid: batch.delete(db.collection("cronogramas").document(tid)); ids.append(tid)
                                    batch.commit(); st.session_state.dados["cronogramas"]=[x for x in st.session_state.dados["cronogramas"] if str(x.get("id")) not in ids]; st.rerun()

        with tab_nova:
            with st.form("form_crono_manual_29", clear_on_submit=True):
                st.markdown("### Criar uma meta")
                st.caption("Preencha apenas o necessário: semana, dia, matéria e tema.")
                c1,c2=st.columns(2)
                m_sem=c1.text_input("Semana / bloco",placeholder="Ex.: Semana 1")
                m_dia=c2.selectbox("Dia",["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado","Domingo"])
                c3,c4=st.columns(2)
                m_mat=c3.selectbox("Matéria",AREAS_MED,key="crono29_mat")
                sub=""
                if m_mat=="Clínica Médica": sub=c4.selectbox("Subespecialidade",SUB_CM,key="crono29_subcm")
                elif m_mat=="Cirurgia Geral": sub=c4.selectbox("Subespecialidade",SUB_CG,key="crono29_subcg")
                m_tema=st.text_input("Tema",placeholder="Ex.: Insuficiência cardíaca — tratamento")
                m_prio=st.select_slider("Prioridade",options=[1,2,3,4,5],value=3,format_func=lambda x: PRIORIDADES.get(x))
                if st.form_submit_button("Adicionar ao cronograma",use_container_width=True,type="primary"):
                    if not m_sem.strip() or not m_tema.strip(): st.error("Preencha a semana e o tema.")
                    else:
                        tema=f"{sub} - {m_tema.strip()}" if sub and sub!="Geral" else m_tema.strip()
                        db_add("cronogramas","cronogramas",{"usuario_id":u_id,"semana":m_sem.strip(),"dia":m_dia,"materia":m_mat,"tema":tema,"prioridade":m_prio,"concluido":False,"data_importacao":str(hoje),"criado_em":get_agora().strftime("%Y-%m-%d %H:%M:%S.%f"),"data_conclusao":None}); st.toast("Meta adicionada!",icon="🎯"); st.rerun()

        with tab_ia:
            st.markdown("### Transformar seu cronograma em metas")
            st.caption("Envie prints. A IA extrai as tarefas sem alterar o restante do seu cronograma.")
            nome_semana=st.text_input("Nome da semana / bloco",placeholder="Ex.: Semana 1 · Reta final",key="crono29_nome")
            ca,cb=st.columns(2)
            with ca:
                st.markdown("**📋 Colar prints**")
                if paste_image_button is not None:
                    pr=paste_image_button(label="Colar imagem (Ctrl+V)",background_color="#2563eb",hover_background_color="#1d4ed8",key="paste_crono29")
                    if pr.image_data is not None:
                        buf=io.BytesIO(); pr.image_data.save(buf,format="PNG"); h=hashlib.md5(buf.getvalue()).hexdigest()
                        if not any(x['hash']==h for x in st.session_state.get('prints_colados',[])): st.session_state.prints_colados.append({'hash':h,'img':pr.image_data,'bytes':buf.getvalue()}); st.rerun()
                if st.session_state.get('prints_colados'): st.success(f"{len(st.session_state.prints_colados)} print(s) na fila")
            with cb:
                imgs=st.file_uploader("Enviar imagens",type=['png','jpg','jpeg'],accept_multiple_files=True,key="crono29_upload")
            if (imgs or st.session_state.get('prints_colados')) and nome_semana and st.button("🪄 Extrair metas com IA",use_container_width=True,key="crono29_extract"):
                client=get_ia_client()
                if not client: st.error("IA não conectada. Configure a GROQ_KEY nos Secrets.")
                else:
                    imagens=[]
                    for im in (imgs or []): imagens.append(otimizar_imagem_para_api(im,max_size=720))
                    for x in st.session_state.get('prints_colados',[]): imagens.append(otimizar_imagem_para_api(x['img'],max_size=720))
                    tarefas=[]; prog=st.progress(0)
                    prompt="Extraia TODAS as tarefas visíveis. Retorne somente JSON: {\"tarefas\":[{\"materia\":\"Clínica Médica\",\"tema\":\"...\",\"cor\":\"azul\"}]} Use somente nomes oficiais de matéria: Clínica Médica, Cirurgia Geral, Pediatria, Ginecologia e Obstetrícia, Medicina Preventiva, Geral."
                    for i,b64 in enumerate(imagens):
                        try:
                            r=chamar_ia(client,modelo=MODELO_VISAO,messages=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}],temperature=.1,max_tokens=2500)
                            tarefas.extend(extrair_json_seguro(r.choices[0].message.content).get('tarefas',[]))
                        except Exception as e: st.warning(f"Imagem {i+1}: {e}")
                        prog.progress((i+1)/max(1,len(imagens)))
                    if tarefas:
                        dias=["Segunda-feira","Terça-feira","Quarta-feira","Quinta-feira","Sexta-feira","Sábado"]
                        batch=db.batch()
                        for i,t in enumerate(tarefas):
                            cor=str(t.get('cor','')).casefold(); p=1 if 'azul' in cor else 2 if 'verde' in cor else 3 if 'amarelo' in cor else 4 if 'vermelho' in cor else 5 if 'roxo' in cor else 3
                            ref=db.collection('cronogramas').document(); item={"usuario_id":u_id,"semana":nome_semana.strip(),"dia":dias[(i//5)%len(dias)],"materia":normalizar_area(t.get('materia'), mapa_aulas),"tema":str(t.get('tema','Sem tema')).strip(),"prioridade":p,"concluido":False,"data_importacao":str(hoje),"criado_em":get_agora().strftime("%Y-%m-%d %H:%M:%S.%f"),"data_conclusao":None}; batch.set(ref,item); item['id']=ref.id; st.session_state.dados['cronogramas'].append(item)
                        batch.commit(); st.session_state.prints_colados=[]; st.toast(f"{len(tarefas)} metas importadas!",icon="🎯"); st.rerun()
                    else: st.warning("Não foi possível encontrar metas nas imagens.")

    elif menu == "⚡ Revisão HIIT":
        st.header("⚡ Revisão Intensiva (HIIT MedCof)")
        aba_dash_hiit, aba_reg_hiit, aba_cal_hiit, aba_notas_hiit, aba_fc_hiit = st.tabs(["⚡ Dashboard HIIT", "📝 Registrar Questões", "📅 Calendário", "📓 Anotações HIIT", "📚 Flashcards HIIT"])

        with aba_dash_hiit:
            st.markdown("### ⚡ Desempenho Exclusivo HIIT")
            
            qs_hiit_all = [dict(q) for q in dados_questoes_hiit]
            revs_hiit_all = [dict(r) for r in dados_revisoes_hiit if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
            
            t_acertos_h = sum(safe_int(q.get('acertos')) for q in qs_hiit_all) + sum(safe_int(r.get('acertos')) for r in revs_hiit_all)
            t_erros_h = sum(safe_int(q.get('erros')) for q in qs_hiit_all) + sum(safe_int(r.get('erros')) for r in revs_hiit_all)
            t_questoes_h = t_acertos_h + t_erros_h
            
            c1_h, c2_h, c3_h, c4_h = st.columns(4)
            taxa_hiit_geral = (t_acertos_h / t_questoes_h * 100) if t_questoes_h > 0 else 0
            c1_h.metric("Questões HIIT", t_questoes_h)
            c2_h.metric("🟢 Acertos", t_acertos_h)
            c3_h.metric("🔴 Erros", t_erros_h)
            c4_h.markdown(
                f"<div style='padding-top:6px'><div style='font-size:14px;opacity:.75'>🎯 Taxa HIIT</div>"
                f"<div style='font-size:30px;font-weight:700;color:{cor_percentual_acerto(taxa_hiit_geral)}'>{taxa_hiit_geral:.1f}%</div></div>",
                unsafe_allow_html=True
            )
            
            st.divider()
            col_gh1, col_gh2 = st.columns([1, 1.5])
            
            modo_grafico_font = "#f8fafc" if st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' else "#0f172a"
            
            with col_gh1:
                if t_questoes_h > 0: 
                    fig_pie_h = px.pie(names=['Acertos', 'Erros'], values=[t_acertos_h, t_erros_h], hole=0.6, color_discrete_sequence=["#2563eb", '#ef4444'])
                    fig_pie_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie_h, use_container_width=True, config={'displayModeBar': False}, theme=None)
            with col_gh2:
                todas_questoes_hiit_grafico = [{"area": normalizar_area(q.get('area'), mapa_aulas), "acertos": safe_int(q.get('acertos')), "erros": safe_int(q.get('erros'))} for q in qs_hiit_all] + [{"area": normalizar_area(r.get('area'), mapa_aulas), "acertos": safe_int(r.get('acertos')), "erros": safe_int(r.get('erros'))} for r in revs_hiit_all]
                df_rh = pd.DataFrame(todas_questoes_hiit_grafico).dropna(subset=['area'])
                if not df_rh.empty:
                    df_gh = df_rh.groupby('area')[['acertos', 'erros']].sum().reset_index()
                    df_gh['Taxa'] = (df_gh['acertos'] / (df_gh['acertos'] + df_gh['erros'])) * 100
                    df_gh = df_gh.sort_values('Taxa')
                    # A barra mantém a cor da MATÉRIA; o percentual usa exclusivamente a escala de DESEMPENHO.
                    fig_bar_h = go.Figure(go.Bar(
                        x=df_gh['Taxa'], y=df_gh['area'], orientation='h',
                        marker_color=[CORES_AREAS.get(str(a), '#64748b') for a in df_gh['area']],
                        marker_line_width=0,
                        hovertemplate="<b>%{y}</b><br>Aproveitamento: %{x:.1f}%<extra></extra>",
                        cliponaxis=False
                    ))
                    for _, row in df_gh.iterrows():
                        taxa_area_h = float(row['Taxa'])
                        fig_bar_h.add_annotation(
                            x=min(taxa_area_h + 2.2, 108), y=row['area'],
                            text=f"<b>{taxa_area_h:.1f}%</b>", showarrow=False,
                            xanchor='left', yanchor='middle',
                            font=dict(size=12, color=cor_percentual_acerto(taxa_area_h)),
                            bgcolor='rgba(0,0,0,0)', borderwidth=0
                        )
                    fig_bar_h.update_xaxes(range=[0, 110], ticksuffix='%', gridcolor='rgba(128,128,128,.12)')
                    fig_bar_h.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, showlegend=False, margin=dict(t=0, b=0, l=0, r=48))
                    st.plotly_chart(fig_bar_h, use_container_width=True, config={'displayModeBar': False}, theme=None)
                    st.markdown(
                        "<div style='font-size:11px;line-height:1.7'>"
                        "<span style='color:#ef4444;font-weight:700'>● &lt;60%</span> · "
                        "<span style='color:#3b82f6;font-weight:700'>● 60–69%</span> · "
                        "<span style='color:#eab308;font-weight:700'>● 70–80%</span> · "
                        "<span style='color:#22c55e;font-weight:700'>● &gt;80%</span>"
                        "</div>", unsafe_allow_html=True
                    )

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

                # Prévia do desempenho: usa EXATAMENTE a mesma escala de cores
                # que alimenta o cálculo das revisões HIIT.
                total_preview = int(acc) + int(err)
                taxa_preview_pct = (int(acc) / total_preview * 100) if total_preview > 0 else 0.0
                cor_preview = cor_percentual_acerto(taxa_preview_pct)
                if total_preview > 0:
                    if taxa_preview_pct < 60:
                        ciclo_preview = "🔴 HIIT Alerta"
                        intervalo_preview = "7 dias"
                    elif taxa_preview_pct < 80:
                        ciclo_preview = "🟡 HIIT Reforço"
                        intervalo_preview = "14 dias"
                    else:
                        ciclo_preview = "🟢 HIIT Domínio"
                        intervalo_preview = "30 dias"
                else:
                    ciclo_preview = "—"
                    intervalo_preview = "—"

                st.markdown(
                    f"""
                    <div style='margin:10px 0 14px;padding:12px 14px;border:1px solid var(--rp-border);
                                border-radius:12px;background:var(--rp-surface);'>
                        <div style='font-size:11px;color:var(--rp-muted);font-weight:800;text-transform:uppercase;
                                    letter-spacing:.04em;margin-bottom:7px;'>Desempenho que será usado para calcular a revisão</div>
                        <div style='display:flex;align-items:center;gap:12px;flex-wrap:wrap;'>
                            <span style='display:inline-block;min-width:72px;text-align:center;padding:6px 11px;
                                         border-radius:999px;background:{cor_preview} !important;
                                         border:1px solid {cor_preview} !important;color:#fff !important;
                                         -webkit-text-fill-color:#fff !important;font-size:15px;font-weight:900;'>
                                {taxa_preview_pct:.1f}%
                            </span>
                            <span style='font-weight:800;color:var(--rp-text);'>{ciclo_preview}</span>
                            <span style='color:var(--rp-muted);font-size:12px;'>Próxima revisão: <b>{intervalo_preview}</b></span>
                        </div>
                        <div style='font-size:10px;color:var(--rp-muted);margin-top:7px;'>
                            🔴 &lt;60% · 🔵 60–69% · 🟡 70–80% · 🟢 &gt;80%
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
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
                        "Área": normalizar_area(b.get('area'), mapa_aulas),
                        "Subtema": limpar_texto(b.get('subtema')),
                        "Acertos": acertos,
                        "Erros": erros,
                        "% Acertos": porcentagem,
                        "ID": b.get('id')
                    })
                df_h = pd.DataFrame(lista_hiit).sort_values(by="Data_obj", ascending=False).drop(columns=["Data_obj", "ID"], errors='ignore')
                
                def colorir_porcentagem_hiit(val):
                    try:
                        num = float(str(val).replace('%', ''))
                        if num > 80: return 'color: #22c55e !important; font-weight: bold !important;'
                        elif num >= 70: return 'color: #eab308 !important; font-weight: bold !important;'
                        elif num >= 60: return 'color: #3b82f6 !important; font-weight: bold !important;'
                        else: return 'color: #ef4444 !important; font-weight: bold !important;'
                    except: return ''

                # Renderização HTML própria: evita que o CSS global do Streamlit
                # sobrescreva as cores do percentual na tabela HIIT.
                colunas_h = [c for c in df_h.columns if c != "ID"]
                html_h = [
                    "<div style='width:100%;overflow-x:auto;border:1px solid var(--rp-border);border-radius:12px;'>",
                    "<table style='width:100%;border-collapse:collapse;font-size:13px;'>",
                    "<thead><tr>"
                ]
                for c in colunas_h:
                    html_h.append(
                        f"<th style='text-align:left;padding:10px 8px;border-bottom:1px solid var(--rp-border);"
                        f"color:var(--rp-muted);font-weight:700;white-space:nowrap;'>{html.escape(str(c))}</th>"
                    )
                html_h.append("</tr></thead><tbody>")

                for _, row in df_h.iterrows():
                    html_h.append("<tr style='border-bottom:1px solid var(--rp-border);'>")
                    for c in colunas_h:
                        valor = "" if pd.isna(row[c]) else str(row[c])
                        if c == "% Acertos":
                            cor_pct = cor_percentual_acerto(valor)
                            # Badge com fundo sólido: não depende do CSS do Streamlit.
                            conteudo = (
                                f"<span style='display:inline-block;min-width:58px;text-align:center;"
                                f"padding:4px 9px;border-radius:999px;background:{cor_pct} !important;"
                                f"border:1px solid {cor_pct} !important;color:#ffffff !important;"
                                f"-webkit-text-fill-color:#ffffff !important;font-weight:900 !important;"
                                f"line-height:1.2;'>{html.escape(valor)}</span>"
                            )
                        else:
                            conteudo = html.escape(valor)
                        html_h.append(
                            f"<td style='padding:9px 8px;color:var(--rp-text);"
                            f"white-space:nowrap;'>{conteudo}</td>"
                        )
                    html_h.append("</tr>")

                html_h.append("</tbody></table></div>")
                st.markdown("".join(html_h), unsafe_allow_html=True)

                st.markdown(
                    "<div style='font-size:11px;margin-top:8px;color:var(--rp-muted);'>"
                    "<b>Desempenho:</b> "
                    "<span style='display:inline-block;background:#ef4444;color:#fff !important;padding:3px 7px;border-radius:999px;font-weight:800;'> &lt;60% </span> · "
                    "<span style='display:inline-block;background:#3b82f6;color:#fff !important;padding:3px 7px;border-radius:999px;font-weight:800;'> 60–69% </span> · "
                    "<span style='display:inline-block;background:#eab308;color:#fff !important;padding:3px 7px;border-radius:999px;font-weight:800;'> 70–80% </span> · "
                    "<span style='display:inline-block;background:#22c55e;color:#fff !important;padding:3px 7px;border-radius:999px;font-weight:800;'> &gt;80% </span>"
                    "</div>",
                    unsafe_allow_html=True
                )
                    
                st.write("---")
                with st.expander("✏️ Editar ou Excluir Histórico HIIT"):
                    opcoes_edicao_h = {}
                    for q_item in dados_questoes_hiit:
                        data_formatada = formatar_data_br(q_item.get('data'))
                        q_id = str(q_item.get('id', '0000'))
                        chave = f"{data_formatada} | {normalizar_area(q_item.get('area'), mapa_aulas)} - {limpar_texto(q_item.get('subtema'))} (ID: {q_id[:4]})"
                        opcoes_edicao_h[chave] = q_item
                        
                    if opcoes_edicao_h:
                        qh_selec = st.selectbox("Selecione o registro HIIT que deseja alterar:", list(opcoes_edicao_h.keys()))
                        qh_dados = opcoes_edicao_h[qh_selec]
                        qh_id_alvo = str(qh_dados.get('id', '0000'))
                        
                        col_e1h, col_e2h = st.columns(2)
                        novo_ac_h = col_e1h.number_input("Editar Acertos HIIT", min_value=0, value=safe_int(qh_dados.get('acertos')), key=f"ac_h_{qh_id_alvo}")
                        novo_er_h = col_e2h.number_input("Editar Erros HIIT", min_value=0, value=safe_int(qh_dados.get('erros')), key=f"er_h_{qh_id_alvo}")
                        
                        col_btn1h, col_btn2h = st.columns(2)
                        if col_btn1h.button("💾 Salvar Alterações", use_container_width=True, key=f"sv_h_{qh_id_alvo}"):
                            if qh_dados.get('id'):
                                db_update("questoes_hiit", "questoes_hiit", qh_id_alvo, {"acertos": novo_ac_h, "erros": novo_er_h})
                                st.toast("Registro HIIT atualizado com sucesso!", icon="✅")
                                time.sleep(0.5)
                                st.rerun()
                            
                        if col_btn2h.button("🗑️ Excluir Registro", use_container_width=True, key=f"dl_h_{qh_id_alvo}"):
                            if qh_dados.get('id'):
                                db_delete("questoes_hiit", "questoes_hiit", qh_id_alvo)
                                st.toast("Registro HIIT excluído!", icon="🗑️")
                                time.sleep(0.5)
                                st.rerun()

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
                r['area'] = normalizar_area(r.get('area', 'Geral'), mapa_aulas)
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
                    st.markdown(f"**<span style='color:{cor_area(r['area'], mapa_aulas)};'>⬤</span> {r['tema']}**", unsafe_allow_html=True)
                    st.caption(f"Status: {r.get('ciclo','')} | Agendado: {formatar_data_br(r['data_agendada_obj'])}")
                    with st.expander("✅ Registrar Desempenho e Concluir"):
                        with st.form(f"form_concluir_hiit_{r['id']}", clear_on_submit=True):
                            st.info("Registre seus acertos para gerar a próxima meta de revisão.")
                            col_ac, col_er = st.columns(2)
                            acertos_h = col_ac.number_input("🟢 Acertos", min_value=0, key=f"ac_{r['id']}")
                            erros_h = col_er.number_input("🔴 Erros", min_value=0, key=f"er_{r['id']}")
                            
                            if st.form_submit_button("✅ Marcar Concluída e Agendar Próxima", use_container_width=True):
                                original_doc = next((doc for doc in st.session_state.dados["revisoes_hiit"] if str(doc['id']) == str(r['id'])), r)
                                tema_salvar = original_doc.get('tema', r.get('tema'))
                                area_salvar = original_doc.get('area', normalizar_area(r.get('area'), mapa_aulas))
                                
                                db_update("revisoes_hiit", "revisoes_hiit", r['id'], {
                                    "status": "Concluída", 
                                    "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S"),
                                    "acertos": acertos_h,
                                    "erros": erros_h
                                })
                                
                                total_h = acertos_h + erros_h
                                if total_h > 0:
                                    taxa = acertos_h / total_h
                                    if taxa < 0.60:
                                        ciclo_nome = "🔴 HIIT Alerta (7d)"
                                        dias_prox = 7
                                    elif taxa < 0.80:
                                        ciclo_nome = "🟡 HIIT Reforço (14d)"
                                        dias_prox = 14
                                    else:
                                        ciclo_nome = "🟢 HIIT Domínio (30d)"
                                        dias_prox = 30
                                        
                                    nova_data = parse_data(str(get_agora().date())) + timedelta(days=dias_prox)
                                    
                                    doc_rev = db.collection("revisoes_hiit").document()
                                    nova_rev = {
                                        "usuario_id": u_id,
                                        "area": area_salvar,
                                        "tema": tema_salvar,
                                        "ciclo": ciclo_nome,
                                        "data_agendada": str(nova_data),
                                        "status": "Pendente"
                                    }
                                    doc_rev.set(nova_rev)
                                    nova_rev['id'] = doc_rev.id
                                    st.session_state.dados["revisoes_hiit"].append(nova_rev)
                                    
                                    st.toast(f"✅ Concluído! Próxima revisão agendada para {formatar_data_br(nova_data)}", icon="🚀")
                                else:
                                    st.toast("✅ Sessão Concluída!", icon="🚀")
                                    
                                time.sleep(1)
                                st.rerun()

        with aba_notas_hiit:
            if 'hiit_nota_imgs_temp' not in st.session_state: st.session_state.hiit_nota_imgs_temp = []
            
            # GATILHO PARA LIMPAR O CACHE DO NAVEGADOR
            if st.session_state.get('limpar_nova_nota_hiit', False):
                st.session_state.hiit_nota_imgs_temp = []
                st.session_state.limpar_nova_nota_hiit = False
                components.html("<script>Object.keys(window.parent.localStorage).forEach(k => { if(k.startsWith('autosave_nota_')) window.parent.localStorage.removeItem(k); });</script>", height=0)
                st.toast("✅ Anotação salva no Caderno HIIT!", icon="📝")
                
            aba_hn1, aba_hn2 = st.tabs(["➕ Novo Resumo HIIT", "📖 Cadernos HIIT"])
            with aba_hn1:
                st.markdown("### ⚡ Laboratório de Resumos HIIT")
                st.info("💡 **Dica de Ouro:** Suas anotações aqui viram Flashcards Atômicos e Simulados com 1 clique. Seja direto e foque no alto rendimento!")
                
                with st.container(border=True):
                    col_b, col_i = st.columns([1, 2])
                    with col_b:
                        st.markdown("#### 📸 1. Anexos Visuais")
                        st.caption("Tabelas, fluxogramas ou o print do seu erro.")
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
                                    if st.button("🗑️ Remover", key=f"rm_hiit_img_{idx}"):
                                        st.session_state.hiit_nota_imgs_temp.pop(idx)
                                        st.rerun()
                
                st.markdown("#### ✍️ 2. Estruturar o Resumo")
                col_ah, col_sh = st.columns(2)
                area_h = col_ah.selectbox("Grande Área", AREAS_MED, key="sel_bloco_hiit")
                sub_ah = ""
                if area_h == "Clínica Médica":
                    sub_ah = col_sh.selectbox("Subespecialidade", SUB_CM, key="hiit_sub_cm_nota")
                elif area_h == "Cirurgia Geral":
                    sub_ah = col_sh.selectbox("Subespecialidade", SUB_CG, key="hiit_sub_cg_nota")

                sub_h = st.text_input("Tema / Assunto", key="hiit_input_tema")
                
                with st.container(border=True):
                    render_toolbar()
                    txt_h = st.text_area("Anotação / Tópicos Chaves", height=200, key="draft_hiit_txt_key")

                if st.button("💾 Salvar Resumo HIIT", use_container_width=True, type="primary"):
                    if sub_h and txt_h:
                        s_final_h = f"{sub_ah} - {sub_h}" if sub_ah and sub_ah != "Geral" else sub_h
                        db_add("anotacoes_hiit", "anotacoes_hiit", {
                            "usuario_id": u_id, "area": area_h, "subtema": s_final_h, "pontos_chave": txt_h,
                            "imagens_b64": st.session_state.hiit_nota_imgs_temp, "data_criacao": str(hoje)
                        })
                        st.session_state.limpar_nova_nota_hiit = True
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
                                                                prompt_fc = f"""[SISTEMA NÍVEL 5] Transforme TODA a anotação abaixo em flashcards. Crie um flashcard para CADA tópico, conceito ou detalhe presente no texto, garantindo que absolutamente NADA fique de fora. Crie um objeto JSON: {{"flashcards": [{{"frente": "...", "verso": "..."}}]}}
                                                                Retorne APENAS o JSON puro. Não explique.
                                                                Resumo: {nh.get('pontos_chave', '')}"""
                                                                r_fc = chamar_ia_json_estrito(
                                                                    client_ia,
                                                                    modelo=MODELO_TEXTO,
                                                                    messages=[{"role": "user", "content": prompt_fc}],
                                                                    max_completion_tokens=2000
                                                                )
                                                                fcs = extrair_json_seguro(r_fc.choices[0].message.content).get("flashcards", [])
                                                                if fcs:
                                                                    batch = db.batch()
                                                                    for fc in fcs:
                                                                        doc_ref = db.collection("flashcards_hiit").document()
                                                                        n_fc = {"usuario_id": u_id, "area": normalizar_area(nh.get('area'), mapa_aulas), "tema": limpar_texto(nh.get('subtema')), "frente": fc.get('frente'), "verso": fc.get('verso'), "path_imagem": None, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                                                                        batch.set(doc_ref, n_fc)
                                                                        n_fc["id"] = doc_ref.id
                                                                        st.session_state.dados["flashcards_hiit"].append(n_fc)
                                                                    batch.commit()
                                                                    st.success(f"✅ {len(fcs)} Flashcards HIIT gerados e adicionados ao deck HIIT!")
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
                                                                r_q = chamar_ia(client_ia, modelo=MODELO_TEXTO, messages=[{"role": "user", "content": prompt_q}], temperature=0.4, max_tokens=3000)
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
                                            edit_ah = col_eah.selectbox("Grande Área", AREAS_MED, index=AREAS_MED.index(normalizar_area(nh.get('area'), mapa_aulas)) if normalizar_area(nh.get('area'), mapa_aulas) in AREAS_MED else 0, key=f"ea_h_{id_nh}")
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
                                                
                                                with st.container(border=True):
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

        with aba_fc_hiit:
            st.markdown("### 📚 Modo Estudo - Flashcards HIIT")
            
            # --- LÓGICA DE ORGANIZAÇÃO EM CASCATA ---
            cards_vencidos = [d for d in dados_flashcards_hiit if parse_data(d.get('data_prox_revisao')) <= hoje]
            
            if not cards_vencidos:
                st.success("🎉 Você zerou o deck HIIT de hoje. Parabéns!")
            else:
                # Agrupa os cartões vencidos por Grande Área e depois por Tema
                deck_organizado = {}
                for card in cards_vencidos:
                    area = normalizar_area(card.get('area', 'Geral'), mapa_aulas)
                    tema = limpar_texto(card.get('tema', 'Sem Tema'))
                    if area not in deck_organizado: deck_organizado[area] = {}
                    if tema not in deck_organizado[area]: deck_organizado[area][tema] = []
                    deck_organizado[area][tema].append(card)
                
                areas_pendentes = sorted(list(deck_organizado.keys()))
                abas_areas_fc = st.tabs(areas_pendentes)
                
                for idx_aba, area_atual in enumerate(areas_pendentes):
                    with abas_areas_fc[idx_aba]:
                        st.markdown(f"#### <span style='color:{CORES_AREAS.get(area_atual, '#64748b')};'>⬤</span> Cartões de {area_atual}", unsafe_allow_html=True)
                        temas_da_area = sorted(list(deck_organizado[area_atual].keys()))
                        
                        # Pegamos sempre o primeiro cartão do primeiro tema disponível nesta área
                        tema_ativo = temas_da_area[0]
                        cartoes_do_tema = deck_organizado[area_atual][tema_ativo]
                        c_data_h = cartoes_do_tema[0]
                        c_data_id_h = str(c_data_h.get("id", "000"))
                        
                        st.caption(f"**Progresso na Área:** Restam {sum(len(deck_organizado[area_atual][t]) for t in temas_da_area)} cartões hoje.")
                        
                        with st.container(border=True):
                            st.markdown(f"**Tema:** {tema_ativo}")
                            st.markdown(f"### ❔ {c_data_h.get('frente', '')}")
                            
                            chave_ans = f"ans_hiit_{c_data_id_h}"
                            if chave_ans not in st.session_state: st.session_state[chave_ans] = False
                            
                            if st.button("Revelar Resposta", key=f"rev_ans_hiit_{c_data_id_h}"): 
                                st.session_state[chave_ans] = True
                                st.rerun()
                                
                            if st.session_state[chave_ans]:
                                st.info(f"**💡 Resposta:** {c_data_h.get('verso', '')}")
                                b1_h, b2_h, b3_h = st.columns(3)
                                
                                def avaliar_hiit(peso, cid=c_data_id_h, c_dict=c_data_h, k_ans=chave_ans): 
                                    facil, interv = float(c_dict.get('facilidade', 2.5)), safe_int(c_dict.get('intervalo'))
                                    if peso == 'err': ni, nf = 1, max(1.3, facil - 0.2)
                                    elif peso == 'bom': ni, nf = max(1, int((interv or 1) * facil)), facil
                                    else: ni, nf = max(1, int((interv or 1) * facil * 1.3)), facil + 0.15
                                    db_update("flashcards_hiit", "flashcards_hiit", cid, {"intervalo": ni, "facilidade": nf, "data_prox_revisao": str(get_agora().date() + timedelta(days=ni))})
                                    st.session_state[k_ans] = False
                                    
                                if b1_h.button("🔴 Errei (1d)", use_container_width=True, key=f"btn_err_h_{c_data_id_h}"): 
                                    avaliar_hiit('err')
                                    st.rerun()
                                if b2_h.button("🟡 Bom", use_container_width=True, key=f"btn_bom_h_{c_data_id_h}"): 
                                    avaliar_hiit('bom')
                                    st.rerun()
                                if b3_h.button("🟢 Fácil", use_container_width=True, key=f"btn_facil_h_{c_data_id_h}"): 
                                    avaliar_hiit('facil')
                                    st.rerun()
            
            st.divider()
            with st.expander("Gerenciar Flashcards HIIT"):
                if dados_flashcards_hiit:
                    df_fcs_h = pd.DataFrame(dados_flashcards_hiit)
                    st.dataframe(df_fcs_h[['area', 'tema', 'frente', 'data_prox_revisao']], use_container_width=True)
                    del_fc_h = st.selectbox("Selecione para excluir:", [f"{f.get('id')} | {f.get('frente')[:30]}..." for f in dados_flashcards_hiit], key="del_fc_hiit_sel")
                    if st.button("🗑️ Excluir Flashcard", key="btn_del_fc_h"):
                        db_delete("flashcards_hiit", "flashcards_hiit", del_fc_h.split(" | ")[0])
                        st.toast("Excluído!", icon="🗑️")
                        time.sleep(0.5)
                        st.rerun()

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
                        "Área": normalizar_area(b.get('area'), mapa_aulas),
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
                        chave = f"{data_formatada} | {normalizar_area(q_item.get('area'), mapa_aulas)} - {limpar_texto(q_item.get('subtema'))} (ID: {q_id[:4]})"
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
                erro_escolhido = st.selectbox("Escolha um conceito que você errou:", reversed([f"{normalizar_area(b.get('area'), mapa_aulas)} - {limpar_texto(b.get('subtema'))}: {b.get('conceito_chave')}" for b in baterias_erros]))
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
                t_str = f"{normalizar_area(q.get('area'), mapa_aulas)} - {limpar_texto(q.get('subtema'))}"
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
                        st.markdown(f"<span style='color:{CORES_AREAS.get(normalizar_area(c_data.get('area', 'Geral'), mapa_aulas), '#64748b')};'>⬤</span> **{normalizar_area(c_data.get('area', 'Geral'), mapa_aulas)}** | Tema: {limpar_texto(c_data.get('tema', 'Sem Tema'))}", unsafe_allow_html=True)
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
                    removidas_crono = remover_aula_do_cronograma(a, n_aula["tema"])
                    if removidas_crono:
                        st.toast(f"Aula registrada! {removidas_crono} item(ns) removido(s) do cronograma.", icon="📚")
                    else:
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
                    st.markdown(f"#### <span style='color:{cor_area(al.get('area'), mapa_aulas)};'>⬤</span> {limpar_texto(al.get('tema', 'Aula sem título'))}", unsafe_allow_html=True)
                    st.caption(f"{normalizar_area(al.get('area', ''), mapa_aulas)} | Data: {formatar_data_br(al.get('data_aula'))}")

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

    elif menu == "📝 Anotações Rápidas":
        st.header("Caderno de Resumos e Anotações")
        
        # INICIALIZAÇÃO DE ESTADOS
        if 'nota_imgs_temp' not in st.session_state: st.session_state.nota_imgs_temp = []
            
        # GATILHO PARA LIMPAR O CACHE DO NAVEGADOR
        if st.session_state.get('limpar_nova_nota', False):
            st.session_state.nota_imgs_temp = []
            st.session_state.limpar_nova_nota = False
            components.html("<script>Object.keys(window.parent.localStorage).forEach(k => { if(k.startsWith('autosave_nota_')) window.parent.localStorage.removeItem(k); });</script>", height=0)
            st.toast("✅ Anotação salva com sucesso!", icon="📝")
            
        aba_nova, aba_lista = st.tabs(["➕ Nova Anotação", "📖 Meus Resumos"])
        
        with aba_nova:
            st.markdown("### ⚡ Laboratório de Resumos")
            st.info("💡 **Dica de Ouro:** Suas anotações aqui viram Flashcards Atômicos e Simulados com 1 clique. Seja direto e foque no alto rendimento!")
            
            with st.container(border=True):
                col_btn, col_img = st.columns([1, 2])
                with col_btn:
                    st.markdown("#### 📸 1. Anexos Visuais")
                    st.caption("Tabelas, fluxogramas ou o print do seu erro.")
                    if paste_image_button is not None:
                        res_paste_nota = paste_image_button(
                            label="CLIQUE AQUI E APERTE Ctrl+V",
                            background_color="#2563eb",
                            hover_background_color="#1d4ed8",
                            key="paste_nota_nova"
                        )
                        if res_paste_nota.image_data is not None:
                            img_b64 = otimizar_imagem_para_api(res_paste_nota.image_data, max_size=1024)
                            if img_b64 and img_b64 not in st.session_state.nota_imgs_temp:
                                st.session_state.nota_imgs_temp.append(img_b64)
                                st.rerun()
                    else:
                        st.warning("Biblioteca de colar imagem não detectada.")
                        
                with col_img:
                    if st.session_state.nota_imgs_temp:
                        st.write(f"**{len(st.session_state.nota_imgs_temp)} imagem(ns) anexada(s):**")
                        cols = st.columns(3)
                        for idx, img_b64 in enumerate(st.session_state.nota_imgs_temp):
                            with cols[idx % 3]:
                                if isinstance(img_b64, str) and len(img_b64) > 50:
                                    try:
                                        st.image(base64.b64decode(img_b64), use_container_width=True)
                                    except: pass
                                if st.button("🗑️ Remover", key=f"rmv_img_nota_{idx}"):
                                    st.session_state.nota_imgs_temp.pop(idx)
                                    st.rerun()

            st.markdown("#### ✍️ 2. Estruturar o Resumo")
            
            col_a, col_s = st.columns(2)
            a = col_a.selectbox("Grande Área", AREAS_MED, key="n_area_nova")
            sub_a = ""
            if a == "Clínica Médica":
                sub_a = col_a.selectbox("Subespecialidade", SUB_CM, key="n_sub_cm")
            elif a == "Cirurgia Geral":
                sub_a = col_a.selectbox("Subespecialidade", SUB_CG, key="n_sub_cg")
                
            with st.form("form_nova_nota", clear_on_submit=True):
                s = st.text_input("Subtema (Ex: Insuficiência Cardíaca)")
                
                with st.container(border=True):
                    render_toolbar()
                    # O state temporário mantém o texto mesmo se cair a internet
                    if "draft_nota_txt" not in st.session_state: st.session_state.draft_nota_txt = ""
                    p = st.text_area("Pontos Chave / Resumo", height=200, value=st.session_state.draft_nota_txt, help="Anote aqui os tópicos mais relevantes. Use os comandos de formatação acima.")
                    st.session_state.draft_nota_txt = p # Salva no state on the fly
                
                if st.form_submit_button("💾 Salvar Anotação", use_container_width=True, type="primary"):
                    if s and p:
                        s_final = f"{sub_a} - {s}" if sub_a and sub_a != "Geral" else s
                        db_add("anotacoes", "anotacoes", {
                            "usuario_id": u_id,
                            "area": a,
                            "subtema": s_final,
                            "pontos_chave": p,
                            "imagens_b64": st.session_state.nota_imgs_temp,
                            "data_criacao": str(hoje)
                        })
                        st.session_state.limpar_nova_nota = True
                        st.session_state.draft_nota_txt = "" # Limpa o rascunho apenas após o save final
                        time.sleep(0.5)
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
                
                # --- SEPARAR POR ÁREA EM ABAS (NOVO LAYOUT) ---
                areas_presentes = sorted(list(set([normalizar_area(n.get('area', 'Geral'), mapa_aulas) for n in notas_exibir])))
                
                if not notas_exibir:
                    st.warning("Nenhuma anotação encontrada para esta pesquisa.")
                else:
                    abas_areas = st.tabs(areas_presentes)
                    for i, area_tab in enumerate(areas_presentes):
                        with abas_areas[i]:
                            notas_area = [n for n in notas_exibir if normalizar_area(n.get('area', 'Geral'), mapa_aulas) == area_tab]
                            
                            for nota in notas_area:
                                nota_id = str(nota.get('id', '0000'))
                                subtema_str = limpar_texto(nota.get('subtema'))
                                data_str = formatar_data_br(nota.get('data_criacao'))
                                
                                # --- NOTA COMPACTA (EXPANDER) ---
                                with st.expander(f"📝 {subtema_str} - {data_str}"):
                                    c_del1, c_del2 = st.columns([0.85, 0.15])
                                    with c_del2:
                                        if st.button("🗑️ Excluir", key=f"del_nota_{nota_id}", use_container_width=True):
                                            db_delete("anotacoes", "anotacoes", nota_id)
                                            st.toast("Anotação excluída!", icon="🗑️")
                                            st.rerun()
                                    
                                    # Renderização permitindo HTML e Markdown Nativo (Títulos e Tópicos)
                                    conteudo_nota = nota.get('pontos_chave', '')
                                    st.markdown(f"<div style='border-left: 3px solid {cor_area(nota.get('area'), mapa_aulas)}; padding-left: 15px; margin-top: 10px; margin-bottom: 20px;'>\n\n{conteudo_nota}\n\n</div>", unsafe_allow_html=True)
                                    
                                    # Exibindo as imagens de forma organizada (Grade)
                                    imgs_exibir = list(nota.get('imagens_b64', []))
                                    if nota.get('imagem_b64') and nota.get('imagem_b64') not in imgs_exibir:
                                        imgs_exibir.insert(0, nota['imagem_b64'])
                                        
                                    if imgs_exibir:
                                        st.write("") # Espaçamento
                                        cols_view = st.columns(max(1, min(len(imgs_exibir), 4)))
                                        for idx_v, img_b64_v in enumerate(imgs_exibir):
                                            with cols_view[idx_v % 4]:
                                                if isinstance(img_b64_v, str) and len(img_b64_v) > 50:
                                                    try: st.image(base64.b64decode(img_b64_v), use_container_width=True)
                                                    except: pass
                                    
                                    st.divider()
                                    
                                    # --- BOTÃO DE EDITAR INDIVIDUAL E SEGURO ---
                                    if st.session_state.get('nota_em_edicao') != nota_id:
                                        if st.button("✏️ Editar esta Anotação", key=f"btn_abrir_edit_{nota_id}"):
                                            st.session_state.nota_em_edicao = nota_id
                                            st.rerun()
                                    else:
                                        if st.button("❌ Cancelar Edição", key=f"btn_cancel_edit_{nota_id}"):
                                            st.session_state.nota_em_edicao = None
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
                                                    key=f"paste_edit_{nota_id}" 
                                                )
                                                if res_paste_edit.image_data is not None:
                                                    img_eb64 = otimizar_imagem_para_api(res_paste_edit.image_data, max_size=1024)
                                                    if img_eb64 and img_eb64 not in imgs_exibir:
                                                        imgs_exibir.append(img_eb64)
                                                        db_update("anotacoes", "anotacoes", nota_id, {"imagens_b64": imgs_exibir, "imagem_b64": firestore.DELETE_FIELD})
                                                        st.rerun()
                                        with col_eimg:
                                            if imgs_exibir:
                                                cols_e = st.columns(max(1, min(len(imgs_exibir), 3)))
                                                for idx_e, img_b64_e in enumerate(imgs_exibir):
                                                    with cols_e[idx_e % 3]:
                                                        if isinstance(img_b64_e, str) and len(img_b64_e) > 50:
                                                            try: st.image(base64.b64decode(img_b64_e), use_container_width=True)
                                                            except: pass
                                                        if st.button("🗑️ Remover", key=f"rmv_medit_{nota_id}_{idx_e}"):
                                                            imgs_exibir.pop(idx_e)
                                                            db_update("anotacoes", "anotacoes", nota_id, {"imagens_b64": imgs_exibir, "imagem_b64": firestore.DELETE_FIELD})
                                                            st.rerun()

                                        st.markdown("#### ✍️ Editar Texto")
                                        
                                        col_ea, col_es = st.columns(2)
                                        edit_a = col_ea.selectbox("Grande Área", AREAS_MED, index=AREAS_MED.index(normalizar_area(nota.get('area'), mapa_aulas)) if normalizar_area(nota.get('area'), mapa_aulas) in AREAS_MED else 0, key=f"ea_{nota_id}")
                                        sub_ea = ""
                                        if edit_a == "Clínica Médica":
                                            sub_ea = col_ea.selectbox("Subespecialidade", SUB_CM, key=f"sub_ea_cm_{nota_id}")
                                        elif edit_a == "Cirurgia Geral":
                                            sub_ea = col_ea.selectbox("Subespecialidade", SUB_CG, key=f"sub_ea_cg_{nota_id}")
                                        
                                        # Limpar a subespecialidade se já vier no texto
                                        s_puro = nota.get('subtema', '')
                                        if " - " in s_puro and s_puro.split(" - ")[0] in SUB_CM:
                                            s_puro = " - ".join(s_puro.split(" - ")[1:])
                                        elif " - " in s_puro and s_puro.split(" - ")[0] in SUB_CG:
                                            s_puro = " - ".join(s_puro.split(" - ")[1:])
                                            
                                        with st.form(f"form_edicao_{nota_id}", clear_on_submit=False):
                                            edit_s = st.text_input("Subtema", value=s_puro)
                                            
                                            with st.container(border=True):
                                                render_toolbar()
                                                edit_p = st.text_area("Pontos Chave / Resumo", value=nota.get('pontos_chave', ''), height=200)
                                            
                                            if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                                                if edit_s and edit_p:
                                                    edit_s_final = f"{sub_ea} - {edit_s}" if sub_ea and sub_ea != "Geral" else edit_s
                                                    db_update("anotacoes", "anotacoes", nota_id, {"area": edit_a, "subtema": edit_s_final, "pontos_chave": edit_p})
                                                    st.session_state.nota_em_edicao = None
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

    elif menu == "📅 Agenda de Revisões":
        st.header("Organizador Adaptativo de Ciclos")
        
        todas_pendentes_cru = [r for r in dados_revisoes if str(r.get('status', '')).lower() in ['pendente', 'pendentes']]
        hoje_revs = [r for r in todas_pendentes_cru if parse_data(r.get('data_agendada')) == hoje]
        qtd_hoje = len(hoje_revs)
        futuras = sorted([r for r in todas_pendentes_cru if parse_data(r.get('data_agendada')) > hoje], key=lambda x: parse_data(x.get('data_agendada')))
        prox_data_str = formatar_data_br(futuras[0].get('data_agendada')) if futuras else "Nenhuma agendada"

        st.markdown("### 🎯 Seu Painel de Missões")
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            st.info(f"**🗓️ Para Hoje:** Você tem **{qtd_hoje}** revisões agendadas.")
        with col_st2:
            st.success(f"**⏭️ Próxima Futura:** {prox_data_str}")
        st.divider()
        
        aba_pendentes, aba_historico = st.tabs(["📝 Revisões Pendentes", "✅ Histórico"])
        
        with aba_pendentes:
            c_v, c_o = st.columns(2)
            visao = c_v.radio("Filtro Rápido:", ["📆 Para Hoje", "🗓️ Próximos 7 Dias", "♾️ Todas Futuras", "🔎 Data Específica"], horizontal=True)
            ordem = c_o.radio("Ordem:", ["🚨 Urgência", "🆕 Mais Atuais", "🕰️ Mais Antigas"], horizontal=True)
            
            data_filtro_exata = None
            if visao == "🔎 Data Específica": data_filtro_exata = st.date_input("Filtrar para o dia:", hoje, format="DD/MM/YYYY")
            
            desempenho_por_tema = {}
            for q in dados_questoes:
                t_str = limpar_texto(q.get('subtema', ''))
                if t_str not in desempenho_por_tema: desempenho_por_tema[t_str] = {"ac": 0, "er": 0}
                desempenho_por_tema[t_str]["ac"] += safe_int(q.get('acertos', 0))
                desempenho_por_tema[t_str]["er"] += safe_int(q.get('erros', 0))
            
            todas_pendentes = []
            for r_orig in dados_revisoes:
                if str(r_orig.get('status', '')).lower() not in ['pendente', 'pendentes']: continue
                r = dict(r_orig)
                r['data_agendada_obj'] = parse_data(r.get('data_agendada'))
                r['tema'] = r.get('tema') or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('tema', 'Sem título')
                r['area'] = normalizar_area(r.get('area'), mapa_aulas) or mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('area', 'Geral')
                r['data_aula_obj'] = parse_data(mapa_aulas.get(str(r.get('aula_id', '')).strip(), {}).get('data_aula')) if r.get('aula_id') else r['data_agendada_obj']
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

            if visao == "🔎 Data Específica" and data_filtro_exata:
                lista_pendentes = [r for r in todas_pendentes if r['data_agendada_obj'] == data_filtro_exata]
            elif visao == "📆 Para Hoje":
                lista_pendentes = [r for r in todas_pendentes if r['data_agendada_obj'] == hoje]
            elif visao == "🗓️ Próximos 7 Dias":
                lista_pendentes = [r for r in todas_pendentes if hoje <= r['data_agendada_obj'] <= (hoje + timedelta(days=7))]
            else:
                lista_pendentes = [r for r in todas_pendentes if r['data_agendada_obj'] >= hoje]
            
            if "Atuais" in ordem: lista_pendentes.sort(key=lambda x: x['data_aula_obj'], reverse=True)
            elif "Antigas" in ordem: lista_pendentes.sort(key=lambda x: x['data_aula_obj'])
            else: lista_pendentes.sort(key=lambda x: x['data_agendada_obj'])

            if not lista_pendentes: st.success("🎉 Tudo em dia para os filtros selecionados!")
            
            for r in lista_pendentes:
                tema_card = limpar_texto(r['tema'])
                pct_str = "--"
                cor_pct = "#94a3b8"
                if tema_card in desempenho_por_tema:
                    ac = desempenho_por_tema[tema_card]['ac']
                    er = desempenho_por_tema[tema_card]['er']
                    tot = ac + er
                    if tot > 0:
                        pct = ac / tot
                        pct_str = f"{pct*100:.0f}%"
                        cor_pct = cor_percentual_acerto(pct * 100)

                with st.container(border=True):
                    c1_card, c2_card = st.columns([0.8, 0.2])
                    with c1_card:
                        st.markdown(f"<h5 style='margin-bottom:0;'><span style='color:{cor_area(r['area'], mapa_aulas)};'>⬤</span> {tema_card}</h5>", unsafe_allow_html=True)
                        st.caption(f"Ciclo: **{r.get('ciclo','')}** | Data: **{formatar_data_br(r['data_agendada_obj'])}**")
                    with c2_card:
                        st.markdown(f"<div style='text-align:right;'><span style='font-size:11px; color:#94a3b8;'>Sua Taxa de Acertos</span><br><strong style='font-size:18px; color:{cor_pct};'>{pct_str}</strong></div>", unsafe_allow_html=True)
                        
                    with st.expander("✅ Concluir Revisão"):
                        with st.form(f"f_{r['id']}", clear_on_submit=True):
                            col1, col2, col3 = st.columns(3)
                            q = col1.number_input("Questões Feitas", 0)
                            e = col2.number_input("Erros", 0, max_value=max(q,0))
                            f = col3.number_input("Flashcards Lidos", 0)
                            if st.form_submit_button("✅ Marcar Concluída", use_container_width=True):
                                db_update("revisoes", "revisoes", r['id'], {"status": "Concluída", "questoes_feitas": q, "erros": e, "acertos": q-e, "flashcards_feitas": f, "data_conclusao": get_agora().strftime("%Y-%m-%d %H:%M:%S")})
                                st.toast("✅ Revisão Concluída!", icon="🚀")
                                time.sleep(0.5)
                                st.rerun()

        with aba_historico:
            conc_docs = [d for d in dados_revisoes if str(d.get('status', '')).lower() in ["concluída", "concluida"]]
            if conc_docs:
                dados_h = []
                for d in conc_docs:
                    tema = d.get('tema') or mapa_aulas.get(str(d.get('aula_id', '')).strip(), {}).get('tema', 'Sem título')
                    tema = limpar_texto(tema)
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
                    
                    modo_grafico_font = "#f8fafc" if st.session_state.get('user_settings', {}).get('tema_modo', 'Escuro') == 'Escuro' else "#0f172a"
                    
                    with c1g: 
                        fig1 = px.bar(df_ag, x="Data", y=["Acertos", "Erros"], barmode="group", color_discrete_map={"Acertos":"#22c55e", "Erros":"#ef4444"})
                        fig1.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False}, theme=None)
                    with c2g: 
                        fig2 = px.bar(df_ag, x="Data", y="Cards")
                        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color=modo_grafico_font, margin=dict(t=0, b=0, l=0, r=0))
                        st.plotly_chart(fig2, use_container_width=True, config={'displayModeBar': False}, theme=None)
                    
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
                                db_update("revisoes", "revisoes", opcoes_desfazer[rev_selecionada], {"status": "Pendente", "questoes_feitas": 0, "erros": 0, "acertos": 0, "flashcards_feitas": 0, "data_conclusao": None})
                                st.toast("Revisão desfeita!", icon="⏪")
                                time.sleep(0.5)
                                st.rerun()

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
                        for col in ["aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "focus_sessoes", "materiais", "cronogramas", "anotacoes", "questoes_hiit", "revisoes_hiit", "anotacoes_hiit", "flashcards_hiit"]:
                            for doc in db.collection(col).where(filter=FieldFilter("usuario_id", "==", uid)).get(): db.collection(col).document(doc.id).delete()
                        db.collection("usuarios").document(uid).delete(); invalidar_cache(); st.rerun()
                    else: st.warning("Você não pode banir a si mesmo.")
            
            st.divider()
            st.subheader("📦 Exportação de Backup em Nuvem")
            if st.button("Baixar Dados (JSON)"):
                with st.spinner("Coletando tudo..."):
                    backup_data = {colecao: {d.id: d.to_dict() for d in db.collection(colecao).get()} for colecao in ["usuarios", "aulas", "revisoes", "flashcards", "questoes_sessoes", "simulados", "cronogramas", "anotacoes", "questoes_hiit", "revisoes_hiit", "anotacoes_hiit", "flashcards_hiit"]}
                    st.download_button(label="📥 Baixar snapshot_nuvem.json", data=json.dumps(backup_data, default=str, indent=4), file_name="snapshot_nuvem.json", mime="application/json")
        except Exception as e:
            st.error(f"Erro Admin: {e}")
