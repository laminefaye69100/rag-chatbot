import os
os.environ["OLLAMA_NUM_GPU"] = "0"

from langchain.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatOllama
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# Dossier où Chroma va stocker les embeddings
DB_DIR = "chroma"  # simplifié pour correspondre à ton app.py

# ===============================
# 🧠 SYSTEM PROMPT : contexte
# ===============================
SYSTEM_PROMPT = """Tu es un assistant IA qui répond UNIQUEMENT avec le contexte fourni.
- Si l'information n'est pas présente dans le contexte, dis clairement que tu ne l'as pas.
- Réponds en français, de manière claire et structurée.
- Si possible, cite les sources à la fin.
--------------------
Contexte:
{context}

Question: {question}

Réponse:"""

# ===============================
# 🔎 RÉCUPÉRATION (RETRIEVER)
# ===============================
def make_retriever(db_dir=DB_DIR, k=3):
    """
    Crée un retriever basé sur les embeddings Ollama (nomic-embed-text).
    """
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vectordb = Chroma(persist_directory=db_dir, embedding_function=embeddings)
    return vectordb.as_retriever(search_kwargs={"k": k})

# ===============================
# 🔗 CHAÎNE PRINCIPALE RAG
# ===============================
def make_chain(db_dir=DB_DIR):
    """
    Construit la chaîne RAG complète :
    1. Récupération du contexte via embeddings.
    2. Génération de réponse avec modèle Ollama (local).
    """
    retriever = make_retriever(db_dir=db_dir, k=3)
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)

    # Sélection du modèle selon ce qui est dispo
    # (llama3.2:1b recommandé, sinon phi3:mini)
    try:
        llm = ChatOllama(model="llama3.2:1b", temperature=0.2)
    except Exception:
        llm = ChatOllama(model="phi3:mini", temperature=0.2)

    def format_docs(docs):
        out = []
        for d in docs:
            meta = d.metadata.get("source", "source inconnue")
            out.append(f"[{meta}] {d.page_content}")
        return "\n\n".join(out)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain

# ===============================
# 📊 STATISTIQUES D’INDEX
# ===============================
def get_index_stats(db_dir="chroma"):
    """
    Retourne le nombre de collections et de chunks indexés dans Chroma.
    """
    import chromadb
    client = chromadb.PersistentClient(db_dir)
    collections = client.list_collections()
    total_chunks = 0
    for col in collections:
        try:
            total_chunks += len(col.get()['ids'])
        except Exception:
            pass
    return {"collections": len(collections), "chunks": total_chunks}
