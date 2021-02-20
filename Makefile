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

lint: ## This checks python files modified by you.
	{ git diff --name-only; git ls-files --others --exclude-standard; git diff --cached --name-only; } | xargs pre-commit run --files

lint-all: ## This checks all python files in the repository
	pre-commit run -a

format: ## This formats all changed python files.
	-{ git diff --name-only; git ls-files --others --exclude-standard; git diff --cached --name-only; } | xargs pre-commit run --hook-stage manual isort-edit --files
	-{ git diff --name-only; git ls-files --others --exclude-standard; git diff --cached --name-only; } | xargs pre-commit run --hook-stage manual black-edit --files

format-all: ## This formats all python files in the repository
	-pre-commit run -a --hook-stage manual isort-edit
	-pre-commit run -a --hook-stage manual black-edit

build-docker-image: ## build docker image
	make -C kelvin-api clean
	(cd docker && ./build_docker_image)

tests: ## run tests in ucs-school-lib and kelvin-api
	python3 -m pytest -l -v ucs-school-lib/modules/ucsschool/lib/tests/ kelvin-api/tests/
