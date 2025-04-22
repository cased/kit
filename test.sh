#!/bin/bash
# test.sh: Run all tests in the correct environment
set -e

# Ensure environment is set up
source $HOME/.venv/bin/activate 2>/dev/null || true
export KIT_TREE_SITTER_LIB="build/my-languages.so"

# Run tests with uv if available, else fallback to python
if command -v uv &> /dev/null; then
  uv run pytest -v tests
else
  python -m pytest -v tests
fi
