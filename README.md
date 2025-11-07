# Food Delivery — Flask Backend
[![CI](https://github.com/TaylorBrown96/SE25Fall/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/TaylorBrown96/SE25Fall/actions/workflows/ci.yml)
[![Docs](https://github.com/TaylorBrown96/SE25Fall/actions/workflows/docs.yml/badge.svg?branch=main&event=push)](https://github.com/TaylorBrown96/SE25Fall/actions/workflows/docs.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)]()
![Tests](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/TaylorBrown96/0c223cf33bf0cc9b91667676c415aafa/raw/tests-badge.json)
[![codecov](https://codecov.io/gh/TaylorBrown96/SE25Fall/branch/main/graph/badge.svg)](https://codecov.io/gh/TaylorBrown96/SE25Fall)
[![Flask](https://img.shields.io/badge/Flask-2.x-lightgrey?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/github/license/TaylorBrown96/SE25Fall.svg)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/TaylorBrown96/SE25Fall.svg)](https://github.com/TaylorBrown96/SE25Fall/commits)
[![GitHub issues](https://img.shields.io/github/issues/TaylorBrown96/SE25Fall.svg)](https://github.com/TaylorBrown96/SE25Fall/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/TaylorBrown96/SE25Fall.svg)](https://github.com/TaylorBrown96/SE25Fall/pulls)
[![Repo Size](https://img.shields.io/github/repo-size/TaylorBrown96/SE25Fall.svg)](https://github.com/TaylorBrown96/SE25Fall)
[![Contributors](https://img.shields.io/github/contributors/TaylorBrown96/SE25Fall.svg)](https://github.com/TaylorBrown96/SE25Fall/graphs/contributors)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Lint: ruff](https://img.shields.io/badge/lint-ruff-46a2f1?logo=ruff&logoColor=white)](https://github.com/astral-sh/ruff)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.xxxxx.svg)](https://doi.org/10.5281/zenodo.xxxxx)
---

## ⚙️Installation

### Windows (PowerShell)
```powershell
# 1) Clone
git clone https://github.com/<TaylorBrown96>/<SE25Fall>.git
cd <SE25Fall>/proj2

# 2) Create & activate a venv
py -3 -m venv .venv

# If activation is blocked, either:
# a) temporary bypass: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# b) or use CMD activation script: .venv\Scripts\activate.bat
. .\.venv\Scripts\Activate.ps1

# 3) Install packages
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### MacOS / Linux (Bash/Zsh)
```bash
# 1) Clone the repository
git clone https://github.com/<TaylorBrown96>/<SE25Fall>.git
cd <SE25Fall>/proj2

# 2) Create & activate a venv
python3 -m venv .venv
source .venv/bin/activate

# 3) Install packages
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 🚀Usage

### Running the Application
Once dependencies are installed and the virtual environment is activated, you can run the Flask server:

### Windows (PowerShell)
```powershell
# Set the application entry point
$env:FLASK_APP = "Flask_app.py"

# Start the development server
python -m flask run
```

### MacOS / Linux (Bash/Zsh)
```bash
# Set the application entry point
export FLASK_APP="Flask_app.py"

# Start the development server
python -m flask run
```

### Running Tests
Execute unit tests using pytest:
```bash
# For full information run:
pytest
# Add a '-q'(quiet) flag to show concise, easy-to-read output (dots for passes, 'F' for failures):
pytest -q
```

## 📚Documentation

### _Documentation is generated using pdoc._
Documentation is automatically generated using pdoc and deployed to GitHub Pages whenever new changes are merged into the `main` branch.

### 🧩 Automated Docs
* CI/CD workflow (`docs.yml`) builds and publishes docs from `proj2/` to the `gh-pages` branch.

* Live documentation becomes available at the GitHub Pages link after each successful merge.

* Source code is hidden; only public functions, classes, and docstrings are shown.

### 🖥️ Build Docs Locally
You can also generate and preview the documentation manually:
### Windows (PowerShell)
```powershell
# Temporarily add current directory to Python path
$env:PYTHONPATH="." ;
pdoc proj2 --no-show-source --template-dir proj2\pdoc_templates -o proj2\site
python .\scripts\build_docs.py
# View the documentation in your default browser
start proj2\site\index.html
```

### MacOS / Linux (Bash/Zsh)
```bash
# Temporarily add current directory to Python path
export PYTHONPATH="."
pdoc proj2 --no-show-source --template-dir proj2/pdoc_templates -o proj2/site
python ./scripts/build_docs.py
# View the documentation in your default browser
open proj2/site/index.html
```

The generated HTML files will be available in the `proj2/site` directory.
