#!/bin/bash
# Ensure all deps (including vector search) are installed, then run tests

export PYTHONPATH=src
uv run pytest --cov=src/kit --cov-report=term-missing "$@"
