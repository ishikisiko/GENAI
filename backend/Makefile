SHELL := /bin/bash

.PHONY: install format lint test test-integration migrate

install:
\tpip install -e ".[dev]"

format:
\truff format src tests

lint:
\truff check src tests

test:
\tpytest

test-integration:
\tRUN_BACKEND_INTEGRATION=1 pytest -m integration tests/integration

migrate:
\tpython -m backend.scripts.migrate --help
