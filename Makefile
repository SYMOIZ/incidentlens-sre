.PHONY: install test lint run cli docker-up docker-down

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest -q --cov=app --cov-report=term-missing

lint:
	python -m ruff check app tests
	python -m ruff format --check app tests

fmt:
	python -m ruff check --fix app tests
	python -m ruff format app tests

run:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

cli:
	python -m app.cli --help

docker-up:
	docker compose up --build -d

docker-down:
	docker compose down
