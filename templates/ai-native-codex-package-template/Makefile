PATH := $(HOME)/.local/bin:$(PATH)
VENV_BIN := .venv/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PYTEST := $(VENV_BIN)/pytest
VENV_RUFF := $(VENV_BIN)/ruff
VENV_MYPY := $(VENV_BIN)/mypy

.PHONY: help setup-env validate test lint typecheck

FOCUSED_TESTS := tests/test_ai_native_package_scaffold.py tests/test_task_goal.py tests/test_agent_telemetry_reader.py

help:
	@printf '%s\n' 'Targets: setup-env validate test lint typecheck'

setup-env:
	@if command -v uv >/dev/null 2>&1; then \
		uv sync --extra dev; \
	else \
		if [ ! -x "$(VENV_PYTHON)" ]; then python3 -m venv .venv; fi; \
		$(VENV_PYTHON) -m pip install -e ".[dev]"; \
	fi

validate:
	@$(MAKE) setup-env
	@PYTHONPATH=src $(VENV_PYTHON) -m ai_native_package --help
	@PYTHONPATH=src $(VENV_PYTHON) -m ai_native_package validate-doc-update-record --project-root .
	@PYTHONPATH=src $(VENV_PYTHON) -m ai_native_package validate-project-pack --project-root .
	@$(VENV_PYTEST) -q $(FOCUSED_TESTS)
	@$(VENV_RUFF) check .
	@$(VENV_MYPY) src

test:
	@$(MAKE) setup-env
	@$(VENV_PYTEST) -q $(FOCUSED_TESTS)

lint:
	@$(MAKE) setup-env
	@$(VENV_RUFF) check .

typecheck:
	@$(MAKE) setup-env
	@$(VENV_MYPY) src
