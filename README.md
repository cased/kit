# kit 🛠️ Code Intelligence Toolkit

<img src="https://github.com/user-attachments/assets/7bdfa9c6-94f0-4ee0-9fdd-cbd8bd7ec060" width="360">

`kit` is a production-ready toolkit for codebase mapping, symbol extraction, code search, and building LLM-powered developer tools, agents, and workflows. 

Use `kit` to build things like code reviewers, code generators, even IDEs, all enriched with the right code context. Work with `kit` directly from Python, or with MCP + function calling, REST, or CLI.

Explore the **[full documentation](https://kit.cased.com)** for detailed usage, advanced features, and practical examples. Check out docs for kit's [local dev MCP server](https://kit-mcp.cased.com), too.


## Quick Installation

### Install from PyPI

```bash
uv pip install cased-kit

# With ML features for advanced analysis and vector search
uv pip install 'cased-kit[all]'
```

### Install Globally with uv (easiest for CLI usage)

If you want to use the `kit` CLI globally without affecting your system Python, use `uv tool install`. This creates an isolated environment for `kit` while making the CLI available from anywhere:

```bash
# Install the base kit CLI globally
uv tool install cased-kit

# Everything (including MCP server and all features)
uv tool install cased-kit[all]
```

After installation, the `kit` and `kit-dev-mcp` commands will be available globally. To manage your uv tool installations:

```bash
# List installed tools
uv tool list

# Uninstall if needed
uv tool uninstall cased-kit
```

### Claude Code Plugin

Use kit directly in [Claude Code](https://claude.ai/code) with the official plugin:

```bash
/plugin marketplace add cased/claude-code-plugins
/plugin install kit-cli
```

The plugin gives Claude autonomous access to kit's codebase analysis tools. Claude will automatically use kit when you ask questions like:
- "How does authentication work in this codebase?"
- "Find all usages of the UserModel class"
- "What are the dependencies of this project?"
- "Show me the file structure of src/"

See the [Claude Code Integration Guide](https://kit.cased.com/introduction/claude-code) for details.

## Toolkit Usage

### Basic Python API

```python
from kit import Repository

# Load a local repository
repo = Repository("/path/to/your/local/codebase")

# Load a remote public GitHub repo
repo = Repository("https://github.com/owner/repo")

# Load a private GitHub repo (automatically uses KIT_GITHUB_TOKEN if set)
repo = Repository("https://github.com/owner/private-repo")

# Or explicitly
repo = Repository("https://github.com/owner/private-repo", github_token="ghp_...")

# At a specific commit, tag, or branch
# repo = Repository("https://github.com/owner/repo", ref="v1.2.3")
```

```python
# Explore a repo
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

`kit` provides a comprehensive CLI for repository analysis and code exploration.

**Repository Analysis:**
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
```

**PR Reviews:**
```bash
# Initialize configuration
kit review --init-config

# Review GitHub PRs
kit review --dry-run https://github.com/owner/repo/pull/123
kit review https://github.com/owner/repo/pull/123

# Review local git diffs (no PR required!)
kit review main..feature  # Compare branches
kit review HEAD~3..HEAD   # Review last 3 commits
kit review --staged       # Review staged changes
```

**PR Summaries:**
```bash
# Generate PR summaries for quick triage
kit summarize https://github.com/owner/repo/pull/123
kit summarize --update-pr-body https://github.com/owner/repo/pull/123
```

**Commit Messages:**
```bash
# Generate intelligent commit messages from staged changes
git add .  # Stage your changes first
kit commit  # Analyze and commit with AI-generated message
```

**Package Search** (requires Chroma API key):
```bash
kit package-search-grep numpy "def.*fft" --max-results 10  # Plain grep-style output
kit package-search-grep numpy "def.*fft" --json           # Structured JSON output
kit package-search-hybrid django "authentication middleware"
kit package-search-read requests "requests/models.py"
```

See the [CLI Documentation](https://kit.cased.com/introduction/cli) for comprehensive usage examples.

## Key Toolkit Capabilities

`kit` helps your apps and agents understand and interact with codebases, with components to build your own AI-powered developer tools.

*   **Explore Code Structure:**
    *   High-level view with `repo.get_file_tree()` to list all files and directories. You can also pass a subdirectory for a more limited scan.
    *   Dive down with `repo.extract_symbols()` to identify functions, classes, and other code constructs, either across the entire repository or within a single file.
    *   Use `repo.extract_symbols_incremental()` to get fast, cache-aware symbol extraction—best when dealing with small changes to repositories.

*   **Pinpoint Information:**
    *   Run fast regular expression searches across your codebase using `repo.search_text()` (automatically uses [ripgrep](https://github.com/BurntSushi/ripgrep) when available for 10x speedup).
    *   Track specific symbols (like a function or class) with `repo.find_symbol_usages()`.
    *   Find code by structure with AST-based pattern matching (async functions, try blocks, class inheritance, etc.).

*   **Prepare Code for LLMs & Analysis:**
    *   Break down large files into manageable pieces for LLM context windows using `repo.chunk_file_by_lines()` or `repo.chunk_file_by_symbols()`.
    *   Get the full definition of a function or class off a line number within it using `repo.extract_context_around_line()`.

*   **Generate Code Summaries:**
    *   Use LLMs to create natural language summaries for files, functions, or classes using the `Summarizer` (e.g., `summarizer.summarize_file()`, `summarizer.summarize_function()`).
    *   Build a searchable index of these AI-generated docstrings with `DocstringIndexer` and query it with `SummarySearcher` for intelligent code discovery.

*   **Analyze Code Dependencies:**
    *   Map import relationships between modules using `repo.get_dependency_analyzer()` to understand your codebase structure.
    *   Generate dependency reports and LLM-friendly context with `analyzer.generate_dependency_report()` and `analyzer.generate_llm_context()`.

*   **Search Package Source Code (via Chroma):**
    *   Search through popular package source code using `ChromaPackageSearch` for regex patterns and semantic queries.
    *   Access source code from packages like numpy, django, fastapi, pandas, and more.
    *   Integrated into kit-dev MCP for seamless package exploration in AI assistants.

*   **Repository Versioning & Historical Analysis:**
    *   Analyze repositories at specific commits, tags, or branches using the `ref` parameter.
    *   Compare code evolution over time, work with diffs, ensure reproducible analysis results
    *   Access git metadata including current SHA, branch, and remote URL with `repo.current_sha`, `repo.current_branch`, etc.

*   **Multi-Repository Analysis:**
    *   Analyze multiple repositories together with `MultiRepo` for microservices, monorepos, or team projects.
    *   Unified search, symbol lookup, and dependency auditing across all repos.
    *   CLI support: `kit multi search`, `kit multi deps`, `kit multi summary`.

## MCP Server (kit-dev MCP)

`kit` includes an enhanced MCP (Model Context Protocol), **kit-dev**, designed especially for individual local dev work. It includes kit's production-grade code intelligence and context building, and adds in multi-source documentation research and package searching.

**Environment Variables:** `OPENAI_API_KEY`, `OPENAI_BASE_URL` (for proxies/custom endpoints), `ANTHROPIC_API_KEY`

**[→ Full kit-dev MCP Documentation](https://kit-mcp.cased.com)**

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

**[→ Complete PR Reviewer Documentation](src/kit/pr_review/README.md)**

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

### Commit Messages

Generate intelligent commit messages from staged changes using the same repository intelligence:

```bash
git add .       # Stage your changes
kit commit      # Analyze and commit with AI-generated message
```

## Documentation

**[Full Documentation](https://kit.cased.com)** - Detailed usage, advanced features, and practical examples.
Full REST documentation is also available.

**[kit-dev MCP Documentation](https://kit-mcp.cased.com)** - Complete guide for the enhanced MCP server

**[Changelog](https://kit.cased.com/changelog)** - Track all changes and improvements across kit releases

## License

MIT License

## Contributing

- **Local Development**: Check out our [Running Tests](https://kit.cased.com/development/running-tests) guide to get started with local development.
- **Project Direction**: See our [Roadmap](https://kit.cased.com/development/roadmap) for future plans and focus areas.

To contribute, fork the repository, make your changes, and submit a pull request.
