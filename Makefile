### Defensive settings for make:
#     https://tech.davis-hansson.com/p/make/
SHELL:=bash
.SHELLFLAGS:=-eu -o pipefail -c
.SILENT:
.DELETE_ON_ERROR:
MAKEFLAGS+=--warn-undefined-variables
MAKEFLAGS+=--no-builtin-rules

.DEFAULT_GOAL := help

SRC := src/plone_client
UV ?= uv

# installed?
ifeq (, $(shell which $(UV) ))
  $(error "UV=$(UV) not found in $(PATH)")
endif

GREEN=\033[0;32m
RED=\033[0;31m
RESET=\033[0m

.PHONY: help
help: ## This help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.venv/bin/python: pyproject.toml
	@echo -e "$(GREEN)==> Install environment$(RESET)"
	@$(UV) sync --all-extras
	@touch .venv/bin/python

.PHONY: install
install: .venv/bin/python ## Install the library, the command line and the development tools

.PHONY: clean
clean: ## Remove the environment and generated files
	@echo -e "$(RED)==> Cleaning environment and build$(RESET)"
	rm -rf .venv .ruff_cache .pytest_cache .mypy_cache .coverage dist docs/_build

############################################
# QA
############################################
.PHONY: format
format: install ## Format the code base
	@echo -e "$(GREEN)==> Format codebase$(RESET)"
	@uvx ruff@latest check --select I --fix --config pyproject.toml src tests
	@uvx ruff@latest format --config pyproject.toml src tests

.PHONY: lint
lint: install ## Check the code base; changes nothing
	@echo -e "$(GREEN)==> Lint codebase$(RESET)"
	@uvx ruff@latest check --no-fix --config pyproject.toml src tests
	@uvx ruff@latest format --check --config pyproject.toml src tests
	@uvx pyroma@latest -d .
	@uvx check-python-versions@latest .
	@$(UV) run mypy $(SRC)

.PHONY: check
check: format lint ## Format, then check the code base

############################################
# Tests
############################################
.PHONY: test
test: install ## Run the unit tests
	@echo -e "$(GREEN)==> Unit tests$(RESET)"
	@$(UV) run pytest

.PHONY: test-coverage
test-coverage: install ## Run the unit tests with a coverage report
	@$(UV) run pytest --cov=plone_client --cov-report=term-missing

.PHONY: test-integration
test-integration: install ## Run the integration tests against Plone in Docker (PLONE_IMAGE=…)
	@echo -e "$(GREEN)==> Integration tests$(RESET)"
	@$(UV) run pytest -m integration tests/integration

############################################
# Docs and changelog
############################################
.PHONY: docs
docs: ## Build the documentation
	@$(UV) run --group docs sphinx-build -W -b html docs docs/_build/html

.PHONY: changelog
changelog: ## Preview the next change log entry
	@uvx towncrier build --draft --version=next
