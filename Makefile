.DEFAULT_GOAL := help
PYTHON        ?= python3
SRC           := src/plone_client
TESTS         := tests

# Python checks
UV?=uv

# installed?
ifeq (, $(shell which $(UV) ))
  $(error "UV=$(UV) not found in $(PATH)")
endif

BACKEND_FOLDER=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

VENV_FOLDER=$(BACKEND_FOLDER)/.venv
BIN_FOLDER=$(VENV_FOLDER)/bin

all: build

# Add the following 'help' target to your Makefile
# And add help text after each target name starting with '\#\#'
.PHONY: help
help: ## This help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

$(VENV_FOLDER): ## Install dependencies
	@echo "$(GREEN)==> Install environment$(RESET)"
	@uv sync

.PHONY: install
install: $(VENV_FOLDER) ## Install the project

.PHONY: clean
clean: ## Clean environment
	@echo "$(RED)==> Cleaning environment and build$(RESET)"
	rm -rf $(VENV_FOLDER) .python-version .ruff_cache .pytest_cache uv.lock

############################################
# QA
############################################
.PHONY: lint
lint: $(VENV_FOLDER) ## Check code base according to our standards
	@echo "$(GREEN)==> Lint codebase$(RESET)"
	@uvx ruff@latest check --fix --config $(BACKEND_FOLDER)/pyproject.toml
	@uvx pyroma@latest -d .
	@uvx check-python-versions@latest .
	@uv run mypy $(SRC)

.PHONY: format
format: $(VENV_FOLDER) ## Fix code base according to our standards
	@echo "$(GREEN)==> Format codebase$(RESET)"
	@uvx ruff@latest check --select I --fix --config $(BACKEND_FOLDER)/pyproject.toml
	@uvx ruff@latest format --config $(BACKEND_FOLDER)/pyproject.toml

.PHONY: check
check: format lint ## Check and fix code base according to Plone standards

############################################
# Tests
############################################
.PHONY: test
test: $(VENV_FOLDER) ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest

.PHONY: test-coverage
test-coverage: $(VENV_FOLDER) ## Test the code with pytest
	@echo "🚀 Testing code: Running pytest"
	@uv run pytest --cov=plone_client --cov-report term-missing

# ------------------------------------------------------------------
# Docs
# ------------------------------------------------------------------

docs:  ## Build Sphinx docs (requires docs/conf.py)
	$(MAKE) -C docs html
