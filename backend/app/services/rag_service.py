import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Load embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize FAISS index (dimension = embedding size)
embedding_dim = 384
index = faiss.IndexFlatL2(embedding_dim)

# Store mapping for docs
documents = []

def add_documents(texts: list[str]):
    global documents
    embeddings = embedder.encode(texts)
    index.add(np.array(embeddings).astype("float32"))
    documents.extend(texts)

def search_documents(query: str, k: int = 3):
    query_vec = embedder.encode([query])
    D, I = index.search(np.array(query_vec).astype("float32"), k)
    results = [documents[i] for i in I[0] if i < len(documents)]
    return results