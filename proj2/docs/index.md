## How to Run (Local)

```bash
# terminal 1
cd SE25Fall
python -m venv venv && source venv/bin/activate
pip install -r <your-requirements-if-any>
pip install flask flasgger flask-wtf python-dotenv mkdocs mkdocs-material mkdocstrings mkdocstrings-python pymdown-extensions pytest
make run

# terminal 2 (export OpenAPI into docs)
make export-openapi

# terminal 3 (serve docs)
mkdocs serve
```