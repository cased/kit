# kit 🛠️ Code Intelligence Toolkit

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
repo = kit.Repo("/path/to/your/local/codebase")

# Or a remote public GitHub repo
# repo = kit.Repo("https://github.com/owner/repo")

# Explore the repo
# print(repo.get_file_tree())
# print(repo.extract_symbols('some_file.py'))
```

## Dive Deeper

For detailed guides, tutorials, API reference, and core concepts, please see the **[Full Documentation](docs/src/content/docs/index.mdx)**.


## License

MIT License
