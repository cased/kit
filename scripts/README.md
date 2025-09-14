# Kit Scripts

This directory contains utility scripts for kit-dev-mcp development and testing.

## Available Scripts

### 🚀 `launch_mcp_inspector.sh`
Launch the MCP Inspector UI to interact with kit-dev-mcp visually.

```bash
./scripts/launch_mcp_inspector.sh
```

### 🧪 `test_mcp_tools.py`
Manual test suite for all kit-dev-mcp functionality including Context7 integration.

```bash
python scripts/test_mcp_tools.py
```

Tests:
- Repository management
- Symbol extraction
- Code search (text, grep, AST)
- Context7 documentation research
- Smart context building

### 🖱️ `kit-cursor-helper.py`
Helper script for using kit-dev-mcp tools directly from Cursor IDE terminal.

```bash
python scripts/kit-cursor-helper.py open /path/to/repo
python scripts/kit-cursor-helper.py search "async def"
python scripts/kit-cursor-helper.py grep-ast "try_statement"
python scripts/kit-cursor-helper.py research fastapi
```

### 📊 `benchmark.py`
Performance benchmarking for kit operations.

### 🔍 `test_ollama_local.py`
Test script for local Ollama integration.

### 🎯 Other Scripts
- `format.sh` - Code formatting
- `release.sh` - Release automation
- `test.sh` - Run test suite
- `typecheck.sh` - Type checking