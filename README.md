# kit 🛠️ Code Intelligence Toolkit

<img src="https://github.com/user-attachments/assets/7bdfa9c6-94f0-4ee0-9fdd-cbd8bd7ec060" width="360">

`kit` is a production-ready toolkit for codebase mapping, symbol extraction, code search, and building LLM-powered developer tools, agents, and workflows. 

Use `kit` to build things like code reviewers, code generators, even IDEs, all enriched with the right code context. Work with `kit` directly from Python, or with MCP + function calling, REST, or CLI.

`kit` also ships with [damn fine PR reviewer](https://kit.cased.com/pr-reviewer/) that works with your choice of LLM, at just the cost of tokens, showcasing the power of this library for building full products.

Explore the **[Full Documentation](https://kit.cased.com)** for detailed usage, advanced features, and practical examples.

## Quick Installation

### Install from PyPI

```bash
pip install cased-kit

# With semantic search features (includes PyTorch, sentence-transformers)
pip install cased-kit[ml]

# Everything (including MCP server and all features)
pip install cased-kit[all]
```

### Install Globally with uv (Recommended for CLI usage)

If you want to use the `kit` CLI globally without affecting your system Python, use `uv tool install`. This creates an isolated environment for `kit` while making the CLI available from anywhere:

```bash
# Install the base kit CLI globally
uv tool install cased-kit

# With semantic search features (includes PyTorch, sentence-transformers)
uv tool install cased-kit[ml]

# Everything (including MCP server and all features)
uv tool install cased-kit[all]
```

After installation, the `kit` and `kit-mcp` commands will be available globally. To manage your uv tool installations:

```bash
# List installed tools
uv tool list

# Uninstall if needed
uv tool uninstall cased-kit
```

### Install from Source

```bash
git clone https://github.com/cased/kit.git
cd kit
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## Basic Toolkit Usage

### Python API

```python
from kit import Repository

# Load a local repository
repo = Repository("/path/to/your/local/codebase")

# Load a remote public GitHub repo
# repo = Repository("https://github.com/owner/repo")

# Load a private GitHub repo (automatically uses KIT_GITHUB_TOKEN if set)
# repo = Repository("https://github.com/owner/private-repo")
# Or explicitly: repo = Repository("https://github.com/owner/private-repo", github_token="ghp_...")

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

# Read one file
main_py = repo.get_file_content("src/main.py")

# Read many files in one round-trip
contents = repo.get_file_content([
    "src/main.py",
    "src/utils/helper.py",
    "tests/test_main.py",
])
print(contents["src/utils/helper.py"])
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

# Initialize configuration for reviews
kit review --init-config

# Review GitHub PRs
kit review --dry-run https://github.com/owner/repo/pull/123
kit review https://github.com/owner/repo/pull/123

# Review local git diffs (no PR required!)
kit review main..feature  # Compare branches
kit review HEAD~3..HEAD   # Review last 3 commits
kit review --staged       # Review staged changes

# Generate PR summaries for quick triage
kit summarize https://github.com/owner/repo/pull/123
kit summarize --update-pr-body https://github.com/owner/repo/pull/123

# Generate intelligent commit messages from staged changes
git add .  # Stage your changes first
kit commit  # Analyze and commit with AI-generated message
```

The CLI supports all major repository operations with Unix-friendly output for scripting and automation. See the [CLI Documentation](https://kit.cased.com/introduction/cli) for comprehensive usage examples.

## Key Toolkit Capabilities

`kit` helps your apps and agents understand and interact with codebases, with components to build your own AI-powered developer tools.

*   **Explore Code Structure:**
    *   High-level view with `repo.get_file_tree()` to list all files and directories. You can also pass a subdirectory for a more limited scan.
    *   Dive down with `repo.extract_symbols()` to identify functions, classes, and other code constructs, either across the entire repository or within a single file.
    *   Use the new (as of 1.1.0) and faster `repo.extract_symbols_incremental()` to get fast, cache-aware symbol extraction—best when when dealing with small changes to repositories.

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
    *   **TypeScript / Node Client**: `npm install @runcased/kit` for type-safe wrapper that shells out to the same CLI.
    *   **REST API**: HTTP endpoints for web applications and microservices.
    *   **MCP Server**: Model Context Protocol integration for AI agents and development tools.


## High-Performance Incremental Analysis

kit's incremental analysis system provides intelligent caching that dramatically improves performance for repeated symbol extraction operations. This system is particularly powerful for development workflows where you're iterating on code and need fast analysis of changes.

**Key Performance Benefits:**
- **25x faster symbol extraction** on warm cache scenarios
- **Per-file incremental analysis**: Only analyzes files that have actually changed
- **Multi-strategy cache invalidation**: Uses file modification time, size, and content hash for accurate change detection
- **Automatic git state detection**: Invalidates caches when you switch branches, commit, merge, or rebase
- **LRU cache management**: Automatically manages memory usage with configurable cache size limits


**Manual Cache Management:**
```python
# Get performance statistics
stats = repo.get_incremental_stats()
print(f"Cache hit rate: {stats['cache_hit_rate']}")

# Clean up stale entries
repo.cleanup_incremental_cache()

# Clear all cached data
repo.clear_incremental_cache()
```

## MCP Server

The `kit` tool includes an MCP (Model Context Protocol) server that allows AI agents and other development tools to interact with a codebase programmatically.

MCP support is currently in alpha. Add a stanza like this to your MCP tool:


```jsonc
{
  "mcpServers": {
    "kit-mcp": {
      "command": "uvx",
      "args": ["--from", "cased-kit", "kit-mcp"],
      "env": {
        "KIT_GITHUB_TOKEN": "ghp_your_token_here"  // Optional: for private repos
      }
    }
  }
}
```

This requires you have `uvx` installed (`pip install uvx` or `pipx install uvx`).

If you have installed `cased-kit` with `pip` or some other method, you can invoke with python: 

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

## kit-powered Features & Utilities

As both demonstrations of this library, and as standalone products,
`kit` ships with MIT-licensed, CLI-based pull request review and summarization features.

### PR Reviews

The pull request reviewer ranks with the better closed-source paid options, but at 
a fraction of the cost with cloud models. At Cased we use `kit` extensively
with models like Sonnet 4 and gpt4.1, paying just for the price of tokens.

```bash
kit review --init-config
kit review https://github.com/owner/repo/pull/123
```

**Key Features:**
- **Whole repo context**: Uses `kit` so has all the features of this library
- **Production-ready**: Rivals paid services, but MIT-licensed; just pay for tokens
- **Custom context profiles**: Organization-specific coding standards and review guidelines automatically applied
- **Cost transparency**: Real-time token usage and pricing
- **Fast**: No queuing, shared services: just your code and the LLM
- **Works from wherever**: Trigger reviews with the CLI, or run it via CI

`kit` also has first-class support for free local models via [Ollama](https://ollama.ai/). 
No API keys, no costs, no data leaving your machine.

**📖 [Complete PR Reviewer Documentation](src/kit/pr_review/README.md)**

### PR Summaries

For quick PR triage and understanding, `kit` includes a fast, cost-effective PR summarization feature.
Perfect for teams that need to quickly understand what PRs do before deciding on detailed review.

```bash
kit summarize https://github.com/owner/repo/pull/123
kit summarize --update-pr-body https://github.com/owner/repo/pull/123
```

**Key Features:**
- **5-10x cheaper** than full reviews (~$0.005-0.02 vs $0.01-0.05+)
- **Fast triage**: Quick overview of changes, impact, and key modifications
- **PR body updates**: Automatically add AI summaries to PR descriptions for team visibility
- **Same LLM support**: Works with OpenAI, Anthropic, Google, and free Ollama models
- **Repository intelligence**: Leverages symbol extraction and dependency analysis for context

### Commit Messages

Generate intelligent commit messages from staged changes using the same repository intelligence:

```bash
git add .       # Stage your changes
kit commit      # Analyze and commit with AI-generated message
```

## Documentation

Explore the **[Full Documentation](https://kit.cased.com)** for detailed usage, advanced features, and practical examples.
Full REST documentation is also available.

📝 **[Changelog](https://kit.cased.com/changelog)** - Track all changes and improvements across kit releases


## License

MIT License

## Contributing

- **Local Development**: Check out our [Running Tests](https://kit.cased.com/development/running-tests) guide to get started with local development.
- **Project Direction**: See our [Roadmap](https://kit.cased.com/development/roadmap) for future plans and focus areas.
- **Discord**: [Join the Discord](https://discord.gg/DzxxC9SdvZ) to talk kit and Cased

To contribute, fork the repository, make your changes, and submit a pull request.
