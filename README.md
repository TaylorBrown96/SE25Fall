# Food Delivery — Flask Backend

[![CI](https://img.shields.io/github/actions/workflow/status/TaylorBrown96/SE25Fall/ci.yml?branch=main)](https://github.com/TaylorBrown96/SE25Fall/actions)
[![Docs](https://img.shields.io/github/actions/workflow/status/TaylorBrown96/SE25Fall/docs.yml?label=docs)](https://github.com/TaylorBrown96/SE25Fall/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()

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
cd proj2
# Temporarily add current directory to Python path
$env:PYTHONPATH="." ; pdoc --docformat google --no-show-source -o site.
# View the documentation in your default browser
explorer .\site\index.html
```

### MacOS / Linux (Bash/Zsh)
```bash
cd proj2
# Temporarily add current directory to Python path
PYTHONPATH=. pdoc --docformat google --no-show-source -o site .
# View the documentation in your default browser
open ./site/index.html
```

The generated HTML files will be available in the `proj2/site` directory.
