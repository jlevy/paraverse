# Makefile for easy development workflows. See README.md.

.DEFAULT_GOAL := default

# Use only the checked-in project configuration. Otherwise uv merges user- and
# system-level settings into uv.lock, which can make it fail on another machine.
UV_CONFIG_FILE := $(CURDIR)/uv.toml
export UV_CONFIG_FILE

# Safe default for every dependency resolution invoked through this Makefile.
UV_EXCLUDE_NEWER ?= 14 days
export UV_EXCLUDE_NEWER

.PHONY: default install lint lint-check test load serve upgrade clean

default: install lint test

install:
	uv sync --all-extras --all-groups

lint:
	uv run python devtools/lint.py

lint-check:
	uv run python devtools/lint.py --check

test:
	uv run pytest

load:
	uv run paraverse-graph load

serve:
	uv run paraverse-graph serve

upgrade:
	uv sync --upgrade --all-extras --all-groups

clean:
	-rm -rf dist/
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .venv/
	-rm -rf .data/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
