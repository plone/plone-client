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
CODE := src tests docs/_examples
UV ?= uv

DOCS_DIR := docs
DOCS_BUILDDIR := $(DOCS_DIR)/_build
DOCS_SPHINXOPTS ?=
DOCS_VALEOPTS ?=
DOCS_VALEFILES = $(shell find $(DOCS_DIR) -type f -name "*.md" -not -path "$(DOCS_BUILDDIR)/*" -not -path "$(DOCS_DIR)/_styles/*" -print)

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
	@uvx ruff@latest check --select I --fix --config pyproject.toml $(CODE)
	@uvx ruff@latest format --config pyproject.toml $(CODE)

.PHONY: lint
lint: install ## Check the code base; changes nothing
	@echo -e "$(GREEN)==> Lint codebase$(RESET)"
	@uvx ruff@latest check --no-fix --config pyproject.toml $(CODE)
	@uvx ruff@latest format --check --config pyproject.toml $(CODE)
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
docs: ## Build the documentation (warnings are errors)
	@echo -e "$(GREEN)==> Build documentation$(RESET)"
	@$(UV) run --all-extras --group docs sphinx-build -W --keep-going -b html $(DOCS_DIR) "$(DOCS_BUILDDIR)/html" $(DOCS_SPHINXOPTS)

.PHONY: docs-livehtml
docs-livehtml: ## Rebuild the documentation on changes, with live reload in the browser
	@$(UV) run --all-extras --group docs sphinx-autobuild --ignore "*.swp" --port 8050 \
		-b html $(DOCS_DIR) "$(DOCS_BUILDDIR)/html" $(DOCS_SPHINXOPTS)

.PHONY: docs-linkcheck
docs-linkcheck: ## Check that all links in the documentation resolve
	@echo -e "$(GREEN)==> Check documentation links$(RESET)"
	@$(UV) run --all-extras --group docs sphinx-build -b linkcheck $(DOCS_DIR) "$(DOCS_BUILDDIR)/linkcheck"

.PHONY: docs-vale
docs-vale: ## Check the documentation with Vale
	@echo -e "$(GREEN)==> Check documentation with Vale$(RESET)"
	@$(UV) run --group docs vale sync
	@$(UV) run --group docs vale --no-wrap $(DOCS_VALEOPTS) $(DOCS_VALEFILES)

.PHONY: docs-clean
docs-clean: ## Remove the built documentation
	@echo -e "$(RED)==> Clean documentation$(RESET)"
	@rm -rf "$(DOCS_BUILDDIR)"

.PHONY: changelog
changelog: ## Preview the next change log entry
	@uvx towncrier build --draft --version=next

############################################
# Release
############################################
.PHONY: release
release: install ## Release the package to pypi.org
	@echo -e "$(GREEN)==> Release package$(RESET)"
	@$(UV) run --group release prerelease
	@$(UV) run --group release release
	@rm -Rf dist
	@$(UV) build
	@$(UV) publish
	@$(UV) run --group release postrelease
