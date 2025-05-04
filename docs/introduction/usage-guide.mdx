---
title: Usage Guide
---

This guide provides practical examples of how to use the core `Repo` object in `kit` to interact with your codebase.

## Initializing a `Repo`

First, create an instance of the `Repo` class, pointing it to your code. `kit` can work with local directories or clone remote Git repositories.
This is the starting point for any analysis, giving `kit` access to the codebase.

### Local Directory

If your code is already on your machine:

```python
from kit import Repo

repo = Repo("/path/to/your/local/project")
```

### Remote Git Repository

`kit` can clone a public or private Git repository. For private repos, provide a GitHub token.

```python
# Public repo
repo = Repo("https://github.com/owner/repo-name")

# Private repo (requires token)
# Ensure the token has appropriate permissions
github_token = "your_github_pat_here"
repo = Repo("https://github.com/owner/private-repo-name", github_token=github_token)
```

### Caching

When cloning remote repositories, `kit` caches them locally to speed up subsequent initializations. By default, caches are stored in a temporary directory. You can specify a persistent cache directory:

```python
repo = Repo(
    "https://github.com/owner/repo-name", 
    cache_dir="/path/to/persistent/cache"
)
```

## Basic Exploration

Once initialized, you can explore the codebase.
Use these methods to get a high-level overview of the repository's structure and key code elements, or to gather foundational context for an LLM.

### Getting the File Tree

List all files and directories:

```python
file_tree = repo.get_file_tree()
# Returns a list of dicts: [{'path': '...', 'is_dir': False, ...}, ...]
```

### Extracting Symbols

Identify functions, classes, etc., across the whole repo or in a specific file:

```python
# All symbols
all_symbols = repo.extract_symbols()

# Symbols in a specific file
specific_symbols = repo.extract_symbols("src/my_module.py")
# Returns a list of dicts: [{'name': '...', 'type': 'function', ...}, ...]
```

### Searching Text

Perform simple text or regex searches:

```python
matches = repo.search_text("my_function_call", file_pattern="*.py")
# Returns a list of dicts: [{'file': '...', 'line_number': 10, ...}, ...]
```

(See [API Primitives](/core-concepts/api-primitives) for more detail on the output format of these methods.)

## Preparing Code for LLMs

`kit` provides utilities to prepare code snippets for large language models.
These methods help break down large codebases into manageable pieces suitable for LLM context windows or specific analysis tasks.

### Chunking

Split files into manageable chunks, either by line count or by symbol definition:

```python
# Chunk by lines
line_chunks = repo.chunk_file_by_lines("src/long_file.py", max_lines=100)

# Chunk by symbols (functions, classes)
symbol_chunks = repo.chunk_file_by_symbols("src/long_file.py")
```

### Extracting Context

Get the specific function or class definition surrounding a given line number:

```python
context = repo.extract_context_around_line("src/my_module.py", line=42)
# Returns a dict like {'name': 'my_function', 'type': 'function', 'code': 'def my_function(...): ...'}
```

## Semantic Code Search

Perform vector-based semantic search (requires configuration).
Go beyond keyword search to find code related by meaning or concept, useful for discovery and understanding.

```python
# NOTE: Requires prior setup - see Core Concepts > Configuring Semantic Search
results = repo.search_semantic("find code related to database connections", top_k=3)
```

(See [Configuring Semantic Search](/core-concepts/configuring-semantic-search) for setup details.)

## Finding Symbol Usages

Locate all definitions and references of a specific symbol:
Track down where functions or classes are defined and used throughout the codebase for impact analysis or refactoring.

```python
usages = repo.find_symbol_usages("MyClass", symbol_type="class")
# Returns a list of dicts showing definitions and text matches across the repo.
```

## Exporting Data

`kit` can export the gathered information (file tree, symbols, index, usages) to JSON files for use in other tools or offline analysis.
Persist the results of your analysis or integrate `kit`'s findings into other development workflows.

```python
# Export the full index (files + symbols)
repo.write_index("repo_index.json")

# Export only symbols
repo.write_symbols("symbols.json")

# Export file tree
repo.write_file_tree("file_tree.json")

# Export usages of a symbol
repo.write_symbol_usages("MyClass", "my_class_usages.json", symbol_type="class")
