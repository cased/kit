import os
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from pathlib import Path

class VectorDBBackend:
    """
    Abstract vector DB interface for pluggable backends.
    """
    def add(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]]):
        raise NotImplementedError
    def query(self, embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
        raise NotImplementedError
    def persist(self):
        pass

class ChromaDBBackend(VectorDBBackend):
    def __init__(self, persist_dir: str):
        if chromadb is None:
            raise ImportError("chromadb is not installed. Run 'pip install chromadb'.")
        self.persist_dir = persist_dir
        self.client = chromadb.Client(Settings(persist_directory=persist_dir))
        self.collection = self.client.get_or_create_collection("kit_code_chunks")
    def add(self, embeddings, metadatas):
        ids = [str(i) for i in range(len(metadatas))]
        self.collection.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
    def query(self, embedding, top_k):
        results = self.collection.query(query_embeddings=[embedding], n_results=top_k)
        hits = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            meta["score"] = results["distances"][0][i]
            hits.append(meta)
        return hits
    def persist(self):
        # ChromaDB v1.x does not require or support explicit persist, it is automatic.
        pass

class VectorSearcher:
    def __init__(self, repo, embed_fn, backend: Optional[VectorDBBackend] = None, persist_dir: Optional[str] = None):
        self.repo = repo
        self.embed_fn = embed_fn  # Function: str -> List[float]
        self.persist_dir = persist_dir or os.path.join(".kit", "vector_db")
        self.backend = backend or ChromaDBBackend(self.persist_dir)
        self.chunk_metadatas: List[Dict[str, Any]] = []
        self.chunk_embeddings: List[List[float]] = []
    def build_index(self, chunk_by: str = "symbols"):
        self.chunk_metadatas = []
        self.chunk_embeddings = []
        for file in self.repo.get_file_tree():
            if not file["is_dir"]:
                path = file["path"]
                if chunk_by == "symbols":
                    chunks = self.repo.chunk_file_by_symbols(path)
                    for chunk in chunks:
                        code = chunk["code"]
                        emb = self.embed_fn(code)
                        meta = {"file": path, **chunk}
                        self.chunk_metadatas.append(meta)
                        self.chunk_embeddings.append(emb)
                else:
                    chunks = self.repo.chunk_file_by_lines(path, max_lines=50)
                    for code in chunks:
                        emb = self.embed_fn(code)
                        meta = {"file": path, "code": code}
                        self.chunk_metadatas.append(meta)
                        self.chunk_embeddings.append(emb)
        self.backend.add(self.chunk_embeddings, self.chunk_metadatas)
        self.backend.persist()
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        emb = self.embed_fn(query)
        return self.backend.query(emb, top_k)
