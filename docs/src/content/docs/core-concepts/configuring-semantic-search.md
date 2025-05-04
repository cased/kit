---
title: Configuring Semantic Search
---

Semantic search allows you to find code based on meaning rather than just keywords. To enable this in `kit`, you need to configure a vector embedding model and potentially a vector database backend.

## Required: Embedding Function

You must provide an embedding function (`embed_fn`) when first accessing semantic search features via `repo.get_vector_searcher()` or `repo.search_semantic()`.

This function takes a list of text strings and returns a list of corresponding embedding vectors.

```python
from kit import Repo
# Example using a hypothetical embedding function
from my_embedding_library import get_embeddings

repo = Repo("/path/to/repo")

# Define the embedding function wrapper if necessary
def embed_fn(texts: list[str]) -> list[list[float]]:
    # Adapt this to your specific embedding library/API
    return get_embeddings(texts)

# Pass the function when searching
results = repo.search_semantic("database connection logic", embed_fn=embed_fn)

# Or when getting the searcher explicitly
vector_searcher = repo.get_vector_searcher(embed_fn=embed_fn)
```

Popular choices include models from OpenAI, Cohere, or open-source models via libraries like Hugging Face's `sentence-transformers`.

## Optional: Backend and Persistence

By default, `kit` uses an in-memory Faiss index. For larger projects or persistence, you can specify a backend and a persistence directory.

(Details on supported backends and configuration options to be added.)

```python
# Example placeholder for future backend configuration
vector_searcher = repo.get_vector_searcher(
    embed_fn=embed_fn, 
    backend="chromadb", # Hypothetical backend
    persist_dir="./kit_vector_db" # Directory to save the index
)
```
