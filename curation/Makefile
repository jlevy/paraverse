# Makefile for curation lists. See README.md.

.DEFAULT_GOAL := default

# Use only the checked-in project configuration. Otherwise uv merges user- and
# system-level settings into uv.lock, which can make it fail on another machine.
UV_CONFIG_FILE := $(CURDIR)/uv.toml
export UV_CONFIG_FILE

# Safe default for every dependency resolution invoked through this Makefile.
UV_EXCLUDE_NEWER ?= 14 days
export UV_EXCLUDE_NEWER

# The dataset `build` checks its header-only list, then rebuilds the existing saved
# inputs with the pipeline at ../vendor/<dataset>/pipeline.
DATASET ?= universe2026-md
export DATASET

SRC_PATHS := src tests

.PHONY: default install lint lint-check test check build upgrade clean

default: install lint test check

install:
	uv sync --all-groups

lint:
	uv run codespell --write-changes $(SRC_PATHS) README.md
	uv run ruff check --fix $(SRC_PATHS)
	uv run ruff format $(SRC_PATHS)
	uv run basedpyright --stats $(SRC_PATHS)

lint-check:
	uv run codespell $(SRC_PATHS) README.md
	uv run ruff check $(SRC_PATHS)
	uv run ruff format --check $(SRC_PATHS)
	uv run basedpyright --stats $(SRC_PATHS)

test:
	uv run pytest

# Check every list under this directory against the format and the data policy.
check:
	uv run paraverse-curation check

# Check the lists, then rebuild DATASET with its own pipeline if the selected list is empty.
build: check
	uv run paraverse-curation build --dataset "$$DATASET"

upgrade:
	uv sync --upgrade --all-groups

clean:
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .venv/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
