# kit 🛠️ Code Intelligence Toolkit

<img src="https://github.com/user-attachments/assets/7bdfa9c6-94f0-4ee0-9fdd-cbd8bd7ec060" width="360">

`kit` is a production-ready toolkit for codebase mapping, symbol extraction, code search, and building LLM-powered developer tools, agents, and workflows. 

Use `kit` to build things like code reviewers, code generators, even IDEs, all enriched with the right code context.

Work with `kit` directly from Python, or with MCP + function calling, REST, or CLI!

`kit` also ships with damn fine PR reviewer that works with **any LLM** (including completely free local models via Ollama, or paid cloud models like Claude and gpt4.1) showcasing the power of this library in just a few lines of code.

## Quick Installation

### Install from PyPI

```bash
pip install cased-kit

# With semantic search features (includes PyTorch, sentence-transformers)
pip install cased-kit[ml]

# Everything (including MCP server and all features)
pip install cased-kit[all]
```

### Install from Source

```bash
git clone https://github.com/cased/kit.git
cd kit
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## Basic Usage

### Python API

```python
from kit import Repository

# Load a local repository
repo = Repository("/path/to/your/local/codebase")

# Load a remote public GitHub repo
# repo = Repository("https://github.com/owner/repo")

# Load a repository at a specific commit, tag, or branch
# repo = Repository("https://github.com/owner/repo", ref="v1.2.3")

# Explore the repo
print(repo.get_file_tree())
# Output: [{"path": "src/main.py", "is_dir": False, ...}, ...]

print(repo.extract_symbols('src/main.py'))
# Output: [{"name": "main", "type": "function", "file": "src/main.py", ...}, ...]

# Access git metadata
print(f"Current SHA: {repo.current_sha}")
print(f"Branch: {repo.current_branch}")
```

### Command Line Interface

`kit` also provides a comprehensive CLI for repository analysis and code exploration:

```bash
# Get repository file structure
kit file-tree /path/to/repo

# Extract symbols (functions, classes, etc.)
kit symbols /path/to/repo --format table

# Search for code patterns
kit search /path/to/repo "def main" --pattern "*.py"

# Find symbol usages
kit usages /path/to/repo "MyClass"

# Export data for external tools
kit export /path/to/repo symbols symbols.json

# Initialize configuration and review a PR
kit review --init-config
kit review --dry-run https://github.com/owner/repo/pull/123
kit review https://github.com/owner/repo/pull/123
```

The CLI supports all major repository operations with Unix-friendly output for scripting and automation. See the [CLI Documentation](https://kit.cased.com/introduction/cli) for comprehensive usage examples.

### AI-Powered PR Reviews

As both of a demonstration of this library, and as a standalone product,
`kit` includes a MIT-licensed, CLI-based pull request reviewer that
ranks with the better closed-source paid options—but **completely free** 
with local Ollama models, or at a fraction of the cost with cloud models.

**🆓 Free option**: Use local Ollama models (qwen2.5-coder, codellama, etc.)
**💰 Low-cost option**: Use Claude or GPT-4 at cost (~10 cents per review)

```bash
# Option 1: Free with Ollama (install ollama.ai first)
ollama pull qwen2.5-coder:latest
kit review --init-config  # Select ollama provider
kit review https://github.com/owner/repo/pull/123

# Option 2: Cloud models (Claude or GPT-4) 
kit review --init-config  # Select anthropic or openai provider
kit review https://github.com/owner/repo/pull/123
```

**Key Features:**
- **Whole repo context**: Uses `kit` so has all the features of this library
- **Production-ready**: Rivals paid services, but MIT-licensed; just pay for tokens
- **Cost transparency**: Real-time token usage and pricing
- **Fast**: No queuing, shared services: just your code and the LLM
- **Works from wherever**: Trigger reviews with the CLI, or run it via CI

**📖 [Complete PR Reviewer Documentation](src/kit/pr_review/README.md)**

## 🆓 Local AI Models (No Cost)

`kit` has first-class support for **free local AI models** via [Ollama](https://ollama.ai/). No API keys, no costs, no data leaving your machine.

```python
from kit import Repository
from kit.summaries import OllamaConfig

# Use any Ollama model for local code intelligence
repo = Repository("/path/to/your/codebase")
config = OllamaConfig(model="qwen2.5-coder:latest")  # Latest code-specialized model
summarizer = repo.get_summarizer(config=config)

# Summarize code locally
summary = summarizer.summarize_file("main.py")
print(summary)  # Cost: $0.00
```

**Why Choose Ollama:**
- ✅ **No cost** - unlimited usage
- ✅ **Complete privacy** - data never leaves your machine  
- ✅ **No API keys** - just install and run
- ✅ **Works offline** - perfect for secure environments

**Quick Setup:**
```bash
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull qwen2.5-coder:latest  # Best for code
```

**📚 [Complete Ollama Guide →](https://kit.cased.com/introduction/ollama)**  
*Latest models, advanced examples, troubleshooting, and more*

## Key Features & Capabilities

`kit` helps your apps and agents understand and interact with codebases, with components to build your own AI-powered developer tools.

*   **Explore Code Structure:**
    *   High-level view with `repo.get_file_tree()` to list all files and directories.
    *   Dive down with `repo.extract_symbols()` to identify functions, classes, and other code constructs, either across the entire repository or within a single file.

*   **Pinpoint Information:**
    *   Run regular expression searches across your codebase using `repo.search_text()`.
    *   Track specific symbols (like a function or class) with `repo.find_symbol_usages()`.
    *   Perform semantic code search using vector embeddings to find code based on meaning rather than just keywords.

*   **Prepare Code for LLMs & Analysis:**
    *   Break down large files into manageable pieces for LLM context windows using `repo.chunk_file_by_lines()` or `repo.chunk_file_by_symbols()`.
    *   Get the full definition of a function or class off a line number within it using `repo.extract_context_around_line()`.

*   **Generate Code Summaries:**
    *   Use LLMs to create natural language summaries for files, functions, or classes using the `Summarizer` (e.g., `summarizer.summarize_file()`, `summarizer.summarize_function()`).
    *   Works with **any LLM**: free local models (Ollama), or cloud models (OpenAI, Anthropic, Google).
    *   Build a searchable semantic index of these AI-generated docstrings with `DocstringIndexer` and query it with `SummarySearcher` to find code based on intent and meaning.

*   **Analyze Code Dependencies:**
    *   Map import relationships between modules using `repo.get_dependency_analyzer()` to understand your codebase structure.
    *   Generate dependency reports and LLM-friendly context with `analyzer.generate_dependency_report()` and `analyzer.generate_llm_context()`.

*   **Repository Versioning & Historical Analysis:**
    *   Analyze repositories at specific commits, tags, or branches using the `ref` parameter.
    *   Compare code evolution over time, work with diffs, ensure reproducible analysis results
    *   Access git metadata including current SHA, branch, and remote URL with `repo.current_sha`, `repo.current_branch`, etc.

*   **Multiple Access Methods:**
    *   **Python API**: Direct integration for building applications and scripts.
    *   **Command Line Interface**: 11+ commands for shell scripting, CI/CD, and automation workflows.
    *   **REST API**: HTTP endpoints for web applications and microservices.
    *   **MCP Server**: Model Context Protocol integration for AI agents and development tools.

*   **AI-Powered Code Review:**
    *   Automated PR review with `kit review` using **free local models (Ollama)** or cloud models (Claude, GPT-4).
    *   Repository cloning and comprehensive file analysis for deep code understanding.
    *   Configurable review depth (quick, standard, thorough) and customizable analysis settings.
    *   Seamless GitHub integration with automatic comment posting and PR workflow integration.
    *   Cost transparency with real-time LLM token usage tracking and pricing information (free for Ollama).

## MCP Server

The `kit` tool includes an MCP (Model Context Protocol) server that allows AI agents and other development tools to interact with a codebase programmatically.

MCP support is currently in alpha. Add a stanza like this to your MCP tool:

```jsonc
{
  "mcpServers": {
    "kit-mcp": {
      "command": "python",
      "args": ["-m", "kit.mcp"]
    }
  }
}
```

The `python` executable invoked must be the one where `cased-kit` is installed.
If you see `ModuleNotFoundError: No module named 'kit'`, ensure the Python
interpreter your MCP client is using is the correct one.


## Documentation

Explore the **[Full Documentation](https://kit.cased.com)** for detailed usage, advanced features, and practical examples.
Full REST documentation is also available.


## License

MIT License

## Contributing

- **Local Development**: Check out our [Running Tests](https://kit.cased.com/development/running-tests) guide to get started with local development.
- **Project Direction**: See our [Roadmap](https://kit.cased.com/development/roadmap) for future plans and focus areas.
- **Discord**: [Join the Discord](https://discord.gg/XpqU65pY) to talk kit and Cased

To contribute, fork the repository, make your changes, and submit a pull request.
