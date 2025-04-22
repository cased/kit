#!/bin/bash
# Run mypy type checks for all source and test code
export PYTHONPATH=src
mypy src/kit
mypy tests
