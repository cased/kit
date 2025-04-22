# Makefile for kit project
# Usage:
#   make setup   # Clone grammars, build .so, install deps, set env
#   make test    # Run all tests

setup:
	bash init.sh

test:
	bash test.sh

.PHONY: setup test
