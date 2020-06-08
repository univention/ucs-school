.PHONY: help format lint setup_devel_env
.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

setup_devel_env: ## setup development environment (virtualenv)
	@if [ -d venv ]; then \
		echo "Directory 'venv' exists."; \
	else \
		python3 -m venv venv && \
		. venv/bin/activate && \
		python3 -m pip install -U pip && \
		python3 -m pip install black==19.10b0 && \
		pre-commit install && \
		echo "==> Run '. venv/bin/activate' to activate virtual env."; \
		echo "==> Run 'pre-commit run -a' to execute pre-commit hooks manually."; \
	fi

lint: ## Needs the virtualenv to be activated!
	black --config .black --check .

format: ## Needs the virtualenv to be activated!
	black --config .black .