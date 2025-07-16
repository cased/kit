#!/bin/bash
# This script runs Prettier (formatting), ESLint (linting), and TypeScript type checking for the TS client.
# Pass --fix as the first argument to automatically apply Prettier and ESLint fixes.

set -e

# Navigate to repo root
cd "$(dirname "$0")/.."

cd clients/typescript

# Ensure dependencies installed
if [ ! -d "node_modules" ]; then
  echo "Installing TypeScript client dependencies..."
  npm ci
fi

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
echo "Running TypeScript type check..."
npm run typecheck

echo "✅ TypeScript formatting, linting, and type checks passed!" 