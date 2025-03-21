.PHONY: install lint test type-check format check-all

install:
	poetry install

lint:
	poetry run black . --check
	poetry run isort . --check-only

format:
	poetry run black .
	poetry run isort .

test:
	poetry run pytest tests/ -v

type-check:
	poetry run mypy gamefriend tests

check-all: lint test type-check 