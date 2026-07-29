import os
import glob

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.config import settings

DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs")


def get_embeddings():
    return GoogleGenerativeAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
    )


def get_qdrant_client() -> QdrantClient:
    if settings.QDRANT_URL:
        return QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None)
    path = os.path.join(os.path.dirname(__file__), "..", "data", "qdrant_local")
    return QdrantClient(path=path)


def ensure_collection(client: QdrantClient):
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=settings.EMBEDDING_DIM, distance=Distance.COSINE),
        )


def load_documents():
    docs = []
    for path in glob.glob(os.path.join(DOCS_DIR, "*")):
        if path.lower().endswith(".pdf"):
            docs.extend(PyPDFLoader(path).load())
        elif path.lower().endswith(".txt") or path.lower().endswith(".md"):
            docs.extend(TextLoader(path, encoding="utf-8").load())
    return docs


def build_vectorstore() -> QdrantVectorStore:
    client = get_qdrant_client()
    ensure_collection(client)

    docs = load_documents()
    if docs:
        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
        print(f"Loaded {len(docs)} document(s) -> {len(chunks)} chunks")

    vectorstore = QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=get_embeddings(),
    )

    if docs:
        vectorstore.add_documents(chunks)
        print(f"Stored {len(chunks)} chunks in Qdrant collection '{settings.QDRANT_COLLECTION}'")
    else:
        print(f"No documents found in {DOCS_DIR} — drop .pdf/.txt files there and rerun.")

    return vectorstore


if __name__ == "__main__":
    vs = build_vectorstore()

    test_query = "What is this document about?"
    try:
        results = vs.similarity_search(test_query, k=2)
        print(f"\nTest query: '{test_query}'")
        for i, r in enumerate(results, 1):
            print(f"  [{i}] {r.page_content[:150]}...")
    except Exception as e:
        print(f"Test search skipped (probably no documents yet): {e}")
