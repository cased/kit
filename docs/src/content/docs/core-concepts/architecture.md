---
title: Architecture
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
