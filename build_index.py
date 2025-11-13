# build_index.py
from pathlib import Path
import os
from load_documents import load_all_documents, split_docs
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma


# Répertoire des embeddings
DB_DIR = "chroma"


def build_index(data_dir="data", persist_dir=DB_DIR, embed_model="nomic-embed-text"):
    """
    Construit l'index Chroma à partir des documents PDF/TXT/MD/DOCX dans ./data.
    """
    print("🔍 Chargement des documents...")

    docs = load_all_documents(data_dir)
    chunks = split_docs(docs)

    if not chunks:
        print("❌ [ERREUR] Aucun document trouvé dans ./data/")
        return

    print(f"📄 {len(docs)} documents chargés, {len(chunks)} chunks générés.")
    print("🧠 Génération des embeddings avec Ollama...")

    # Désactive le GPU pour Ollama (utile sur CPU)
    os.environ["OLLAMA_NUM_GPU"] = "0"

    # Embeddings Ollama
    embeddings = OllamaEmbeddings(model=embed_model)

    # Création du vecteurstore
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir
    )

    print(f"✅ [OK] Index mis à jour ({vectordb._collection.count()} chunks) → {persist_dir}")


if __name__ == "__main__":
    Path(DB_DIR).mkdir(parents=True, exist_ok=True)
    build_index()
