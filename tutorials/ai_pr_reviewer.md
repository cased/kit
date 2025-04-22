# Tutorial: Building a Production-Ready AI PR Reviewer with Symbol Extraction

## Overview

This guide shows how to build a robust, language-agnostic AI-powered Pull Request (PR) reviewer using the symbol extraction engine in this repo. You'll learn how to extract code structure from PRs, generate meaningful context for LLMs, and automate actionable code review comments on GitHub.

---

## Architecture Overview

**Components:**
- **Symbol Extractor:** Parses code for structured symbols (functions, resources, etc.)
- **PR Change Fetcher:** Gets changed files and diffs from GitHub
- **Symbol Diff Engine:** Compares base vs. head commit symbols for meaningful changes
- **LLM Prompt Builder:** Crafts targeted prompts for review
- **LLM Integration:** Calls OpenAI or other LLMs for code analysis
- **GitHub Bot:** Posts review comments or suggestions automatically

```
[GitHub PR] → [Changed Files] → [Symbol Extractor] → [Symbol Diff]
      ↓                                            ↑
  [Base Commit]                               [Head Commit]
      ↓                                            ↑
  [Symbols]      → [LLM Prompt] → [LLM] → [Review Suggestions] → [GitHub Comments]
```

---

## Prerequisites

- Python 3.8+
- This repo (`kit`) installed (e.g., `uv pip install -e .`)
- GitHub CLI (`gh`) or PyGithub for API access
- OpenAI API key (or other LLM provider)
- A GitHub repository with PRs

---

## 1. Extracting Code Symbols from PRs

Extract symbols from both base and head commits for each changed file:

```python
from kit.tree_sitter_symbol_extractor import TreeSitterSymbolExtractor
from pathlib import Path

def extract_symbols_from_file(filepath):
    ext = Path(filepath).suffix
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()
    return TreeSitterSymbolExtractor.extract_symbols(ext, code)
```

---

## 2. Fetching Changed Files from GitHub

You can use the GitHub CLI or PyGithub:

```python
import subprocess
import json

def get_changed_files(pr_number, repo_slug):
    # Using GitHub CLI:
    cmd = [
        "gh", "pr", "view", str(pr_number),
        "--repo", repo_slug,
        "--json", "files"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    files = json.loads(result.stdout)["files"]
    return [f["path"] for f in files]
```

---

## 3. Extracting Symbols from Both Commits

For each file, check out both the base and head commit, extract symbols, then diff:

```python
import tempfile
import shutil
import os

def extract_symbols_for_commit(repo_path, commit_sha, file_path):
    tmp_dir = tempfile.mkdtemp()
    try:
        # Checkout the specific file at the given commit
        result = subprocess.run([
            "git", "show", f"{commit_sha}:{file_path}"
        ], cwd=repo_path, check=True, capture_output=True, text=True)
        file_tmp_path = os.path.join(tmp_dir, os.path.basename(file_path))
        with open(file_tmp_path, "w") as f:
            f.write(result.stdout)
        return extract_symbols_from_file(file_tmp_path)
    finally:
        shutil.rmtree(tmp_dir)
```

---

## 4. Symbol Diffing Logic

Compare symbol lists to find added, removed, or changed symbols:

```python
def diff_symbols(symbols_before, symbols_after):
    before_set = {(s['type'], s['name']) for s in symbols_before}
    after_set = {(s['type'], s['name']) for s in symbols_after}
    added = after_set - before_set
    removed = before_set - after_set
    return {
        "added": [s for s in symbols_after if (s['type'], s['name']) in added],
        "removed": [s for s in symbols_before if (s['type'], s['name']) in removed]
    }
```

---

## 5. Building LLM Prompts

Craft prompts that focus the LLM on meaningful, structural changes:

```python
def build_llm_prompt(symbol_diff, file_path):
    prompt = f"Review the following code changes in {file_path}:\n"
    if symbol_diff['added']:
        prompt += "\nNew symbols:\n"
        for s in symbol_diff['added']:
            prompt += f"- {s['type']} `{s['name']}`\n"
    if symbol_diff['removed']:
        prompt += "\nRemoved symbols:\n"
        for s in symbol_diff['removed']:
            prompt += f"- {s['type']} `{s['name']}`\n"
    prompt += "\nSuggest improvements, spot errors, and flag security issues."
    return prompt
```

**Advanced Prompt Tips:**
- Include code snippets for new/changed functions/resources.
- Add context: file path, project type, coding standards.
- Limit prompt size for large PRs (summarize, chunk, or prioritize).

---

## 6. Calling an LLM

Example with OpenAI:

```python
import openai

def get_llm_review(prompt, api_key):
    openai.api_key = api_key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are a senior code reviewer."},
                  {"role": "user", "content": prompt}]
    )
    return response['choices'][0]['message']['content']
```

---

## 7. Posting Review Comments to GitHub

You can automate posting review comments using the GitHub CLI or API:

```python
def post_github_comment(pr_number, repo_slug, body):
    subprocess.run([
        "gh", "pr", "comment", str(pr_number),
        "--repo", repo_slug,
        "--body", body
    ])
```

---

## 8. Handling Large PRs and Edge Cases

- **Chunking:** For very large PRs, break changed symbols into batches and review incrementally.
- **Language Support:** Use the symbol extractor for all supported languages in your repo.
- **Error Handling:** Log failures and fall back gracefully if extraction fails on some files.

---

## 9. Security, Scaling, and Customization

- **Security:** Never leak secrets in prompts or logs. Use read-only tokens for CI bots.
- **Scaling:** Run in CI/CD, use caching for symbol extraction, parallelize LLM calls.
- **Customization:** Tune prompts for your team's review style, add custom symbol filters, or integrate with Slack/Teams.

---

## 10. Full Example Workflow Script

```python
# Pseudocode for full review bot
pr_number = 42
repo_slug = "your-org/your-repo"
api_key = "sk-..."  # OpenAI key

changed_files = get_changed_files(pr_number, repo_slug)
for file_path in changed_files:
    symbols_base = extract_symbols_for_commit('.', 'base_sha', file_path)
    symbols_head = extract_symbols_for_commit('.', 'head_sha', file_path)
    symbol_diff = diff_symbols(symbols_base, symbols_head)
    if symbol_diff['added'] or symbol_diff['removed']:
        prompt = build_llm_prompt(symbol_diff, file_path)
        review = get_llm_review(prompt, api_key)
        post_github_comment(pr_number, repo_slug, review)
```

---

## Conclusion

By extracting structured symbols and diffing them across PRs, you provide LLMs with rich, focused context—enabling reviews that are more accurate, actionable, and scalable than line-based diffs. This approach supports multi-language repos, large PRs, and can be extended for security, compliance, onboarding, and more.

---

**Want to go further?**  
- Add inline comments for specific lines/blocks.
- Integrate with GitHub Actions for full automation.
- Use embeddings for semantic diffing and smarter context selection.

---
