import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb import (
        CloudClient,  # type: ignore[attr-defined]
        PersistentClient,  # type: ignore[attr-defined]
    )
except ImportError:
    chromadb = None  # type: ignore[assignment]
    CloudClient = None  # type: ignore[assignment]


def _resolve_batch_size(collection: Any, default: int = 2000) -> int:
    """Derive a safe batch size for collection.add calls."""

    env_value = os.environ.get("KIT_CHROMA_BATCH_SIZE")
    if env_value:
        try:
            env_batch = int(env_value)
            if env_batch > 0:
                default = env_batch
            else:
                logger.warning("Ignoring non-positive KIT_CHROMA_BATCH_SIZE=%s", env_value)
        except ValueError:
            logger.warning("Ignoring invalid KIT_CHROMA_BATCH_SIZE=%s", env_value)

    try:
        client = getattr(collection, "_client", None)
        settings = getattr(client, "_settings", None)
        limit = getattr(settings, "max_batch_size", None)
        if isinstance(limit, int) and limit > 0:
            return min(default, limit)
    except Exception:  # pragma: no cover - best effort only
        pass

    return max(1, default)


class VectorDBBackend:
    """
    Abstract vector DB interface for pluggable backends.
    """

    def add(self, embeddings: List[List[float]], metadatas: List[Dict[str, Any]], ids: Optional[List[str]] = None):
        raise NotImplementedError

    def query(self, embedding: List[float], top_k: int) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def persist(self):
        pass

    def delete(self, ids: List[str]):
        """Remove vectors by their IDs. Backends that don't support fine-grained deletes may no-op."""
        raise NotImplementedError

    def count(self) -> int:
        raise NotImplementedError


class ChromaDBBackend(VectorDBBackend):
    def __init__(self, persist_dir: str, collection_name: Optional[str] = None):
        if chromadb is None:
            raise ImportError("chromadb is not installed. Run 'pip install chromadb'.")
        self.persist_dir = persist_dir
        self.client = PersistentClient(path=self.persist_dir)
        self.is_local = True  # Flag to identify local backend

        final_collection_name = collection_name
        if final_collection_name is None:
            # Use a collection name scoped to persist_dir to avoid dimension clashes across multiple tests/processes
            final_collection_name = f"kit_code_chunks_{abs(hash(persist_dir))}"
        self.collection_name = final_collection_name
        self.collection = self.client.get_or_create_collection(self.collection_name)
        self._batch_size = _resolve_batch_size(self.collection)

    def add(self, embeddings, metadatas, ids: Optional[List[str]] = None):
        # Skip adding if there is nothing to add (prevents ChromaDB error)
        if not embeddings or not metadatas:
            return
        if len(embeddings) != len(metadatas):
            raise ValueError("Embeddings and metadatas must be the same length.")
        if ids is not None and len(ids) != len(embeddings):
            raise ValueError("The number of IDs must match the number of embeddings and metadatas.")

        self._reset_collection()

        final_ids = ids or [str(i) for i in range(len(metadatas))]
        batch_size = max(1, self._batch_size or len(embeddings))
        for start in range(0, len(embeddings), batch_size):
            end = start + batch_size
            batch_embeddings = embeddings[start:end]
            batch_metadatas = metadatas[start:end]
            batch_ids = final_ids[start:end]
            self.collection.add(embeddings=batch_embeddings, metadatas=batch_metadatas, ids=batch_ids)

    def query(self, embedding, top_k):
        if top_k <= 0:
            return []
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

    def count(self) -> int:
        return self.collection.count()

    # ------------------------------------------------------------------
    # Incremental-index support helpers
    # ------------------------------------------------------------------
    def delete(self, ids: List[str]):
        """Delete vectors by ID if the underlying collection supports it."""
        if not ids:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception:
            # Some Chroma versions require where filter; fall back to no-op
            pass

    def _reset_collection(self) -> None:
        """Ensure we start from a clean collection before bulk re-add."""
        try:
            if self.collection.count() > 0:
                cleared = False
                try:
                    self.client.delete_collection(self.collection_name)
                    cleared = True
                except Exception:
                    pass

                if not cleared:
                    try:
                        self.collection.delete(where={"source": {"$ne": "__kit__never__"}})
                        cleared = True
                    except Exception:
                        pass

                if not cleared:
                    try:
                        existing = self.collection.get(include=[])
                        ids = existing.get("ids") if isinstance(existing, dict) else None
                        if ids:
                            self.collection.delete(ids=list(ids))
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            self.collection = self.client.get_or_create_collection(self.collection_name)
            self._batch_size = _resolve_batch_size(self.collection)


class ChromaCloudBackend(VectorDBBackend):
    """ChromaDB Cloud backend for vector search using Chroma's managed cloud service."""

    def __init__(
        self,
        collection_name: Optional[str] = None,
        api_key: Optional[str] = None,
        tenant: Optional[str] = None,
        database: Optional[str] = None,
    ):
        if chromadb is None or CloudClient is None:
            raise ImportError("chromadb is not installed. Run 'pip install chromadb'.")
        self.is_local = False  # Flag to identify cloud backend

        # Get credentials from environment if not provided
        api_key = api_key or os.environ.get("CHROMA_API_KEY")
        tenant = tenant or os.environ.get("CHROMA_TENANT")
        database = database or os.environ.get("CHROMA_DATABASE")

        if not database:
            raise ValueError(
                "Chroma Cloud database not specified. Set CHROMA_DATABASE environment variable "
                "or pass database directly. Create a database in your Chroma Cloud dashboard first."
            )

        if not tenant:
            raise ValueError(
                "Chroma Cloud tenant not specified. Set CHROMA_TENANT environment variable "
                "(check your Chroma Cloud dashboard for your tenant UUID) or pass tenant directly."
            )

        # Validate tenant UUID format
        uuid_pattern = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)
        if not uuid_pattern.match(tenant):
            raise ValueError(
                f"Invalid tenant format: '{tenant}'. "
                "Chroma Cloud requires a valid UUID (e.g., '3893b771-b971-4f45-8e30-7aac7837ad7f'). "
                "Check your Chroma Cloud dashboard for your tenant UUID."
            )

        if not api_key:
            raise ValueError(
                "Chroma Cloud API key not found. Set CHROMA_API_KEY environment variable or pass api_key directly."
            )

        self.client = CloudClient(
            tenant=tenant,
            database=database,
            api_key=api_key,
        )

        final_collection_name = collection_name or "kit_code_chunks"
        self.collection_name = final_collection_name
        self.collection = self.client.get_or_create_collection(self.collection_name)
        self._batch_size = _resolve_batch_size(self.collection)

    def add(self, embeddings, metadatas, ids: Optional[List[str]] = None):
        # Skip adding if there is nothing to add (prevents ChromaDB error)
        if not embeddings or not metadatas:
            return

        # Note: For cloud backend, we append data instead of clearing
        # This preserves data across sessions and allows incremental updates
        # If you need to clear, manually delete the collection in the dashboard

        if len(embeddings) != len(metadatas):
            raise ValueError("Embeddings and metadatas must be the same length.")
        if ids is not None and len(ids) != len(embeddings):
            raise ValueError("The number of IDs must match the number of embeddings and metadatas.")

        final_ids = ids or [str(i) for i in range(len(metadatas))]
        batch_size = max(1, self._batch_size or len(embeddings))
        for start in range(0, len(embeddings), batch_size):
            end = start + batch_size
            batch_embeddings = embeddings[start:end]
            batch_metadatas = metadatas[start:end]
            batch_ids = final_ids[start:end]
            self.collection.add(embeddings=batch_embeddings, metadatas=batch_metadatas, ids=batch_ids)

    def query(self, embedding, top_k):
        if top_k <= 0:
            return []
        results = self.collection.query(query_embeddings=[embedding], n_results=top_k)
        hits = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            meta["score"] = results["distances"][0][i]
            hits.append(meta)
        return hits

    def persist(self):
        # Cloud backend auto-persists, no action needed
        pass

    def count(self) -> int:
        return self.collection.count()

    def delete(self, ids: List[str]):
        """Delete vectors by ID."""
        if not ids:
            return
        try:
            self.collection.delete(ids=ids)
        except Exception:
            pass


def get_default_backend(persist_dir: Optional[str] = None, collection_name: Optional[str] = None) -> VectorDBBackend:
    """
    Factory function to create the appropriate backend based on environment configuration.

    Checks KIT_USE_CHROMA_CLOUD environment variable to determine backend:
    - If KIT_USE_CHROMA_CLOUD is "true" and CHROMA_API_KEY is set: uses ChromaCloudBackend
    - Otherwise: uses local ChromaDBBackend

    Args:
        persist_dir: Directory for local persistence (ignored for cloud backend)
        collection_name: Name of the collection to use

    Returns:
        VectorDBBackend instance
    """
    use_cloud = os.environ.get("KIT_USE_CHROMA_CLOUD", "").lower() == "true"

    if use_cloud:
        api_key = os.environ.get("CHROMA_API_KEY")
        if not api_key:
            raise ValueError(
                "KIT_USE_CHROMA_CLOUD is set to true but CHROMA_API_KEY is not found. "
                "Please set CHROMA_API_KEY environment variable or set KIT_USE_CHROMA_CLOUD=false"
            )
        return ChromaCloudBackend(collection_name=collection_name)
    else:
        if persist_dir is None:
            raise ValueError("persist_dir is required for local ChromaDB backend")
        return ChromaDBBackend(persist_dir, collection_name)


class VectorSearcher:
    def __init__(self, repo, embed_fn, backend: Optional[VectorDBBackend] = None, persist_dir: Optional[str] = None):
        self.repo = repo
        self.embed_fn = embed_fn  # Function: str -> List[float]
        # Make persist_dir relative to repo path if not absolute
        if persist_dir is None:
            self.persist_dir = os.path.join(str(self.repo.local_path), ".kit", "vector_db")
        elif os.path.isabs(persist_dir):
            self.persist_dir = persist_dir
        else:
            self.persist_dir = os.path.join(str(self.repo.local_path), persist_dir)

        # Use factory function if no backend provided
        if backend is None:
            backend = get_default_backend(self.persist_dir, collection_name="kit_code_chunks")
        self.backend = backend
        self.chunk_metadatas: List[Dict[str, Any]] = []
        self.chunk_embeddings: List[List[float]] = []

    def build_index(self, chunk_by: str = "symbols"):
        self.chunk_metadatas = []
        chunk_codes: List[str] = []

        for file in self.repo.get_file_tree():
            if file["is_dir"]:
                continue
            path = file["path"]
            if chunk_by == "symbols":
                chunks = self.repo.chunk_file_by_symbols(path)
                for chunk in chunks:
                    code = chunk["code"]
                    self.chunk_metadatas.append({"file": path, **chunk})
                    chunk_codes.append(code)
            else:
                chunks = self.repo.chunk_file_by_lines(path, max_lines=50)
                for code in chunks:
                    self.chunk_metadatas.append({"file": path, "code": code})
                    chunk_codes.append(code)

        # Embed in batch (attempt). Fallback to per-item if embed_fn doesn't support list input.
        if chunk_codes:
            self.chunk_embeddings = self._batch_embed(chunk_codes)
            self.backend.add(self.chunk_embeddings, self.chunk_metadatas)
            self.backend.persist()

    def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts, falling back to per-item calls if necessary."""
        try:
            bulk = self.embed_fn(texts)  # type: ignore[arg-type]
            if isinstance(bulk, list) and len(bulk) == len(texts) and all(isinstance(v, (list, tuple)) for v in bulk):
                return [list(map(float, v)) for v in bulk]  # ensure list of list[float]
        except Exception:
            pass  # Fall back to per-item
        # Fallback slow path
        return [self.embed_fn(t) for t in texts]

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if top_k <= 0:
            return []
        emb = self.embed_fn(query)
        return self.backend.query(emb, top_k)
