from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredWordDocumentLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_all_documents(data_dir="data"):
    """
    Charge tous les documents depuis un dossier :
    - PDF → via PyPDFLoader
    - TXT / MD → via TextLoader
    - DOCX → via UnstructuredWordDocumentLoader
    Retourne une liste de documents LangChain.
    """
    docs = []
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"❌ [ERREUR] Dossier '{data_dir}' introuvable.")
        return []

    for p in data_path.rglob("*"):
        if not p.is_file():
            continue

        try:
            if p.suffix.lower() == ".pdf":
                docs.extend(PyPDFLoader(str(p)).load())
            elif p.suffix.lower() in [".txt", ".md"]:
                docs.extend(TextLoader(str(p), encoding="utf-8").load())
            elif p.suffix.lower() in [".docx"]:
                docs.extend(UnstructuredWordDocumentLoader(str(p)).load())
        except Exception as e:
            print(f"⚠️ [WARN] Impossible de charger {p.name}: {e}")

    print(f"📄 {len(docs)} documents chargés depuis '{data_dir}'.")
    return docs


def split_docs(docs, chunk_size=800, chunk_overlap=120):
    """
    Divise les documents en morceaux (chunks) pour l’indexation.
    """
    if not docs:
        print("⚠️ Aucun document à découper.")
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ".", "!", "?", " "]
    )

    chunks = splitter.split_documents(docs)
    print(f"🔪 {len(chunks)} chunks créés (taille={chunk_size}, chevauchement={chunk_overlap})")
    return chunks


if __name__ == "__main__":
    docs = load_all_documents("data")
    print(f"[INFO] Documents bruts : {len(docs)}")
    chunks = split_docs(docs)
    print(f"[INFO] Chunks après découpe : {len(chunks)}")
