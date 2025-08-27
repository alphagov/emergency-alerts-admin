.DEFAULT_GOAL := help
SHELL := /bin/bash
TIME = $(shell date +%Y-%m-%dT%H:%M:%S%z)

# Passed through by Dockerfile/buildspec
APP_VERSION ?= unknown

GIT_BRANCH ?= $(shell git symbolic-ref --short HEAD 2> /dev/null || echo "detached")
GIT_COMMIT ?= $(shell git rev-parse HEAD 2> /dev/null || echo "")

BUCKET_NAME = ${BROADCAST_AREAS_BUCKET_NAME}

VIRTUALENV_ROOT := $(shell [ -z $$VIRTUAL_ENV ] && echo $$(pwd)/venv || echo $$VIRTUAL_ENV)
PYTHON_EXECUTABLE_PREFIX := $(shell test -d "$${VIRTUALENV_ROOT}" && echo "$${VIRTUALENV_ROOT}/bin/" || echo "")

## DEVELOPMENT
.PHONY: bootstrap
bootstrap: generate-version-file ## Set up everything to run the app
	${PYTHON_EXECUTABLE_PREFIX}pip3 install -r requirements_local_utils.txt
	npm ci --no-audit
	npm run build
	. environment.sh; ./scripts/get-broadcast-areas-db.sh ./app/broadcast_areas $(BUCKET_NAME)


.PHONY: bootstrap-for-tests
bootstrap-for-tests: generate-version-file ## Set up everything to run the tests
	${PYTHON_EXECUTABLE_PREFIX}pip3 install -r requirements_github_utils.txt
	npm ci --no-audit
	npm run build

.PHONY: watch-frontend
watch-frontend:  ## Build frontend and watch for changes
	. environment.sh; npm run watch

.PHONY: run-flask
run-flask:  ## Run flask
	. environment.sh && flask run -p 6012

.PHONY: npm-audit
npm-audit:  ## Check for vulnerabilities in NPM packages
	npm run audit

.PHONY: help
help:
	@cat $(MAKEFILE_LIST) | grep -E '^[a-zA-Z_-]+:.*?## .*$$' | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: virtualenv
virtualenv:
	[ -z $$VIRTUAL_ENV ] && [ ! -d venv ] && python3 -m venv venv || true

.PHONY: upgrade-pip
upgrade-pip: virtualenv
	${PYTHON_EXECUTABLE_PREFIX}pip3 install --upgrade pip

.PHONY: generate-version-file
generate-version-file: ## Generate the app/version.py file
	@ GIT_COMMIT=${GIT_COMMIT} TIME=${TIME} APP_VERSION=${APP_VERSION} envsubst < app/version.dist.py > app/version.py

.PHONY: test
test: ## Run tests
	flake8 .
	isort --check-only ./app ./tests
	black --check .
	npm test
	py.test -n auto --maxfail=10 tests/

.PHONY: fix-imports
fix-imports: ## Fix imports using isort
	isort ./app ./tests

.PHONY: freeze-requirements
freeze-requirements: ## create static requirements.txt
	${PYTHON_EXECUTABLE_PREFIX}pip3 install --upgrade setuptools pip-tools
	${PYTHON_EXECUTABLE_PREFIX}pip-compile requirements.in

.PHONY: bump-utils
bump-utils:  # Bump emergency-alerts-utils package to latest version
	${PYTHON_EXECUTABLE_PREFIX}python -c "from emergency-alerts-utils.version_tools import upgrade_version; upgrade_version()"

.PHONY: uninstall-packages
uninstall-packages:
	python -m pip uninstall emergency-alerts-utils -y
	python -m pip freeze | xargs python -m pip uninstall -y
