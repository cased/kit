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
  # Apply lint rule fixes (autofixable ones, including unsafe fixes)
  uv run ruff check . --fix --unsafe-fixes
  # Apply formatting fixes
  uv run ruff format .
  echo "Ruff fixes applied successfully!"
else
  echo "Running Ruff linter and formatting check (no fixes applied)..."
  # Ruff check combines linting and format checking
  uv run ruff check .
  echo "Ruff checks passed successfully!"
fi

# -----------------------------------------------------------------------------
# TypeScript Client formatting, linting, and type-checking
# -----------------------------------------------------------------------------

echo "----------------------------------------------"
echo "TypeScript client checks (clients/typescript)"
echo "----------------------------------------------"

# Navigate to TypeScript client directory
pushd clients/typescript > /dev/null

# Install dependencies if node_modules missing
if [ ! -d "node_modules" ]; then
  echo "Installing TypeScript client dependencies..."
  npm ci
fi

# Run Prettier and ESLint
if [ "$1" == "--fix" ]; then
  echo "Running Prettier (write)..."
  npm run format:fix
  echo "Running ESLint with --fix..."
  npm run lint -- --fix
else
  echo "Running Prettier (check)..."
  npm run format
  echo "Running ESLint..."
  npm run lint
fi

# TypeScript type check
echo "Running TypeScript type check (tsc --noEmit)..."
npm run typecheck

popd > /dev/null

echo "✅ All Python & TypeScript formatting and lint checks passed!" 