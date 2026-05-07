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

# ==========================================
# CONFIGURAÇÃO GERAL DA PÁGINA
# ==========================================
st.set_page_config(page_title="Residência PRO", page_icon="🏥", layout="wide")

def ativar_pwa():
    pwa_html = """
    <script>
        if (!document.getElementById('pwa-manifest')) {
            const manifest = {
                "name": "Residência PRO",
                "short_name": "Residência",
                "theme_color": "#ef4444",
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
            st.error(f"Erro ao conectar ao Firebase: {e}")
            st.stop()
    return firestore.client()

db = init_firebase()

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
                st.error(f"Erro ao conectar IA: {e}")
        else:
            st.session_state.model_ia = None
    return st.session_state.model_ia

# ==========================================
# CONSTANTES, CORES E BANCO DE IMAGENS OSCE
# ==========================================
AREAS_MED = ["Clínica Médica", "Cirurgia Geral", "Pediatria", "Ginecologia e Obstetrícia", "Medicina Preventiva", "Geral"]
INSTITUICOES = ["USP-SP", "SUS-SP", "UNICAMP", "UNIFESP", "SCMSP", "IAMSPE", "UFRJ", "Hospital Albert Einstein", "Sírio-Libanês", "Outra"]
MESES_PT = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
CORES_AREAS = {"Clínica Médica": "#3b82f6", "Pediatria": "#ec4899", "Ginecologia e Obstetrícia": "#a855f7", "Medicina Preventiva": "#22c55e", "Cirurgia Geral": "#ef4444", "Geral": "#64748b"}

PRIORIDADES = {
    1: "💎 1 - Diamante Azul",
    2: "🟩 2 - Verde",
    3: "🟨 3 - Amarelo",
    4: "🟥 4 - Vermelho",
    5: "🟪 5 - Roxo"
}

BANCO_IMAGENS_OSCE = {
    "ecg_normal": "https://upload.wikimedia.org/wikipedia/commons/b/b6/12_lead_normal_ECG.png",
    "ecg_infarto_supra": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/1a/12-lead_ECG_showing_inferior_STEMI.png/1024px-12-lead_ECG_showing_inferior_STEMI.png",
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
                st.markdown(f'<div style="border: 1px solid #334155; border-radius: 8px; padding: 10px;"><p style="color: #ef4444; font-weight: bold;">📎 Laudo: {chave}</p><img src="{img_url}" style="width: 100%;"></div>', unsafe_allow_html=True)
            else:
                st.info(f"*(Paciente entrega laudo: {chave} - Sem imagem)*")

# ==========================================
# BANCO DE DADOS DA CALCULADORA DE DOSES
# ==========================================
MEDICAMENTOS = {
    "Pediatria (Baseado em Peso)": {
        "Dipirona (Febre/Dor)": {"dose": 20, "unidade": "mg/kg", "max": 1000, "via": "VO / EV", "obs": "EV: 15-20 mg/kg/dose a cada 6h. VO: 1 gota/kg."},
        "Amoxicilina (OMA/Sinusite)": {"dose": 50, "unidade": "mg/kg/dia", "max": 1500, "via": "VO", "obs": "Dividir em 3 tomadas (8/8h)."},
        "Adrenalina (Anafilaxia)": {"dose": 0.01, "unidade": "mg/kg", "max": 0.3, "via": "IM", "obs": "0,01 mL/kg da ampola 1:1.000 no vasto lateral."}
    },
    "Adulto (Doses por Peso E Fixas)": {
        "AAS (SCA)": {"dose_fixa": "150-300 mg", "via": "VO (Mastigar)", "obs": "3 comprimidos infantis de 100mg macerados na boca."},
        "Adrenalina (Anafilaxia)": {"dose_fixa": "0.3 a 0.5 mg", "via": "IM", "obs": "No vasto lateral da coxa. Ampola pura (1:1.000)."},
        "Amiodarona (PCR FV/TV)": {"dose_fixa": "300 mg", "via": "EV Bolus", "obs": "1ª dose (2 ampolas) pura na PCR. 2ª dose: 150mg."}
    }
}

# ==========================================
# FUNÇÕES GERAIS E DATA
# ==========================================
def get_agora(): return datetime.utcnow() - timedelta(hours=3)
def hash_senha(senha): return hashlib.sha256(str.encode(senha)).hexdigest()
def is_super_admin(nome): return str(nome).lower().strip() in ['joao', 'joão', 'joao victor']
def get_image_base64(img_path):
    with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')

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

# Função Blindada de Cache (Corrige o AttributeError e a Tela Vermelha)
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
        
    codigo_html = f"<div style='background:#1e212b; padding:15px; border-radius:10px;'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'><tr><th style='text-align:center;'>Seg</th><th style='text-align:center;'>Ter</th><th style='text-align:center;'>Qua</th><th style='text-align:center;'>Qui</th><th style='text-align:center;'>Sex</th><th style='text-align:center;'>Sáb</th><th style='text-align:center;'>Dom</th></tr>"
    for week in cal:
        codigo_html += "<tr>"
        for day in week:
            if day == 0: codigo_html += "<td style='border:1px solid #334155; padding:10px; background:#0e1117;'></td>"
            else:
                if day in aulas_dict:
                    temas = "".join([f"<div style='background:{CORES_AREAS.get(a.get('area'), '#64748b')}; color:white; padding:2px; border-radius:4px; font-size:10px; margin-bottom:2px;'>{html.escape(limpar_texto(a.get('tema', '')))}</div>" for a in aulas_dict[day]])
                    codigo_html += f"<td style='border:1px solid #334155; padding:5px; background:#1e293b; height:80px;'><strong>{day}</strong><div>{temas}</div></td>"
                else: codigo_html += f"<td style='border:1px solid #334155; padding:5px; height:80px;'><strong>{day}</strong></td>"
        codigo_html += "</tr>"
    codigo_html += "</table></div>"
    return codigo_html

def gerar_calendario_revisoes_html(revisoes_lista, ano, mes):
    cal = calendar.monthcalendar(ano, mes)
    revs_dict = {}
    for r in revisoes_lista:
        d = parse_data(r.get('data_agendada_obj') if 'data_agendada_obj' in r else r.get('data_agendada'))
        if d and d.year == ano and d.month == mes: revs_dict.setdefault(d.day, []).append(r)
        
    codigo_html = f"<div style='background:#1e212b; padding:15px; border-radius:10px;'><table style='width:100%; border-collapse: collapse; table-layout: fixed;'><tr><th style='text-align:center;'>Seg</th><th style='text-align:center;'>Ter</th><th style='text-align:center;'>Qua</th><th style='text-align:center;'>Qui</th><th style='text-align:center;'>Sex</th><th style='text-align:center;'>Sáb</th><th style='text-align:center;'>Dom</th></tr>"
    for week in cal:
        codigo_html += "<tr>"
        for day in week:
            if day == 0: codigo_html += "<td style='border:1px solid #334155; padding:10px; background:#0e1117;'></td>"
            else:
                if day in revs_dict:
                    temas = "".join([f"<div style='background:{CORES_AREAS.get(r.get('area'), '#64748b')}; color:white; padding:2px; border-radius:4px; font-size:10px; margin-bottom:2px;'>{html.escape(limpar_texto(r.get('tema', '')))} ({r.get('ciclo')})</div>" for r in revs_dict[day]])
                    codigo_html += f"<td style='border:1px solid #334155; padding:5px; background:#1e293b; height:80px;'><strong>{day}</strong><div>{temas}</div></td>"
                else: codigo_html += f"<td style='border:1px solid #334155; padding:5px; height:80px;'><strong>{day}</strong></td>"
        codigo_html += "</tr>"
    codigo_html += "</table></div>"
    return codigo_html

# ==========================================
# GESTÃO DE LOGIN
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
    
    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Sincronizando banco de dados..."):
            try:
                st.session_state.dados = {
                    "aulas": get_user_docs("aulas", u_id),
                    "revisoes": get_user_docs("revisoes", u_id),
                    "flashcards": get_user_docs("flashcards", u_id),
                    "questoes": get_user_docs("questoes_sessoes", u_id),
                    "simulados": get_user_docs("simulados", u_id),
                    "focus": get_user_docs("focus_sessoes", u_id),
                    "materiais": get_user_docs("materiais", u_id),
                    "cronogramas": get_user_docs("cronogramas", u_id)
                }
                
                get_ia_client()
                st.session_state.user_settings = db.collection("usuarios").document(u_id).get().to_dict() or {}
                st.session_state.user_data_loaded = True 
            except Exception as e:
                st.error(f"🚨 Falha ao carregar dados: {e}")
                st.session_state.dados = {}

    # VARIÁVEIS DE CACHE 100% BLINDADAS (Puxando dados de forma segura)
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

    st.markdown(f"<style>.stButton>button {{ background-color: #ef4444 !important; color: white !important; font-weight: bold !important; border-radius: 6px !important; }}</style>", unsafe_allow_html=True)
    st.sidebar.title(f"👤 {st.session_state.user_nome}")

    if st.sidebar.button("Sair da Conta"):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        st.session_state.clear()
        st.rerun()

    opcoes_menu = [
        "🏠 Dashboard", "🗓️ Cronograma IA", "🎯 Questões", "📚 Registro de Aulas",
        "📅 Agenda de Revisões", "✨ AI Tutor & Flashcards", "🏥 Simulados & OSCE",
        "📍 GPS da Aprovação", "⏱️ Modo Foco", "🧮 Calculadora de Doses", "⚙️ Configurações"
    ]
    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ==========================================
    # 🗓️ CRONOGRAMA INTELIGENTE (COM CORES/DATAS)
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
                    with st.spinner("Visão Computacional analisando sua(s) imagem(ns)..."):
                        try:
                            prompt_visao = """Analise estes prints de cronograma. Extraia dias, matérias e temas.
Atribua uma PRIORIDADE para a aula de 1 a 5, onde 1 é Diamante Azul (muito importante) e 5 é Roxo (menos importante). Baseie-se na sua capacidade médica de julgar urgência do tema para residência.
Retorne APENAS um JSON estrito no formato abaixo (uma lista de dicionários), sem nenhum texto adicional:
[
  {"dia": "Segunda-feira", "materia": "Cirurgia", "tema": "Hérnias da Parede Abdominal", "prioridade": 1}
]"""
                            conteudo_api = [{"type": "text", "text": prompt_visao}]
                            for img in imgs_crono:
                                img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                conteudo_api.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
                            
                            # MODELO CORRIGIDO E DEFINITIVO PARA A GROQ
                            resposta = client_ia.chat.completions.create(
                                model="llama-3.2-90b-vision-preview", 
                                messages=[{"role": "user", "content": conteudo_api}], 
                                temperature=0.1
                            )
                            texto_json = resposta.choices[0].message.content.replace("```json", "").replace("```", "").strip()
                            tarefas = json.loads(texto_json)
                            
                            batch = db.batch()
                            for t in tarefas:
                                doc_ref = db.collection("cronogramas").document()
                                batch.set(doc_ref, {
                                    "usuario_id": u_id,
                                    "dia": t.get("dia", ""),
                                    "materia": t.get("materia", ""),
                                    "tema": t.get("tema", ""),
                                    "prioridade": safe_int(t.get("prioridade", 3)),
                                    "concluido": False,
                                    "data_importacao": str(hoje)
                                })
                            batch.commit()
                            invalidar_cache()
                            st.rerun()
                        except Exception as e: st.error(f"Erro: {e}")

        with aba_lista:
            pendentes = [c for c in dados_cronogramas if not c.get("concluido", False)]
            concluidos = [c for c in dados_cronogramas if c.get("concluido", False)]
            
            # Ordenando as pendentes por nível de Prioridade
            pendentes.sort(key=lambda x: safe_int(x.get("prioridade", 3)))
            
            if pendentes:
                st.write("Dê um 'check' assim que assistir:")
                for t in pendentes:
                    with st.container(border=True):
                        col1, col2 = st.columns([0.1, 0.9])
                        with col1:
                            if st.button("✔️", key=f"ok_{t['id']}", help="Marcar Concluída"):
                                db.collection("cronogramas").document(t['id']).update({
                                    "concluido": True,
                                    "data_conclusao": str(get_agora().date())
                                })
                                invalidar_cache()
                                st.rerun()
                        with col2:
                            p_val = safe_int(t.get('prioridade', 3))
                            p_icon = PRIORIDADES.get(p_val, "🟨 3 - Amarelo")
                            st.markdown(f"**{p_icon} | {t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
            else: 
                st.success("🎉 Nenhuma meta pendente! Vá em 'Escanear Print' para nova semana.")

            if concluidos:
                st.divider()
                with st.expander("✅ Histórico de Aulas Assistidas"):
                    for t in reversed(concluidos):
                        col_a, col_b = st.columns([0.8, 0.2])
                        data_c = formatar_data_br(t.get('data_conclusao', ''))
                        col_a.markdown(f"~~{t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~ *(Feito em: {data_c})*")
                        if col_b.button("Desfazer", key=f"undo_{t['id']}"):
                            db.collection("cronogramas").document(t['id']).update({
                                "concluido": False,
                                "data_conclusao": None
                            })
                            invalidar_cache()
                            st.rerun()

    # ==========================================
    # 🧮 CALCULADORA
    # ==========================================
    elif menu == "🧮 Calculadora de Doses":
        st.header("Calculadora Avançada (Diretrizes Nacionais)")
        aba_doses, aba_holliday, aba_obstetricia = st.tabs(["💊 Doses e Condutas", "💧 Hidratação", "🤰 Obstetrícia"])
        with aba_doses:
            col_tipo, col_peso = st.columns(2)
            tipo_paciente = col_tipo.radio("Perfil:", ["Pediatria (Baseado em Peso)", "Adulto (Doses por Peso E Fixas)"])
            peso = col_peso.number_input("Peso (kg)", min_value=0.5, value=70.0 if "Adulto" in tipo_paciente else 15.0, step=0.5)
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

    # ==========================================
    # 📍 GPS DA APROVAÇÃO
    # ==========================================
    elif menu == "📍 GPS da Aprovação":
        st.header("GPS da Aprovação")
        alvo = st.selectbox("🎯 Especialidade Foco?", ["Medicina Intensiva", "Clínica Médica", "Anestesiologia", "Cardiologia"])
        notas_corte = {"USP-SP": {"Medicina Intensiva": 78, "Clínica Médica": 82, "Anestesiologia": 85}, "UNICAMP": {"Medicina Intensiva": 77, "Clínica Médica": 81, "Anestesiologia": 83}}
        if dados_simulados:
            notas = [float(s.get('minha_nota', 0)) for s in dados_simulados]
            st.metric("Sua Média", f"{sum(notas)/len(notas):.1f}%")

    # ==========================================
    # 🏠 DASHBOARD
    # ==========================================
    elif menu == "🏠 Dashboard":
        st.header("Painel de Desempenho Global")
        qs_sess = [dict(q) for q in dados_questoes]
        qs_revs = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        
        t_acertos = sum(safe_int(q.get('acertos')) for q in qs_sess) + sum(safe_int(r.get('acertos')) for r in qs_revs)
        t_erros = sum(safe_int(q.get('erros')) for q in qs_sess) + sum(safe_int(r.get('erros')) for r in qs_revs)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Questões Totais", t_acertos + t_erros)
        c2.metric("🟢 Acertos", t_acertos)
        c3.metric("🔴 Erros", t_erros)
        if t_acertos + t_erros > 0: 
            st.plotly_chart(px.pie(names=['Acertos', 'Erros'], values=[t_acertos, t_erros], color_discrete_sequence=["#3b82f6", '#ef4444']), use_container_width=True)

    # ==========================================
    # 📅 AGENDA DE REVISÕES
    # ==========================================
    elif menu == "📅 Agenda de Revisões":
        st.header("Organizador de Ciclos")
        aba_pendentes, aba_historico = st.tabs(["📝 Pendentes", "✅ Histórico"])
        
        with aba_pendentes:
            todas_pendentes = []
            for r_orig in dados_revisoes:
                if str(r_orig.get('status', '')).lower() not in ['pendente', 'pendentes']: continue
                aula_id_limpo = str(r_orig.get('aula_id', '')).strip()
                if aula_id_limpo in mapa_aulas:
                    r = dict(r_orig)
                    r['data_agendada_obj'] = parse_data(r.get('data_agendada'))
                    r['tema'] = limpar_texto(mapa_aulas[aula_id_limpo].get('tema', 'Sem título'))
                    todas_pendentes.append(r)
            
            lista_pendentes = [r for r in todas_pendentes if r['data_agendada_obj'] <= hoje]
            lista_pendentes.sort(key=lambda x: x['data_agendada_obj'])

            if not lista_pendentes: st.success("🎉 Tudo em dia!")
            for r in lista_pendentes:
                with st.container(border=True):
                    st.markdown(f"**{r['tema']}** ({r.get('ciclo','')})")
                    with st.expander("Concluir"):
                        with st.form(f"f_{r['id']}", clear_on_submit=True):
                            q = st.number_input("Questões", 0)
                            e = st.number_input("Erros", 0)
                            if st.form_submit_button("✅ Marcar Concluída"):
                                db.collection("revisoes").document(r['id']).update({"status": "Concluída", "questoes_feitas": q, "erros": e, "acertos": q-e, "data_conclusao": str(get_agora().date())})
                                invalidar_cache()
                                st.rerun()

        with aba_historico:
            st.info("Suas revisões concluídas são contabilizadas no seu Dashboard e histórico local.")

    # ==========================================
    # 🎯 QUESTÕES
    # ==========================================
    elif menu == "🎯 Questões":
        aba_reg, aba_erros = st.tabs(["📝 Registrar", "🧠 Caderno de Erros Ativo"])
        with aba_reg:
            with st.form("q_form", clear_on_submit=True):
                a = st.selectbox("Área", AREAS_MED)
                s = st.text_input("Subtema")
                acc, err = st.number_input("Acertos", 0), st.number_input("Erros", 0)
                cc = st.text_input("Motivo do erro (Conceito Chave)")
                if st.form_submit_button("Registrar"):
                    db.collection("questoes_sessoes").add({"usuario_id": u_id, "data": str(hoje), "area": a, "subtema": s, "acertos": acc, "erros": err, "conceito_chave": cc})
                    invalidar_cache()
                    st.rerun()

    # ==========================================
    # ✨ AI TUTOR E FLASHCARDS
    # ==========================================
    elif menu == "✨ AI Tutor & Flashcards":
        aba_chat, aba_flash, aba_feynman = st.tabs(["🧠 Tutor Virtual IA", "📚 Flashcards", "🎙️ Técnica Feynman"])
        with aba_chat:
            if 'chat_ia' not in st.session_state: st.session_state.chat_ia = []
            for msg in st.session_state.chat_ia:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            u_in = st.chat_input("Dúvida médica...")
            if u_in:
                client_ia = get_ia_client()
                if client_ia:
                    with st.spinner("Analisando..."):
                        st.session_state.chat_ia.append({"role": "user", "content": u_in})
                        try:
                            r = client_ia.chat.completions.create(model="llama-3.1-8b-instant", messages=st.session_state.chat_ia, temperature=0.3)
                            st.session_state.chat_ia.append({"role": "assistant", "content": r.choices[0].message.content})
                        except: pass
                        st.rerun()

        with aba_flash:
            cards_hoje = [d for d in dados_flashcards if parse_data(d.get('data_prox_revisao')) <= hoje]
            if cards_hoje:
                c_data = cards_hoje[0]
                st.markdown(f"### ❔ {c_data.get('frente', '')}")
                if 'ans' not in st.session_state: st.session_state.ans = False
                if st.button("Revelar"): st.session_state.ans = True
                if st.session_state.ans:
                    st.info(f"**💡 Resposta:** {c_data.get('verso', '')}")
                    if st.button("Feito"): 
                        db.collection("flashcards").document(c_data["id"]).update({"data_prox_revisao": str(get_agora().date() + timedelta(days=1))})
                        invalidar_cache(); st.session_state.ans = False; st.rerun()
            else: st.success("Deck zerado!")

        with aba_feynman:
            st.info("Ensine um tema em áudio e a IA será o seu avaliador.")

    # ==========================================
    # 📚 AULAS
    # ==========================================
    elif menu == "📚 Registro de Aulas":
        st.header("Biblioteca Pessoal de Conteúdo")
        with st.form("n_aula", clear_on_submit=True):
            a, t = st.selectbox("Especialidade", AREAS_MED), st.text_input("Tema")
            if st.form_submit_button("Registrar Aula"):
                a_ref = db.collection("aulas").add({"usuario_id": u_id, "area": a, "tema": t, "data_aula": str(hoje)})
                batch = db.batch()
                for c, dias in {"R1":1, "R7":7, "R15":15}.items():
                    doc_ref = db.collection("revisoes").document()
                    batch.set(doc_ref, {"usuario_id": u_id, "aula_id": a_ref[1].id, "ciclo": c, "data_agendada": str(hoje + timedelta(days=dias)), "status": "Pendente"})
                batch.commit()
                invalidar_cache()
                st.rerun()

    # ==========================================
    # ⏱️ FOCO E CONFIG
    # ==========================================
    elif menu == "⏱️ Modo Foco":
        st.header("Concentração Pomodoro")
        tf = st.selectbox("Duração", [25, 30, 45, 60], index=0)
        if st.button("Iniciar"): st.success(f"Tempo de {tf} minutos rodando!")

    elif menu == "🏥 Simulados & OSCE":
        st.header("Simulados, PDFs e Prova Prática")
        st.info("Estas funções dependem dos envios de prova na nuvem.")

    elif menu == "📁 Materiais e Simulados":
        st.header("Upload de Arquivos")
        st.info("Suporta envio de PDFs.")

    elif menu == "⚙️ Configurações":
        st.header("Configurações do Sistema")
        if st.button("🔄 Forçar Sincronização do Banco de Dados", type="primary"):
            invalidar_cache()
            st.success("Sincronizado! Recarregando...")
            time.sleep(1)
            st.rerun()
