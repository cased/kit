# kit: Code Intelligence Toolkit

A modular, production-grade toolkit for codebase mapping, symbol extraction, code search, and LLM-powered developer workflows. Supports multi-language codebases via `tree-sitter`.

Features a "mid-level API" to build your own custom tools, LLM workflows, and automation: easily build code review bots, semantic code search, documentation generators, and more.

---

## What You Can Build
- **AI-powered code review bots** — Automatically review code changes using LLMs and extracted code context.
- **Semantic code search** — Search for symbols, functions, or patterns across multi-language repos.
- **Automated documentation generators** — Extract code structure and docstrings to build up-to-date docs.
- **Codebase summarizers** — Summarize files, modules, or entire repos for onboarding or LLM context.
- **Dependency graph visualizers** — Visualize code relationships and dependencies for better understanding.
- Multi-language symbol extraction, chunking, and more for Python, JS, Go, HCL, etc.

---

## Table of Contents
- [Features](#features)
- [Quickstart](#quickstart)
- [Core API Primitives](#core-api-primitives)
- [High-Level API](#high-level-api)
- [Semantic (Vector) Search](#semantic-vector-search)
- [Architecture](#architecture)
- [Composing Primitives for Advanced Workflows](#composing-primitives-for-advanced-workflows)
- [Extending Language Support](#extending-language-support)
- [Running Tests](#running-tests)
- [Vision](#vision)
- [File and Directory Exclusion (.gitignore support)](#file-and-directory-exclusion-gitignore-support)

---

## Features
- Multi-language symbol extraction (Python, Go, JS, HCL, ...)
- Query-driven, extensible via tree-sitter `tags.scm`
- Fast file tree and codebase indexing
- Regex/text code search with match details
- Context chunking for LLMs (by lines, by symbols, by scope)
- Unified API for downstream tools, CLI, and LLM workflows
- Robust, type-checked, and fully tested
- Cross-file Impact Detection: Find all usages of a symbol (definition and references) across the codebase


## Quickstart
```bash
git clone https://github.com/cased/kit.git
cd kit
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

---

## Instantiating the Repo Class

You can use a local path or a remote GitHub repository. For private repos, pass a GitHub token.

```python
from kit.repo import Repo
# Local codebase
repo = Repo("/path/to/your/codebase")

# Remote public GitHub repo
repo = Repo("https://github.com/owner/repo")

# Remote private GitHub repo (with token)
repo = Repo("https://github.com/owner/private-repo", github_token="YOUR_TOKEN")
```

---

## Core API Primitives

Below are the main primitives provided by the `Repo` class. Each is documented with its purpose, usage, and example code.

### 1. Get File Tree
**Purpose:** List all files and directories in the repo, with metadata for navigation, search, and tooling.

```python
files = repo.get_file_tree()
# Example output:
# [
#   {"path": "src/kit/repo.py", "is_dir": False, "name": "repo.py", "size": 2048},
#   {"path": "src/kit", "is_dir": True, "name": "kit", "size": 0},
#   ...
# ]
```

### 2. Extract Symbols
**Purpose:** Extracts all top-level symbols (functions, classes, etc.) from the repo or a file, enabling code navigation, documentation, and LLM context.

```python
symbols = repo.extract_symbols()
# Example output (all symbols in repo):
# [
#   {"name": "Repo", "type": "class", "file": "src/kit/repo.py"},
#   {"name": "extract_symbols", "type": "function", "file": "src/kit/repo_mapper.py"},
#   ...
# ]

symbols_py = repo.extract_symbols("foo.py")
# Example output (symbols in foo.py):
# [
#   {"name": "Foo", "type": "class", "file": "foo.py"},
#   {"name": "bar", "type": "function", "file": "foo.py"},
#   ...
# ]
```

### 3. Search Code (Text/Regex)
**Purpose:** Search for text or regex patterns in code, returning file, line, and context. Useful for quick lookups, refactoring, and static analysis.

```python
matches = repo.search_text("def foo")
# Example output:
# [
#   {"file": "src/kit/repo.py", "line_number": 10, "line": "def foo():", "match": "def foo"},
#   {"file": "src/kit/other.py", "line_number": 20, "line": "def foo():", "match": "def foo"},
#   ...
# ]
```

### 4. Chunk File by Lines
**Purpose:** Split a file into blocks of N lines for LLM context windows, summarization, or chunked embeddings.

```python
chunks = repo.chunk_file_by_lines("foo.py", max_lines=50)
# Example output:
# [
#   "def foo():\n    pass",
#   "class Bar:\n    ...",
#   ...
# ]
```

### 5. Chunk File by Symbols
**Purpose:** Split a file into code blocks by symbol (function, class, etc.), enabling symbol-aware LLM prompts and embeddings.

```python
symbol_chunks = repo.chunk_file_by_symbols("foo.py")
# Example output:
# [
#   {"name": "foo", "type": "function", "code": "def foo():\n    pass"},
#   {"name": "Bar", "type": "class", "code": "class Bar:\n    ..."},
#   ...
# ]
```

### 6. Context Extraction Around Line
**Purpose:** Find the function/class/code block that contains a given line number, for precise LLM prompts, inline review, or navigation.

```python
ctx = repo.extract_context_around_line("foo.py", 10)
# Example output:
# {"name": "foo", "type": "function", "code": "def foo():\n    pass"}
```

### 7. Cross-file Impact Detection
**Purpose:** Find all usages (definitions and references) of a symbol across the entire repo. Enables refactoring, review, and LLM-powered impact analysis.

```python
usages = repo.find_symbol_usages("foo", symbol_type="function")
# Example output:
# [
#   {"file": "src/kit/repo.py", "type": "function", "name": "foo", "line": 42, "context": "def foo(): ..."},
#   {"file": "src/kit/other.py", "line": 10, "context": "foo()  # call"},
#   ...
# ]
```

---

## File and Directory Exclusion (.gitignore support)

By default, kit automatically ignores files and directories listed in your `.gitignore` as well as `.git/` and its contents. This ensures your indexes, symbol extraction, and searches do not include build artifacts, dependencies, or version control internals.

**Override:**
- This behavior is the default. If you want to include ignored files, you can override this by modifying the `RepoMapper` logic (see `src/kit/repo_mapper.py`) or subclassing it with custom exclusion rules.

---

## Semantic (Vector) Search

kit supports semantic code search using vector embeddings and ChromaDB.

### How it works
- Chunks your codebase (by symbols or lines)
- Embeds each chunk using your chosen model (OpenAI, HuggingFace, etc)
- Stores embeddings in a local ChromaDB vector database
- Lets you search for code using natural language or code-like queries

### Example Usage
```python
from kit import Repo
from sentence_transformers import SentenceTransformer

# Use any embedding model you like
model = SentenceTransformer("all-MiniLM-L6-v2")
def embed_fn(text):
    return model.encode([text])[0].tolist()

repo = Repo("/path/to/codebase")
vs = repo.get_vector_searcher(embed_fn=embed_fn)
vs.build_index()  # Index all code chunks (run once, or after code changes)

results = repo.search_semantic("How is authentication handled?", embed_fn=embed_fn)
for hit in results:
    print(hit["file"], hit.get("name"), hit.get("type"), hit.get("code"))
# Example output:
# src/kit/auth.py login function def login(...): ...
# src/kit/config.py AUTH_CONFIG variable AUTH_CONFIG = {...}
```

### Pluggable Backend
- By default, uses ChromaDB (local, persistent, fast)
- You can implement your own backend by subclassing `VectorDBBackend`

### Notes
- No hard dependency on ChromaDB unless you use semantic search
- Embedding model is fully pluggable (OpenAI, HuggingFace, etc)
- You can chunk by symbols or lines (see `build_index(chunk_by=...)`)

---

## Repo Convenience Methods: Exporting Data

The `Repo` class provides several helpers to export repository data as JSON files for downstream tools, LLMs, or analysis:

```python
repo.write_index("repo_index.json")
# Writes the full repo index (file tree and symbols) to repo_index.json

repo.write_symbols("symbols.json")
# Writes all extracted symbols from the repo to symbols.json

repo.write_file_tree("file_tree.json")
# Writes the file tree to file_tree.json

repo.write_symbol_usages("foo", "usages.json", symbol_type="function")
# Writes all usages of the symbol 'foo' (functions) to usages.json
```

Each method takes a path to the output file. You can use these for documentation, code search, LLM pipelines, or impact analysis.

---

## Composing Primitives for Advanced Workflows

The primitives in `kit` are designed to be composable. You can combine them to build advanced developer tools, LLM workflows, and automation. `kit` is designed to give you whole repo context, so you can build tools that work at the scale of the codebase.

Here are some common patterns:

### Example: LLM-Powered Code Review with Impact Analysis

1. **Summarize the change:** Use `extract_symbols` and `chunk_file_by_lines` to summarize changed files or symbols for the LLM.
2. **Get context:** Use `extract_context_around_line` to provide precise code context for each change.
3. **Detect cross-file impact:** Use `find_symbol_usages` to find all usages of changed symbols across the repo.
4. **Present to LLM:** Feed the summary, context, and impact info into your LLM prompt for deep, context-aware review.

```python
from kit import Repo
repo = Repo("/path/to/codebase")

# 1. Summarize change
symbols = repo.extract_symbols("foo.py")
chunks = repo.chunk_file_by_lines("foo.py", max_lines=30)

# 2. Get context for a changed line
ctx = repo.extract_context_around_line("foo.py", 23)

# 3. Find all usages of a changed function
usages = repo.find_symbol_usages("foo", symbol_type="function")

# 4. Compose all info for LLM prompt
prompt = f"""
File: foo.py
Changed symbols: {symbols}
Context around line 23: {ctx}
Cross-file usages of 'foo': {usages}
"""
# ...pass your custom prompt to your LLM
```

### Other Composition Ideas
- **Automated Documentation:** Extract all symbols, chunk by symbol, and generate summaries for each to auto-build docs.
- **Refactoring Safety:** Before renaming a symbol, use `find_symbol_usages` to find all references and update them safely.
- **Dependency Graphs:** Combine `extract_symbols` with `find_symbol_usages` to build call graphs or resource dependency maps.

---

## Architecture
- **Repo**: Unified API for file tree, symbols, search, context, and indexing.
- **RepoMapper**: Scans repo, builds file tree, extracts symbols (Python AST or tree-sitter).
- **TreeSitterSymbolExtractor**: Loads `tags.scm` for each language and extracts symbols via queries.
- **ContextExtractor**: Chunks files by lines, symbols, or scope; extracts context for LLMs.
- **CodeSearcher**: Fast regex/text search with file pattern support.

**Why this design?**
- Separates concerns for maintainability and extensibility.
- Enables easy support for new languages and workflows.
- Designed for LLM and code intelligence use cases from the ground up.

---

## Extending Language Support
- To add a new language:
  1. Add a tree-sitter grammar and build it (see [tree-sitter docs](https://tree-sitter.github.io/tree-sitter/creating-parsers)).
  2. Add a `queries/<lang>/tags.scm` file with queries for symbols you want to extract.
  3. Add the file extension to `TreeSitterSymbolExtractor.LANGUAGES`.
  4. Write/expand tests for the new language.

**Why?**
- This approach lets you support any language with a tree-sitter grammar—no need to change core logic.
- `tags.scm` queries make symbol extraction flexible and community-driven.

---

## Running Tests

To run tests using uv and pytest:

```sh
uv pip install -e .[dev]
uv pip install pytest
uv pytest
```

Or to run a specific test file:

```sh
uv pytest tests/test_hcl_symbols.py
```

---

## Vision
kit aims to be the foundation for state-of-the-art IDEs, LLM-powered code tools, and advanced code intelligence workflows.

---

## License

MIT License

---
