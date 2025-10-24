# Food Delivery — Flask Backend

[![CI](https://img.shields.io/github/actions/workflow/status/<TaylorBrown96>/<SE25Fall>/ci.yml?branch=main)](https://github.com/<TaylorBrown96>/<SE25Fall>/actions)
[![Docs](https://img.shields.io/github/actions/workflow/status/<TaylorBrown96>/<SE25Fall>/docs.yml?label=docs)](https://github.com/<TaylorBrown96>/<SE25Fall>/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()

---

## ⚙️Installation

### Windows (PowerShell)
```powershell
# 1) Clone
git clone https://github.com/<TaylorBrown96>/<SE25Fall>.git
cd <SE25Fall>

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
cd <SE25Fall>

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
```bash
Set the application entry point
$env:FLASK_APP = "Flask_app.py"

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

### _Documentation is generated using pdoc and includes modules Flask_app and sqlQueries._
To build the documentation locally:

### Windows (PowerShell)
```powershell
# Temporarily add current directory to Python path
$env:PYTHONPATH="." ; pdoc --docformat google -o site Flask_app sqlQueries
```

### MacOS / Linux (Bash/Zsh)
```bash
# Temporarily add current directory to Python path
PYTHONPATH=. pdoc --docformat google -o site Flask_app sqlQueries
```

The generated HTML files will be available in the ./site directory.
