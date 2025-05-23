---
title: Using kit with MCP
description: Learn how to use kit with the Model Context Protocol (MCP) for AI-powered code understanding
---

Note: MCP support is currently in alpha.

The Model Context Protocol (MCP) provides a unified API for codebase operations, making it easy to integrate kit's capabilities with AI tools and IDEs. This guide will help you set up and use kit with MCP.

Kit provides a MCP server implementation that exposes its code intelligence capabilities through a standardized protocol. When using kit as an MCP server, you gain access to:

- **Code Search**: Perform text-based and semantic code searches
- **Code Analysis**: Extract symbols, find symbol usages, and analyze dependencies
- **Code Summarization**: Create natural language summaries of code
- **File Navigation**: Explore file trees and repository structure

This document guides you through setting up and using `kit` with MCP-compatible tools like Cursor or Claude Desktop.

## What is MCP?

MCP (Model Context Protocol) is a specification that allows AI agents and development tools to interact with your codebase programmatically via a local server. `kit` implements an MCP server to expose its code intelligence features.

## Available MCP Tools in `kit`

Currently, `kit` exposes the following functionalities via MCP tools:

*   `open_repository`: Opens a local or remote Git repository. Supports `ref` parameter for specific commits, tags, or branches.
*   `get_file_tree`: Retrieves the file and directory structure of the open repository.
*   `get_file_content`: Reads the content of a specific file.
*   `search_code`: Performs text-based search across repository files.
*   `extract_symbols`: Extracts functions, classes, and other symbols from a file.
*   `find_symbol_usages`: Finds where a specific symbol is used across the repository.
*   `get_code_summary`: Provides AI-generated summaries for files, functions, or classes.
*   `get_git_info`: Retrieves git metadata including current SHA, branch, and remote URL.

### Opening Repositories with Specific Versions

The `open_repository` tool supports analyzing specific versions of repositories using the optional `ref` parameter:

```json
{
  "tool": "open_repository",
  "arguments": {
    "path_or_url": "https://github.com/owner/repo",
    "ref": "v1.2.3"
  }
}
```

The `ref` parameter accepts:
- **Commit SHAs**: `"abc123def456"`
- **Tags**: `"v1.2.3"`, `"release-2024"`
- **Branches**: `"main"`, `"develop"`, `"feature-branch"`

### Accessing Git Metadata

Use the `get_git_info` tool to access repository metadata:

```json
{
  "tool": "get_git_info",
  "arguments": {
    "repo_id": "your-repo-id"
  }
}
```

This returns information like current commit SHA, branch name, and remote URL - useful for understanding what version of code you're analyzing.

More MCP features are coming soon.

## Setup

1. After installing `kit`, configure your MCP-compatible client by adding a stanza like this to your settings:

Available environment variables for the `env` section:
- `OPENAI_API_KEY`
- `KIT_MCP_LOG_LEVEL`

```json
{
  "mcpServers": {
    "kit-mcp": {
      "command": "python",
      "args": ["-m", "kit.mcp"],
      "env": {
        "KIT_MCP_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

The `python` executable invoked must be the one where `cased-kit` is installed.
If you see `ModuleNotFoundError: No module named 'kit'`, ensure the Python
interpreter your MCP client is using is the correct one.