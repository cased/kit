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
*   `grep_code`: Fast literal string search with directory filtering and smart exclusions.
*   `extract_symbols`: Extracts functions, classes, and other symbols from a file.
*   `find_symbol_usages`: Finds where a specific symbol is used across the repository.
*   `get_code_summary`: Provides AI-generated summaries for files, functions, or classes.
*   `get_git_info`: Retrieves git metadata including current SHA, branch, and remote URL.
*   `review_diff`: Reviews local git diffs using AI-powered code review.

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

### Automatic GitHub Token Handling

For convenience when working with private repositories, the MCP server automatically checks for GitHub tokens in environment variables:

1. First checks `KIT_GITHUB_TOKEN`
2. Falls back to `GITHUB_TOKEN` if `KIT_GITHUB_TOKEN` is not set  
3. Uses no authentication if neither environment variable is set

This means you can set up your MCP client with:

```json
{
  "mcpServers": {
    "kit-mcp": {
      "command": "python",
      "args": ["-m", "kit.mcp"],
      "env": {
        "KIT_GITHUB_TOKEN": "ghp_your_token_here"
      }
    }
  }
}
```

And then simply open private repositories without needing to specify the `github_token` parameter:

```json
{
  "tool": "open_repository", 
  "arguments": {
    "path_or_url": "https://github.com/your-org/private-repo"
  }
}
```

### Reviewing Code Changes

The `review_diff` tool allows you to get AI-powered code reviews for local git diffs without needing to create a GitHub pull request:

```json
{
  "tool": "review_diff",
  "arguments": {
    "repo_id": "your-repo-id",
    "diff_spec": "main..feature"
  }
}
```

The `diff_spec` parameter accepts various git diff specifications:
- **Branch comparisons**: `"main..feature"`, `"develop..my-branch"`
- **Commit ranges**: `"HEAD~3..HEAD"`, `"abc123..def456"`
- **Staged changes**: `"--staged"`

Optional parameters:
- `priority_filter`: Filter by priority levels - `["high"]`, `["medium", "low"]`
- `max_files`: Maximum number of files to review (default: 10)
- `model`: Override the AI model - `"gpt-4"`, `"claude-3-opus"`, etc.

Example with all options:
```json
{
  "tool": "review_diff",
  "arguments": {
    "repo_id": "your-repo-id",
    "diff_spec": "HEAD~1..HEAD",
    "priority_filter": ["high", "medium"],
    "max_files": 20,
    "model": "claude-3-opus"
  }
}
```

The tool will return a comprehensive code review with issues categorized by priority (HIGH, MEDIUM, LOW), including specific file and line references.

More MCP features are coming soon.

## Setup

1. After installing `kit`, configure your MCP-compatible client by adding a stanza like this to your settings:

Available environment variables for the `env` section:
- `OPENAI_API_KEY` - For OpenAI models in code reviews and summaries
- `ANTHROPIC_API_KEY` - For Claude models in code reviews  
- `KIT_ANTHROPIC_TOKEN` - Alternative to ANTHROPIC_API_KEY
- `KIT_OPENAI_TOKEN` - Alternative to OPENAI_API_KEY
- `KIT_MCP_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)
- `KIT_GITHUB_TOKEN` - Automatically used for private repository access
- `GITHUB_TOKEN` - Fallback for private repository access

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