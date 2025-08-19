# Using Chroma Cloud with Kit

Kit now supports [Chroma Cloud](https://trychroma.com), a fully managed vector database service, as an alternative to local ChromaDB storage. This enables better scalability, team collaboration, and eliminates local storage constraints for large codebases.

## Getting Started

### 1. Sign up for Chroma Cloud

Sign up for a free account at [https://trychroma.com/signup](https://trychroma.com/signup)

### 2. Get your API credentials

After signing up, you'll receive:
- An API key
- Tenant information (defaults to `default_tenant`)
- Database information (defaults to `default_database`)

### 3. Configure Kit to use Chroma Cloud

Set the following environment variables:

```bash
# Required: Enable Chroma Cloud backend
export KIT_USE_CHROMA_CLOUD="true"

# Required: Your Chroma Cloud API key
export CHROMA_API_KEY="your-api-key-here"

# Optional: Specify tenant and database (defaults shown)
export CHROMA_TENANT="default_tenant"
export CHROMA_DATABASE="default_database"
```

### 4. Use Kit as normal

Once the environment variables are set, Kit will use Chroma Cloud instead of local storage:

```python
from kit import Repository, VectorSearcher

# Initialize repository
repo = Repository("/path/to/repo")

# Create vector searcher - will use Chroma Cloud automatically
searcher = VectorSearcher(repo, embed_fn=my_embed_function)

# Build index (stored in cloud)
searcher.build_index()

# Search
results = searcher.search("find authentication logic", top_k=5)
```

## Switching Between Local and Cloud

Kit determines which backend to use based on the `KIT_USE_CHROMA_CLOUD` environment variable:
- **`KIT_USE_CHROMA_CLOUD=true`**: Uses Chroma Cloud (requires `CHROMA_API_KEY`)
- **`KIT_USE_CHROMA_CLOUD=false` or unset**: Uses local ChromaDB storage

To switch back to local storage:
```bash
export KIT_USE_CHROMA_CLOUD="false"
# or simply unset it
unset KIT_USE_CHROMA_CLOUD
```

This approach ensures that having `CHROMA_API_KEY` set for other tools won't accidentally switch Kit to cloud mode.

## Programmatic Configuration

You can also explicitly create a cloud backend:

```python
from kit.vector_searcher import ChromaCloudBackend, VectorSearcher

# Create cloud backend explicitly
backend = ChromaCloudBackend(
    api_key="your-api-key",
    tenant="your-tenant",
    database="your-database",
    collection_name="my_project_index"
)

# Use with VectorSearcher
searcher = VectorSearcher(repo, embed_fn=my_embed_function, backend=backend)
```

## Migration

### From Local to Cloud
1. Set up Chroma Cloud credentials
2. Rebuild your indexes (they'll be stored in cloud)

### From Cloud to Local
1. Unset `CHROMA_API_KEY`
2. Rebuild your indexes locally

## Troubleshooting

### Authentication Error
If you see "Chroma Cloud API key not found", ensure:
1. `KIT_USE_CHROMA_CLOUD` is set to `"true"`
2. `CHROMA_API_KEY` is properly set
3. The API key is valid and active

### Collection Name Conflicts
Different projects will use different collection names by default:
- VectorSearcher: `kit_code_chunks`
- DocstringIndexer: `kit_docstring_index`

You can customize these when creating backends explicitly.

## Advanced Configuration

### Custom Collection Names
```python
backend = ChromaCloudBackend(collection_name="my_custom_collection")
```

### Multiple Projects
Use different collection names or databases for different projects:
```python
backend_project_a = ChromaCloudBackend(collection_name="project_a_index")
backend_project_b = ChromaCloudBackend(collection_name="project_b_index")
```

### Environment-specific Configuration
```bash
# Development
export CHROMA_DATABASE="dev_database"

# Production
export CHROMA_DATABASE="prod_database"
```