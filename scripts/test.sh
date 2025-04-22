#!/bin/bash
# Ensure all deps (including vector search) are installed, then run tests
uv pip install .[vector] >/dev/null
export PYTHONPATH=src
python -m pytest "$@"
