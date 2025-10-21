.PHONY: run export-openapi docs-serve docs-build docs-all test lint

run:
	python proj2/Flask_app.py

export-openapi:
	curl -s http://localhost:5000/apispec_1.json -o proj2/docs/api/openapi.json || (echo "Start the app first: make run" && false)

docs-serve:
	mkdocs serve -a 0.0.0.0:8000

docs-build:
	mkdocs build --clean

docs-all: export-openapi docs-build

lint:
	python -m pip install -q black isort
	black --check proj2
	isort --check-only proj2

test:
	pytest -q
