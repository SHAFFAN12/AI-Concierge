import faiss
import numpy as np
import asyncio
import os
import json
import logging

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load embedding model
# Note: SentenceTransformer is not thread-safe for parallel inference in some cases, 
# but for simple usage it's okay. We will run it in an executor.
embedder = None
if SentenceTransformer:
    try:
        embedder = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        logger.error(f"Failed to load SentenceTransformer: {e}")
else:
    logger.warning("SentenceTransformer not found. RAG functionality will be disabled.")

# Storage paths
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")
INDEX_PATH = os.path.join(STORAGE_DIR, "index.faiss")
DOCS_PATH = os.path.join(STORAGE_DIR, "documents.json")

# Ensure storage directory exists
os.makedirs(STORAGE_DIR, exist_ok=True)

# Initialize FAISS index
embedding_dim = 384
index = faiss.IndexFlatL2(embedding_dim)
documents = []

def save_index():
    """Save the FAISS index and documents to disk."""
    try:
        faiss.write_index(index, INDEX_PATH)
        with open(DOCS_PATH, "w", encoding="utf-8") as f:
            json.dump(documents, f)
        logger.info("✅ RAG Index and documents saved to disk.")
    except Exception as e:
        logger.error(f"❌ Failed to save RAG index: {e}")

def load_index():
    """Load the FAISS index and documents from disk if they exist."""
    global index, documents
    if os.path.exists(INDEX_PATH) and os.path.exists(DOCS_PATH):
        try:
            index = faiss.read_index(INDEX_PATH)
            with open(DOCS_PATH, "r", encoding="utf-8") as f:
                documents = json.load(f)
            logger.info(f"✅ Loaded RAG index with {len(documents)} documents.")
        except Exception as e:
            logger.error(f"❌ Failed to load RAG index: {e}")
            # Reset if load fails
            index = faiss.IndexFlatL2(embedding_dim)
            documents = []
    else:
        logger.info("ℹ️ No existing RAG index found. Starting fresh.")

# Load on module import (or can be called explicitly)
load_index()

async def add_documents(texts: list[str]):
    """Async wrapper to add documents and save index."""
    global documents
    
    if embedder is None:
        logger.warning("⚠️ RAG is disabled because SentenceTransformer is not available.")
        return

    loop = asyncio.get_running_loop()
    
    # Run blocking embedding generation in a thread pool
    embeddings = await loop.run_in_executor(None, embedder.encode, texts)
    
    # FAISS add is fast for small data, but good to be safe
    index.add(np.array(embeddings).astype("float32"))
    documents.extend(texts)
    
    # Save after adding
    await loop.run_in_executor(None, save_index)

async def search_documents(query: str, k: int = 3):
    """Async wrapper to search documents."""
    if embedder is None:
        logger.warning("⚠️ RAG is disabled because SentenceTransformer is not available.")
        return []

    loop = asyncio.get_running_loop()
    
    # Run blocking embedding generation in a thread pool
    query_vec = await loop.run_in_executor(None, embedder.encode, [query])
    
    # FAISS search
    D, I = index.search(np.array(query_vec).astype("float32"), k)
    
    results = [documents[i] for i in I[0] if i < len(documents)]
    return results