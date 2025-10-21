.PHONY: run export-openapi docs-serve docs-build docs-all test lint

run:
\tpython proj2/Flask_app.py

export-openapi:
\tcurl -s http://localhost:5000/apispec_1.json -o proj2/docs/api/openapi.json || (echo "Start the app first: make run" && false)

docs-serve:
\tmkdocs serve -a 0.0.0.0:8000

docs-build:
\tmkdocs build --clean

docs-all: export-openapi docs-build

lint:
\tpython -m pip install -q black isort
\tblack --check proj2
\tisort --check-only proj2

test:
\tpytest -q
