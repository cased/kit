# kit 🛠️ Code Intelligence Toolkit


<img src="https://github.com/user-attachments/assets/7bdfa9c6-94f0-4ee0-9fdd-cbd8bd7ec060" width="360">

`kit` is a modular, production-grade Python toolkit for codebase mapping, symbol extraction, code search, and building LLM-powered developer workflows. 

Use `kit` to build AI-powered developer tools (code reviewers, code generators, even IDEs) enriched with the right code context.

## Quick Installation

```bash
git clone https://github.com/cased/kit.git
cd kit
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## Basic Usage

```python
import kit

# Load a local repository
repo = kit.Repository("/path/to/your/local/codebase")

# Load a remote public GitHub repo
# repo = kit.Repository("https://github.com/owner/repo")

# Explore the repo
print(repo.get_file_tree())
# Output: [{"path": "src/main.py", "is_dir": False, ...}, ...]

print(repo.extract_symbols('src/main.py'))
# Output: [{"name": "main", "type": "function", "file": "src/main.py", ...}, ...]
```

## Core API

The `kit.Repository` class provides several core methods:

*   `get_file_tree()`: Lists files and directories.
*   `extract_symbols(filepath=None)`: Extracts functions, classes, etc., from a file or the whole repo.
*   `search_text(query)`: Performs text/regex search across the codebase.
*   `chunk_file_by_lines(filepath, max_lines)`: Splits a file into line-based chunks.
*   `chunk_file_by_symbols(filepath)`: Splits a file into symbol-based chunks.
*   `extract_context_around_line(filepath, line_number)`: Gets the surrounding code block (function/class) for a specific line.
*   `find_symbol_usages(symbol_name, symbol_type=None)`: Finds definitions and references of a symbol across the repo.

*See the [Full Documentation](docs/src/content/docs/index.mdx) for detailed usage and examples.*

## Dive Deeper

For detailed guides, tutorials, API reference, and core concepts, please see the **[Full Documentation](docs/src/content/docs/index.mdx)**.

## License

MIT License
