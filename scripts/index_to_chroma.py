#!/usr/bin/env python
"""Index a repository to Chroma Cloud for semantic search.

Usage:
    python scripts/index_to_chroma.py [--rebuild]
    
Options:
    --rebuild: Delete existing collection and rebuild from scratch
"""

import os
import sys
from pathlib import Path
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kit import Repository
from kit.vector_searcher import VectorSearcher

# Check if sentence-transformers is available
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer('all-MiniLM-L6-v2')
    def embed_fn(text):
        return model.encode(text).tolist()
    print("Using SentenceTransformer embeddings")
except ImportError:
    # Fallback embeddings
    import hashlib
    def embed_fn(text):
        hash_obj = hashlib.sha256(text.encode())
        extended = (hash_obj.digest() * 12)[:384]
        return [float(b) / 255.0 for b in extended]
    print("Using fallback embeddings (install sentence-transformers for better results)")

def main():
    parser = argparse.ArgumentParser(description="Index repository to Chroma Cloud")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index from scratch")
    args = parser.parse_args()
    
    print("\nIndexing Repository to Chroma Cloud")
    print("=" * 50)
    
    # Check if cloud is enabled
    if os.environ.get("KIT_USE_CHROMA_CLOUD", "").lower() != "true":
        print("⚠️  Chroma Cloud is not enabled!")
        print("Set these environment variables:")
        print("  export KIT_USE_CHROMA_CLOUD=true")
        print("  export CHROMA_API_KEY='your-api-key'")
        print("  export CHROMA_TENANT='your-tenant-uuid'")
        print("  export CHROMA_DATABASE='your-database'")
        return 1
    
    # Initialize repository
    repo_path = Path.cwd()
    print(f"Repository: {repo_path}")
    repo = Repository(str(repo_path))
    
    # Create vector searcher
    searcher = VectorSearcher(repo, embed_fn=embed_fn)
    print(f"Backend: {type(searcher.backend).__name__}")
    
    if args.rebuild and "Cloud" in type(searcher.backend).__name__:
        print("\n⚠️  Rebuild flag set - clearing existing data...")
        # For cloud, we need to delete and recreate the collection
        import chromadb
        client = chromadb.CloudClient(
            api_key=os.environ.get("CHROMA_API_KEY"),
            tenant=os.environ.get("CHROMA_TENANT"),
            database=os.environ.get("CHROMA_DATABASE")
        )
        try:
            client.delete_collection("kit_code_chunks")
            print("  Deleted existing collection")
        except:
            pass
        # Recreate searcher to get fresh collection
        searcher = VectorSearcher(repo, embed_fn=embed_fn)
    
    # Check initial count
    initial_count = searcher.backend.count()
    print(f"\nInitial items in collection: {initial_count}")
    
    # Build index
    print("\nBuilding index (this may take a few minutes)...")
    print("Indexing by symbols (functions, classes, etc.)...")
    
    try:
        searcher.build_index(chunk_by="symbols")
        
        # Check final count
        final_count = searcher.backend.count()
        added = final_count - initial_count
        
        print(f"\n✓ Indexing complete!")
        print(f"  Total items: {final_count}")
        if added > 0:
            print(f"  Added: {added} new items")
        
        # Test search
        print("\nTesting search...")
        test_query = "vector search"
        results = searcher.search(test_query, top_k=3)
        
        if results:
            print(f"Found {len(results)} results for '{test_query}':")
            for i, result in enumerate(results, 1):
                file = result.get('file', 'unknown')
                name = result.get('name', '')
                score = result.get('score', 0)
                print(f"  {i}. {file} :: {name} (score: {score:.4f})")
        
        print("\n✓ Repository successfully indexed to Chroma Cloud!")
        print("  You can now search your codebase from anywhere!")
        
    except Exception as e:
        print(f"\n✗ Error during indexing: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())