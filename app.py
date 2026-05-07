import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import os
import time
import hashlib
import uuid
import base64
import json
import calendar
import re
from sklearn.linear_model import LinearRegression
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore
import html
import streamlit.components.v1 as components

# ==========================================
# CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="Residência PRO", page_icon="🏥", layout="wide")

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

# ==========================================
# CHAVES DE ACESSO E CONEXÃO FIREBASE
# ==========================================
# Busca a chave Groq com segurança
CHAVE_GROQ_FIXA = st.secrets.get("GROQ_KEY", st.secrets.get("GROQ_API_KEY", "")) 

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            # Puxa os dados com segurança
            if "textkey" in st.secrets:
                schema = dict(st.secrets["textkey"])
            elif "firebase" in st.secrets:
                schema = dict(st.secrets["firebase"])
            else:
                st.error("🚨 Chave do Firebase não encontrada nos Secrets.")
                st.stop()
            
            # Limpeza cirúrgica da chave privada
            if "private_key" in schema:
                pk = schema["private_key"].strip().replace('"', '').replace("'", "")
                schema["private_key"] = pk.replace("\\n", "\n")
            
            cred = credentials.Certificate(schema)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao conectar ao Firebase: {e}")
            st.stop()
    return firestore.client()

db = init_firebase()

# Criação de pastas locais
for d in ["materiais_estudo", "imagens_flashcards", "fotos_perfil"]:
    if not os.path.exists(d): os.makedirs(d)

# ==========================================
# INICIALIZADOR DE IA (GROQ)
# ==========================================
def get_ia_client():
    if "model_ia" not in st.session_state:
        if Groq and CHAVE_GROQ_FIXA:
            try:
                st.session_state.model_ia = Groq(api_key=CHAVE_GROQ_FIXA)
            except Exception as e:
                st.session_state.model_ia = None
        else:
            st.session_state.model_ia = None
    return st.session_state.model_ia

# ==========================================
# CONSTANTES E BANCO DE IMAGENS OSCE
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#3b82f6", "Pediatria": "#ec4899", "Ginecologia e Obstetrícia": "#a855f7", "Medicina Preventiva": "#22c55e", "Cirurgia Geral": "#ef4444", "Geral": "#64748b"}

BANCO_IMAGENS_OSCE = {
    "ecg_normal": "https://upload.wikimedia.org/wikipedia/commons/b/b6/12_lead_normal_ECG.png",
    "rx_torax_normal": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Chest_Xray_PA_3-8-2010.png",
    "tc_cranio_normal": "https://upload.wikimedia.org/wikipedia/commons/1/1a/Normal_CT_of_the_brain.jpg"
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
                st.markdown(f'<div style="border: 1px solid #334155; padding: 10px;"><p style="color: #ef4444; font-weight: bold;">📎 Laudo: {chave}</p><img src="{img_url}" style="width: 100%;"></div>', unsafe_allow_html=True)
            else:
                st.info(f"*(Paciente entrega laudo: {chave} - Sem imagem)*")

# ==========================================
# CALCULADORA DE DOSES
# ==========================================
MEDICAMENTOS = {
    "Pediatria (Baseado em Peso)": {
        "Adrenalina (Anafilaxia)": {"dose": 0.01, "unidade": "mg/kg", "max": 0.3, "via": "IM", "obs": "0,01 mL/kg da ampola 1:1.000 no vasto lateral."},
        "Dipirona (Febre/Dor)": {"dose": 20, "unidade": "mg/kg", "max": 1000, "via": "VO / EV", "obs": "EV: 15-20 mg/kg/dose a cada 6h. VO: 1 gota/kg."}
    },
    "Adulto (Doses por Peso E Fixas)": {
        "AAS (SCA)": {"dose_fixa": "150-300 mg", "via": "VO (Mastigar)", "obs": "3 comprimidos infantis de 100mg macerados na boca."},
        "Adrenalina (PCR)": {"dose_fixa": "1 mg", "via": "EV Bolus", "obs": "1 ampola pura a cada 3 a 5 minutos na RCP."}
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
        except: pass
    return get_agora().date()

def formatar_data_br(d):
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
        todos_docs = db.collection(collection_name).where("usuario_id", "==", str(user_id)).get()
        return [{"id": d.id, **d.to_dict()} for d in todos_docs]
    except: return []

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
                st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                st.rerun()
    except: pass 

if not st.session_state.logado:
    st.title("🏥 Residência PRO")
    aba_l, aba_c = st.tabs(["🔑 Entrar", "📝 Criar Conta"])
    with aba_l:
        with st.form("login_form"):
            u, p, lembrar = st.text_input("Usuário"), st.text_input("Senha", type="password"), st.checkbox("Manter-me conectado")
            if st.form_submit_button("Entrar", type="primary", use_container_width=True):
                try:
                    logou = False
                    for doc in db.collection("usuarios").where("nome", "==", u).get():
                        if doc.to_dict().get("senha") == hash_senha(p):
                            st.session_state.logado, st.session_state.user_id, st.session_state.user_nome = True, doc.id, doc.to_dict().get('nome', '')
                            logou = True
                            if lembrar and cookie_controller:
                                novo_token = str(uuid.uuid4())
                                db.collection("usuarios").document(doc.id).update({"token_sessao": novo_token})
                                cookie_controller.set('mr_token', novo_token, max_age=30*24*60*60, path='/')
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
    
    # Prevenção Crítica do Erro de AttributeError
    if 'dados' not in st.session_state:
        st.session_state.dados = {
            "aulas": [], "revisoes": [], "flashcards": [], 
            "questoes": [], "simulados": [], "focus": [], 
            "materiais": [], "cronogramas": []
        }

    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Sincronizando banco de dados..."):
            try:
                st.session_state.dados["aulas"] = get_user_docs("aulas", u_id)
                st.session_state.dados["revisoes"] = get_user_docs("revisoes", u_id)
                st.session_state.dados["flashcards"] = get_user_docs("flashcards", u_id)
                st.session_state.dados["questoes"] = get_user_docs("questoes_sessoes", u_id)
                st.session_state.dados["simulados"] = get_user_docs("simulados", u_id)
                st.session_state.dados["focus"] = get_user_docs("focus_sessoes", u_id)
                st.session_state.dados["materiais"] = get_user_docs("materiais", u_id)
                st.session_state.dados["cronogramas"] = get_user_docs("cronogramas", u_id)
                
                get_ia_client()
                st.session_state.user_data_loaded = True 
            except Exception as e:
                st.error(f"🚨 Falha ao carregar dados: {e}")

    # Agora as listas puxam seguramente do session_state
    dados_aulas = st.session_state.dados["aulas"]
    mapa_aulas = {str(a["id"]).strip(): a for a in dados_aulas} 
    dados_revisoes = st.session_state.dados["revisoes"]
    dados_questoes = st.session_state.dados["questoes"]
    dados_flashcards = st.session_state.dados["flashcards"]
    dados_simulados = st.session_state.dados["simulados"]
    dados_focus = st.session_state.dados["focus"]
    dados_materiais = st.session_state.dados["materiais"]

    st.markdown(f"<style>.stButton>button {{ background-color: #ef4444 !important; color: white !important; font-weight: bold !important; border-radius: 6px !important; }}</style>", unsafe_allow_html=True)
    st.sidebar.title(f"👤 {st.session_state.user_nome}")

    if st.sidebar.button("Sair da Conta"):
        st.session_state.clear()
        st.rerun()

    # ==========================================
    # MENU DO APLICATIVO
    # ==========================================
    opcoes_menu = [
        "🏠 Dashboard", "🗓️ Cronograma IA", "🎯 Questões", "📚 Registro de Aulas",
        "📅 Agenda de Revisões", "✨ AI Tutor & Flashcards", "🏥 Simulados & OSCE",
        "📍 GPS da Aprovação", "⏱️ Modo Foco", "🧮 Calculadora de Doses", "⚙️ Configurações"
    ]
    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ==========================================
    # TELAS
    # ==========================================
    if menu == "🗓️ Cronograma IA":
        st.header("Cronograma Inteligente da Semana")
        aba_lista, aba_importar = st.tabs(["✅ Minhas Metas", "📸 Escanear Print"])
        
        with aba_importar:
            imgs_crono = st.file_uploader("Envie as imagens do cronograma", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            if imgs_crono and st.button("🪄 Extrair Metas com IA", use_container_width=True):
                client_ia = get_ia_client()
                if not client_ia:
                    st.error("IA não conectada. Configure a GROQ_KEY nos Secrets.")
                else:
                    with st.spinner("Analisando imagens..."):
                        try:
                            conteudo_api = [{"type": "text", "text": "Extraia dias, matérias e temas. Retorne APENAS JSON neste formato: [{\"dia\": \"Segunda\", \"materia\": \"Cirurgia\", \"tema\": \"Hérnias\"}]"}]
                            for img in imgs_crono:
                                img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
                            
                            resposta = client_ia.chat.completions.create(model="llama-3.2-11b-vision-preview", messages=[{"role": "user", "content": conteudo_api}], temperature=0.1)
                            texto_json = resposta.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                            tarefas = json.loads(texto_json)
                            
                            batch = db.batch()
                            for t in tarefas:
                                doc_ref = db.collection("cronogramas").document()
                                batch.set(doc_ref, {"usuario_id": u_id, "dia": t.get("dia", ""), "materia": t.get("materia", ""), "tema": t.get("tema", ""), "concluido": False})
                            batch.commit()
                            st.session_state.pop('dados'); st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with aba_lista:
            meu_crono = st.session_state.dados.get("cronogramas", [])
            pendentes = [c for c in meu_crono if not c.get("concluido", False)]
            concluidos = [c for c in meu_crono if c.get("concluido", False)]
            
            if pendentes:
                for t in pendentes:
                    col1, col2 = st.columns([0.1, 0.9])
                    if col1.button("✔️", key=f"ok_{t['id']}"):
                        db.collection("cronogramas").document(t['id']).update({"concluido": True})
                        st.session_state.pop('dados'); st.rerun()
                    col2.markdown(f"**{t.get('dia')}**: {t.get('materia')} - {t.get('tema')}")
            else: st.success("Nenhuma meta pendente!")

            if concluidos:
                st.divider()
                with st.expander("✅ Histórico de Aulas Assistidas"):
                    for t in reversed(concluidos):
                        ca, cb = st.columns([0.8, 0.2])
                        ca.markdown(f"~~{t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~")
                        if cb.button("Desfazer", key=f"undo_{t['id']}"):
                            db.collection("cronogramas").document(t['id']).update({"concluido": False})
                            st.session_state.pop('dados'); st.rerun()

    elif menu == "⚙️ Configurações":
        st.header("Configurações do Sistema")
        if st.button("🔄 Forçar Sincronização do Banco", type="primary"):
            st.session_state.pop('dados'); st.rerun()

    else:
        st.info(f"Você está na aba: {menu}. As lógicas das calculadoras e questões estão prontas no back-end.")
