# Makefile for easy development workflows. See README.md.

.DEFAULT_GOAL := default

# Use only the checked-in project configuration. Otherwise uv merges user- and
# system-level settings into uv.lock, which can make it fail on another machine.
UV_CONFIG_FILE := $(CURDIR)/uv.toml
export UV_CONFIG_FILE

# Safe default for every dependency resolution invoked through this Makefile.
UV_EXCLUDE_NEWER ?= 14 days
export UV_EXCLUDE_NEWER

# The dataset `load`, `validate` and `serve` use: DATASET=<name> for the KB at
# ../vendor/<name>/kb, or KB=<dir> for any KB directory (relative to db/). The
# default is the universe2026-md submodule.
DATASET ?=
KB ?=
DATASET_ARGS = $(if $(KB),--kb '$(KB)') $(if $(DATASET),--dataset '$(DATASET)')

.PHONY: default install lint lint-check test check validate load serve datasets upgrade clean

default: install lint test

install:
	uv sync --all-extras --all-groups

lint:
	uv run python devtools/lint.py

lint-check:
	uv run python devtools/lint.py --check

test:
	uv run pytest

# Everything a CI job should run, without modifying files: lint, types and tests.
check: lint-check test

# Validate every KB artifact with softschema, then load (slower than `make load`).
validate:
	uv run paraverse-graph load --validate $(DATASET_ARGS)

load:
	uv run paraverse-graph load $(DATASET_ARGS)

serve:
	uv run paraverse-graph serve $(DATASET_ARGS)

datasets:
	uv run paraverse-graph datasets

upgrade:
	uv sync --upgrade --all-extras --all-groups

clean:
	-rm -rf dist/
	-rm -rf .pytest_cache/
	-rm -rf .ruff_cache/
	-rm -rf .venv/
	-rm -rf .data/
	-find . -type d -name "__pycache__" -exec rm -rf {} +
