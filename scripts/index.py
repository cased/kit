#!/usr/bin/env python3
"""
CLI: Index a repo and print the file tree and symbols as JSON
Usage:
    python scripts/index.py /path/to/repo
"""
import sys
import json
from kit import Repository

if __name__ == "__main__":
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    repo = Repository(repo_path)
    index = repo.index()
    print(json.dumps(index, indent=2))
