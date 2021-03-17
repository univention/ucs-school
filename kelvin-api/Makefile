.PHONY: clean clean-test clean-pyc clean-build docs help
.DEFAULT_GOAL := help

define BROWSER_PYSCRIPT
import os, webbrowser, sys

try:
	from urllib import pathname2url
except:
	from urllib.request import pathname2url

webbrowser.open("file://" + pathname2url(os.path.abspath(sys.argv[1])))
endef
export BROWSER_PYSCRIPT

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

BROWSER := python -c "$$BROWSER_PYSCRIPT"

PY_MODULES := tests ucsschool
PY_PATHS := setup.py $(PY_MODULES)
PY_FILES := $(shell find $(PY_PATHS) -name '*.py')

help:
	@python3 -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

format: ## format source code
	make -C .. format

linters:  ## run isort, black, flake8 etc
	@if [ -e ../Makefile ]; then \
  		# running in dev env (git repo) \
  		make -C .. lint; \
	else \
	  	# running in Docker image build \
		isort --sp .isort.cfg --check-only $(PY_PATHS) && \
	  	echo "==> isort ok" && \
		black --config .black --check $(PY_PATHS) && \
		echo "==> black ok" && \
		flake8 --config .flake8 $(PY_PATHS) && \
		echo "==> flake8 ok"; \
	fi

lint-coverage: .coverage
	coverage report --show-missing --fail-under=30

lint: linters lint-coverage ## check source code style

pytest: ## run pytests (with the current active Python interpreter)
	python3 -m pytest -l -v

opatest: ## run opa test on opa policies
	opa test opa_policies

test: pytest opatest

.coverage: $(PY_FILES)
	coverage run --source tests,ucsschool -m pytest

coverage: .coverage ## check code coverage with the current Python interpreter
	coverage report --show-missing $(MY_COVERAGE_REPORT_ARGS)

coverage-html: coverage ## check code coverage, create HTML report and show in browser
	coverage html
	$(BROWSER) htmlcov/index.html

dist: clean ## builds source and wheel package
	python3 setup.py sdist
	python3 setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python3 -m pip install -e .

build-docker-image: clean ## build docker image
	(cd ../docker && ./build_docker_image)
