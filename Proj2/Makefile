.PHONY: run lint fmt type test cov all

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

lint:
	ruff check .
	black --check .

fmt:
	black .

type:
	mypy app

test:
	pytest -q

cov:
	pytest -q --cov=app --cov-report=term-missing

all: lint type cov