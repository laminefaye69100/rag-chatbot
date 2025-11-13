# ==========================================================
# app.py — Version PRO avec sessions, export, résumé, pin & PDF viewer
# ==========================================================

import os
import json
import time
import html
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from base64 import b64encode

import streamlit as st
import streamlit.components.v1 as components

from rag_pipeline import make_chain, get_index_stats
from build_index import build_index  # pour l’indexation automatique

# ==========================================================
# CONFIG GÉNÉRALE
# ==========================================================
st.set_page_config(
    page_title="RAG Chatbot — Ollama",
    page_icon="🤖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

APP_USER_NAME = "Lamine"
BOT_NAME = "LamBot"

HISTORY_PATH = Path("chat_history.json")   # ancien format (migration)
SESSIONS_PATH = Path("chat_sessions.json") # nouveau format (multi-sessions)
SETTINGS_PATH = Path("chat_settings.json")  # au cas où pour le futur


# ==========================================================
# UTILITAIRES GÉNÉRAUX
# ==========================================================
def now_time_str() -> str:
    return datetime.now().strftime("%H:%M")


def today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ==========================================================
# GESTION DES SESSIONS / CONVERSATIONS
# ==========================================================
def init_sessions():
    """
    Charge les sessions depuis chat_sessions.json.
    Si le fichier n'existe pas, migre l'ancien chat_history.json en une
    session unique "Conversation principale".
    """
    data = load_json(SESSIONS_PATH, None)

    if data is None:
        # Migration éventuelle depuis l’ancien format (liste simple)
        old_history = load_json(HISTORY_PATH, [])
        sess_id = "session-1"
        data = {
            "current_id": sess_id,
            "sessions": [
                {
                    "id": sess_id,
                    "name": "Conversation principale",
                    "created_at": iso_now(),
                    "last_used": iso_now(),
                    "history": old_history if isinstance(old_history, list) else [],
                }
            ],
        }
        save_json(SESSIONS_PATH, data)

    if "sessions_data" not in st.session_state:
        st.session_state.sessions_data = data

    # Si aucune session n'existe (cas extrême), on en crée une.
    if not st.session_state.sessions_data.get("sessions"):
        sess_id = "session-1"
        st.session_state.sessions_data = {
            "current_id": sess_id,
            "sessions": [
                {
                    "id": sess_id,
                    "name": "Conversation principale",
                    "created_at": iso_now(),
                    "last_used": iso_now(),
                    "history": [],
                }
            ],
        }
        save_json(SESSIONS_PATH, st.session_state.sessions_data)

    if "current_session_id" not in st.session_state:
        st.session_state.current_session_id = st.session_state.sessions_data.get(
            "current_id", st.session_state.sessions_data["sessions"][0]["id"]
        )

    # Historique de la session courante dans st.session_state.chat_history
    sess = get_current_session()
    st.session_state.chat_history = sess["history"]


def save_sessions():
    """Sauvegarde l’ensemble des sessions (multi-conversations)."""
    st.session_state.sessions_data["current_id"] = st.session_state.current_session_id
    save_json(SESSIONS_PATH, st.session_state.sessions_data)


def get_current_session():
    for s in st.session_state.sessions_data["sessions"]:
        if s["id"] == st.session_state.current_session_id:
            return s
    # fallback : première session
    return st.session_state.sessions_data["sessions"][0]


def switch_session(new_id: str):
    st.session_state.current_session_id = new_id
    sess = get_current_session()
    st.session_state.chat_history = sess["history"]
    sess["last_used"] = iso_now()
    save_sessions()


def create_new_session(name: str | None = None):
    sessions = st.session_state.sessions_data["sessions"]
    new_id = f"session-{len(sessions) + 1}"
    new_name = name or f"Conversation {len(sessions) + 1}"
    new_sess = {
        "id": new_id,
        "name": new_name,
        "created_at": iso_now(),
        "last_used": iso_now(),
        "history": [],
    }
    sessions.append(new_sess)
    switch_session(new_id)


def delete_current_session():
    sessions = st.session_state.sessions_data["sessions"]
    if len(sessions) <= 1:
        st.warning("Tu dois garder au moins une conversation.")
        return

    cur_id = st.session_state.current_session_id
    sessions = [s for s in sessions if s["id"] != cur_id]
    st.session_state.sessions_data["sessions"] = sessions
    # on prend la première comme nouvelle session courante
    st.session_state.current_session_id = sessions[0]["id"]
    st.session_state.chat_history = sessions[0]["history"]
    save_sessions()


# ==========================================================
# HISTORIQUE (messages) — basé sur la session courante
# ==========================================================
def append_message(role, content, when=None):
    sess = get_current_session()
    msg = {
        "role": role,
        "content": content,
        "time": when or now_time_str(),
        "date": today_str(),
    }
    sess["history"].append(msg)
    sess["last_used"] = iso_now()
    st.session_state.chat_history = sess["history"]
    save_sessions()


def clear_current_history():
    sess = get_current_session()
    sess["history"] = []
    st.session_state.chat_history = []
    save_sessions()


def delete_last_exchange():
    """
    Supprime le dernier couple (user + assistant) de la session courante.
    """
    sess = get_current_session()
    hist = sess["history"]
    if len(hist) < 2:
        return
    # On enlève les deux derniers messages
    sess["history"] = hist[:-2]
    st.session_state.chat_history = sess["history"]
    save_sessions()


def pin_last_answer():
    """
    Marque la dernière réponse de LamBot comme 'pinned'.
    """
    sess = get_current_session()
    for msg in reversed(sess["history"]):
        if msg.get("role") == "assistant":
            msg["pinned"] = True
            break
    save_sessions()


# ==========================================================
# MODE SOMBRE FIXE
# ==========================================================
dark_mode = True
bg_color = "#0e1117"
text_color = "#f5f5f5"
user_bubble = "#1e88e5"
bot_bubble = "#1c1c1c"
bot_text = "#f1f1f1"

st.markdown(
    f"""
<style>
[data-testid="stToolbar"] {{visibility: hidden !important;}}

html, body {{
  background-color: {bg_color};
  color: {text_color};
}}

div.block-container {{
  padding-top: 2.3rem;
}}

.theme-label {{
  position: fixed; top: 10px; right: 20px;
  padding: 6px 10px; border-radius: 10px;
  background: rgba(30,30,30,0.8); color: white;
  font-size: 0.85rem; font-weight: 500;
}}

.stButton > button {{
  width: 100%;
  border-radius: 8px;
  margin-top: 6px;
  background-color: #4CAF50;
  color: white;
  border: 0;
  transition: background-color .3s ease, transform .15s ease;
}}
.stButton > button:hover {{
  background-color: #45a049;
  transform: scale(1.01);
}}

.chat-wrap {{
  max-height: 560px;
  overflow-y: auto;
  background-color: #0d0d0d;
  border-radius: 10px;
  padding: 14px;
  border: 1px solid #444;
}}

.msg {{
  display: flex; margin-bottom: 14px; opacity: 0;
  animation: fadeIn .6s forwards;
}}
@keyframes fadeIn {{
  to {{ opacity:1; transform: translateY(0); }}
}}

.avatar {{ font-size: 24px; margin-right: 10px; margin-top:3px; }}
.avatar.user {{ color:#1e90ff; }}
.avatar.bot {{ color:#00ff88; }}

.bubble {{
  max-width: 80%;
  padding: 10px 14px;
  border-radius: 15px;
  line-height: 1.45;
}}

.user .bubble {{
  background: {user_bubble};
  color: white;
  border-radius: 15px 15px 0 15px;
  margin-left: auto;
}}

.bot .bubble {{
  background: {bot_bubble};
  color: {bot_text};
  border-radius: 15px 15px 15px 0;
}}

.meta {{
  font-size: .8rem; opacity: .75; margin-top: 5px;
}}
.meta-date {{
  font-size: 0.75rem; opacity: 0.7;
}}

/* Bulle "LamBot réfléchit…" */
.typing-bubble {{
  background: {bot_bubble};
  color: {bot_text};
  padding: 10px 16px;
  border-radius: 15px 15px 15px 0;
}}

.dot {{
  animation: blink 1.4s infinite;
  font-size: 1.3rem; opacity:.2;
}}
.dot:nth-child(2) {{ animation-delay:.25s; }}
.dot:nth-child(3) {{ animation-delay:.5s; }}

@keyframes blink {{
  40% {{ opacity:1; }}
}}

.typing-text {{
  border-right: .12em solid #00ff88;
  white-space:pre-wrap;
  overflow:hidden;
  animation: caretBlink .8s infinite;
}}

@keyframes caretBlink {{
  50% {{ border-color: transparent; }}
}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='theme-label'>🌙 Mode sombre</div>", unsafe_allow_html=True)


# ==========================================================
# INITIALISATION RAG & SESSIONS
# ==========================================================
st.title("🤖 RAG Chatbot — Ollama (local)")
st.caption("Chatbot RAG avec indexation Chroma, sessions, historique et animations.")

# Sessions (multi-conversations)
init_sessions()

# Flags de confirmations
if "ask_confirm_history" not in st.session_state:
    st.session_state.ask_confirm_history = False
if "ask_confirm_full_reset" not in st.session_state:
    st.session_state.ask_confirm_full_reset = False

# Chaîne RAG
if "chain" not in st.session_state:
    try:
        st.session_state.chain = make_chain()
        st.success("Chaîne RAG initialisée 🎉")
    except Exception as e:
        st.error(f"Erreur : {e}")


# ==========================================================
# GESTION DES CONVERSATIONS (SESSIONS)
# ==========================================================
st.subheader("🗂️ Conversations")

sessions = st.session_state.sessions_data["sessions"]
current_sess = get_current_session()

col_s1, col_s2, col_s3 = st.columns([2, 1, 1])

with col_s1:
    # Sélecteur de conversation
    options = [f"{i+1}. {s['name']}" for i, s in enumerate(sessions)]
    ids = [s["id"] for s in sessions]
    current_index = ids.index(st.session_state.current_session_id)
    new_index = st.selectbox("Conversation active", range(len(options)),
                             format_func=lambda i: options[i],
                             index=current_index,
                             key="session_select")
    if new_index != current_index:
        switch_session(ids[new_index])

with col_s2:
    if st.button("➕ Nouvelle conversation"):
        create_new_session()

with col_s3:
    if st.button("🗑️ Supprimer cette conversation"):
        delete_current_session()

# Rename
new_name = st.text_input("Renommer la conversation", value=current_sess["name"])
if new_name.strip() and new_name != current_sess["name"]:
    if st.button("✅ Appliquer le nouveau nom"):
        current_sess["name"] = new_name.strip()
        save_sessions()
        st.experimental_rerun()


# ==========================================================
# STATS CHROMA
# ==========================================================
if os.path.exists("chroma"):
    try:
        stats = get_index_stats()
        st.info(f"📊 {stats['collections']} collections — {stats['chunks']} chunks indexés")
    except Exception:
        st.warning("Impossible de lire les statistiques.")
else:
    st.warning("Aucun index Chroma trouvé. Ajoute des fichiers pour créer un index.")


# ==========================================================
# UPLOAD, INDEX AUTOMATIQUE & LECTURE PDF
# ==========================================================
st.subheader("📂 Ajout de documents")

uploaded = st.file_uploader(
    "Ajouter un document (PDF / TXT / MD / DOCX)",
    type=["pdf", "txt", "md", "docx"],
)
if uploaded:
    Path("data").mkdir(exist_ok=True)
    dest = Path("data") / uploaded.name
    dest.write_bytes(uploaded.getbuffer())
    st.success(f"{uploaded.name} ajouté dans ./data")

    # 🔁 Indexation automatique
    with st.spinner("Mise à jour de l’index (automatique)…"):
        try:
            build_index()
            st.success("Index mis à jour ✅")
        except Exception as e:
            st.error(f"Erreur lors de l’indexation automatique : {e}")

# Boutons manuels supplémentaires
c1, c2, c3 = st.columns(3)
with c1:
    if st.button("🔁 Reconstruire index manuellement"):
        with st.spinner("Reconstruction de l’index…"):
            try:
                build_index()
                st.success("Index reconstruit ✅")
            except Exception as e:
                st.error(f"Erreur : {e}")

with c2:
    if st.button("🧽 Effacer historique (conversation courante)"):
        st.session_state.ask_confirm_history = True

with c3:
    if st.button("🗑️ Supprimer dernier échange"):
        delete_last_exchange()
        st.rerun()

# Confirmation effacement historique
if st.session_state.ask_confirm_history:
    st.warning("Tu veux vraiment effacer tout l’historique de cette conversation ?")
    c1c, c2c = st.columns(2)
    with c1c:
        if st.button("✅ Oui, effacer"):
            clear_current_history()
            st.session_state.ask_confirm_history = False
            st.rerun()
    with c2c:
        if st.button("❌ Non, annuler"):
            st.session_state.ask_confirm_history = False

# 📖 LECTURE DES PDF
st.subheader("📖 Lecture des PDFs (data/)")
pdf_dir = Path("data")
if pdf_dir.exists():
    pdf_files = sorted([p for p in pdf_dir.glob("*.pdf")])
    if pdf_files:
        pdf_selected = st.selectbox(
            "Choisir un PDF à lire",
            pdf_files,
            format_func=lambda p: p.name,
        )
        with open(pdf_selected, "rb") as f:
            pdf_bytes = f.read()
        b64 = b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    else:
        st.info("Aucun PDF trouvé dans ./data pour le moment.")
else:
    st.info("Le répertoire ./data n’existe pas encore.")


# ==========================================================
# EXPORT / IMPORT & RÉSUMÉ DE CONVERSATION
# ==========================================================
st.subheader("🧰 Outils conversation")

cur_session = get_current_session()
cur_history = cur_session["history"]

# --- Export Markdown ---
def history_to_markdown(session):
    lines = [
        f"# Conversation — {session['name']}",
        "",
        f"Créée le : {session['created_at']}",
        f"Dernière activité : {session['last_used']}",
        "",
    ]
    for msg in session["history"]:
        speaker = APP_USER_NAME if msg["role"] == "user" else BOT_NAME
        lines.append(
            f"**{speaker} ({msg.get('time','')} — {msg.get('date','')})**"
        )
        lines.append("")
        lines.append(msg.get("content", ""))
        lines.append("")
    return "\n".join(lines)


md_data = history_to_markdown(cur_session)
st.download_button(
    "📥 Télécharger la conversation en .md",
    data=md_data,
    file_name=f"conversation_{cur_session['name'].replace(' ', '_')}.md",
    mime="text/markdown",
)

# --- Export JSON (pour ré-import) ---
json_data = json.dumps(cur_history, ensure_ascii=False, indent=2)
st.download_button(
    "⬇️ Export JSON (pour ré-importer plus tard)",
    data=json_data,
    file_name=f"conversation_{cur_session['name'].replace(' ', '_')}.json",
    mime="application/json",
)

# --- Import JSON ---
uploaded_conv = st.file_uploader(
    "📤 Importer une conversation (JSON exporté)", type=["json"], key="import_conv"
)
if uploaded_conv is not None:
    try:
        imported = json.loads(uploaded_conv.read().decode("utf-8"))
        if isinstance(imported, list):
            # nouvelle session à partir de cet historique
            sessions = st.session_state.sessions_data["sessions"]
            new_name = f"Conversation importée {len(sessions)+1}"
            new_id = f"session-{len(sessions)+1}"
            new_sess = {
                "id": new_id,
                "name": new_name,
                "created_at": iso_now(),
                "last_used": iso_now(),
                "history": imported,
            }
            sessions.append(new_sess)
            switch_session(new_id)
            st.success(f"Conversation importée sous le nom : {new_name}")
            st.experimental_rerun()
        else:
            st.error("Le fichier JSON doit contenir une liste de messages.")
    except Exception as e:
        st.error(f"Impossible d'importer cette conversation : {e}")


# --- Résumé automatique de la conversation ---
def summarize_current_conversation():
    if not cur_history:
        return "Il n'y a encore aucun message dans cette conversation."

    conv_txt = ""
    for msg in cur_history:
        speaker = APP_USER_NAME if msg["role"] == "user" else BOT_NAME
        conv_txt += f"{speaker} : {msg.get('content','')}\n"

    try:
        from langchain_community.chat_models import ChatOllama
        from langchain.prompts import ChatPromptTemplate
        from langchain.schema.output_parser import StrOutputParser

        prompt = ChatPromptTemplate.from_template(
            "Tu es un assistant qui résume des conversations.\n"
            "On te donne une conversation entre un utilisateur et un assistant.\n"
            "Fais un résumé clair, structuré en sections (Contexte, Points clés, "
            "Questions importantes, Pistes de travail).\n\n"
            "CONVERSATION :\n{conversation}\n\nRÉSUMÉ :"
        )

        try:
            llm = ChatOllama(model="llama3.2:1b", temperature=0.2)
        except Exception:
            llm = ChatOllama(model="phi3:mini", temperature=0.2)

        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"conversation": conv_txt})
    except Exception as e:
        return f"Impossible de générer le résumé (erreur : {e})"


if st.button("🧠 Résumer cette conversation"):
    with st.spinner("LamBot prépare un résumé…"):
        summary = summarize_current_conversation()
    st.markdown("### 🧾 Résumé de la conversation")
    st.markdown(summary)


# ==========================================================
# AFFICHAGE CHAT + PIN
# ==========================================================
def render_chat(typing: bool = False, partial_bot_text: str | None = None):
    chat_html = ["<div class='chat-wrap' id='chat-box'>"]

    # 1) Bulle "LamBot réfléchit…" ou streaming — TOUT EN HAUT
    if typing and not partial_bot_text:
        chat_html.append(
            """
<div class='msg bot'>
  <div class='avatar bot'>🤖</div>
  <div style='display:flex;flex-direction:column;'>
      <div class='typing-bubble'>
          <span class='dot'>.</span><span class='dot'>.</span><span class='dot'>.</span>
      </div>
      <div class='meta'>LamBot réfléchit…</div>
  </div>
</div>
"""
        )
    elif partial_bot_text:
        chat_html.append(
            f"""
<div class='msg bot'>
  <div class='avatar bot'>🤖</div>
  <div style='display:flex;flex-direction:column;'>
      <div class='bubble typing-text'>{partial_bot_text}</div>
      <div class='meta'>{now_time_str()} — {BOT_NAME}<br>
          <span class='meta-date'>({today_str()})</span></div>
  </div>
</div>
"""
        )

    # 2) Messages de la conversation — récents EN HAUT
    for msg in reversed(st.session_state.chat_history):
        role = msg.get("role", "assistant")
        ts = msg.get("time", "")
        date = msg.get("date", today_str())
        safe = msg.get("content", "").replace("\n", "<br>")

        if role == "user":
            chat_html.append(
                f"""
<div class='msg user'>
  <div class='avatar user'>👤</div>
  <div style='margin-left:auto;display:flex;flex-direction:column;align-items:flex-end;'>
      <div class='bubble'>{safe}</div>
      <div class='meta'>{ts} — {APP_USER_NAME}<br>
          <span class='meta-date'>({date})</span></div>
  </div>
</div>
"""
            )
        else:
            chat_html.append(
                f"""
<div class='msg bot'>
  <div class='avatar bot'>🤖</div>
  <div style='display:flex;flex-direction:column;'>
      <div class='bubble'>{safe}</div>
      <div class='meta'>{ts} — {BOT_NAME}<br>
          <span class='meta-date'>({date})</span></div>
  </div>
</div>
"""
            )

    chat_html.append("</div>")
    components.html(dedent("\n".join(chat_html)), height=600, scrolling=True)


# ==========================================================
# INPUT + RÉPONSE + PIN
# ==========================================================
st.subheader("💬 Pose ta question…")

user_text = st.text_input(
    " ",
    key="chat_input",
    label_visibility="collapsed",
    placeholder="Ex : Qu’est-ce que le deep learning ?",
)

col_input1, col_input2 = st.columns([3, 1])

with col_input1:
    send_clicked = st.button("Répondre")

with col_input2:
    if st.button("📌 Épingler la dernière réponse"):
        pin_last_answer()
        st.success("Dernière réponse de LamBot épinglée.")

if send_clicked:
    q = (user_text or "").strip()

    if not q:
        st.warning("Écris quelque chose 🙂")
    else:
        append_message("user", q)

        # Affiche le chat + bulle "réfléchit" en haut
        render_chat(typing=True)
        time.sleep(0.6)

        # Génération de la réponse
        try:
            with st.spinner("Réflexion…"):
                answer = st.session_state.chain.invoke({"question": q})
        except Exception as e:
            answer = f"Erreur : {e}"

        # Streaming visuel de la réponse
        partial = ""
        for ch in answer:
            partial += ch
            render_chat(partial_bot_text=partial)
            time.sleep(0.012)

        append_message("assistant", answer)
        st.rerun()
else:
    render_chat()

# Zone d'affichage des réponses épinglées
with st.expander("📌 Réponses importantes (épinglées)", expanded=False):
    pinned_msgs = [
        m for m in get_current_session()["history"] if m.get("pinned") and m.get("role") == "assistant"
    ]
    if not pinned_msgs:
        st.write("Aucune réponse épinglée pour l’instant.")
    else:
        for i, m in enumerate(pinned_msgs, start=1):
            st.markdown(f"**Réponse épinglée {i} ({m.get('time','')} — {m.get('date','')})**")
            st.markdown(m.get("content", ""))
            st.markdown("---")


# ==========================================================
# CONSEILS
# ==========================================================
st.markdown("---")
st.markdown(
    """
**Conseils :**
- 💾 Conversations (multi-sessions) sauvegardées dans `chat_sessions.json`
- 📂 Tes documents sont dans `./data` (indexés automatiquement)
- 🔁 Bouton manuel de reconstruction si besoin
- 🧠 Modèle & retriever configurés dans `rag_pipeline.py`
"""
)
