VENV ?= .venv
PY   := $(VENV)/bin

.PHONY: venv test lint format

venv:
	uv venv --python 3.14 $(VENV)
	uv pip install --python $(VENV) -r requirements_test.txt

test:
	$(PY)/pytest -q

lint:
	$(PY)/ruff check .
	$(PY)/ruff format --check .

format:
	$(PY)/ruff check --fix .
	$(PY)/ruff format .
