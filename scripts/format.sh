#!/bin/bash
# This script runs linting and formatting checks using Ruff.
# Pass --fix as the first argument to automatically apply fixes.

# Exit immediately if a command exits with a non-zero status.
set -e

# Navigate to the root of the repository relative to the script directory
cd "$(dirname "$0")/.."

# Check the first argument
if [ "$1" == "--fix" ]; then
  echo "Running Ruff to apply fixes (linting and formatting)..."
  # Apply lint rule fixes (autofixable ones)
  ruff check . --fix
  # Apply formatting fixes
  ruff format .
  echo "Ruff fixes applied successfully!"
else
  echo "Running Ruff linter and formatting check (no fixes applied)..."
  # Ruff check combines linting and format checking
  ruff check .
  echo "Ruff checks passed successfully!"
fi 