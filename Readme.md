# 🤖 RAG Chatbot – Ollama (Local)  
Chatbot RAG (Retrieval-Augmented Generation) complet, puissant et 100% local.  
Construit avec **Streamlit**, **LangChain**, **ChromaDB**, et **Ollama**, il permet d’interroger intelligemment vos documents (PDF, TXT, DOCX, MD) grâce à un pipeline d’indexation + LLM local optimisé.

---

# ✨ Fonctionnalités

### 🔍 Recherche intelligente (RAG)
- Extraction + découpage automatique des documents  
- Embeddings via **nomic-embed-text** (Ollama)  
- Indexation vectorielle avec **ChromaDB**  
- RAG complet : *retrieval → contexte → LLM génératif*

### 🤖 Interface Chatbot Avancée
- Streaming du texte (effet écriture)  
- Bulle “LamBot réfléchit…” animée  
- Mode sombre entièrement custom  
- Historique enrichi (date + heure)  
- Messages récents en haut  
- Raccourcis ergonomiques

### 🗂️ Système de Sessions (multi-conversations)
- Créer des conversations  
- Renommer  
- Supprimer  
- Navigation entre sessions  
- Sauvegarde automatique dans `chat_sessions.json`

### 📌 Outils professionnels
- Épinglage de réponses importantes  
- Résumé automatique de conversation via LLM  
- Export Markdown (.md)  
- Export JSON (ré-importable)  
- Import de conversations  
- Suppression dernier échange ou reset complet  

### 📂 Gestion des documents
- Upload PDF / TXT / MD / DOCX  
- Indexation automatique  
- Reconstruction manuelle si nécessaire  
- Viewer PDF intégré  
- Localisation : dossier `./data`

---

# 📦 Installation

## 1️⃣ Cloner le dépôt

```bash
git clone https://github.com/laminefaye69100/rag-chatbot.git
cd rag-chatbot
```

## 2️⃣ Créer un environnement virtuel

### Linux / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows
```bash
python -m venv .venv
.venv\Scripts\activate
```

## 3️⃣ Installer les dépendances
```bash
pip install -r requirements.txt
```

## 4️⃣ Installer Ollama + modèles nécessaires
Installer Ollama :  
👉 https://ollama.com

Télécharger les modèles :

```bash
ollama pull llama3.2:1b
ollama pull phi3:mini
ollama pull nomic-embed-text
```

## 5️⃣ Lancer Ollama
```bash
ollama serve
```

---

# 🧠 Indexation de documents

Place tes fichiers dans :

```
./data/
```

Puis génère l’index :

```bash
python build_index.py
```

Ou laisse l’application indexer automatiquement lorsque tu uploades un document.

---

# 🚀 Lancer l’application Streamlit

```bash
streamlit run app.py
```

Application disponible sur :  
👉 **http://localhost:8501/**

---

# 📖 Guide d’utilisation

### 🗂️ Gestion des conversations
- Changer de conversation  
- Créer une nouvelle  
- Renommer  
- Supprimer  
- Historique sauvegardé automatiquement  

### ✏️ Utiliser le chatbot
- Écrire une question  
- Recevoir une réponse basée sur vos documents  
- Visualisation en streaming  

### 📌 Fonctionnalités avancées
- Épingler une réponse informative  
- Export Markdown  
- Export JSON  
- Import JSON en nouvelle conversation  
- Résumé automatique structuré  

### 📄 Lecture des PDF
- Sélectionner un PDF dans la liste  
- Affichage intégré via iframe  
- Lisible immédiatement dans le navigateur  

---

# 📊 Architecture du projet

```
rag-chatbot/
│── app.py                 # Interface Streamlit (chat, sessions, outils…)
│── rag_pipeline.py        # Pipeline RAG (retriever + prompt + LLM)
│── build_index.py         # Construction / actualisation de l’index Chroma
│── load_documents.py      # Chargement + découpage PDF/TXT/MD/DOCX
│── requirements.txt       # Dépendances
│── chat_sessions.json     # Sauvegarde multi-conversations
│── chroma/                # Base vectorielle persistante
│── data/                  # Documents utilisateur
│── README.md              # Documentation
```

---

# 🔧 Technologies utilisées

| Composant | Description |
|----------|-------------|
| **Streamlit** | Interface web simple et performante |
| **LangChain** | Orchestration du RAG |
| **ChromaDB** | Stockage vectoriel des embeddings |
| **Ollama** | Exécution locale des modèles |
| **llama3.2:1b** | LLM local pour la génération |
| **phi3:mini** | Modèle fallback |
| **nomic-embed-text** | Embeddings performants |

---

# 🧪 Tester le pipeline RAG

Quelques questions possibles :

- *"Donne-moi un résumé du document X ?"*
- *"Quels sont les points clés du chapitre 2 ?"*
- *"Explique-moi ce passage présent dans le PDF."*  
- *"Quelle réponse a été donnée dans la conversation précédente ?"*

---

# 👨‍💻 Auteur

**Amadou Lamine Faye**  
Master 2 – Intelligence Artificielle  
Université Lyon 1  

GitHub : https://github.com/laminefaye69100

---

# 📜 Licence

Projet disponible uniquement pour usage personnel et académique.  
Revente ou redistribution interdite sans autorisation.

---

Si tu veux une version encore plus professionnelle (badges, images, schémas UML du pipeline, GIF du chatbot, etc.), je peux la générer ! 🚀


---
## 📝 Notes supplémentaires

- Le RAG utilise **Ollama (CPU/GPU)** → fonctionne totalement **hors‑ligne**
- L’index est **persistant** → redémarrage possible sans reconstruction
- Aucun cloud → **données 100% privées**
- Compatible **Linux / macOS / Windows**
