SHELL := /bin/bash

.PHONY: install format lint test migrate

install:
\tpip install -e ".[dev]"

format:
\truff format src tests

lint:
\truff check src tests

test:
\tpytest

migrate:
\tpython -m backend.scripts.migrate --help
