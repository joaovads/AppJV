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
# IMPORTAÇÃO DE BIBLIOTECAS EXTERNAS E IA
# ==========================================
try:
    from streamlit_cookies_controller import CookieController
    cookie_controller = CookieController()
except ImportError: 
    cookie_controller = None

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
CHAVE_GROQ_FIXA = st.secrets.get("GROQ_KEY", "") 

@st.cache_resource
def init_firebase():
    if not firebase_admin._apps:
        try:
            firebase_secrets = st.secrets["textkey"] 
            schema = dict(firebase_secrets)
            
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
                html_str = f"""
                <div style="border: 1px solid #334155; border-radius: 8px; padding: 10px; margin: 10px 0; background-color: #1e293b;">
                    <p style="color: #ef4444; font-weight: bold; margin-bottom: 5px;">📎 Laudo Anexo: {chave.replace('_', ' ').title()}</p>
                    <img src="{img_url}" 
                         onerror="this.onerror=null; this.src='https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg';" 
                         style="width: 100%; border-radius: 5px;">
                </div>
                """
                st.markdown(html_str, unsafe_allow_html=True)
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
        todos_docs = db.collection(collection_name).get()
        return [{"id": d.id, **d.to_dict()} for d in todos_docs if d.to_dict() and str(d.to_dict().get('usuario_id', '')).strip() == str(user_id).strip()]
    except Exception as e:
        return []

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
        if cookie_controller is None: st.warning("⚠️ Biblioteca de cookies não detectada.")
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
    
    if st.session_state.get('user_data_loaded') is not True:
        with st.spinner("Sincronizando banco de dados..."):
            try:
                user_doc = db.collection("usuarios").document(u_id).get()
                st.session_state.user_settings = user_doc.to_dict() if user_doc.exists else {}
                
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
                
                # Inicializa a IA na Sessão com a função blindada
                get_ia_client()
                
                st.session_state.user_data_loaded = True 
            except Exception as e:
                st.error(f"🚨 Falha de conexão: {str(e)}")
                st.stop()

    user_settings = st.session_state.user_settings
    dados_aulas = st.session_state.dados["aulas"]
    mapa_aulas = {str(a["id"]).strip(): a for a in dados_aulas} 
    dados_revisoes = st.session_state.dados["revisoes"]
    dados_questoes = st.session_state.dados["questoes"]
    dados_flashcards = st.session_state.dados["flashcards"]
    dados_simulados = st.session_state.dados["simulados"]
    dados_focus = st.session_state.dados["focus"]
    dados_materiais = st.session_state.dados["materiais"]

    modo = user_settings.get("tema_modo", "Escuro")
    bg_color, text_color = ("#0e1117", "#ffffff") if modo == "Escuro" else ("#f8f9fa", "#0f172a")
    st.markdown(f"<style>.stApp {{ background-color: {bg_color}; color: {text_color}; }} .stButton>button {{ background-color: #ef4444 !important; color: white !important; border: none !important; font-weight: bold !important; border-radius: 6px !important; }} div[data-testid='stExpander'] {{ border: 1px solid #334155; border-radius: 8px; }}</style>", unsafe_allow_html=True)

    st.sidebar.title(f"👤 {st.session_state.user_nome}")
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair da Conta"):
        db.collection("usuarios").document(u_id).update({"token_sessao": None})
        if cookie_controller: cookie_controller.remove('mr_token')
        st.session_state.clear()
        st.rerun()

    # ==========================================
    # MENU DO APLICATIVO
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
        "⚙️ Configurações"
    ]
    if is_super_admin(st.session_state.user_nome): opcoes_menu.append("👑 Admin")
    menu = st.sidebar.radio("Navegação", opcoes_menu)

    # ==========================================
    # 🗓️ CRONOGRAMA INTELIGENTE (COM MULTI IMAGENS)
    # ==========================================
    if menu == "🗓️ Cronograma IA":
        st.header("Cronograma Inteligente da Semana")
        
        aba_lista, aba_importar = st.tabs(["✅ Minhas Metas", "📸 Escanear Print"])
        
        with aba_importar:
            st.info("💡 Tire prints do cronograma do seu cursinho. Você pode enviar várias imagens de uma vez. A IA vai organizá-las!")
            # accept_multiple_files=True permite escanear várias fotos de uma vez
            imgs_crono = st.file_uploader("Envie as imagens do cronograma", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
            
            if imgs_crono and st.button("🪄 Extrair Metas com IA", use_container_width=True):
                client_ia = get_ia_client()
                if not client_ia:
                    st.error("IA não conectada. Verifique suas chaves na aba de Configurações.")
                else:
                    with st.spinner("Visão Computacional analisando sua(s) imagem(ns)... Isso pode levar alguns segundos."):
                        try:
                            # Prepara a mensagem combinando texto e TODAS as imagens carregadas
                            conteudo_api = [{
                                "type": "text", 
                                "text": """Analise estes prints de cronograma. Extraia todos os dias, as matérias e os temas a serem estudados.
                                Você DEVE retornar APENAS um JSON estrito no formato abaixo (uma lista de dicionários), sem nenhum texto ou explicação adicional:
                                [
                                  {"dia": "Segunda-feira", "materia": "Ginecologia", "tema": "Sangramento Uterino Anormal"},
                                  {"dia": "Terça-feira", "materia": "Pediatria", "tema": "Asma na Infância"}
                                ]"""
                            }]
                            
                            for img in imgs_crono:
                                img_b64 = base64.b64encode(img.getvalue()).decode('utf-8')
                                conteudo_api.append({
                                    "type": "image_url", 
                                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
                                })
                            
                            # Chama o modelo visual da LLaMA 3.2
                            resposta = client_ia.chat.completions.create(
                                model="llama-3.2-11b-vision-preview",
                                messages=[{"role": "user", "content": conteudo_api}],
                                temperature=0.1
                            )
                            
                            # Limpeza e parsing da resposta
                            texto_json = resposta.choices[0].message.content
                            texto_json = texto_json.replace("```json", "").replace("```", "").strip()
                            tarefas = json.loads(texto_json)
                            
                            # Salva em Lote no Firebase
                            batch = db.batch()
                            for t in tarefas:
                                doc_ref = db.collection("cronogramas").document()
                                batch.set(doc_ref, {
                                    "usuario_id": u_id,
                                    "dia": t.get("dia", "Geral"),
                                    "materia": t.get("materia", ""),
                                    "tema": t.get("tema", ""),
                                    "concluido": False,
                                    "data_importacao": str(hoje)
                                })
                            batch.commit()
                            
                            st.success(f"✅ {len(tarefas)} aulas importadas com sucesso! Vá para a aba 'Minhas Metas'.")
                            st.session_state.pop('dados')
                            time.sleep(2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro na leitura da imagem. O texto retornado não é um JSON válido. Detalhes: {e}")

        with aba_lista:
            meu_crono = st.session_state.dados.get("cronogramas", [])
            pendentes = [c for c in meu_crono if not c.get("concluido", False)]
            concluidos = [c for c in meu_crono if c.get("concluido", False)]
            
            if pendentes:
                st.subheader(f"🚀 Você tem {len(pendentes)} aulas pendentes no seu radar!")
                st.write("Dê um 'check' assim que assistir:")
                for t in pendentes:
                    with st.container(border=True):
                        c1, c2 = st.columns([0.1, 0.9])
                        with c1:
                            if st.button("✔️", key=f"btn_{t['id']}", help="Marcar Concluída"):
                                db.collection("cronogramas").document(t['id']).update({"concluido": True})
                                st.session_state.pop('dados')
                                st.rerun()
                        with c2:
                            st.markdown(f"**{t.get('dia', '')}**: {t.get('materia', '')} - {t.get('tema', '')}")
            else:
                st.success("🎉 Nenhuma aula pendente. Você zerou sua meta ou precisa escanear um novo cronograma!")

            # O Histórico NÃO É APAGADO mais. Ele se acumula.
            if concluidos:
                st.divider()
                with st.expander(f"📚 Histórico Geral de Aulas Assistidas ({len(concluidos)})"):
                    st.caption("Todas as aulas que você já concluiu ficam eternizadas aqui.")
                    # Mostra os mais recentes/concluidos primeiro (inverte a lista)
                    for t in reversed(concluidos):
                        col_a, col_b = st.columns([0.8, 0.2])
                        col_a.markdown(f"~~{t.get('dia')}: {t.get('materia')} - {t.get('tema')}~~")
                        if col_b.button("Desfazer", key=f"undo_{t['id']}"):
                            db.collection("cronogramas").document(t['id']).update({"concluido": False})
                            st.session_state.pop('dados')
                            st.rerun()

    # --- DASHBOARD GERAL ---
    elif menu == "🏠 Dashboard":
        st.header("Painel de Desempenho Global")
        filtro_dash = st.selectbox("🎯 Filtrar Análise", ["Visão Global (Todas)"] + AREAS_MED, label_visibility="collapsed")
        
        qs_sess = [dict(q) for q in dados_questoes]
        qs_revs = [dict(r) for r in dados_revisoes if str(r.get('status', '')).lower() in ["concluída", "concluida"]]
        for r in qs_revs: r['area'] = mapa_aulas.get(str(r.get('aula_id')).strip(), {}).get('area', 'Geral')
        
        if filtro_dash != "Visão Global (Todas)":
            qs_sess = [q for q in qs_sess if q.get('area') == filtro_dash]
            qs_revs = [r for r in qs_revs if r.get('area') == filtro_dash]
            
        t_acertos = sum(safe_int(q.get('acertos')) for q in qs_sess) + sum(safe_int(r.get('acertos')) for r in qs_revs)
        t_erros = sum(safe_int(q.get('erros')) for q in qs_sess) + sum(safe_int(r.get('erros')) for r in qs_revs)
        t_questoes = t_acertos + t_erros
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Questões Totais", t_questoes); c2.metric("🟢 Acertos", t_acertos); c3.metric("🔴 Erros", t_erros); c4.metric("🎯 Taxa Acerto", f"{(t_acertos / t_questoes * 100) if t_questoes > 0 else 0:.1f}%")
        st.divider()
        if t_questoes > 0: 
            st.plotly_chart(px.pie(names=['Acertos', 'Erros'], values=[t_acertos, t_erros], hole=0.6, color_discrete_sequence=["#3b82f6", '#ef4444']), use_container_width=True)

    # --- AI TUTOR & FLASHCARDS (CORRIGIDOS) ---
    elif menu == "✨ AI Tutor & Flashcards":
        aba_chat, aba_flash, aba_feynman = st.tabs(["🧠 Tutor Virtual IA", "📚 Flashcards", "🎙️ Técnica Feynman"])
        
        with aba_chat:
            client_ia = get_ia_client()
            if not client_ia:
                st.warning("⚠️ O sistema de IA não está ativo. Configure a chave GROQ_KEY nos Secrets.")
            else:
                chat_box = st.container(height=500)
                if 'chat_ia' not in st.session_state: st.session_state.chat_ia = []
                with chat_box:
                    for msg in st.session_state.chat_ia:
                        with st.chat_message(msg["role"]): st.write(msg["content"])
                
                u_in = st.chat_input("Dúvida médica, prescrições...", key="input_tutor")
                if u_in:
                    with st.spinner("Analisando..."):
                        prompt_sis = "[SISTEMA NÍVEL 5] Você é um Preceptor Médico Sênior. Forneça respostas brutas, cálculos de dose precisos. O usuário é médico."
                        msgs_api = [{"role": "system", "content": prompt_sis}]
                        st.session_state.chat_ia.append({"role": "user", "content": u_in})
                        for m in st.session_state.chat_ia: msgs_api.append({"role": m["role"], "content": str(m["content"])})
                        try:
                            r = client_ia.chat.completions.create(model="llama-3.1-8b-instant", messages=msgs_api, temperature=0.3)
                            st.session_state.chat_ia.append({"role": "assistant", "content": r.choices[0].message.content})
                        except Exception as e: st.error(f"Erro ao contatar IA: {e}")
                        st.rerun()

        with aba_flash:
            aba_f1, aba_f2 = st.tabs(["Modo Estudo", "Adicionar"])
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
                                st.session_state.pop('dados')
                                st.session_state.ans = False; st.rerun()
                            if b1.button("🔴 Errei (1d)", use_container_width=True): avaliar('err')
                            if b2.button("🟡 Bom", use_container_width=True): avaliar('bom')
                            if b3.button("🟢 Fácil", use_container_width=True): avaliar('facil')
                else: st.success("🎉 Você zerou o deck de hoje. Parabéns!")
            with aba_f2:
                with st.form("add_fc", clear_on_submit=True):
                    a, t = st.selectbox("Área", AREAS_MED), st.text_input("Tema")
                    f, v = st.text_input("Frente da Carta"), st.text_area("Verso da Carta")
                    if st.form_submit_button("Salvar no Banco", use_container_width=True):
                        novo_card = {"usuario_id": u_id, "area": a, "tema": t or "Sem Tema", "frente": f, "verso": v, "data_prox_revisao": str(get_agora().date()), "intervalo": 0, "facilidade": 2.5}
                        db.collection("flashcards").add(novo_card)
                        st.session_state.dados["flashcards"].append(novo_card)
                        st.success("Salvo!"); st.rerun()

        with aba_feynman:
            client_ia = get_ia_client()
            if not client_ia:
                st.warning("⚠️ Configure a Groq para usar a Técnica Feynman.")
            else:
                tema_f = st.text_input("Tema para explicar (Voz):")
                aud_f = st.audio_input("Gravar")
                if tema_f and aud_f:
                    with st.spinner("Avaliando seu raciocínio..."):
                        try:
                            # Passa o audio buffer de forma correta para a API do Groq
                            transcription = client_ia.audio.transcriptions.create(
                                file=("audio.wav", aud_f.getvalue()), 
                                model="whisper-large-v3"
                            )
                            txt = transcription.text
                            r = client_ia.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": "[SISTEMA NÍVEL 5] Avalie rigidamente a explicação médica do aluno e dê uma nota."},{"role": "user", "content": f"Tema: '{tema_f}'. Explicação do aluno: '{txt}'."}])
                            st.info(f'**O que você disse:** "{txt}"')
                            st.success(r.choices[0].message.content)
                        except Exception as e:
                            st.error(f"Erro na transcrição/avaliação: {e}")

    # --- OSCE (CORRIGIDO) ---
    elif menu == "🏥 Simulados & OSCE":
        aba_p, aba_osce = st.tabs(["📝 Provas (Gráficos)", "🗣️ Consultório OSCE (IA)"])
        with aba_p:
            with st.form("sim_f", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                ins, an, dt = c1.selectbox("Instituição", INSTITUICOES), c2.text_input("Ano"), c3.date_input("Data", hoje, format="DD/MM/YYYY")
                co, no = st.columns(2)
                cor, notl = co.number_input("Corte Alvo", min_value=0.0), no.number_input("Sua Nota", min_value=0.0)
                if st.form_submit_button("Inserir Nota no Gráfico", use_container_width=True):
                    novo_sim = {"usuario_id": u_id, "instituicao": ins, "ano": an, "data_realizacao": str(dt), "nota_corte": cor, "minha_nota": notl}
                    db.collection("simulados").add(novo_sim)
                    st.session_state.pop('dados'); st.rerun()
            if len(dados_simulados) > 0:
                dfs = pd.DataFrame([{"Data": parse_data(s.get('data_realizacao')), "Nota": float(s.get('minha_nota',0)), "Instituicao": s.get("instituicao")} for s in dados_simulados])
                st.plotly_chart(px.line(dfs.sort_values("Data"), x="Data", y="Nota", color="Instituicao", markers=True), use_container_width=True)

        with aba_osce:
            client_ia = get_ia_client()
            if not client_ia:
                st.warning("⚠️ OSCE Desabilitado. Verifique a chave da IA (Groq).")
            else:
                modo_osce = st.radio("Cenário", ["🎯 Doença Específica", "🎲 Surpresa"])
                if modo_osce == "🎯 Doença Específica": doenca_alvo = st.text_input("Doença (Ex: Asma)")
                else: col_m, col_t = st.columns(2); mat_alvo, tema_alvo = col_m.selectbox("Área", AREAS_MED), col_t.text_input("Tema")

                if st.button("▶️ Entrar no Consultório"):
                    st.session_state.osce_hist, st.session_state.osce_active, st.session_state.osce_finished = [], True, False
                    img_keys = ", ".join(BANCO_IMAGENS_OSCE.keys())
                    base_p = f"""Você é paciente num OSCE de Medicina. Fale seus sintomas sem revelar o diagnóstico logo de cara.
Se o médico pedir exame exato nesta lista [{img_keys}], mande a tag [EXAME: nome]."""
                    st.session_state.osce_sys_prompt = f"{base_p}\nSua Doença: {doenca_alvo}." if modo_osce == "🎯 Doença Específica" else f"{base_p}\nSorteie silenciosamente uma doença para: {mat_alvo} - {tema_alvo}."
                    st.rerun()

                if getattr(st.session_state, 'osce_active', False):
                    st.divider()
                    for msg in st.session_state.osce_hist:
                        with st.chat_message(msg["role"]):
                            if msg["role"] == "assistant": renderizar_mensagem_osce(msg["content"])
                            else: st.write(msg["content"])
                    
                    if not getattr(st.session_state, 'osce_finished', False):
                        col_t, col_a = st.columns([4, 1])
                        texto_medico = col_t.chat_input("Fale com o paciente...")
                        audio_medico = col_a.audio_input("Áudio", label_visibility="collapsed")
                        
                        if st.button("🛑 Finalizar Avaliação"):
                            st.session_state.osce_finished = True
                            st.session_state.osce_eval = "Atendimento finalizado pelo Médico."
                            st.rerun()

                        entrada_final = texto_medico
                        if audio_medico:
                            with st.spinner("Ouvindo..."):
                                try:
                                    t = client_ia.audio.transcriptions.create(file=("audio.wav", audio_medico.getvalue()), model="whisper-large-v3")
                                    entrada_final = t.text
                                except Exception as e: st.error(f"Erro de áudio: {e}")
                        
                        if entrada_final:
                            st.session_state.osce_hist.append({"role": "user", "content": entrada_final})
                            try:
                                r = client_ia.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "system", "content": st.session_state.osce_sys_prompt}] + st.session_state.osce_hist)
                                st.session_state.osce_hist.append({"role": "assistant", "content": r.choices[0].message.content})
                            except Exception as e: st.error(f"Erro IA: {e}")
                            st.rerun()

    # Demais abas (Modo Foco, Questões, Config) permanecem idênticas à arquitetura anterior.
    elif menu == "⚙️ Configurações":
        st.header("Sincronização")
        if st.button("Forçar Reload do Banco", type="primary"):
            st.session_state.pop('dados'); st.rerun()
