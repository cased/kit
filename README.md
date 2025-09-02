# Kit 🛠️ Production-Grade Code Intelligence Platform (plus a lot more)

<img src="https://github.com/user-attachments/assets/7bdfa9c6-94f0-4ee0-9fdd-cbd8bd7ec060" width="360">

**Kit** is a comprehensive code intelligence toolkit and platform:

### 1. **Core Toolkit** - Build Your Own AI Developer Tools
The foundation that powers everything: a production-ready library for codebase mapping, symbol extraction, and intelligent code search. Build your own code reviewers, generators, IDE plugins, or any LLM-powered development tool. Features a comprehensive CLI so you can work with kit in any language.

### 2. **Kit Dev MCP** - Supercharge Your AI Assistant
An enhanced MCP server that gives Cursor, Windsurf, Claude Code, and VS Code super-powered context capabilities:
- Smart context building for any development task
- Real-time file watching and change detection
- Semantic code search with AI embeddings
- Documentation research for any package
- A lot more

[**→ Explore Kit Dev MCP**](https://kit-dev.cased.com)

### 3. **AI PR Reviewer** - Production-Ready Code Reviews
A complete, customizable pull request reviewer that provides:
- Context-aware feedback using semantic understanding
- Security vulnerability detection
- Performance analysis
- CI/CD integration

[**→ Learn About PR Reviewer**](https://kit.cased.com/pr-reviewer/)

The entire toolkit is free, MIT-licensed. The only costs you ever pay (if only) are at-cost LLM tokens,
with your own API keys.

---

## 🚀 Quick Start

Choose your path based on what you want to build:

### For AI Assistant Users (MCP Server)
```bash
# Install Kit with MCP server (simple, works everywhere)
pip install cased-kit

# Or with all extras (quote for zsh compatibility)
pip install 'cased-kit[all]'

# Configure your AI assistant (Cursor, Windsurf, Claude Code, VS Code)
# See full guide: https://kit.cased.com/docs/quickstart
```

### For Developers (Core Toolkit)
```bash
# Install the core toolkit
pip install cased-kit

# With ML features for semantic search
pip install cased-kit[ml]
```

### For Teams (PR Reviewer)
```bash
# Install with all features 
pip install 'cased-kit[all]'
# Or just: pip install cased-kit

# Run your first review
kit review PR_URL
```

## 💡 Core Toolkit Usage

The power behind all Kit solutions - use it to build your own tools:

```python
from kit import Repository

# Load any repository
repo = Repository("/path/to/codebase")
# Or from GitHub: repo = Repository("https://github.com/owner/repo")

# Extract code intelligence
symbols = repo.extract_symbols('src/main.py')
# Output: [{"name": "main", "type": "function", ...}, ...]

# Semantic code search
results = repo.search_code("authentication", mode="semantic")

# Build context for LLMs
context = repo.get_context_for_task("implement OAuth2")
```

## 🎨 Build With Kit

Kit's core toolkit enables you to create:

- **Code Reviewers** - Context-aware analysis with your choice of LLM
- **Documentation Generators** - Extract and explain code structure
- **Refactoring Tools** - Understand dependencies before making changes
- **Security Scanners** - Find vulnerabilities with deep code understanding
- **AI Coding Assistants** - Provide perfect context to any LLM
- **Custom IDE Features** - Build language servers and code intelligence

## 🏗️ Architecture

All three Kit offerings share the same powerful core:

```
┌─────────────────────────────────────────────┐
│          Kit Local Dev MCP Server           │
│  (Cursor, Windsurf, Claude Code, VS Code)   │
├─────────────────────────────────────────────┤
│            AI PR Reviewer                   │
│     (CLI, GitHub Actions, CI/CD)            │
├─────────────────────────────────────────────┤
│           Core Kit Toolkit                  │
│   • Symbol Extraction (25x faster)          │
│   • Semantic Search                         │
│   • Dependency Analysis                     │
│   • Context Building                        │
│   • Documentation Research                  │
└─────────────────────────────────────────────┘
```

## 🔥 Key Features

### Performance at Scale
- **25x faster** symbol extraction with incremental caching
- Handle repositories with **millions of lines** of code
- Optimized for **monorepos** and complex architectures

### Intelligent Code Understanding
- Language-aware parsing (Python, JS/TS, Go, Java, C++, more)
- Semantic search using embeddings
- Cross-file dependency tracking
- Docstring and comment extraction

### Developer Experience
- Simple Python API
- MCP protocol support
- REST API server
- CLI tools
- GitHub integration

## 📚 Documentation

- **[Full Documentation](https://kit.cased.com)** - Complete guides and API reference
- **[Kit Local Dev MCP](http://localhost:3000)** - MCP server documentation
- **[PR Reviewer Guide](https://kit.cased.com/pr-reviewer/)** - Setup and configuration
- **[Examples](https://kit.cased.com/tutorials/)** - Real-world usage patterns

## 🛠️ Installation Options

### Global CLI with uv (Recommended)
```bash
# Install globally without affecting system Python
uv tool install 'cased-kit[all]' 
# Or simply: uv tool install cased-kit

# Now use from anywhere
kit review PR_URL
kit-mcp-local-dev
```

### From Source
```bash
git clone https://github.com/cased/kit.git
cd kit
pip install -e .[all]
```

## 🤝 Community & Support

Kit is open source (MIT licensed) and actively maintained.

- **GitHub**: [github.com/cased/kit](https://github.com/cased/kit)
- **Issues**: [Report bugs or request features](https://github.com/cased/kit/issues)
- **Discussions**: [Join the community](https://github.com/cased/kit/discussions)

## 🏢 Built by Cased

Kit is built by [Cased](https://cased.com), with deep expertise in developer tools and code intelligence.

---

**Ready to enhance your development workflow?**

- 🚀 [Try Kit Local Dev MCP](http://localhost:3000) for AI-powered development
- 📖 [Read the Docs](https://kit.cased.com) to build your own tools
- 🔍 [Setup PR Reviews](https://kit.cased.com/pr-reviewer/) for your team