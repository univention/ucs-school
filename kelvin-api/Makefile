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

PY_FILES := setup.py ucsschool/

help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

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
	isort --apply --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --force-alphabetical-sort-within-sections --recursive $(PY_FILES)
	black  $(PY_FILES)

lint: ## check source code style
	isort --check-only --multi-line=3 --trailing-comma --force-grid-wrap=0 --combine-as --line-width 88 --force-alphabetical-sort-within-sections --recursive $(PY_FILES)
	black --check $(PY_FILES)
	flake8 --max-line-length=90 $(PY_FILES) || echo "Ignored for now - lots of stubs"

test: ## run tests quickly with the default Python
	python -m pytest

coverage-html: test ## check code coverage, create HTML report and show in browser
	coverage html
	$(BROWSER) htmlcov/index.html

dist: clean ## builds source and wheel package
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist

install: clean ## install the package to the active Python's site-packages
	python setup.py install

build-docker-image: clean ## build docker image
	(cd ../docker && ./build_docker_image)
